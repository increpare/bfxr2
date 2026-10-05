"""Render new specialists on fixed native, cross-engine and tagged references."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.coverage import verify_archived_audio
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture import load as load_mixture
from neural_invert.coverage_mixture_eval import read_wave, write_wave
from neural_invert.data import file_hash, _json_write, parameter_hash
from neural_invert.experiment import audition_pcm
from neural_invert.predict import load_model, predict
from neural_invert.schema import ControlSchema
from neural_invert.temporal import predict_temporal

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/specialists-v1'
OUT = ROOT/'evaluation'
PLAN = BASE/'evaluations/specialists-v1-plan.json'
POLICY = BASE/'evaluations/specialists-v1-evaluation-policy.json'
ARMS = ('Transfxr','old-Boomr','old-Footsteppr','Boomr','Footsteppr')
PRIOR = BASE/'runs/native-mixture-input-stability-v1/results.json'
BOOK = BASE/'listening_data/2026-10-04-temporal-v3-quick-01'


def main():
    if OUT.exists():
        raise FileExistsError('Fresh evaluation required')
    torch.set_num_threads(1)
    plan = json.loads(PLAN.read_text())
    policy = json.loads(POLICY.read_text())
    assert policy['planSha256']==file_hash(PLAN)
    shared_path = Path(policy['sharedModelPath'])
    assert file_hash(shared_path/'best.pt')==policy['checkpointSha256']
    assert file_hash(shared_path/'training.json')==policy['trainingSha256']
    shared, shared_meta = load_model(shared_path)
    receipt = json.loads((ROOT/'training-receipt.json').read_text())
    frozen = json.loads((ROOT/'targets.json').read_text())
    assert receipt['complete'] and receipt['planSha256']==file_hash(PLAN)
    assert receipt['targetsSha256']==file_hash(ROOT/'targets.json')
    prior = json.loads(PRIOR.read_text())
    assert prior['complete'] and len(prior['rows'])==122
    trained, training_controls, numeric_controls, schemas, fitted_metas = {}, {}, {}, {}, {}
    for name in plan['engines']:
        path = ROOT/'models'/name
        assert receipt['models'][name]['checkpointSha256']==file_hash(path/'best.pt')
        assert receipt['models'][name]['trainingSha256']==file_hash(path/'training.json')
        report = json.loads((path/'training.json').read_text())
        saved = torch.load(path/'best.pt', map_location='cpu', weights_only=True)
        assert report['epochs']==90 and len(report['history'])==90 and report['metadata']==saved['metadata']
        assert report['checkpointHash']==file_hash(path/'best.pt')
        assert report['bestValidationLoss']==saved['validationLoss']==min(r['validationLoss'] for r in report['history'])
        trained[name] = load_model(path)
        data = Path(frozen['datasets'][name]['path'])
        assert file_hash(data/'manifest.json')==frozen['datasets'][name]['manifestSha256']
        meta = json.loads((data/(name+'.json')).read_text())
        fitted_metas[name] = meta
        training_controls[name] = {meta['rows'][i]['parameterHash'] for i in meta['train']}
        schemas[name] = ControlSchema(meta['spec'])
        def encoded(params):
            unit, cat = schemas[name].encode(params)
            return (tuple(unit.tolist()), tuple(cat.tolist()))
        numeric_controls[name] = {encoded(meta['rows'][i]['params']) for i in meta['train']}
    mixture = load_mixture(BASE/'runs/native-mixture-v1/models/mixture')
    assert mixture[1]['checkpointHash']==prior['checkpointSha256']
    book = json.loads((BOOK/'manifest.json').read_text())
    book_target = next(t for t in book['targets'] if t['source']['name']=='card/bookClose.ogg')
    verify_archived_audio(BOOK, book_target['referenceAudio'])
    book_wave, rate = sf.read(BOOK/book_target['referenceAudio']['file'], dtype='float32')
    assert rate==44100
    work = [(r['target'], r) for r in prior['rows']]+[(r,None) for r in frozen['rows']]
    work.append((dict(id='tagged/card/bookClose.ogg', group='real-repeated-book', source=book_target['source'],
                      archiveManifestSha256=file_hash(BOOK/'manifest.json'), archiveTargetId=book_target['id']), None))
    OUT.mkdir()
    _json_write(OUT/'targets.json', dict(targets=[t for t,_ in work], priorSha256=file_hash(PRIOR),
        nativeTargetsSha256=file_hash(ROOT/'targets.json'), bookManifestSha256=file_hash(BOOK/'manifest.json'),
        planSha256=file_hash(PLAN),policySha256=file_hash(POLICY),scriptSha256=file_hash(__file__)))
    result = dict(complete=False, trainingReceiptSha256=file_hash(ROOT/'training-receipt.json'),
        targetsSha256=file_hash(OUT/'targets.json'), scriptSha256=file_hash(__file__), rows=[],
        checkpoints={**{k:m['checkpointHash'] for k,(_,m) in trained.items()},'Transfxr':mixture[1]['checkpointHash'],
            'old-Boomr':shared_meta['checkpointHash'],'old-Footsteppr':shared_meta['checkpointHash']},
        policySha256=file_hash(POLICY),
        scope='155 references including 32 native test controls; all five arms receive identical audition PCM. Four proposals each; no search, source-engine label or pitch guard used for selection. Old shared-v2 engine heads included; not an all-synth system benchmark.')
    with Renderer() as renderer:
        for index, (target, previous) in enumerate(work):
            folder = OUT/f'{index:03d}'
            folder.mkdir()
            if previous is not None:
                reference = audition_pcm(read_wave(target))
                assert audio_hash(reference)==previous['inputPcmHash']
            elif target['group']=='real-repeated-book':
                reference = book_wave
            else:
                assert target['parameterHash'] not in training_controls[target['sourceSynth']]
                fitted = fitted_metas[target['sourceSynth']]
                assert target['sourceRow'] in fitted['test']
                assert target['sourceRow'] not in fitted['train']+fitted['val']
                p, wave = renderer.render(target['sourceSynth'], target['sourceParams'], target['sourceSeed'])
                assert p==target['sourceParams'] and audio_hash(wave)==target['sourceAudioHash']
                reference = audition_pcm(wave)
            # The two earlier source-engine examples must also be unseen controls.
            source_params = target.get('sourceParams', target.get('sourceTarget', {}).get('sourceParams'))
            name = target.get('sourceSynth')
            if name in training_controls and source_params:
                assert parameter_hash(dict(synth=name,params=source_params)) not in training_controls[name]
                unit, cat = schemas[name].encode(source_params)
                assert (tuple(unit.tolist()),tuple(cat.tolist())) not in numeric_controls[name]
            objective = MatchObjective(reference)
            target = {**target, **write_wave(folder/'target.wav', reference)}
            sf.write(folder/'target-audition.wav', reference, 44100, subtype='PCM_16')
            pools = {}
            for engine in ARMS:
                if engine=='Transfxr' and previous is not None:
                    proposals = previous['pools']['pcm16Input']
                elif engine=='Transfxr':
                    proposals = predict_temporal(*mixture, reference, renderer, count=4)
                elif engine.startswith('old-'):
                    # Same frozen shared encoder/normalization, only the requested
                    # head is evaluated. The source synth does not choose it.
                    proposals = predict(shared,{**shared_meta,'engines':[engine[4:]]},reference,renderer,per_synth=4)
                else:
                    proposals = predict(*trained[engine], reference, renderer, per_synth=4)
                assert len(proposals)==4
                candidates = []
                for slot, candidate in enumerate(proposals):
                    if engine=='Transfxr' and previous is not None:
                        wave = read_wave(candidate)
                        wave_info = {k:candidate[k] for k in ('waveFile','waveFileSha256','audioHash')}
                    else:
                        params, wave = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
                        assert params==candidate['params']
                        wave_info = write_wave(folder/f'{engine}-{slot}.wav', wave)
                    heard = audition_pcm(wave)
                    score = float(objective.score_batch([heard])[0])
                    if engine=='Transfxr' and previous is not None:
                        assert abs(score-candidate['score'])<1e-7
                    candidates.append(dict(synth=candidate['synth'],origin=engine,params=candidate['params'],seed=candidate['seed'],
                        provenance=candidate['provenance'],score=score,slot=slot,**wave_info,
                        auditionHash=audio_hash(heard)))
                pools[engine] = candidates
            selected = {engine:min(pool,key=lambda c:c['score']) for engine,pool in pools.items()}
            winner = min(selected.values(),key=lambda c:c['score'])
            result['rows'].append(dict(target=target,pools=pools,selected=selected,winner=winner))
            print(json.dumps(dict(done=index+1,total=len(work),target=target['id'],
                scores={k:c['score'] for k,c in selected.items()},winner=winner['origin'])),flush=True)
            if (index+1)%10==0:
                _json_write(OUT/'results.json',result)
    assert len(result['rows'])==155
    groups = {}
    for row in result['rows']:
        key = row['target']['group']
        if row['target'].get('variant'):
            key += '/'+row['target']['variant']
        groups.setdefault(key,[]).append(row)
    summary = {}
    for key, rows in groups.items():
        summary[key] = dict(count=len(rows), meanDistance={engine:float(np.mean([r['selected'][engine]['score'] for r in rows]))
                           for engine in ARMS},
            selectedCounts={engine:sum(r['winner']['origin']==engine for r in rows) for engine in ARMS},
            meanCombinedDistance=float(np.mean([r['winner']['score'] for r in rows])))
    result.update(complete=True,summary=summary)
    _json_write(OUT/'results.json',result)
    _json_write(BASE/'evaluations/specialists-v1-evaluation.json',dict(complete=True,scriptSha256=file_hash(__file__),
        reportSha256=file_hash(OUT/'results.json'),trainingReceiptSha256=file_hash(ROOT/'training-receipt.json'),
        checkpoints=result['checkpoints'],targets=155,summary=summary,scope=result['scope']))
    print(json.dumps(summary),flush=True)


if __name__ == '__main__':
    main()
