"""Audit fresh target exclusion, whole/event fits, original Bfxr and gallery identities."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.audio import prepare_target
from match.renderer import BfxrRenderer
from multisynth.timeline import TimelineRenderer
from multisynth.support_objective import SupportObjective
from multisynth.event_split import split_events
from multisynth.coverage_feedback import coverage_model
from multisynth.coverage import verify_archived_audio
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/support-transfer-v1';GALLERY=BASE/'runs/support-transfer-v1-listening'

def main():
    out=BASE/'evaluations/support-transfer-v1-verification.json'
    if out.exists():raise FileExistsError('Preserve verification')
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());report=json.loads((ROOT/'results.json').read_text())
    assert p['complete'] and report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert all(file_hash(f)==h for f,h in p['codeHashes'].items()) and all(file_hash(f)==h for f,h in p['checkpoints'].items())
    assert all(file_hash(BASE/f)==h for f,h in p['uiHashes'].items())
    prior_files=set();prior_pcm=set()
    for f,h in p['priorArchives'].items():
        assert file_hash(f)==h;archive=Path(f).parent;m=json.loads(Path(f).read_text())
        for t in m['targets']:
            prior_files.add(t['source'].get('sha256'));verify_archived_audio(archive,t['referenceAudio'])
            wave,rate=sf.read(archive/t['referenceAudio']['file'],dtype='float32');assert rate==44100;prior_pcm.add(audio_hash(wave))
    gallery=json.loads((GALLERY/'results.json').read_text());audit=json.loads((BASE/'evaluations/support-transfer-v1-listening-audit.json').read_text())
    model=coverage_model(GALLERY,gallery['results'],gallery['metadata']);assert model['experimentId']==audit['experimentId']
    assert audit['resultsSha256']==file_hash(GALLERY/'results.json') and audit['htmlSha256']==file_hash(GALLERY/'index.html')
    assert all(file_hash(GALLERY/f)==h for f,h in audit['audioFiles'].items());assert len(p['rows'])==len(report['rows'])==len(gallery['results'])==6
    checks=[];segment_attempts=joint_attempts=proposals=0;seen=set()
    with TimelineRenderer() as timeline,BfxrRenderer(jobs=1) as bfxr:
        assert timeline.inventory==p['inventory']
        for i,(entry,row,record) in enumerate(zip(p['rows'],report['rows'],gallery['results'])):
            dest=ROOT/f'{i+1:03d}';assert row['complete'] and row['entry']==entry and record['source']==entry['source']
            assert row['protocolSha256']==report['protocolSha256']
            ref,rate=sf.read(dest/'target.wav',dtype='float32');assert rate==44100 and file_hash(dest/'target.wav')==entry['wavSha256']
            assert audio_hash(ref)==entry['auditionHash'] not in prior_pcm|seen;seen.add(audio_hash(ref))
            assert file_hash(entry['source']['path'])==entry['source']['sha256'] not in prior_files
            assert np.array_equal(ref,audition_pcm(prepare_target(entry['source']['path'])))
            assert entry['boundaries']==split_events(ref)
            assert file_hash(GALLERY/record['folder']/'target.wav')==entry['wavSha256']
            for match in entry['historicalBfxrMatches']:assert file_hash(match['path'])==entry['source']['sha256']
            assert entry['source']['historicalBfxrSplits']==sorted({m['split'] for m in entry['historicalBfxrMatches']})
            for arm in row['arms']:
                if 'reuses' in arm:
                    assert arm=={'arm':'events','reuses':'whole'} and entry['boundaries']==[0,len(ref)];continue
                bounds=arm['boundaries'];assert bounds==([0,len(ref)] if arm['arm']=='whole' else entry['boundaries'])
                initial=json.loads(arm['initialParams']['layers']);final=json.loads(arm['params']['layers'])
                assert len(arm['parts'])==len(initial)==len(final)==len(bounds)-1
                for j,(part,a,b) in enumerate(zip(arm['parts'],initial,final)):
                    assert [part['start'],part['end']]==bounds[j:j+2]
                    assert a['start']==bounds[j]/44100 and a['synth']==b['synth'] and a['params']==part['selected']['params']
                    assert abs(a['start']-b['start'])<=.040000001
                    if j==0:assert b['start']==0
                    for k in ('seed','instrumentSeed','masterVolume'):assert a['params'].get(k)==b['params'].get(k)
                    source,wave=timeline.source(dict(synth=part['selected']['synth'],params=part['selected']['params']),seed=.5)
                    assert audio_hash(wave)==part['nativeHash'] and source['params']==part['selected']['params']
                    assert abs(SupportObjective(ref[bounds[j]:bounds[j+1]]).score(audition_pcm(wave))-part['selected']['score'])<1e-6
                    r=part['selected']['provenance']['refinement'];assert r['budget']==128 and len(r['trace'])==129 and np.all(np.diff(r['trace'])<=0)
                    segment_attempts+=128;proposals+=part['proposed'];assert part['valid']+len(part['failures'])==part['proposed']
                assert len(arm['trace'])==513 and np.all(np.diff(arm['trace'])<=0) and sum(arm['attempted'].values())==512
                assert arm['failures']==0;joint_attempts+=512
                _,initial_wave=timeline.render(arm['initialParams'],uncached=True)
                assert abs(SupportObjective(ref).score(audition_pcm(initial_wave))-arm['trace'][0])<1e-6
            expected={};actual={}
            for c in row['options']:
                if c['synth']=='Stackr':
                    pp,native=timeline.render(c['params'],uncached=True);assert pp==c['params']
                    assert c['sourceHash']==timeline.inventory['sourceHash']
                    own=next(a for a in row['arms'] if a['arm']==c['role']);own=next(a for a in row['arms'] if a['arm']=='whole') if 'reuses' in own else own
                    assert c['params']==own['params'] and abs(c['supportScore']-own['score'])<1e-6
                else:
                    assert c['role']=='bfxr' and c['provenance']['budget']==2000 and c['provenance']['backend']==p['bfxrBackend']
                    native=bfxr.render(c['params'],seed=c['seed'])
                pcm=audition_pcm(native);assert audio_hash(native)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                stored,rate=sf.read(dest/c['file'],dtype='float32');assert rate==44100 and np.array_equal(stored,pcm)
                assert file_hash(dest/c['file'])==c['wavSha256'] and abs(SupportObjective(ref).score(pcm)-c['supportScore'])<1e-6
                expected[c['role']]=c['auditionHash']
            for c in record['candidates']:
                wave,rate=sf.read(GALLERY/record['folder']/c['file'],dtype='float32');assert rate==44100
                for role in c['provenance']['selectionAliases']:assert role not in actual;actual[role]=audio_hash(wave)
            assert actual==expected and len(record['candidates'])==len(set(expected.values()))
            checks.append(dict(name=entry['source']['name'],events=len(entry['boundaries'])-1,options=len(record['candidates']),nativeReplay=True,excludedPriorExactAudio=True,
                historicalBfxrSplits=entry['source']['historicalBfxrSplits']))
    result=dict(complete=True,scriptSha256=file_hash(__file__),protocolSha256=file_hash(ROOT/'protocol.json'),reportSha256=file_hash(ROOT/'results.json'),
        experimentId=model['experimentId'],checks=checks,segmentAttempts=segment_attempts,jointAttempts=joint_attempts,rawProposals=proposals,
        originalBfxrEvaluations=sum(r['options'][-1]['provenance']['evaluations'] for r in report['rows']),
        humanLikeness='Unknown until listening; no default promotion')
    _json_write(out,result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
