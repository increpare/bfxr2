"""Frozen actual-DSP evaluation of a trained fixed Boomr/Transfxr inverse."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from multisynth.composition import CompositionRenderer
from multisynth.renderer import Renderer
from multisynth.joint_refine import MixSpace, optimize
from multisynth.coverage import verify_archived_audio, copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.pair_train import load, predict as pair_predict
from neural_invert.predict import load_model, predict
from neural_invert.coverage_mixture import load as load_temporal
from neural_invert.temporal import predict_temporal
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import write_wave, read_wave
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/pair-inverse-v1'
GALLERY=BASE/'runs/pair-inverse-v1-listening'
OLD=BASE/'listening_data/2026-10-06-off-model-transfer-v1-quick-02'
JOINT=BASE/'listening_data/2026-10-06-mixr-joint-v1-quick-02'
BOOM=BASE/'runs/specialists-v1/models/Boomr'
TRANS=BASE/'runs/native-mixture-v1/models/mixture'
METRIC=BASE/'models/preference-neural-v2.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-pair-inverse.md')
CODE=[Path(__file__)]+[Path('tools')/p for p in (
 'multisynth/joint_refine.py','multisynth/search.py','multisynth/composition.py','multisynth/renderer.py',
 'multisynth/features.py','multisynth/gesture.py','multisynth/preference.py','multisynth/soft_periodicity.py',
 'match/structure.py','match/objective.py','match/features.py','match/audio.py',
 'neural_invert/pair_train.py','neural_invert/pair_model.py','neural_invert/predict.py',
 'neural_invert/model.py','neural_invert/temporal.py','neural_invert/coverage_mixture.py',
 'neural_invert/coverage_train.py','neural_invert/experiment.py','neural_invert/features.py','neural_invert/schema.py')]


def lowpass(wave, cutoff):
    taps=np.arange(129)-64
    kernel=2*cutoff/44100*np.sinc(2*cutoff/44100*taps)*np.hamming(129)
    kernel/=kernel.sum()
    return np.convolve(wave,kernel,mode='full')[64:64+len(wave)].astype(np.float32)


def downsample_roundtrip(wave):
    reduced=lowpass(wave,5000)[::4]
    return np.interp(np.arange(len(wave)),np.arange(len(reduced))*4,reduced).astype(np.float32)


def bindings():return {str(p):file_hash(p) for p in CODE}


def freeze():
    if (ROOT/'protocol.json').exists():raise FileExistsError('Preserve frozen evaluation')
    old=json.loads((OLD/'manifest.json').read_text());joint=json.loads((JOINT/'manifest.json').read_text())
    entries=[]
    for t in old['targets']:
        later=[x for x in joint['targets'] if x['source']['name']==t['source']['name']]
        archive=JOINT if later else OLD;t=later[-1] if later else t
        cid=(t['choice']['preferredCandidateIds'][0] if t['choice']['kind']=='best' else
             next(c['id'] for c in t['candidates'] if c['role']==('previous' if later else 'soft')))
        m=joint if later else old;c=next(c for c in m['candidates'] if c['id']==cid)
        verify_archived_audio(archive,t['referenceAudio']);verify_archived_audio(archive,c['audio'])
        entries.append(dict(archive=str(archive),target=t,retained=c))
    model,meta=load(ROOT/'model')
    with CompositionRenderer() as r:inventory=r.inventory
    p=dict(complete=True,entries=entries,inventory=inventory,bindings=bindings(),planSha256=file_hash(PLAN),
        checkpointSha256=meta['checkpointHash'],dataManifestSha256=file_hash(ROOT/'data/manifest.json'),
        baselineHashes={str(q/'best.pt'):file_hash(q/'best.pt') for q in (BOOM,TRANS)},
        archiveHashes={str(q/'manifest.json'):file_hash(q/'manifest.json') for q in (OLD,JOINT)},metricSha256=file_hash(METRIC),
        seed=20261021,budgetPerExternalArm=256,
        baselinePolicy='Four proposals: Boomr rank0 alone, Transfxr mode0 alone, paired ranks1/1 balance.35, paired ranks2/2 balance.65. All source seeds and gains .5. No known native source conditioning.',
        rawPolicy='Four complete learned hypotheses, categorical argmax. Score every actual render under both frozen audio scorers.',
        perturbations='First32 native tests cycling 129tap Hamming-sinc lowpass2500Hz, quantize8bit, anti-aliased decimate to11025Hz then linear interpolation to44100Hz, lowpass+8bit. No altered inputs enter training.',
        selection='All8 external references, unchanged order. Exact archived earlier comparison plus preference-refined independent composition and preference-refined trained pair. Same256 mutation attempts, four raw proposals attempted per arm; valid starts only, failures retained; not equal total historical compute. At most3 options, exact duplicates removed.',
        scope='Fixed Boomr+Transfxr learned inverse; synthetic component-disjoint native tests, overlapping native families. External references are repeated development cases, never pair training labels. Original Bfxr historical real-fit overlap remains; old control clips retained exactly. Neither control loss nor score establishes audible likeness.')
    _json_write(ROOT/'protocol.json',p)
    _json_write(BASE/'evaluations/pair-inverse-v1-protocol.json',{k:v for k,v in p.items() if k!='entries'}|dict(
        protocolSha256=file_hash(ROOT/'protocol.json'),targets=[e['target']['source'] for e in entries]))


def verify(p):
    receipt=json.loads((BASE/'evaluations/pair-inverse-v1-protocol.json').read_text())
    assert receipt['protocolSha256']==file_hash(ROOT/'protocol.json') and p['bindings']==bindings()
    assert p['planSha256']==file_hash(PLAN) and p['dataManifestSha256']==file_hash(ROOT/'data/manifest.json')
    assert p['checkpointSha256']==file_hash(ROOT/'model/best.pt') and p['metricSha256']==file_hash(METRIC)
    for group in ('baselineHashes','archiveHashes'):
        assert all(file_hash(path)==stamp for path,stamp in p[group].items())


class Evaluation:
    def __init__(self,renderer,single):
        self.renderer=renderer;self.single=single
        self.model,self.meta=load(ROOT/'model')
        self.boom,self.bmeta=load_model(BOOM);self.trans,self.tmeta=load_temporal(TRANS)
        self.metric=PreferenceMetric.load(METRIC)
    def proposals(self,ref):
        new=pair_predict(self.model,self.meta,ref)
        b=predict(self.boom,self.bmeta,ref,self.single,per_synth=4)
        t=predict_temporal(self.trans,self.tmeta,ref,self.single,count=4)
        if min(len(b),len(t))<3:raise ValueError('Independent baseline has fewer than3 distinct proposals')
        def source(c):
            params=deepcopy(c['params']);params['masterVolume']=.5
            for k in ('seed','instrumentSeed'):
                if k in params:params[k]=.5
            return dict(synth=c['synth'],name=c['synth'],params=params,renderSeed=.5)
        baseline=[]
        for a,z,balance in [(0,None,0),(None,0,1),(1,1,.35),(2,2,.65)]:
            baseline.append(dict(sources=json.dumps([source(b[a]) if a is not None else None,source(t[z]) if z is not None else None]),balance=balance,masterVolume=.5,seed=.5))
        assert len(new)==len(baseline)==4
        return dict(trained=new,independent=baseline)
    def evaluate(self,ref,folder,refine=False,index=0):
        folder.mkdir(parents=True);soft=SoftPeriodicityObjective(ref);desc=describe(ref)
        def scores(w):return dict(soft=float(soft.score(w)),preference=float(self.metric.distances(desc,describe(w))[0]))
        def save(params,filename):
            canonical,w=self.renderer.render(params);heard=audition_pcm(w)
            if not len(heard) or np.max(np.abs(heard))<1e-6:raise ValueError('Silent prediction')
            return dict(params=canonical,**write_wave(folder/filename,w),scores=scores(heard),auditionHash=audio_hash(heard))
        arms={}
        for ai,(name,proposals) in enumerate(self.proposals(ref).items()):
            raw=[];failures=[]
            for i,params in enumerate(proposals):
                try:raw.append(save(params,f'{name}-{i}.wav'))
                except (ValueError,RuntimeError) as error:
                    failures.append(dict(index=i,params=params,error=str(error)))
            _json_write(folder/(name+'-raw.json'),dict(candidates=raw,failures=failures,attempted=len(proposals)))
            if not raw:raise ValueError('All raw hypotheses failed; exact failures preserved for diagnosis')
            row=dict(raw=raw,rawFailures=failures,rawAttempts=len(proposals),selected=min(raw,key=lambda c:c['scores']['preference']),softSelected=min(raw,key=lambda c:c['scores']['soft']))
            if refine:
                def score(params):
                    canonical,w=self.renderer.render(params);heard=audition_pcm(w)
                    if not len(heard) or np.max(np.abs(heard))<1e-6:raise ValueError('Silent refinement')
                    return canonical,float(self.metric.distances(desc,describe(heard))[0])
                fit=optimize([c['params'] for c in raw],MixSpace(self.single.specs),score,budget=256,seed=20261021+index*100+ai)
                selected=save(fit['params'],name+'-refined.wav')
                assert abs(selected['scores']['preference']-fit['score'])<1e-7
                row.update(refinement=fit,selected=selected)
            for c in [row['selected'],row['softSelected']]:
                canonical,w=self.renderer.render(c['params'],uncached=True)
                assert canonical==c['params'] and np.array_equal(w,read_wave(c))
                c['nativeReplay']=True
            arms[name]=row
        result=dict(complete=True,arms=arms);_json_write(folder/'result.json',result);return result


def run(stage):
    torch.set_num_threads(1);p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    output=ROOT/(stage+'.json')
    if output.exists():raise FileExistsError('Preserve experiment')
    rows=[]
    with CompositionRenderer() as r,Renderer() as s:
        assert r.inventory==p['inventory'] and s.inventory['sourceHash']==r.inventory['baseSourceHash']
        evaluator=Evaluation(r,s)
        if stage=='external':
            for i,e in enumerate(p['entries']):
                archive=Path(e['archive']);verify_archived_audio(archive,e['target']['referenceAudio'])
                ref,rate=sf.read(archive/e['target']['referenceAudio']['file'],dtype='float32');assert rate==44100
                row=evaluator.evaluate(ref,ROOT/'external'/f'{i:03d}',True,i);rows.append(dict(index=i,source=e['target']['source'],**row))
                print(json.dumps(dict(external=i+1,scores={k:v['selected']['scores'] for k,v in row['arms'].items()})),flush=True)
        else:
            data=json.loads((ROOT/'data/rows.json').read_text());tests=[row for row in data if row['split']=='test']
            for i in range(128):
                target=tests[i if i<96 else i-96];_,wave=r.render(target['params'],uncached=True)
                assert audio_hash(wave)==target['audioHash'];ref=audition_pcm(wave);kind='native'
                if i>=96:
                    j=(i-96)%4;kind=['lowpass','8bit','11025Hz','lowpass+8bit'][j]
                    if j in (0,3):ref=lowpass(ref,2500)
                    if j in (1,3):ref=np.round(ref*127)/127
                    if j==2:ref=downsample_roundtrip(ref)
                    ref=audition_pcm(ref)
                folder=ROOT/'native'/f'{i:03d}';row=evaluator.evaluate(ref,folder)
                sf.write(folder/'target.wav',ref,44100,subtype='PCM_16')
                objective=SoftPeriodicityObjective(ref);target_desc=describe(ref)
                def oracle_scores(heard):
                    return dict(soft=float(objective.score(heard)),preference=float(evaluator.metric.distances(target_desc,describe(heard))[0]))
                known=dict(exactMixture=oracle_scores(audition_pcm(wave)),sources=[])
                for slot,source in enumerate(json.loads(target['params']['sources'])):
                    if source is None:continue
                    sources=[None,None];sources[slot]=source
                    source_params,source_wave=r.render(dict(sources=json.dumps(sources),balance=float(slot),masterVolume=.5,seed=.5),uncached=True)
                    known['sources'].append(dict(slot=slot,params=source_params,**write_wave(folder/f'known-source-{slot}.wav',source_wave),scores=oracle_scores(audition_pcm(source_wave))))
                rows.append(dict(index=i,targetId=target['id'],structure=target['kind'],kind=kind,referenceHash=audio_hash(ref),knownSources=known,**row))
                if (i+1)%8==0:print(json.dumps(dict(native=i+1,total=128)),flush=True)
    verify(p);result=dict(complete=True,rows=rows,protocolSha256=file_hash(ROOT/'protocol.json'));_json_write(output,result)
    groups={'external':rows} if stage=='external' else {kind:[x for x in rows if x['kind']==kind] for kind in dict.fromkeys(x['kind'] for x in rows)}
    summary={kind:{metric:dict(trainedMedian=float(np.median([x['arms']['trained']['selected']['scores'][metric] for x in group])),
        independentMedian=float(np.median([x['arms']['independent']['selected']['scores'][metric] for x in group])),
        trainedLower=sum(x['arms']['trained']['selected']['scores'][metric]<x['arms']['independent']['selected']['scores'][metric] for x in group),count=len(group)) for metric in ('soft','preference')} for kind,group in groups.items()}
    _json_write(BASE/f'evaluations/pair-inverse-v1-{stage}.json',dict(complete=True,summary=summary,reportSha256=file_hash(output),protocolSha256=result['protocolSha256'],scope=p['scope']))


def gallery():
    p=json.loads((ROOT/'protocol.json').read_text());verify(p);report=json.loads((ROOT/'external.json').read_text())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json') and len(report['rows'])==8
    if GALLERY.exists():raise FileExistsError('Preserve gallery')
    GALLERY.mkdir();records=[]
    with CompositionRenderer() as r:
        assert r.inventory==p['inventory']
        for i,(e,row) in enumerate(zip(p['entries'],report['rows'])):
            folder=GALLERY/f'{i+1:03d}';folder.mkdir();archive=Path(e['archive']);t=e['target'];old=e['retained']
            for audio in (t['referenceAudio'],old['audio']):verify_archived_audio(archive,audio)
            copy_archived_audio(archive/t['referenceAudio']['file'],folder/'target.wav');copy_archived_audio(archive/old['audio']['file'],folder/'previous.wav')
            wave,_=sf.read(folder/'previous.wav',dtype='float32');seen={audio_hash(wave)}
            options=[{**old,'role':'previous','file':'previous.wav','label':'Earlier comparison','provenance':{**old['provenance'],'retainedArchive':str(archive),'retainedCandidateId':old['id'],'auditionTransform':'Exact archived PCM'}}]
            for arm in ('independent','trained'):
                c=row['arms'][arm]['selected'];params,w=r.render(c['params'],uncached=True)
                assert params==c['params'] and np.array_equal(w,read_wave(c));heard=audition_pcm(w)
                assert audio_hash(heard)==c['auditionHash']
                if c['auditionHash'] in seen:continue
                seen.add(c['auditionHash']);sf.write(folder/(arm+'.wav'),heard,44100,subtype='PCM_16')
                actual,rate=sf.read(folder/(arm+'.wav'),dtype='float32');assert rate==44100 and np.array_equal(actual,heard)
                options.append(dict(synth='Mixr',params=params,seed=0,sourceHash=p['inventory']['sourceHash'],role=arm,label='Trained mixture model' if arm=='trained' else 'Independent models combined',file=arm+'.wav',
                    provenance=dict(method='pair-inverse-v1',arm=arm,checkpointHash=p['checkpointSha256'] if arm=='trained' else None,protocolSha256=file_hash(ROOT/'protocol.json'),reportSha256=file_hash(ROOT/'external.json'),scores=c['scores'],auditionHash=c['auditionHash'],actualMixrReplay=True,searchAttempts=256)))
            assert 2<=len(options)<=3
            records.append(dict(folder=folder.name,source=t['source'],candidates=options,note='External development sound; earlier comparison and two equally refined neural approaches.'))
    metadata=dict(complete=True,experiment='pair-inverse-v1-listening',targetCount=8,galleryTitle='Does learning from mixtures help?',galleryIntro=[
        'Eight external sounds. Each compares the earlier clip with two approaches: independent models combined, and a new model trained directly on mixtures.',
        'The new model covers Boomr and Transfxr only. Both approaches get the same short fitting budget. These references were excluded from its training.',
        'Choose the closest, then how close. None close is useful evidence. Earlier Bfxr clips retain their historical training overlap.'],
        scope=p['scope'],selectionPolicy=p['selection'],protocolSha256=file_hash(ROOT/'protocol.json'),reportSha256=file_hash(ROOT/'external.json'),humanReviewRequired=True,
        uiCodeHashes={q.name:file_hash(q) for q in BASE.glob('quick_*') if q.is_file()})
    model=export_coverage(GALLERY,records,metadata)
    receipt=dict(complete=True,experimentId=model['experimentId'],targetCount=8,optionCounts=[len(x['candidates']) for x in records],resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),audioFiles={str(q.relative_to(GALLERY)):file_hash(q) for q in sorted(GALLERY.glob('*/*.wav'))})
    _json_write(BASE/'evaluations/pair-inverse-v1-listening-audit.json',receipt);print(json.dumps(receipt|dict(audioFiles=len(receipt['audioFiles']))),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['freeze','native','external','gallery']);a=p.parse_args()
    if a.stage in ('native','external'):run(a.stage)
    else:{'freeze':freeze,'gallery':gallery}[a.stage]()
