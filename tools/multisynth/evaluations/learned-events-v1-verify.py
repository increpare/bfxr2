"""Recompute external timing predictions, native fits and exact earlier anchors."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.timeline import TimelineRenderer
from multisynth.event_split import split_events
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from neural_invert.event_timing import TimingNet,features,decode
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/learned-events-v1';GALLERY=BASE/'runs/learned-events-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-legacy-transfer-v1-quick-01';TIMING=BASE/'runs/event-timing-v1'

def main():
    torch.set_num_threads(1)
    protocol=json.loads((ROOT/'protocol.json').read_text());report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and len(report['rows'])==12 and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert all(file_hash(p)==h for p,h in protocol['codeHashes'].items())
    assert all(file_hash(p)==h for p,h in protocol['checkpoints'].items())
    gate=json.loads((TIMING/'evaluation.json').read_text());assert gate['gatePassed']
    assert gate['checkpointSha256']==protocol['timingCheckpointSha256']==file_hash(TIMING/'best.pt')
    net=TimingNet();net.load_state_dict(torch.load(TIMING/'best.pt',weights_only=False)['model']);net.eval()
    gallery=json.loads((GALLERY/'results.json').read_text());model=coverage_model(GALLERY,gallery['results'],gallery['metadata'])
    audit=json.loads((BASE/'evaluations/learned-events-v1-listening-audit.json').read_text())
    assert audit['experimentId']==model['experimentId'] and audit['reportSha256']==file_hash(ROOT/'results.json')
    assert audit['resultsSha256']==file_hash(GALLERY/'results.json') and audit['htmlSha256']==file_hash(GALLERY/'index.html')
    assert all(file_hash(GALLERY/p)==h for p,h in audit['audioFiles'].items())
    assert all(file_hash(BASE/p)==h for p,h in audit['uiCodeHashes'].items())
    expected={};trials=[]
    with TimelineRenderer() as renderer:
        assert renderer.inventory==protocol['inventory']
        for i,row in enumerate(report['rows']):
            entry=protocol['rows'][i];assert row['entry']==entry
            target=entry['target'];previous=entry['previous'];archive=Path(entry['previousArchive'])
            verify_archived_audio(ARCHIVE,target['referenceAudio']);verify_archived_audio(archive,previous['audio'])
            previousManifest=json.loads((archive/'manifest.json').read_text())
            prior=next(t for t in previousManifest['targets'] if t['referenceAudio']['pcmSha256']==target['referenceAudio']['pcmSha256'])
            assert prior['choice']['preferredCandidateIds']==[previous['id']] and previous['id'] in prior['choice']['auditionedCandidateIds']
            assert next(c for c in previousManifest['candidates'] if c['id']==previous['id'])==previous
            reference,sr=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32')
            assert sr==44100 and audio_hash(reference)==entry['referenceHash']
            if entry['arm']=='learned':
                with torch.no_grad():probs=net(torch.from_numpy(features(reference))[None]).sigmoid()[0].numpy()
                bounds=decode(probs,len(reference))
            else:bounds=split_events(reference)
            assert entry['boundaries']==bounds
            assert len(row['parts'])==len(bounds)-1
            initial=json.loads(row['initialParams']['layers'])
            assert [layer['start'] for layer in initial]==[v/44100 for v in bounds[:-1]]
            for j,part in enumerate(row['parts']):
                assert [part['start'],part['end']]==bounds[j:j+2]
                selected=part['selected'];refine=selected['provenance']['refinement']
                assert refine['budget']==128 and len(refine['trace'])==129 and np.all(np.diff(refine['trace'])<=1e-12)
                source,wave=renderer.source(dict(synth=selected['synth'],params=selected['params']),seed=.5)
                assert source['params']==selected['params'] and audio_hash(wave)==part['nativePcmHash']
                score=float(MatchObjective(reference[bounds[j]:bounds[j+1]]).score(audition_pcm(wave)))
                assert abs(score-selected['score'])<1e-6
                assert initial[j]['synth']==selected['synth'] and initial[j]['params']==selected['params']
            assert len(row['trace'])==129 and np.all(np.diff(row['trace'])<=1e-12)
            c=next(c for c in row['options'] if c['role']=='scheduled')
            layers=json.loads(c['params']['layers'])
            for j,layer in enumerate(layers):
                assert layer['params']==initial[j]['params'] and layer['synth']==initial[j]['synth']
                assert abs(layer['start']-initial[j]['start'])<=.040000001
            params,raw=renderer.render(c['params'],uncached=True);pcm=audition_pcm(raw)
            assert params==c['params'] and audio_hash(raw)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
            assert abs(float(MatchObjective(reference).score(pcm))-c['score'])<1e-6
            old,rate=sf.read(archive/previous['audio']['file'],dtype='float32');assert rate==44100
            mapping=expected.setdefault(entry['trialIndex'],{})
            mapping[entry['arm']]=audio_hash(pcm);mapping['previous']=audio_hash(old)
            trials.append(dict(trialIndex=entry['trialIndex'],name=target['source']['name'],arm=entry['arm'],events=len(row['parts']),
                proposed=sum(p['proposed'] for p in row['parts']),valid=sum(p['valid'] for p in row['parts']),
                segmentAttempts=128*len(row['parts']),timelineAttempts=128,nativeReplayVerified=True))
        for record in gallery['results']:
            trial=int(record['folder'])-1;entry=protocol['rows'][trial*2]
            assert record['source']==entry['target']['source']
            reference,rate=sf.read(GALLERY/record['folder']/'target.wav',dtype='float32')
            assert rate==44100 and audio_hash(reference)==entry['referenceHash']
            actual={}
            for c in record['candidates']:
                wave,rate=sf.read(GALLERY/record['folder']/c['file'],dtype='float32');assert rate==44100
                for alias in c['provenance']['selectionAliases']:actual[alias]=audio_hash(wave)
            assert actual==expected[trial] and len(record['candidates'])==len(set(actual.values()))
            expected.pop(trial)
        for skipped in audit.get('skippedAlreadyHeard',[]):
            trial=skipped['trialIndex'];duplicate=skipped['duplicateOf'];archive=Path(duplicate['archive'])
            assert file_hash(archive/'manifest.json')==audit['publication']['archiveHashes'][str(archive/'manifest.json')]
            old=json.loads((archive/'manifest.json').read_text());assert old['experimentId']==duplicate['experimentId']
            target=next(t for t in old['targets'] if t['id']==duplicate['targetId'])
            ids={c['id'] for c in target['candidates']}
            assert target['choice']['kind']!='skip' and ids<=set(target['choice']['auditionedCandidateIds'])
            assert target['referenceAudio']['pcmSha256']==protocol['rows'][trial*2]['target']['referenceAudio']['pcmSha256']
            hashes=set();pcmHashes=set()
            for c in old['candidates']:
                if c['id'] not in ids:continue
                verify_archived_audio(archive,c['audio']);wave,rate=sf.read(archive/c['audio']['file'],dtype='float32');assert rate==44100
                hashes.add(audio_hash(wave));pcmHashes.add(c['audio']['pcmSha256'])
            assert hashes==set(expected[trial].values()) and sorted(pcmHashes)==duplicate['options']
            expected.pop(trial)
        assert set(expected)=={r['trialIndex'] for r in audit['skippedIdentical']}
        assert all(len(set(v.values()))==1 for v in expected.values())
    receipt=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(ROOT/'protocol.json'),
        reportSha256=file_hash(ROOT/'results.json'),experimentId=model['experimentId'],trials=trials,
        targetCount=len(gallery['results']),optionCounts=audit['optionCounts'],earlierPcmPreserved=True,
        interpretation='Native timing gate passed; external perceptual improvement remains unknown pending human feedback.')
    _json_write(BASE/'evaluations/learned-events-v1-verification.json',receipt)
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
