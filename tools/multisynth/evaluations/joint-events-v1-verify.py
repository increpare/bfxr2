"""Independent native replay, exact feedback-anchor and paired-search audit."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.timeline import TimelineRenderer
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from neural_invert.benchmark import audio_hash
from neural_invert.experiment import audition_pcm
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/joint-events-v1';GALLERY=BASE/'runs/joint-events-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-learned-events-v1-quick-01'

def main():
    torch.set_num_threads(1)
    output=BASE/'evaluations/joint-events-v1-verification.json'
    if output.exists():raise FileExistsError('Preserve verification')
    p=json.loads((ROOT/'protocol.json').read_text());report=json.loads((ROOT/'results.json').read_text())
    audit=json.loads((BASE/'evaluations/joint-events-v1-listening-audit.json').read_text())
    gallery=json.loads((GALLERY/'results.json').read_text());manifest=json.loads((ARCHIVE/'manifest.json').read_text())
    assert p['complete'] and all(file_hash(f)==h for f,h in p['codeHashes'].items())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert audit['reportSha256']==file_hash(ROOT/'results.json')
    assert audit['resultsSha256']==file_hash(GALLERY/'results.json') and audit['htmlSha256']==file_hash(GALLERY/'index.html')
    assert all(file_hash(GALLERY/f)==h for f,h in audit['audioFiles'].items())
    assert all(file_hash(BASE/f)==h for f,h in audit['uiCodeHashes'].items())
    model=coverage_model(GALLERY,gallery['results'],gallery['metadata']);assert model['experimentId']==audit['experimentId']
    assert len(report['rows'])==len(gallery['results'])==len(p['rows'])==4
    oldcs={c['id']:c for c in manifest['candidates']};checks=[]
    with TimelineRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        for i,(entry,row,record) in enumerate(zip(p['rows'],report['rows'],gallery['results'])):
            assert row['entry']==entry and record['source']==entry['target']['source']
            target=next(t for t in manifest['targets'] if t['id']==entry['target']['id']);assert target==entry['target']
            assert target['choice']['preferredCandidateIds']==[entry['previous']['id']]
            assert entry['previous']==oldcs[entry['previous']['id']]
            reference,rate=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
            reference_copy,rate=sf.read(GALLERY/record['folder']/'target.wav',dtype='float32');assert rate==44100 and np.array_equal(reference,reference_copy)
            objective=MatchObjective(reference);initial=entry['initial'];pp,ww=renderer.render(initial['params'],uncached=True)
            assert pp==initial['params'] and audio_hash(ww)==initial['nativeHash']
            initial_score=objective.score(audition_pcm(ww));original=json.loads(pp['layers']);overlaps=[]
            for j,layer in enumerate(original[:-1]):
                _,source=renderer.source(layer,seed=pp['seed'])
                end=layer['start']+len(source)/44100/(2**(layer['pitch']/12))
                overlaps.append(max(0.,end-original[j+1]['start']))
            expected={};scores={};changed={}
            assert [c['role'] for c in row['options']]==['timeline','joint']
            for c in row['options']:
                assert sum(c['attempted'].values())==p['budget']==2048
                assert all(c['accepted'][k]<=c['attempted'][k] for k in ('source','timeline'))
                assert len(c['trace'])==2049 and abs(c['trace'][0]-initial_score)<1e-6 and abs(c['trace'][-1]-c['score'])<1e-9
                assert np.isfinite(c['trace']).all() and np.all(np.diff(c['trace'])<=0)
                assert c['failures']==0
                canonical,native=renderer.render(c['params'],uncached=True);pcm=audition_pcm(native)
                assert canonical==c['params'] and audio_hash(native)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                assert abs(objective.score(pcm)-c['score'])<1e-6
                layers=json.loads(canonical['layers']);assert len(layers)==len(original)
                assert {k:v for k,v in canonical.items() if k!='layers'}=={k:v for k,v in pp.items() if k!='layers'}
                nchanged=0
                for j,(a,b) in enumerate(zip(original,layers)):
                    assert a['synth']==b['synth'] and abs(a['start']-b['start'])<=.040000001
                    assert .01<=b['gain']<=1 and -12<=b['pitch']<=12
                    if j==0:assert b['start']==0
                    for key in ('masterVolume','seed','instrumentSeed'):
                        assert a['params'].get(key)==b['params'].get(key)
                    nchanged+=a['params']!=b['params']
                if c['role']=='timeline':assert nchanged==0 and c['attempted']['source']==c['accepted']['source']==0
                else:assert c['attempted']['source']>0
                expected[c['role']]=audio_hash(pcm);scores[c['role']]=c['score'];changed[c['role']]=nchanged
            verify_archived_audio(ARCHIVE,entry['previous']['audio']);old,rate=sf.read(ARCHIVE/entry['previous']['audio']['file'],dtype='float32');assert rate==44100
            expected['previous']=audio_hash(old);actual={}
            for c in record['candidates']:
                wave,rate=sf.read(GALLERY/record['folder']/c['file'],dtype='float32');assert rate==44100
                for alias in c['provenance']['selectionAliases']:
                    assert alias not in actual;actual[alias]=audio_hash(wave)
            assert actual==expected and len(record['candidates'])==len(set(expected.values()))
            # No entire repeated audition set: reference plus all option PCM defines a trial.
            for archivepath in sorted((BASE/'listening_data').glob('*/manifest.json')):
                m=json.loads(archivepath.read_text())
                if m.get('schemaVersion')!=3:continue
                cs={c['id']:c for c in m['candidates']}
                for oldtarget in m['targets']:
                    if oldtarget.get('referenceAudio',{}).get('pcmSha256')!=target['referenceAudio']['pcmSha256']:continue
                    oldhashes=set()
                    for item in oldtarget['candidates']:
                        w,sr=sf.read(archivepath.parent/cs[item['id']]['audio']['file'],dtype='float32');assert sr==44100
                        oldhashes.add(audio_hash(w))
                    assert oldhashes!=set(actual.values()),'Entire comparison already available in retained feedback'
            checks.append(dict(name=target['source']['name'],initialScore=initial_score,scores=scores,
                sourceLayersChanged=changed,initialOverlapSeconds=overlaps,exactEarlierWinnerVerified=True,nativeReplayVerified=True))
    result=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(ROOT/'protocol.json'),
        reportSha256=file_hash(ROOT/'results.json'),experimentId=model['experimentId'],checks=checks,
        attempts=4*2*2048,neuralWeightsRetrained=False,perceptualImprovement='Unknown until human feedback')
    _json_write(output,result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
