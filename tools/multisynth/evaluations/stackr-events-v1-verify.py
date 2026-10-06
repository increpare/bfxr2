"""Independent native/archived replay and publication audit for Stackr pilot."""
import json
from pathlib import Path
import hashlib
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.timeline import TimelineRenderer
from multisynth.event_split import split_events
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/stackr-events-v1';GALLERY=BASE/'runs/stackr-events-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-legacy-transfer-v1-quick-01'

def main():
    torch.set_num_threads(1)
    protocol=json.loads((ROOT/'protocol.json').read_text());report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and len(report['rows'])==4
    assert report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert protocol['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    assert protocol['archiveFeedbackSha256']==file_hash(ARCHIVE/'feedback.json')
    assert all(file_hash(p)==h for p,h in protocol['codeHashes'].items())
    assert all(file_hash(p)==h for p,h in protocol['checkpoints'].items())
    gallery=json.loads((GALLERY/'results.json').read_text())
    model=coverage_model(GALLERY,gallery['results'],gallery['metadata'])
    audit=json.loads((BASE/'evaluations/stackr-events-v1-listening-audit.json').read_text())
    assert audit['experimentId']==model['experimentId']
    assert audit['reportSha256']==file_hash(ROOT/'results.json')
    assert audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['htmlSha256']==file_hash(GALLERY/'index.html')
    assert all(file_hash(GALLERY/p)==h for p,h in audit['audioFiles'].items())
    assert all(file_hash(BASE/p)==h for p,h in audit['uiCodeHashes'].items())
    trials=[]
    with TimelineRenderer() as renderer:
        assert renderer.inventory==protocol['inventory']
        for i,(row,record) in enumerate(zip(report['rows'],gallery['results'])):
            entry=protocol['rows'][i];assert row['entry']==entry
            target=entry['target'];previous=entry['previous'];folder=GALLERY/record['folder']
            assert record['source']==target['source']
            assert target['choice']['preferredCandidateIds']==[previous['id']]
            for info in [target['referenceAudio'],previous['audio']]:verify_archived_audio(ARCHIVE,info)
            reference,sr=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32')
            published,sr2=sf.read(folder/'target.wav',dtype='float32')
            assert sr==sr2==44100 and np.array_equal(reference,published)
            assert audio_hash(reference)==entry['referenceHash'] and split_events(reference)==entry['boundaries']
            old,sr=sf.read(ARCHIVE/previous['audio']['file'],dtype='float32')
            copy,sr2=sf.read(folder/'previous.wav',dtype='float32')
            assert sr==sr2==44100 and np.array_equal(old,copy)
            objective=MatchObjective(reference)
            assert len(row['parts'])==len(entry['boundaries'])-1
            initial=json.loads(row['initialParams']['layers'])
            assert [l['start'] for l in initial]==[x/44100 for x in entry['boundaries'][:-1]]
            for j,part in enumerate(row['parts']):
                a,b=entry['boundaries'][j:j+2];assert (part['start'],part['end'])==(a,b)
                best=part['selected'];refine=best['provenance']['refinement']
                assert refine['budget']==128 and len(refine['trace'])==129
                assert np.all(np.diff(refine['trace'])<=1e-12)
                source,wave=renderer.source(dict(synth=best['synth'],params=best['params']),seed=.5)
                assert source['params']==best['params'] and audio_hash(wave)==part['nativePcmHash']
                score=float(MatchObjective(reference[a:b]).score(audition_pcm(wave)))
                assert abs(score-best['score'])<1e-6
                assert initial[j]['synth']==best['synth'] and initial[j]['params']==best['params']
            assert len(row['trace'])==129 and np.all(np.diff(row['trace'])<=1e-12)
            assert row['finalScore']<=row['initialScore']+1e-12
            parts={c['role']:c for c in row['options']}
            scheduled=json.loads(parts['scheduled']['params']['layers'])
            simultaneous=json.loads(parts['simultaneous']['params']['layers'])
            assert [l|{'start':0} for l in scheduled]==simultaneous
            for j,layer in enumerate(scheduled):
                assert layer['params']==initial[j]['params'] and layer['synth']==initial[j]['synth']
                assert abs(layer['start']-initial[j]['start'])<=.040000001
            hashes={}
            for c in row['options']:
                params,wave=renderer.render(c['params'],uncached=True);pcm=audition_pcm(wave)
                assert params==c['params'] and audio_hash(wave)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                saved,rate=sf.read(ROOT/f'{i+1:03d}'/(c['role']+'.wav'),dtype='float32')
                assert rate==44100 and np.array_equal(saved,pcm)
                assert abs(float(objective.score(pcm))-c['score'])<1e-6
                hashes[c['role']]=audio_hash(pcm)
            expected={'scheduled':hashes['scheduled'],'simultaneous':hashes['simultaneous'],'previous':audio_hash(old)}
            actual={}
            for c in record['candidates']:
                wave,rate=sf.read(folder/c['file'],dtype='float32');assert rate==44100
                for alias in c['provenance']['selectionAliases']:actual[alias]=audio_hash(wave)
            assert actual==expected
            assert len(record['candidates'])==len(set(expected.values()))
            trials.append(dict(name=target['source']['name'],events=len(row['parts']),
                proposed=sum(p['proposed'] for p in row['parts']),valid=sum(p['valid'] for p in row['parts']),
                segmentAttempts=128*len(row['parts']),timelineAttempts=128,options=len(record['candidates']),
                previousCopiedExactly=True,nativeReplayVerified=True))
    result=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(ROOT/'protocol.json'),
        reportSha256=file_hash(ROOT/'results.json'),experimentId=model['experimentId'],trials=trials,
        humanQuality='Unknown; numeric search improvement does not establish perceptual benefit.')
    _json_write(BASE/'evaluations/stackr-events-v1-verification.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
