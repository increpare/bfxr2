"""Frozen fresh external transfer for whole-sound and event-wise native inversion."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.audio import prepare_target
from match.objective import MatchObjective
from match.bfxr_io import render_worker_cmd
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from multisynth.timeline import TimelineRenderer
from multisynth.joint_timeline import refine
from multisynth.event_split import split_events
from multisynth.support_objective import SupportObjective
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.cli import AUDIO_SUFFIXES,source_info
from neural_invert.predict import load_model,predict
from neural_invert.temporal import predict_temporal
from neural_invert.coverage_mixture import load as load_mixture
from neural_invert.evaluate import OriginalBfxr,rendered_candidates,refine_candidate,serializable
from neural_invert.data import file_hash,_json_write
from neural_invert.benchmark import audio_hash
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/support-transfer-v1';GALLERY=BASE/'runs/support-transfer-v1-listening'
CORPUS=Path('/Users/stephenlavelle/Documents/bfxr2/tools/targets_non_bfxr_big/tags')
SHARED=BASE/'runs/neural-v2/acoustic-model';MIXTURE=BASE/'runs/native-mixture-v1/models/mixture'
BFXR=Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
PLAN=Path('docs/superpowers/plans/2026-10-06-support-transfer.md');SEED=20261108
TAGS=('card','footstep','hit','bell','laser','collect')
ASSETS=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio_support.js','quick_listening.html',
    'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']

class Objective(SupportObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

class SourceAdapter:
    def __init__(self,timeline,renderer):self.timeline=timeline;self.specs=renderer.specs
    def render(self,synth,params,seed):
        source,wave=self.timeline.source(dict(synth=synth,params=params),seed=.5)
        return source['params'],wave

def bindings():
    files=[Path(__file__),PLAN,Path('tools/multisynth/joint_timeline.py'),Path('tools/multisynth/support_objective.py'),
        Path('tools/neural_invert/evaluate.py'),Path('tools/neural_invert/predict.py'),Path('tools/neural_invert/temporal.py'),
        Path('tools/neural_invert/features.py'),Path('tools/neural_invert/coverage_mixture.py'),Path('tools/neural_invert/schema.py'),
        Path('tools/neural_invert/experiment.py'),Path('tools/multisynth/event_split.py'),Path('tools/match/objective.py'),
        Path('tools/match/features.py'),Path('tools/match/audio.py'),Path('tools/match/optimizer.py')]
    return {str(f):file_hash(f) for f in files}

def freeze():
    if ROOT.exists():raise FileExistsError('Preserve run')
    archives={};hashes=set();pcms=set();rows=[];rejected=[]
    for path in sorted((BASE/'listening_data').glob('*/manifest.json')):
        archives[str(path)]=file_hash(path);m=json.loads(path.read_text())
        for t in m['targets']:
            hashes.add(t['source'].get('sha256'));verify_archived_audio(path.parent,t['referenceAudio'])
            wave,rate=sf.read(path.parent/t['referenceAudio']['file'],dtype='float32');assert rate==44100
            pcms.add(audio_hash(wave))
    rng=np.random.default_rng(SEED)
    for tag in TAGS:
        paths=sorted(f for f in (CORPUS/tag).rglob('*') if f.is_file() and f.suffix.lower() in AUDIO_SUFFIXES);rng.shuffle(paths)
        for f in paths:
            reason=None;info=sf.info(f)
            if not .025<=info.duration<=1.5:reason='duration'
            elif file_hash(f) in hashes:reason='prior-file'
            else:
                wave=audition_pcm(prepare_target(f))
                if not len(wave) or np.max(np.abs(wave))<1e-6:reason='silence'
                elif audio_hash(wave) in pcms:reason='prior-or-selected-pcm'
            if reason:rejected.append(dict(name=str(f.relative_to(CORPUS)),reason=reason));continue
            rows.append(dict(source=source_info(f,CORPUS),seed=SEED+1009*len(rows),samples=len(wave),
                auditionHash=audio_hash(wave),boundaries=split_events(wave)))
            pcms.add(audio_hash(wave));break
        else:raise ValueError('No eligible reference in '+tag)
    historical=json.loads(BFXR.with_name('manifest.json').read_text());by_size={}
    for entry in historical:
        f=Path(entry['path'])
        if f.is_file():by_size.setdefault(f.stat().st_size,[]).append(entry)
    for row in rows:
        path=Path(row['source']['path']);matches=[e for e in by_size.get(path.stat().st_size,[]) if file_hash(e['path'])==row['source']['sha256']]
        row['historicalBfxrMatches']=matches;row['source']['historicalBfxrSplits']=sorted({e['split'] for e in matches})
    with TimelineRenderer() as timeline:inventory=timeline.inventory
    ROOT.mkdir()
    for i,row in enumerate(rows):
        dest=ROOT/f'{i+1:03d}';dest.mkdir();wave=audition_pcm(prepare_target(row['source']['path']))
        assert audio_hash(wave)==row['auditionHash'];sf.write(dest/'target.wav',wave,44100,subtype='PCM_16');row['wavSha256']=file_hash(dest/'target.wav')
    protocol=dict(complete=True,rows=rows,rejected=rejected,priorArchives=archives,inventory=inventory,codeHashes=bindings(),
        checkpoints={str(f):file_hash(f) for f in (SHARED/'best.pt',MIXTURE/'best.pt',BFXR)},
        bfxrBackend=dict(command=render_worker_cmd(),sha256=file_hash(render_worker_cmd()[0])),
        historicalBfxrManifestSha256=file_hash(BFXR.with_name('manifest.json')),segmentBudget=128,jointBudget=512,bfxrBudget=2000,
        uiHashes={f:file_hash(BASE/f) for f in ASSETS},
        scope='Six unjudged tagged external files, excluding retained exact file/PCM. Historical Bfxr overlaps disclosed; source-family independence not certified. Frozen experts; no retraining. Each segment128 source mutations, each patch512 joint attempts. Event arms use more total work with more events. Original Bfxr has independent historical2000-budget optimizer.',
        auditionPolicy=dict(version='signal-support-half-v1',relativeAmplitudeFloor=.001,exposure='halfway through first/last above-threshold sample support; full completion also counts',playback='unchanged'))
    _json_write(ROOT/'protocol.json',protocol);_json_write(BASE/'evaluations/support-transfer-v1-protocol.json',protocol)
    print(json.dumps(dict(frozen=[dict(name=r['source']['name'],events=len(r['boundaries'])-1,bfxrOverlap=r['source']['historicalBfxrSplits']) for r in rows])),flush=True)

def checked():
    p=json.loads((ROOT/'protocol.json').read_text());assert p['complete'] and p['codeHashes']==bindings()
    assert all(file_hash(f)==h for f,h in p['checkpoints'].items()) and all(file_hash(f)==h for f,h in p['priorArchives'].items())
    assert all(file_hash(BASE/f)==h for f,h in p['uiHashes'].items())
    assert p['bfxrBackend']['command']==render_worker_cmd() and file_hash(render_worker_cmd()[0])==p['bfxrBackend']['sha256']
    assert p['historicalBfxrManifestSha256']==file_hash(BFXR.with_name('manifest.json'))
    return p

def fit(index):
    p=checked();entry=p['rows'][index];dest=ROOT/f'{index+1:03d}';torch.set_num_threads(1);started=time.monotonic()
    if (dest/'result.json').exists():raise FileExistsError('Preserve completed fit')
    assert file_hash(dest/'target.wav')==entry['wavSha256'];reference,rate=sf.read(dest/'target.wav',dtype='float32');assert rate==44100
    shared=load_model(SHARED);mixture=load_mixture(MIXTURE);options=[];arms=[]
    with Renderer() as renderer,TimelineRenderer() as timeline,BfxrRenderer(jobs=1) as bfxr:
        assert timeline.inventory==p['inventory'] and renderer.inventory['sourceHash']==timeline.inventory['baseSourceHash']
        assert all(m['sourceHash']==renderer.inventory['sourceHash'] for m in (shared[1],mixture[1]));adapter=SourceAdapter(timeline,renderer)
        def save(role,synth,params,seed,raw,provenance,source_hash):
            pcm=audition_pcm(raw);sf.write(dest/(role+'.wav'),pcm,44100,subtype='PCM_16')
            return dict(role=role,synth=synth,params=params,seed=seed,sourceHash=source_hash,file=role+'.wav',
                nativeHash=audio_hash(raw),auditionHash=audio_hash(pcm),wavSha256=file_hash(dest/(role+'.wav')),
                supportScore=float(SupportObjective(reference).score(pcm)),provenance=provenance)
        for arm,bounds in [('whole',[0,len(reference)]),('events',entry['boundaries'])]:
            if arm=='events' and bounds==[0,len(reference)]:
                options.append({**deepcopy(options[0]),'role':'events'});arms.append(dict(arm=arm,reuses='whole'));continue
            layers=[];parts=[]
            for j,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
                segment=reference[a:b];local=Objective(segment)
                proposals=predict(*shared,segment,renderer,per_synth=2)+predict_temporal(*mixture,segment,renderer,count=4)
                proposals=[{**c,'seed':.5} for c in proposals if c['synth'] in timeline.inventory['sources']]
                raw,failures=rendered_candidates(proposals,adapter,local);assert raw
                best=refine_candidate(min(raw,key=lambda c:c['score']),adapter,local,p['segmentBudget'],entry['seed']+71*j)
                source,audio=timeline.source(dict(synth=best['synth'],params=best['params']),seed=.5);assert np.array_equal(audio,best['wave'])
                gain=float(np.clip(np.sqrt(np.mean(segment**2))/max(np.sqrt(np.mean(audio**2)),1e-8),.03,.9))
                layers.append(dict(synth=best['synth'],name=best['synth'],params=best['params'],start=a/44100,gain=gain,pitch=0))
                parts.append(dict(start=a,end=b,proposed=len(proposals),valid=len(raw),failures=failures,selected=serializable(best),nativeHash=audio_hash(audio)))
            initial,raw=timeline.render(dict(layers=json.dumps(layers),seed=.5,spacing=1,masterVolume=.5))
            result=refine(initial,timeline,renderer.specs,Objective(reference),p['jointBudget'],entry['seed'],joint=True)
            detail=dict(arm=arm,boundaries=bounds,parts=parts,initialParams=initial,**{k:v for k,v in result.items() if k!='wave'})
            _json_write(dest/(arm+'-fit.json'),detail)
            pp,replay=timeline.render(result['params'],uncached=True);assert pp==result['params'] and np.array_equal(replay,result['wave'])
            c=save(arm,'Stackr',pp,0,replay,dict(origin='native-whole-or-events',neuralWeightsRetrained=False,
                boundaries=bounds,nativeSeed=.5,seedFieldMeaning='Gallery ID only; actual seed in params',segmentBudget=128,jointBudget=512),timeline.inventory['sourceHash'])
            assert abs(c['supportScore']-result['score'])<1e-6;options.append(c);arms.append(detail)
            print(json.dumps(dict(target=index+1,arm=arm,events=len(parts),score=result['score'])),flush=True)
        original=OriginalBfxr(BFXR,bfxr).approximate(reference,MatchObjective(reference),budget=2000,seed=entry['seed'])
        replay=bfxr.render(original['params'],seed=original['seed']);assert np.array_equal(replay,original['wave'])
        options.append(save('bfxr','Bfxr',original['params'],original['seed'],replay,
            {**original['provenance'],'origin':'original-bfxr','backend':p['bfxrBackend']},renderer.inventory['sourceHash']))
    result=dict(complete=True,entry=entry,arms=arms,options=options,protocolSha256=file_hash(ROOT/'protocol.json'),seconds=time.monotonic()-started)
    _json_write(dest/'result.json',result);print(json.dumps(dict(done=index+1,seconds=result['seconds'])),flush=True)
    return result

def run():
    p=checked()
    if (ROOT/'results.json').exists():raise FileExistsError('Preserve results')
    with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fit,range(6)))
    assert checked()==p;report=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),rows=rows)
    _json_write(ROOT/'results.json',report);_json_write(BASE/'evaluations/support-transfer-v1-evaluation.json',report)

def publish():
    p=checked();report=json.loads((ROOT/'results.json').read_text());assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    if GALLERY.exists():raise FileExistsError('Preserve gallery')
    GALLERY.mkdir();records=[]
    for i,row in enumerate(report['rows']):
        dest=GALLERY/f'{i+1:03d}';dest.mkdir();(dest/'target.wav').write_bytes((ROOT/dest.name/'target.wav').read_bytes())
        options=[];seen={}
        for c in row['options']:
            if c['auditionHash'] in seen:seen[c['auditionHash']]['provenance']['selectionAliases'].append(c['role']);continue
            (dest/c['file']).write_bytes((ROOT/dest.name/c['file']).read_bytes());assert file_hash(dest/c['file'])==c['wavSha256']
            option={k:c[k] for k in ('role','synth','params','seed','sourceHash','file')}|dict(label='Comparison option',
                provenance={**c['provenance'],'selectionAliases':[c['role']],'nativeHash':c['nativeHash'],'auditionHash':c['auditionHash'],
                    'supportScore':c['supportScore'],'protocolSha256':report['protocolSha256']})
            options.append(option);seen[c['auditionHash']]=option
        assert len(options)>1
        records.append(dict(folder=dest.name,source=row['entry']['source'],candidates=options,note='Fresh to listening; compare the complete gesture, pitch and texture.'))
    metadata=dict(experiment='support-transfer-v1-listening',complete=True,targetCount=6,humanReviewRequired=True,
        galleryTitle='Six fresh sounds — does event fitting transfer?',galleryIntro=[
            'Six tagged sounds not used in earlier listening rounds. Choose the closest and say how close it feels.',
            'Whole-sound fitting, event-by-event fitting and original Bfxr are compared. Identical results are merged.',
            'Newer experts were trained on synthetic sounds. Historical Bfxr overlap is recorded; these are not certified independent source families.'],
        scope=p['scope'],auditionPolicy=p['auditionPolicy'],protocolSha256=report['protocolSha256'],reportSha256=file_hash(ROOT/'results.json'),
        uiCodeHashes=p['uiHashes'],diagnosticQuestion=dict(version='quick-mismatch-v1',optional=True,trigger='similar, least-bad, or none close'))
    model=export_coverage(GALLERY,records,metadata);page=(GALLERY/'index.html').read_text()
    for old,new in [('quick_audio.js','quick_audio_support.js'),('quick_listening.js','quick_listening_diagnostic.js')]:
        needle='<script>'+(BASE/old).read_text()+'</script>';assert page.count(needle)==1
        replacement=('<script>'+(BASE/'quick_mismatch.js').read_text()+'</script>') if old=='quick_listening.js' else ''
        page=page.replace(needle,replacement+'<script>'+(BASE/new).read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>');(GALLERY/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],targetCount=6,optionCounts=[len(r['candidates']) for r in records],
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),reportSha256=file_hash(ROOT/'results.json'),
        audioFiles={str(f.relative_to(GALLERY)):file_hash(f) for f in sorted(GALLERY.glob('*/*.wav'))},uiCodeHashes=p['uiHashes'])
    _json_write(BASE/'evaluations/support-transfer-v1-listening-audit.json',audit);print(json.dumps(dict(experimentId=model['experimentId'],counts=audit['optionCounts'])),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','publish']);globals()[parser.parse_args().stage]()
