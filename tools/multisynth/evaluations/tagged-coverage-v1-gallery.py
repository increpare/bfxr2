"""Audit actual candidate coverage and retain exact human winners for listening."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.coverage import copy_archived_audio, verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, verify_dataset_files, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.temporal_gallery import backend_provenance

BASE=Path('tools/multisynth')
OUT=BASE/'runs/tagged-coverage-v1'
GALLERY=BASE/'runs/tagged-coverage-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-05-specialists-tagged-quick-01'
METRIC=BASE/'models/preference-neural-v2.json'
AUDIT=BASE/'evaluations/tagged-coverage-v1-listening-audit.json'


def main():
    if GALLERY.exists() or AUDIT.exists():
        raise FileExistsError('Preserve published feedback experiment')
    torch.set_num_threads(1)
    protocol=json.loads((OUT/'protocol.json').read_text())
    report=json.loads((OUT/'results.json').read_text())
    assert report['complete'] and len(report['rows'])==5
    assert report['scriptSha256']==protocol['scriptSha256']==file_hash(BASE/'evaluations/tagged-coverage-v1.py')
    assert report['protocolSha256']==file_hash(OUT/'protocol.json')
    assert protocol['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    assert protocol['metricSha256']==file_hash(METRIC)
    manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    candidates={c['id']:c for c in manifest['candidates']}
    metric=PreferenceMetric.load(METRIC)
    prior_path=BASE/'runs/specialists-tagged-v1/results.json'
    assert file_hash(prior_path)==protocol['priorReportSha256']
    prior=json.loads(prior_path.read_text())
    prior_rows={r['target']['source']['sha256']:r for r in prior['rows']}
    data={}
    index_rows=0
    for binding in protocol['datasets']:
        path=Path(binding['path']);assert file_hash(path/'manifest.json')==binding['manifestSha256']
        meta=json.loads((path/'manifest.json').read_text());verify_dataset_files(path,meta)
        for engine in meta['engines']:
            shard=json.loads((path/(engine+'.json')).read_text())
            assert shard['train']==meta['splits'][engine]['train']
            assert not set(shard['train'])&set(shard['val']+shard.get('test',[]))
            data[(str(path),engine)]=shard
            index_rows+=len(shard['train'])
    assert index_rows==report['indexRows']==64415
    checks=[];records=[];replays=0;file_checks=0;max_error=0.
    with Renderer() as renderer,BfxrRenderer(jobs=1) as bfxr:
        backend=backend_provenance(bfxr)
        for target,row in zip(manifest['targets'],report['rows']):
            assert row['target']==target
            assert row==json.loads((OUT/row['folder']/'result.json').read_text())
            verify_archived_audio(ARCHIVE,target['referenceAudio'])
            reference,rate=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
            assert np.array_equal(reference,read_wave(row['reference']))
            objective=MatchObjective(reference);descriptor=describe(reference)
            def scores(pcm):
                return dict(matching=float(objective.score_batch([pcm])[0]),
                    preference=float(metric.distances(descriptor,describe(pcm))[0]))
            winner=candidates[target['choice']['preferredCandidateIds'][0]]
            verify_archived_audio(ARCHIVE,winner['audio'])
            baseline,rate=sf.read(ARCHIVE/winner['audio']['file'],dtype='float32');assert rate==44100
            assert row['baseline']==dict(candidateId=winner['id'],pcmHash=audio_hash(baseline),scores=scores(baseline))
            heard_hashes=set()
            for item in target['candidates']:
                c=candidates[item['id']];verify_archived_audio(ARCHIVE,c['audio'])
                pcm,_=sf.read(ARCHIVE/c['audio']['file'],dtype='float32');heard_hashes.add(audio_hash(pcm))
            old_row=prior_rows[target['source']['sha256']]
            expected_old=[c for pool in old_row['pools'].values() for c in pool]
            assert len(expected_old)==len(row['pools']['retainedNeural'])==59
            for expected,c in zip(expected_old,row['pools']['retainedNeural']):
                assert all(c[k]==v for k,v in expected.items() if k!='provenance')
                assert c['provenance']=={**expected['provenance'],'retainedReportSha256':protocol['priorReportSha256']}
            for label,pool in row['pools'].items():
                for c in pool:
                    raw=read_wave(c);file_checks+=1
                    pcm=audition_pcm(raw);assert audio_hash(pcm)==c['auditionHash']
                    actual=scores(pcm)
                    error=max(abs(actual[k]-c['scores'][k]) for k in actual)
                    assert error<1e-6;max_error=max(error,max_error)
                    exact_replay({**c,'wave':raw},renderer,bfxr);replays+=1
                    if label=='retrieved':
                        for evidence in c['provenance']['retrieval']:
                            shard=data[(evidence['dataset'],c['synth'])]
                            i=evidence['sourceRow'];source=shard['rows'][i]
                            assert i in shard['train'] and i not in shard['val']+shard.get('test',[])
                            assert source['params']==c['params'] and source['seed']==c['seed']
                            assert source['audioHash']==audio_hash(raw)==c['provenance']['originalAudioHash']
                    if label=='refined':
                        refinement=c['provenance']['refinement'];arm=refinement['scoreName']
                        assert refinement['budget']==128 and len(refinement['trace'])==129
                        assert abs(c['scores'][arm]-refinement['finalScore'])<1e-6
                        assert all(b<=a+1e-7 for a,b in zip(refinement['trace'],refinement['trace'][1:]))
            assert len(row['pools']['refined'])==4
            all_candidates=[c for pool in row['pools'].values() for c in pool]
            novel=[c for c in all_candidates if c['auditionHash'] not in heard_hashes]
            selected={arm:min(novel,key=lambda c:c['scores'][arm]) for arm in ('matching','preference')}
            assert selected==row['choices']
            qualifies=any(c['scores'][arm]<row['baseline']['scores'][arm]-1e-6 for arm,c in selected.items())
            assert qualifies==row['qualifying']
            check=dict(source=target['source']['name'],qualifying=qualifies,
                baseline=row['baseline'],choices={arm:dict(synth=c['synth'],scores=c['scores'],audioHash=c['auditionHash'],
                    method=c['provenance'].get('method'),refined='refinement' in c['provenance']) for arm,c in selected.items()})
            checks.append(check)
            if qualifies:
                folder=f'{len(records)+1:03d}'
                record=dict(folder=folder,source=target['source'],referenceArchive=target['referenceAudio'],candidates=[],
                    note='Choose the closest, then how close it is. One option is your exact previous winner.')
                record['candidates'].append({**winner,'role':'previous','label':'Previous comparison option','file':'previous.wav',
                    'archiveAudio':winner['audio'],'provenance':{**winner['provenance'],
                        'archiveManifestSha256':file_hash(ARCHIVE/'manifest.json'),'archiveCandidateId':winner['id'],
                        'auditionTransform':'exact archived PCM, no renormalization','previousAdequacy':target['choice']['adequacy']['level'],
                        'auditionMatchObjective':row['baseline']['scores']['matching']}})
                seen={audio_hash(baseline)}
                for arm,c in selected.items():
                    if c['auditionHash'] in seen:continue
                    seen.add(c['auditionHash']);role='selected' if arm=='matching' else 'alternative'
                    record['candidates'].append({**c,'role':role,'label':'New comparison option','file':role+'.wav',
                        'sourceHash':backend['sourceHash'] if c.get('expert')=='original-bfxr' else renderer.inventory['sourceHash'],
                        'provenance':{**c['provenance'],'selectionScore':arm,'reportSha256':file_hash(OUT/'results.json'),
                            'auditionMatchObjective':c['scores']['matching'],'preferenceNeuralV2':c['scores']['preference'],
                            'auditionPcmHash':c['auditionHash'],'auditionTransform':'single peak normalization and PCM16',
                            **({'verifiedOriginalBackend':backend} if c.get('expert')=='original-bfxr' else {})}})
                assert 2<=len(record['candidates'])<=3
                records.append(record)
            print(json.dumps(dict(verified=target['source']['name'],replays=replays,qualifying=qualifies)),flush=True)
        assert backend==backend_provenance(bfxr)
    assert sum(c['qualifying'] for c in checks)==report['qualifying']
    receipt=dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(OUT/'results.json'),
        protocolSha256=file_hash(OUT/'protocol.json'),referenceArchiveSha256=file_hash(ARCHIVE/'manifest.json'),
        replayedCandidates=replays,fileChecks=file_checks,maxScoreError=max_error,indexRows=index_rows,
        checks=checks,qualifying=len(records),originalBackend=backend,
        scope='All saved candidate raw audio independently DSP replayed and rescored. Train membership and source controls checked. Selected exact previous winners preserved. Repeated development targets; no new human adequacy or neural-training claim.')
    if records:
        GALLERY.mkdir()
        for record in records:
            dest=GALLERY/record['folder'];dest.mkdir()
            copy_archived_audio(ARCHIVE/record.pop('referenceArchive')['file'],dest/'target.wav')
            for c in record['candidates']:
                if 'archiveAudio' in c:
                    copy_archived_audio(ARCHIVE/c.pop('archiveAudio')['file'],dest/c['file'])
                else:
                    sf.write(dest/c['file'],audition_pcm(read_wave(c)),44100,subtype='PCM_16')
                pcm,rate=sf.read(dest/c['file'],dtype='float32');assert rate==44100
                c['provenance']['auditionWavSha256']=file_hash(dest/c['file'])
        model=export_coverage(GALLERY,records,dict(experiment='tagged-coverage-v1-listening',complete=True,
            targetCount=len(records),galleryTitle='Can better starting presets close the gap?',humanReviewRequired=True,
            galleryIntro=['Your exact previous winner is included. Every trial also has a new recreation.',
                'Choose the closest, then how close it is. The sounds are shuffled; None are close is useful.',
                'This tests new candidate generation and selection, not a newly trained neural model.'],
            reportSha256=receipt['reportSha256'],protocolSha256=receipt['protocolSha256'],scriptSha256=file_hash(__file__),
            referenceArchiveSha256=receipt['referenceArchiveSha256'],
            selectionPolicy='Same five development targets. Publish targets with novel audio and improvement over exact human winner by at least one frozen scorer. Preserve winner; deduplicate matching/preference alternatives.',
            uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()}))
        receipt.update(experimentId=model['experimentId'],resultsSha256=file_hash(GALLERY/'results.json'),
            htmlSha256=file_hash(GALLERY/'index.html'),audioFiles={str(p.relative_to(GALLERY)):file_hash(p) for p in GALLERY.glob('*/*.wav')})
        print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(GALLERY/'index.html'),experimentId=model['experimentId'])),flush=True)
    _json_write(AUDIT,receipt)


if __name__=='__main__':main()
