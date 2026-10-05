"""Publish a small diagnostic from an explicit outcome-selected listening manifest."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from multisynth.coverage_feedback import export_coverage
from multisynth.coverage import copy_archived_audio, verify_archived_audio
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import read_wave, TRANSFER
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

ROOT=Path('tools/multisynth/runs/native-mixture-v1')
SELECTION=Path('tools/multisynth/evaluations/native-mixture-v1-listening-targets.json')
OUT=Path('tools/multisynth/runs/native-mixture-v1-listening')
AUDIT=Path('tools/multisynth/evaluations/native-mixture-v1-audit.json')


def run():
    selection=json.loads(SELECTION.read_text());report=json.loads((ROOT/'evaluation/results.json').read_text())
    audit=json.loads(AUDIT.read_text())
    assert report['complete'] and audit['complete'] and audit['reportSha256']==file_hash(ROOT/'evaluation/results.json')
    assert selection['reportSha256']==audit['reportSha256']
    byid={r['target']['id']:r for r in report['rows']}
    previous={r['target']['id']:r for r in json.loads(TRANSFER.read_text())['rows']}
    OUT.mkdir(exist_ok=False);records=[];checks=[]
    def save(path,wave):
        heard=audition_pcm(wave);sf.write(path,heard,44100,subtype='PCM_16')
        replay,rate=sf.read(path,dtype='float32');assert rate==44100 and np.array_equal(replay,heard)
        return dict(actualRenderAudioHash=audio_hash(wave),auditionPcmSha256=audio_hash(heard),
                    auditionWavSha256=file_hash(path),auditionTransform='single peak normalization to 0.5 and PCM16 quantization')
    with Renderer() as renderer:
        for index,item in enumerate(selection['rows']):
            row=byid[item['id']];target=row['target'];folder=f'{index+1:03d}';dest=OUT/folder;dest.mkdir()
            reference=save(dest/'target.wav',read_wave(target))
            target_audio,rate=sf.read(dest/'target.wav',dtype='float32');objective=MatchObjective(target_audio)
            new=row['selected'][item['newArm']]
            archive=None
            if item['baseline']=='archive':
                archive=Path(item['archive']);manifest=json.loads((archive/'manifest.json').read_text())
                oldtarget=next(t for t in manifest['targets'] if t['id']==item['archiveTargetId'])
                assert oldtarget['choice']['kind']=='best'
                cid=oldtarget['choice']['preferredCandidateIds'][0]
                baseline=next(c for c in manifest['candidates'] if c['id']==cid)
                verify_archived_audio(archive,oldtarget['referenceAudio']);verify_archived_audio(archive,baseline['audio'])
                ref,_=sf.read(archive/oldtarget['referenceAudio']['file'],dtype='float32')
                assert np.array_equal(ref,target_audio)
            elif item['baseline']=='transfer-ensemble':baseline=previous[item['id']]['selected']['ensemble']
            else:
                assert item['baseline']=='baseline';baseline=row['selected']['baseline']
            record=dict(folder=folder,source=dict(name=item['label'],sha256=reference['auditionWavSha256'],sourceTarget=target),
                        note='Compare gesture, pitch and character with the reference. Replay as needed.',referenceProvenance=reference,candidates=[])
            heard=[]
            for role,title,c in [('previous','Comparison option 1',baseline),('selected','Comparison option 2',new)]:
                path=dest/(role+'.wav')
                if role=='previous' and archive is not None:
                    copy_archived_audio(archive/c['audio']['file'],path)
                    audio,_=sf.read(path,dtype='float32')
                    info=dict(auditionPcmSha256=audio_hash(audio),auditionWavSha256=file_hash(path),
                              auditionTransform='exact previously auditioned PCM; no additional normalization',
                              archiveManifestSha256=file_hash(archive/'manifest.json'),archiveCandidateId=c['id'])
                    source_hash=c['sourceHash']
                else:
                    audio=read_wave(c);p,replay=renderer.render('Transfxr',c['params'],c['seed'])
                    assert p==c['params'] and np.array_equal(audio,replay)
                    info=save(path,audio);source_hash=renderer.inventory['sourceHash']
                audio,_=sf.read(path,dtype='float32');heard.append(audio_hash(audio))
                card={**c,'role':role,'label':title,'file':role+'.wav','sourceHash':source_hash,
                      'provenance':{**c['provenance'],**info,'experimentReportSha256':audit['reportSha256'],
                                    'sourceCase':item['id'],'selectionReason':item['reason'],
                                    'auditionMatchObjective':float(objective.score_batch([audio])[0])}}
                record['candidates'].append(card)
            assert heard[0]!=heard[1], 'Do not ask for duplicate audio comparison'
            records.append(record);checks.append(dict(id=item['id'],auditionHashes=heard,
                scores=[c['provenance']['auditionMatchObjective'] for c in record['candidates']]))
    metadata=dict(experiment='native-mixture-v1-listening',complete=True,targetCount=len(records),
        galleryTitle='Retrained Transfxr · six short comparisons',humanReviewRequired=True,
        galleryIntro=['Choose the closer recreation; immediately say how close it is while the sound is still on screen.',
            'None are close and Skip advance immediately. Replay always starts at the beginning; feedback is saved locally.',
            'This is a deliberately selected diagnostic, including strengths and weaknesses. Some references are familiar, but every pair includes a new recreation.'],
        reportSha256=audit['reportSha256'],auditSha256=file_hash(AUDIT),selectionSha256=file_hash(SELECTION),
        scriptSha256=file_hash(__file__),checkpoints=report['checkpoints'],
        selectionPolicy=selection['policy'],uiCodeHashes={p.name:file_hash(p) for p in Path('tools/multisynth').glob('quick_*') if p.is_file()})
    model=export_coverage(OUT,records,metadata)
    receipt=dict(complete=True,experimentId=model['experimentId'],htmlSha256=file_hash(OUT/'index.html'),
                 resultsSha256=file_hash(OUT/'results.json'),checks=checks,
                 audioFiles={str(p.relative_to(OUT)):file_hash(p) for p in OUT.glob('*/*.wav')},
                 scope='Selected new DSP replayed; archived old PCM exact; all audition transforms and candidate distinction verified.')
    _json_write(OUT/'export-audit.json',receipt)
    _json_write(Path('tools/multisynth/evaluations/native-mixture-v1-listening-audit.json'),receipt)
    print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(OUT/'index.html'),experimentId=model['experimentId'])),flush=True)

if __name__=='__main__':run()
