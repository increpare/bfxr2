"""Learned versus heuristic event boundaries, with exact latest human anchors."""
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
from neural_invert.event_timing import TimingNet, features as timing_features, decode
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
ROOT=BASE/'runs/learned-events-v1'
GALLERY=BASE/'runs/learned-events-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-legacy-transfer-v1-quick-01'
SHARED=BASE/'runs/neural-v2/acoustic-model'
MIXTURE=BASE/'runs/native-mixture-v1/models/mixture'
PLAN=Path('docs/superpowers/plans/2026-10-06-learned-events.md')
SEED=20261103
INDICES=tuple(range(6))
TIMING=BASE/'runs/event-timing-v1'
LATEST=BASE/'listening_data/2026-10-06-stackr-events-v1-quick-01'

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
    paths=[Path(__file__),PLAN,TIMING/'best.pt',TIMING/'evaluation.json',BASE/'evaluations/event-timing-v1-verification.json',LATEST/'manifest.json',LATEST/'feedback.json',Path('tools/neural_invert/event_timing.py'),Path('tools/multisynth/event_split.py'),Path('tools/multisynth/timeline.py'),
        Path('tools/neural_invert/evaluate.py'),Path('tools/neural_invert/predict.py'),
        Path('tools/neural_invert/temporal.py'),Path('tools/neural_invert/features.py'),
        Path('tools/neural_invert/coverage_mixture.py'),Path('tools/neural_invert/schema.py'),
        Path('tools/neural_invert/experiment.py'),Path('tools/match/objective.py'),
        Path('tools/match/features.py'),Path('tools/match/audio.py')]
    return {str(p):file_hash(p) for p in paths}

def freeze():
    if ROOT.exists():raise FileExistsError('Preserve previous experiment')
    torch.set_num_threads(1)
    gate=json.loads((TIMING/'evaluation.json').read_text())
    verified=json.loads((BASE/'evaluations/event-timing-v1-verification.json').read_text())
    assert gate['complete'] and gate['gatePassed'] and verified['complete'] and verified['gatePassed']
    assert gate['checkpointSha256']==verified['checkpointSha256']==file_hash(TIMING/'best.pt')
    assert verified['evaluationSha256']==file_hash(TIMING/'evaluation.json')
    model=TimingNet();model.load_state_dict(torch.load(TIMING/'best.pt',weights_only=False)['model']);model.eval()
    manifest=json.loads((ARCHIVE/'manifest.json').read_text());candidates={c['id']:c for c in manifest['candidates']}
    latest=json.loads((LATEST/'manifest.json').read_text());new_candidates={c['id']:c for c in latest['candidates']}
    latest_by_pcm={t['referenceAudio']['pcmSha256']:t for t in latest['targets']}
    rows=[]
    with TimelineRenderer() as timeline:inventory=timeline.inventory
    for i in INDICES:
        target=manifest['targets'][i];choice=target['choice'];assert choice['kind']=='best'
        winner=candidates[choice['preferredCandidateIds'][0]];previousArchive=ARCHIVE
        current=latest_by_pcm.get(target['referenceAudio']['pcmSha256'])
        if current:
            assert current['choice']['kind']=='best'
            winner=new_candidates[current['choice']['preferredCandidateIds'][0]];previousArchive=LATEST
            assert winner['id'] in current['choice']['auditionedCandidateIds']
        else:assert winner['id'] in choice['auditionedCandidateIds']
        verify_archived_audio(ARCHIVE,target['referenceAudio']);verify_archived_audio(previousArchive,winner['audio'])
        wave,rate=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
        with torch.no_grad():prob=model(torch.from_numpy(timing_features(wave))[None]).sigmoid()[0].numpy()
        for arm,bounds in [('learned',decode(prob,len(wave))),('heuristic',split_events(wave))]:
            rows.append(dict(target=target,previous=winner,previousArchive=str(previousArchive),
                trialIndex=i,arm=arm,boundaries=bounds,seed=SEED+1009*i,referenceHash=audio_hash(wave)))
    protocol=dict(complete=True,rows=rows,inventory=inventory,codeHashes=bindings(),
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),archiveFeedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        checkpoints={str(p/'best.pt'):file_hash(p/'best.pt') for p in (SHARED,MIXTURE)},
        timingCheckpointSha256=file_hash(TIMING/'best.pt'),timingEvaluationSha256=file_hash(TIMING/'evaluation.json'),
        splitPolicy=POLICY,segmentBudget=128,timelineBudget=128,sourceSeed=.5,
        parentFittingScriptSha256=file_hash(BASE/'evaluations/stackr-events-v1.py'),
        scope='Six repeated external references. Learned timing versus heuristic boundaries; fixed existing shared22/Transfxr control experts.128 mutations per event plus128 per timeline; differing counts mean unequal total work. Historical original-Bfxr overlap. No unseen-source or perceptual-improvement claim.',
        selection='All six references, both scheduled fits and exact latest human winner. Merge exact PCM aliases; report all-identical trials without asking a one-option question.')
    ROOT.mkdir();_json_write(ROOT/'protocol.json',protocol)
    _json_write(BASE/'evaluations/learned-events-v1-protocol.json',protocol)
    print(json.dumps({'frozen':[{ 'name':r['target']['source']['name'],'arm':r['arm'],'cuts':r['boundaries']} for r in rows]}),flush=True)


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
    _json_write(BASE/'evaluations/learned-events-v1-evaluation.json',result)


def publish():
    frozen=checked();report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json') and len(report['rows'])==12
    if GALLERY.exists():raise FileExistsError('Preserve published gallery')
    GALLERY.mkdir();records=[];skipped=[]
    with TimelineRenderer() as timeline:
        assert timeline.inventory==frozen['inventory']
        for trial in range(6):
            pair=report['rows'][trial*2:trial*2+2];entry=pair[0]['entry']
            assert [r['entry']['arm'] for r in pair]==['learned','heuristic']
            assert all(r['entry']['trialIndex']==trial for r in pair)
            assert all(r['entry']['target']==entry['target'] and r['entry']['previous']==entry['previous'] for r in pair)
            dest=GALLERY/f'{trial+1:03d}';dest.mkdir()
            copy_archived_audio(ARCHIVE/entry['target']['referenceAudio']['file'],dest/'target.wav')
            options=[];seen={}
            for row in pair:
                arm=row['entry']['arm'];c=next(c for c in row['options'] if c['role']=='scheduled')
                params,raw=timeline.render(c['params'],uncached=True);pcm=audition_pcm(raw)
                assert params==c['params'] and audio_hash(raw)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                if c['auditionHash'] in seen:
                    seen[c['auditionHash']]['provenance']['selectionAliases'].append(arm);continue
                filename=arm+'.wav';sf.write(dest/filename,pcm,44100,subtype='PCM_16')
                assert file_hash(dest/filename)==c['wavSha256']
                option={**c,'role':arm,'label':'Comparison option','file':filename,'provenance':dict(
                    origin='native-stackr-events',selectionAliases=[arm],protocolSha256=report['protocolSha256'],
                    nativeHash=c['nativeHash'],auditionHash=c['auditionHash'],eventBoundaries=row['entry']['boundaries'],
                    timingCheckpointSha256=frozen['timingCheckpointSha256'] if arm=='learned' else None,
                    seedPolicy=frozen['inventory']['seedPolicy'],nativeSeed=.5,
                    seedFieldMeaning='Integer gallery identifier; actual native seed is params.seed',
                    neuralSynthControlsRetrained=False,timingModelTrained=arm=='learned')}
                options.append(option);seen[c['auditionHash']]=option
            previous=entry['previous'];previousArchive=Path(entry['previousArchive'])
            verify_archived_audio(previousArchive,previous['audio'])
            copy_archived_audio(previousArchive/previous['audio']['file'],dest/'previous.wav')
            pcm,rate=sf.read(dest/'previous.wav',dtype='float32');assert rate==44100
            if audio_hash(pcm) in seen:seen[audio_hash(pcm)]['provenance']['selectionAliases'].append('previous')
            else:options.append({k:v for k,v in previous.items() if k not in ('id','audio','targetId','audioSha256','paramsSha256')}|
                dict(role='previous',file='previous.wav',label='Comparison option',provenance={**previous['provenance'],
                    'parentCandidateId':previous['id'],'parentExperimentId':json.loads((previousArchive/'manifest.json').read_text())['experimentId'],
                    'selectionAliases':['previous'],'exactEarlierPcmSha256':previous['audio']['pcmSha256']}))
            if len(options)==1:
                skipped.append(dict(trialIndex=trial,reason='All candidate PCM identical',source=entry['target']['source']));continue
            records.append(dict(folder=dest.name,source=entry['target']['source'],candidates=options,
                note='Repeated external reference. Compare the whole gesture and choose how close it feels.'))
    if not records:raise ValueError('No discriminating comparisons; do not ask for feedback')
    assets=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js','quick_listening.html',
            'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']
    metadata=dict(experiment='learned-events-v1-listening',complete=True,targetCount=len(records),humanReviewRequired=True,
        galleryTitle='Can learned event timing help?',galleryIntro=[
            'Six external sounds you have judged, with new native Stackr comparisons and your exact latest choice.',
            'A small timing CNN trained on synthetic Stackr sequences chooses event boundaries. Compare it with the earlier waveform splitter; identical audio is merged.',
            'Both use the same frozen synth-control experts and128 mutations per event. Different event counts mean different total work. Repeated development cases with historical Bfxr overlap; native timing accuracy does not establish audible likeness.'],
        scope=frozen['scope'],selectionPolicy=frozen['selection'],protocolSha256=report['protocolSha256'],
        timingCheckpointSha256=frozen['timingCheckpointSha256'],reportSha256=file_hash(ROOT/'results.json'),
        uiCodeHashes={p:file_hash(BASE/p) for p in assets},
        diagnosticQuestion=dict(version='quick-mismatch-v1',optional=True,trigger='similar, least-bad, or none close'))
    model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>'
    assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    info='<details class="quick-help"><summary>What is this testing?</summary><p>Repeated external sounds. Two native Stackr fits use either a newly trained event-timing CNN or the old waveform splitter. Both use frozen synth-control experts,128 mutations per event and128 timeline mutations; different counts mean different total work. Your latest winner is copied exactly. Identical audio is merged. Timing training used only synthetic schedules with component-disjoint validation/test. These listening sources overlap historical Bfxr training and are not unseen-source validation.</p></details>'
    page=page.replace('<div class="quick-topline">',info+'<div class="quick-topline">')
    (GALLERY/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],targetCount=len(records),skippedIdentical=skipped,
        optionCounts=[len(r['candidates']) for r in records],reportSha256=file_hash(ROOT/'results.json'),
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        audioFiles={str(p.relative_to(GALLERY)):file_hash(p) for p in sorted(GALLERY.glob('*/*.wav'))},uiCodeHashes=metadata['uiCodeHashes'])
    _json_write(BASE/'evaluations/learned-events-v1-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],counts=audit['optionCounts'],skipped=skipped)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','publish'])
    globals()[parser.parse_args().stage]()
