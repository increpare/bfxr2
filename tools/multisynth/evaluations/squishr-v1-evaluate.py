"""Compare shared and independent Squishr heads on frozen exact audio."""
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.audio import prepare_target
from match.objective import MatchObjective
from multisynth.coverage import verify_archived_audio
from multisynth.renderer import Renderer
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import read_wave, write_wave
from neural_invert.data import file_hash, _json_write, verify_dataset_files
from neural_invert.evaluate import rendered_candidates, refine_candidate, serializable
from neural_invert.experiment import audition_pcm
from neural_invert.predict import load_model, predict
from neural_invert.schema import ControlSchema

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/squishr-v1'
OUT = ROOT/'evaluation'
PROTOCOL = BASE/'evaluations/squishr-v1-protocol.json'
ARMS = ('shared', 'specialist')


class SoftAudition(SoftPeriodicityObjective):
    def score_batch(self, waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])


def main():
    torch.set_num_threads(1)
    protocol = json.loads(PROTOCOL.read_text())
    frozen = json.loads((ROOT/'targets.json').read_text())
    receipt = json.loads((ROOT/'training-receipt.json').read_text())
    assert receipt['complete'] and receipt['protocolSha256']==file_hash(PROTOCOL)
    assert receipt['targetsSha256']==file_hash(ROOT/'targets.json')
    assert receipt['checkpointSha256']==file_hash(ROOT/'model/best.pt')
    assert receipt['trainingSha256']==file_hash(ROOT/'model/training.json')
    assert frozen['protocolSha256']==file_hash(PROTOCOL)
    for path, checksum in protocol['codeHashes'].items():
        assert file_hash(path)==checksum, path
    training = json.loads((ROOT/'model/training.json').read_text())
    saved = torch.load(ROOT/'model/best.pt',map_location='cpu',weights_only=True)
    assert training['epochs']==60 and len(training['history'])==60
    assert training['metadata']==saved['metadata']
    assert training['bestValidationLoss']==saved['validationLoss']==min(r['validationLoss'] for r in training['history'])
    assert training['checkpointHash']==file_hash(ROOT/'model/best.pt')
    assert file_hash(ROOT/'fit-data/manifest.json')==frozen['fitManifestSha256']
    verify_dataset_files(ROOT/'fit-data',json.loads((ROOT/'fit-data/manifest.json').read_text()))
    meta = json.loads((ROOT/'fit-data/Squishr.json').read_text())
    schema = ControlSchema(meta['spec'])
    def controls(params):
        unit, cat = schema.encode(params)
        return tuple(unit.tolist()),tuple(cat.tolist())
    excluded = {controls(meta['rows'][i]['params']) for i in meta['train']+meta['val']}
    models = {'shared':load_model(Path(protocol['sharedCheckpoint']).parent),'specialist':load_model(ROOT/'model')}
    assert models['shared'][1]['checkpointHash']==protocol['sharedCheckpointSha256']
    assert models['specialist'][1]['checkpointHash']==receipt['checkpointSha256']
    binding = dict(scriptSha256=file_hash(__file__),protocolSha256=file_hash(PROTOCOL),
        targetsSha256=file_hash(ROOT/'targets.json'),trainingReceiptSha256=file_hash(ROOT/'training-receipt.json'),
        checkpoints={k:m[1]['checkpointHash'] for k,m in models.items()})
    OUT.mkdir(exist_ok=True)
    if (OUT/'binding.json').exists():
        assert json.loads((OUT/'binding.json').read_text())==binding
    else:
        _json_write(OUT/'binding.json',binding)
    rows = []
    with Renderer() as renderer:
        source_hash = renderer.inventory['sourceHash']
        for index, target in enumerate(frozen['tagged']+frozen['native']):
            dest = OUT/f'{index+1:03d}'
            if (dest/'result.json').exists():
                row = json.loads((dest/'result.json').read_text())
                assert row['complete'] and row['target']==target and row['binding']==binding
                assert row['sourceHash']==source_hash
                reference = read_wave(row['reference'])
                soft_check, legacy_check = SoftPeriodicityObjective(reference), MatchObjective(reference)
                for arm in ARMS:
                    for c in row['arms'][arm]['raw']+[row['arms'][arm]['refined']]:
                        wave = read_wave(c)
                        exact_replay({**c,'wave':wave},renderer,None)
                        heard = audition_pcm(wave)
                        assert audio_hash(heard)==c['auditionHash']
                        assert abs(soft_check.score(heard)-c['score'])<1e-6
                        assert abs(legacy_check.score(heard)-c['legacyScore'])<1e-6
                rows.append(row)
                continue
            dest.mkdir()
            started = time.monotonic()
            if target['group']=='native-test':
                assert target['sourceRow'] in meta['test']
                assert controls(target['sourceParams']) not in excluded
                params, raw = renderer.render('Squishr',target['sourceParams'],target['sourceSeed'])
                assert params==target['sourceParams'] and audio_hash(raw)==target['sourceAudioHash']
                reference = audition_pcm(raw)
            elif 'referenceArchive' in target:
                archive = Path(target['referenceArchive'])
                assert file_hash(archive/'manifest.json')==target['archiveManifestSha256']
                verify_archived_audio(archive,target['referenceAudio'])
                reference,sr = sf.read(archive/target['referenceAudio']['file'],dtype='float32')
                assert sr==44100 and audio_hash(reference)==target['auditionHash']
            else:
                assert file_hash(target['source']['path'])==target['source']['sha256']
                reference = audition_pcm(prepare_target(target['source']['path']))
                assert audio_hash(reference)==target['auditionHash']
            ref_info = write_wave(dest/'reference-float.wav',reference)
            sf.write(dest/'reference.wav',reference,44100,subtype='PCM_16')
            check,sr = sf.read(dest/'reference.wav',dtype='float32')
            assert sr==44100 and np.array_equal(check,reference)
            objective, legacy = SoftAudition(reference), MatchObjective(reference)
            def save(candidate, filename):
                exact_replay(candidate,renderer,None)
                heard = audition_pcm(candidate['wave'])
                assert abs(objective.score_batch([candidate['wave']])[0]-candidate['score'])<1e-6
                return serializable({**candidate,**write_wave(dest/filename,candidate['wave']),
                    'sourceHash':source_hash,'auditionHash':audio_hash(heard),'legacyScore':float(legacy.score(heard)),
                    'provenance':{**candidate['provenance'],'evaluationBinding':binding,
                        'inputPcmHash':audio_hash(reference),'selector':'SoftPeriodicityObjective'}})
            arms, failures = {}, []
            for arm in ARMS:
                model, metadata = models[arm]
                proposed = [{**c,'origin':arm} for c in predict(model,{**metadata,'engines':['Squishr']},reference,renderer,
                    per_synth=protocol['evaluation']['proposalsPerArm'])]
                accepted, bad = rendered_candidates(proposed,renderer,objective)
                failures.extend([dict(arm=arm,**b) for b in bad])
                assert accepted, f'No valid proposal for {arm} / {target["id"]}'
                raw = [save(c,f'{arm}-raw-{i}.wav') for i,c in enumerate(accepted)]
                initial = min(accepted,key=lambda c:c['score'])
                refined = refine_candidate(initial,renderer,objective,protocol['evaluation']['refinementBudgetPerArm'],
                    protocol['evaluation']['searchSeed']+index*1009)
                assert refined['score']<=initial['score']+1e-7
                arms[arm] = dict(proposedCount=len(proposed), validCount=len(accepted), raw=raw,
                    selectedRaw=min(raw,key=lambda c:c['score']), refined=save(refined,arm+'-refined.wav'))
            assert arms['shared']['proposedCount']==arms['specialist']['proposedCount']
            row = dict(complete=True,target=target,reference=ref_info,arms=arms,failures=failures,
                seconds=time.monotonic()-started,binding=binding,sourceHash=source_hash,folder=dest.name)
            _json_write(dest/'result.json',row)
            rows.append(row)
            print(json.dumps(dict(done=index+1,total=37,target=target['id'],seconds=round(row['seconds'],1),
                scores={a:{s:round(arms[a][s]['score'],4) for s in ('selectedRaw','refined')} for a in ARMS})),flush=True)
    assert len(rows)==37
    summary = {}
    for group in ('native-test','tagged-new','tagged-repeated'):
        group_rows = [r for r in rows if r['target']['group']==group]
        summary[group] = dict(count=len(group_rows))
        for stage in ('selectedRaw','refined'):
            summary[group][stage] = dict(
                meanSoft={a:float(np.mean([r['arms'][a][stage]['score'] for r in group_rows])) for a in ARMS},
                meanLegacy={a:float(np.mean([r['arms'][a][stage]['legacyScore'] for r in group_rows])) for a in ARMS},
                specialistLowerSoft=sum(r['arms']['specialist'][stage]['score']<r['arms']['shared'][stage]['score'] for r in group_rows))
    result = dict(complete=True,binding=binding,rows=rows,summary=summary,sourceHash=source_hash,
        mutationAttempts=37*2*protocol['evaluation']['refinementBudgetPerArm'],scope=protocol['scope'])
    _json_write(OUT/'results.json',result)
    _json_write(BASE/'evaluations/squishr-v1-evaluation.json',dict(complete=True,binding=binding,summary=summary,
        reportSha256=file_hash(OUT/'results.json'),targets=37,mutationAttempts=result['mutationAttempts'],
        splitCounts=frozen['splitCounts'],scope=protocol['scope'],failures=sum(len(r['failures']) for r in rows)))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()
