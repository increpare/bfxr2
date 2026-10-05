"""Exact render audit and old-winner/legacy-search/soft-search comparison."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.coverage import verify_archived_audio,copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash,exact_replay
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash,_json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');RUN=BASE/'runs/soft-periodicity-v1';OUT=BASE/'runs/soft-periodicity-v1-listening'
ARCHIVES=[BASE/'listening_data/2026-10-05-tagged-coverage-quick-01',BASE/'listening_data/2026-10-05-specialists-tagged-quick-01']

def main():
    if OUT.exists():raise FileExistsError('Preserve published listening experiment')
    torch.set_num_threads(1)
    report=json.loads((RUN/'results.json').read_text());assert report['complete'] and report['mutationAttempts']==5120
    assert report['protocol']['scriptSha256']==file_hash(BASE/'evaluations/soft-periodicity-v1-search.py')
    assert report['protocol']['objectiveSha256']==file_hash(BASE/'soft_periodicity.py')
    archives=[(root,json.loads((root/'manifest.json').read_text())) for root in ARCHIVES]
    OUT.mkdir();records=[];checks=[];replayed=0
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==report['sourceHash']
        for row in report['rows']:
            source=row['target']['source'];reference=read_wave(row['reference'])
            objectives={'legacy':MatchObjective(reference),'soft':SoftPeriodicityObjective(reference)}
            for arm,value in row['arms'].items():
                assert value['selected']==min(value['finalists'],key=lambda c:c['newScores'][arm])
                for c in value['finalists']:
                    wave=read_wave(c);exact_replay({**c,'wave':wave},renderer,None);replayed+=1
                    pcm=audition_pcm(wave);assert audio_hash(pcm)==c['auditionHash']
                    for name,obj in objectives.items():assert abs(obj.score(pcm)-c['newScores'][name])<1e-6
            baseline=None
            for root,m in archives:
                matches=[t for t in m['targets'] if t['source']['sha256']==source['sha256']]
                if not matches or matches[0]['choice']['kind']!='best':continue
                target=matches[0];cid=target['choice']['preferredCandidateIds'][0]
                baseline=(root,target,next(c for c in m['candidates'] if c['id']==cid));break
            assert baseline is not None
            root,target,c=baseline
            verify_archived_audio(root,target['referenceAudio']);x,sr=sf.read(root/target['referenceAudio']['file'],dtype='float32')
            assert sr==44100 and np.array_equal(x,reference)
            verify_archived_audio(root,c['audio']);old,sr=sf.read(root/c['audio']['file'],dtype='float32');assert sr==44100
            folder=OUT/row['folder'];folder.mkdir();copy_archived_audio(root/target['referenceAudio']['file'],folder/'target.wav')
            copy_archived_audio(root/c['audio']['file'],folder/'previous.wav')
            record=dict(folder=folder.name,source=source,candidates=[{**c,'role':'previous','label':'Earlier preferred option','file':'previous.wav',
                'provenance':{**c['provenance'],'retainedArchive':str(root),'retainedManifestSha256':file_hash(root/'manifest.json'),
                    'retainedCandidateId':c['id'],'previousAdequacy':target['choice']['adequacy']['level'],
                    'auditionTransform':'Exact archived PCM, no normalization'}}],
                note='Actual synth outputs. Choose the closest, then how close it is. An exact earlier preferred option is included.')
            seen={audio_hash(old)}
            for arm,value in row['arms'].items():
                c=value['selected'];pcm=audition_pcm(read_wave(c))
                if audio_hash(pcm) in seen:continue
                seen.add(audio_hash(pcm));name=arm+'.wav';sf.write(folder/name,pcm,44100,subtype='PCM_16')
                record['candidates'].append({**c,'role':'selected' if arm=='legacy' else 'alternative','label':'New comparison option','file':name,
                    'provenance':{**c['provenance'],'searchReportSha256':file_hash(RUN/'results.json'),
                        'auditionMatchObjective':c['newScores']['legacy'],'softPeriodicity':c['newScores']['soft'],
                        'auditionWavSha256':file_hash(folder/name),'auditionTransform':'Single peak normalization and PCM16'}})
            assert 2<=len(record['candidates'])<=3
            records.append(record);checks.append(dict(source=source['name'],options=[dict(role=c['role'],synth=c['synth']) for c in record['candidates']]))
    metadata=dict(experiment='soft-periodicity-v1-listening',complete=True,targetCount=len(records),
        galleryTitle='Does a more stable search score help?',galleryIntro=[
            'These are actual synth outputs. Each trial includes an exact earlier preferred option and new search results.',
            'Both searches use identical starting controls and equal mutation budgets. One uses an experimental smooth periodicity score.',
            'Choose the closest, then how close it is. No new inverse network has been trained in this experiment.'],
        humanReviewRequired=True,reportSha256=file_hash(RUN/'results.json'),scriptSha256=file_hash(__file__),
        objectiveSha256=file_hash(BASE/'soft_periodicity.py'),selectionPolicy='All five fixed targets, own-score winner per arm, deduplicate exact audio; retain most recent best synth option, falling back one session for the rejected brick trio.',
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()})
    model=export_coverage(OUT,records,metadata)
    page=(OUT/'index.html').read_text();needle='<p class="quick-help">'
    assert page.count(needle)==1
    page=page.replace(needle,needle+'<b>Actual synth outputs: two search methods and an earlier preferred option.</b> ')
    (OUT/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],replayedFinalists=replayed,checks=checks,
        resultsSha256=file_hash(OUT/'results.json'),htmlSha256=file_hash(OUT/'index.html'),
        scriptSha256=file_hash(__file__),reportSha256=file_hash(RUN/'results.json'),
        audioFiles={str(p.relative_to(OUT)):file_hash(p) for p in sorted(OUT.glob('*/*.wav'))})
    _json_write(BASE/'evaluations/soft-periodicity-v1-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],checks=checks)),flush=True)
if __name__=='__main__':main()
