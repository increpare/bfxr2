"""Repeated external capability probe: event-conditioned native Stackr fitting."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from multisynth.timeline import TimelineRenderer
from multisynth.event_split import split_events, POLICY
from multisynth.coverage import verify_archived_audio, copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.predict import load_model, predict
from neural_invert.coverage_mixture import load as load_mixture
from neural_invert.temporal import predict_temporal
from neural_invert.evaluate import rendered_candidates, refine_candidate, serializable

BASE=Path('tools/multisynth')
ROOT=BASE/'runs/stackr-events-v1'
GALLERY=BASE/'runs/stackr-events-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-legacy-transfer-v1-quick-01'
SHARED=BASE/'runs/neural-v2/acoustic-model'
MIXTURE=BASE/'runs/native-mixture-v1/models/mixture'
PLAN=Path('docs/superpowers/plans/2026-10-06-stackr-events.md')
SEED=20261103
INDICES=(0,2,3,5)

class Objective(MatchObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

class SourceAdapter:
    def __init__(self,timeline,renderer):
        self.timeline=timeline;self.specs=renderer.specs
    def render(self,synth,params,seed):
        source,wave=self.timeline.source(dict(synth=synth,params=params,start=0,gain=.5,pitch=0),seed=.5)
        return source['params'],wave

def bindings():
    paths=[Path(__file__),PLAN,Path('tools/multisynth/event_split.py'),Path('tools/multisynth/timeline.py'),
        Path('tools/neural_invert/evaluate.py'),Path('tools/neural_invert/predict.py'),
        Path('tools/neural_invert/temporal.py'),Path('tools/neural_invert/features.py'),
        Path('tools/neural_invert/coverage_mixture.py'),Path('tools/neural_invert/schema.py'),
        Path('tools/neural_invert/experiment.py'),Path('tools/match/objective.py'),
        Path('tools/match/features.py'),Path('tools/match/audio.py')]
    return {str(p):file_hash(p) for p in paths}

def freeze():
    if ROOT.exists():raise FileExistsError('Preserve previous experiment')
    manifest=json.loads((ARCHIVE/'manifest.json').read_text());candidates={c['id']:c for c in manifest['candidates']}
    rows=[]
    with TimelineRenderer() as timeline:
        inventory=timeline.inventory
    for i in INDICES:
        target=manifest['targets'][i];choice=target['choice'];assert choice['kind']=='best'
        winner=candidates[choice['preferredCandidateIds'][0]]
        assert winner['id'] in choice['auditionedCandidateIds']
        verify_archived_audio(ARCHIVE,target['referenceAudio']);verify_archived_audio(ARCHIVE,winner['audio'])
        wave,rate=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
        rows.append(dict(target=target,previous=winner,boundaries=split_events(wave),seed=SEED+1009*i,
            referenceHash=audio_hash(wave)))
    protocol=dict(complete=True,rows=rows,inventory=inventory,codeHashes=bindings(),
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),archiveFeedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        checkpoints={str(p/'best.pt'):file_hash(p/'best.pt') for p in (SHARED,MIXTURE)},
        splitPolicy=POLICY,segmentBudget=128,timelineBudget=128,sourceSeed=.5,
        scope='Four repeated external references, including two prior similar controls. Frozen existing shared22 and Transfxr mixture experts; no neural retraining. Segment-conditioned proposals and actual native Stackr. Historical Bfxr overlap; no generalization or equal-baseline-budget claim.',
        selection='All four preselected rows, even score regressions. Final scheduled stack, exact same components with zero starts, exact previous human winner. Deduplicate exact PCM with role aliases.')
    ROOT.mkdir();_json_write(ROOT/'protocol.json',protocol)
    _json_write(BASE/'evaluations/stackr-events-v1-protocol.json',protocol)
    print(json.dumps({'frozen':[{ 'name':r['target']['source']['name'],'cuts':r['boundaries']} for r in rows]}),flush=True)

def checked():
    protocol=json.loads((ROOT/'protocol.json').read_text())
    assert protocol['codeHashes']==bindings()
    assert protocol['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json')
    assert protocol['archiveFeedbackSha256']==file_hash(ARCHIVE/'feedback.json')
    assert all(file_hash(p)==h for p,h in protocol['checkpoints'].items())
    return protocol

def run():
    frozen=checked();torch.set_num_threads(1)
    if (ROOT/'results.json').exists():raise FileExistsError('Preserve completed run')
    shared=load_model(SHARED);mixture=load_mixture(MIXTURE);rows=[]
    with Renderer() as renderer, TimelineRenderer() as timeline:
        assert timeline.inventory==frozen['inventory']
        assert renderer.inventory['sourceHash']==timeline.inventory['baseSourceHash']
        assert all(m['sourceHash']==renderer.inventory['sourceHash'] for m in (shared[1],mixture[1]))
        adapter=SourceAdapter(timeline,renderer)
        for i,entry in enumerate(frozen['rows']):
            dest=ROOT/f'{i+1:03d}';dest.mkdir();started=time.monotonic()
            reference,rate=sf.read(ARCHIVE/entry['target']['referenceAudio']['file'],dtype='float32')
            assert rate==44100 and audio_hash(reference)==entry['referenceHash']
            sf.write(dest/'target.wav',reference,44100,subtype='PCM_16')
            objective=Objective(reference);bounds=entry['boundaries'];layers=[];parts=[]
            for j,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
                wave=reference[a:b];local=Objective(wave)
                proposed=predict(*shared,wave,renderer,per_synth=2)+predict_temporal(*mixture,wave,renderer,count=4)
                proposed=[{**c,'seed':.5} for c in proposed if c['synth'] in timeline.inventory['sources']]
                raw,failures=rendered_candidates(proposed,adapter,local)
                if not raw:raise ValueError('No audible segment hypothesis')
                initial=min(raw,key=lambda c:c['score'])
                best=refine_candidate(initial,adapter,local,frozen['segmentBudget'],entry['seed']+71*j)
                source,actual=timeline.source(dict(synth=best['synth'],params=best['params']),seed=.5)
                assert np.array_equal(actual,best['wave'])
                gain=float(np.clip(np.sqrt(np.mean(wave**2))/max(np.sqrt(np.mean(actual**2)),1e-8),.03,.9))
                layers.append(dict(synth=best['synth'],name=best['synth'],params=best['params'],start=a/44100,gain=gain,pitch=0))
                sf.write(dest/f'part-{j+1}.wav',actual,44100,subtype='FLOAT')
                parts.append(dict(start=a,end=b,proposed=len(proposed),valid=len(raw),failures=failures,
                    selected=serializable(best),nativePcmHash=audio_hash(actual)))
                print(json.dumps(dict(target=i+1,event=j+1,events=len(bounds)-1,synth=best['synth'],score=best['score'])),flush=True)
            params,wave=timeline.render(dict(layers=json.dumps(layers),seed=.5,masterVolume=.5,spacing=1))
            initialScore=score=float(objective.score_batch([wave])[0]);trace=[score];rng=np.random.default_rng(entry['seed'])
            initialParams=deepcopy(params)
            for step in range(frozen['timelineBudget']):
                candidate=deepcopy(params);ll=json.loads(candidate['layers']);slot=int(rng.integers(len(ll)))
                field=rng.choice(['start','gain','pitch']);scale=(1,.5,.25,.1)[min(3,step*4//frozen['timelineBudget'])]
                if field=='start':
                    center=bounds[slot]/44100
                    ll[slot][field]=0 if slot==0 else float(np.clip(ll[slot][field]+rng.normal()*.025*scale,max(0,center-.04),center+.04))
                elif field=='gain':ll[slot][field]=float(np.clip(ll[slot][field]+rng.normal()*.2*scale,.01,1))
                else:ll[slot][field]=float(np.clip(ll[slot][field]+rng.normal()*2*scale,-12,12))
                candidate['layers']=json.dumps(ll);cc,ww=timeline.render(candidate)
                ss=float(objective.score_batch([ww])[0])
                if ss<score:params,wave,score=cc,ww,ss
                trace.append(score)
            scheduled=deepcopy(params);simultaneous=deepcopy(params)
            ll=json.loads(simultaneous['layers'])
            for layer in ll:layer['start']=0
            simultaneous['layers']=json.dumps(ll)
            options=[]
            for role,pp in [('scheduled',scheduled),('simultaneous',simultaneous)]:
                pp,ww=timeline.render(pp);cc,rr=timeline.render(pp,uncached=True)
                assert cc==pp and np.array_equal(ww,rr)
                pcm=audition_pcm(ww);sf.write(dest/(role+'.wav'),pcm,44100,subtype='PCM_16')
                options.append(dict(role=role,params=pp,seed=0,synth='Stackr',sourceHash=timeline.inventory['sourceHash'],
                    nativeHash=audio_hash(ww),auditionHash=audio_hash(pcm),wavSha256=file_hash(dest/(role+'.wav')),
                    score=float(objective.score_batch([ww])[0])))
            row=dict(entry=entry,parts=parts,initialParams=initialParams,initialScore=initialScore,finalScore=score,
                trace=trace,options=options,seconds=time.monotonic()-started)
            _json_write(dest/'result.json',row);rows.append(row)
            print(json.dumps(dict(done=i+1,seconds=round(row['seconds'],1),initial=initialScore,final=score)),flush=True)
    assert checked()==frozen
    result=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),rows=rows)
    _json_write(ROOT/'results.json',result)
    _json_write(BASE/'evaluations/stackr-events-v1-evaluation.json',result)


def publish():
    frozen=checked();report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    if GALLERY.exists():raise FileExistsError('Preserve published gallery')
    GALLERY.mkdir();records=[]
    with TimelineRenderer() as timeline:
        assert timeline.inventory==frozen['inventory']
        for i,row in enumerate(report['rows']):
            assert row['entry']==frozen['rows'][i]
            entry=row['entry'];dest=GALLERY/f'{i+1:03d}';dest.mkdir()
            copy_archived_audio(ARCHIVE/entry['target']['referenceAudio']['file'],dest/'target.wav')
            options=[];seen={}
            for c in row['options']:
                params,raw=timeline.render(c['params'],uncached=True);pcm=audition_pcm(raw)
                assert params==c['params'] and audio_hash(raw)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                if c['auditionHash'] in seen:
                    seen[c['auditionHash']]['provenance']['selectionAliases'].append(c['role']);continue
                filename=c['role']+'.wav';sf.write(dest/filename,pcm,44100,subtype='PCM_16')
                assert file_hash(dest/filename)==c['wavSha256']
                option={**c,'label':'Comparison option','file':filename,'provenance':dict(
                    origin='native-stackr-events',selectionAliases=[c['role']],protocolSha256=report['protocolSha256'],
                    nativeHash=c['nativeHash'],auditionHash=c['auditionHash'],eventBoundaries=entry['boundaries'],
                    seedPolicy=frozen['inventory']['seedPolicy'],nativeSeed=.5,seedFieldMeaning='Integer gallery identifier; actual native seed is params.seed',neuralRetraining=False)}
                options.append(option);seen[c['auditionHash']]=option
            previous=entry['previous'];copy_archived_audio(ARCHIVE/previous['audio']['file'],dest/'previous.wav')
            pcm,rate=sf.read(dest/'previous.wav',dtype='float32');assert rate==44100
            if audio_hash(pcm) in seen:seen[audio_hash(pcm)]['provenance']['selectionAliases'].append('previous')
            else:options.append({k:v for k,v in previous.items() if k not in ('id','audio','targetId','audioSha256','paramsSha256')}|
                dict(role='previous',file='previous.wav',label='Comparison option',provenance={**previous['provenance'],
                    'parentCandidateId':previous['id'],'parentExperimentId':json.loads((ARCHIVE/'manifest.json').read_text())['experimentId'],
                    'selectionAliases':['previous'],'exactEarlierPcmSha256':previous['audio']['pcmSha256']}))
            records.append(dict(folder=dest.name,source=entry['target']['source'],candidates=options,
                note='Repeated external reference. Compare the whole gesture and choose how close it feels.'))
    assets=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js','quick_listening.html',
            'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']
    metadata=dict(experiment='stackr-events-v1-listening',complete=True,targetCount=4,humanReviewRequired=True,
        galleryTitle='Four comparisons — fitting the separate events',galleryIntro=[
            'Four sounds you just judged: book flip and coin, plus attack and bell controls.',
            'Compare a native Stackr timeline, the same components starting together, and your exact earlier choice. Identical options are merged.',
            'Existing inverse models fit individual events; no neural weights were retrained. Repeated development cases, including historical Bfxr overlap. Choose the closest, then how close.'],
        scope=frozen['scope'],selectionPolicy=frozen['selection'],protocolSha256=report['protocolSha256'],
        reportSha256=file_hash(ROOT/'results.json'),uiCodeHashes={p:file_hash(BASE/p) for p in assets},
        diagnosticQuestion=dict(version='quick-mismatch-v1',optional=True,trigger='similar, least-bad, or none close'))
    model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>'
    assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    info='<details class="quick-help"><summary>What is this testing?</summary><p>Four repeated external sounds. New options use native Stackr: independently fitted synth events, either scheduled or starting together. Your previous winner is preserved exactly. The bell may have no detected boundary; identical audio is merged. This tests event representation, not new neural training or unseen-source generalization. Earlier search budgets differ. All four sources occur in historical Bfxr training.</p></details>'
    page=page.replace('<div class="quick-topline">',info+'<div class="quick-topline">')
    (GALLERY/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],targetCount=4,optionCounts=[len(r['candidates']) for r in records],
        reportSha256=file_hash(ROOT/'results.json'),resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        audioFiles={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))},uiCodeHashes=metadata['uiCodeHashes'])
    _json_write(BASE/'evaluations/stackr-events-v1-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],counts=audit['optionCounts'])),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','publish'])
    globals()[parser.parse_args().stage]()
