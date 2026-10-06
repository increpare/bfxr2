"""Train a fixed small timing predictor on component-disjoint native Stackr data."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from torch.nn import functional as F
from multisynth.timeline import TimelineRenderer
from multisynth.event_split import split_events
from neural_invert.event_timing import features,targets,decode,TimingNet,match_events,POLICY
from neural_invert.data import file_hash,_json_write
from neural_invert.benchmark import audio_hash
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/event-timing-v1'
SOURCE=BASE/'runs/neural-v2/data-certified-v2'
ENGINES=('Bfxr','Transfxr','Boomr','Pluckr','Rustlr','Crittr','Clonkr','Squishr')
POOL={'train':16,'val':8,'test':8};COUNTS={'train':1536,'val':384,'test':384}
SEED=20261104
PLAN=Path('docs/superpowers/plans/2026-10-06-event-timing-model.md')

def bindings():
    paths=[Path(__file__),PLAN,BASE/'evaluations/event-timing-v1-bank-preflight.json',BASE/'evaluations/event-timing-v1-bank-preflight-02.json',Path('tools/neural_invert/event_timing.py'),Path('tools/multisynth/event_split.py'),
        Path('tools/neural_invert/experiment.py'),Path('tools/match/audio.py'),
        Path('tools/neural_invert/benchmark.py'),Path('tools/neural_invert/data.py')]
    return {str(p):file_hash(p) for p in paths}

def key_of(source):
    return hashlib.sha256(json.dumps({k:source[k] for k in ('synth','params')},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def split_of(key):
    n=int(key[:8],16)%100
    return 'train' if n<50 else 'val' if n<75 else 'test'

def bank():
    if ROOT.exists():raise FileExistsError('Preserve existing experiment')
    ROOT.mkdir();(ROOT/'bank').mkdir()
    sourceManifest=json.loads((SOURCE/'manifest.json').read_text());assert sourceManifest['complete']
    protocol=dict(complete=False,codeHashes=bindings(),seed=SEED,engines=ENGINES,pool=POOL,counts=COUNTS,
        sourceManifestSha256=file_hash(SOURCE/'manifest.json'),parentMetadataSha256={n:file_hash(SOURCE/(n+'.json')) for n in ENGINES},
        featurePolicy=POLICY,epochs=40,batchSize=64,learningRate=.001,weightDecay=.0001,positiveWeight=10,
        gate=dict(nativeMinimumF1=.75,nativeImprovementOverHeuristic=.10,nativeMinimumCountAccuracy=.75,
            degradationPolicy='Each4-bit and1500Hz-lowpass test F1 must not be below its heuristic comparator'),
        scope='Synthetic schedules. Canonical components and exact PCM disjoint, preset families overlap. No real audio or human-fitted patch used for timing training. No neural synth-control experts changed.')
    _json_write(ROOT/'protocol.json',protocol);rng=np.random.default_rng(SEED);saved={};seen_pcm=set();rejections=Counter()
    with TimelineRenderer() as renderer:
        protocol['inventory']=renderer.inventory
        assert sourceManifest['sourceHash']==renderer.inventory['baseSourceHash']
        for name in ENGINES:
            metadata=json.loads((SOURCE/(name+'.json')).read_text())
            assert file_hash(SOURCE/(name+'.json'))==sourceManifest['files'][name]['metadataSha256']
            fills=Counter()
            for index in rng.permutation(len(metadata['rows'])):
                row=metadata['rows'][int(index)]
                if not .06<=row['audioSamples']/44100<=.4:continue
                pp=deepcopy(row['params']);pp['masterVolume']=.5
                for k in ('seed','instrumentSeed'):
                    if k in pp:pp[k]=.5
                source,wave=renderer.source(dict(synth=name,params=pp),seed=.5)
                key=key_of(source);split=split_of(key)
                if fills[split]>=POOL[split] or key in saved:continue
                peak=float(np.max(np.abs(wave)))
                if not .06<=len(wave)/44100<=.4 or peak<1e-6:rejections['durationOrSilence']+=1;continue
                onset=int(np.flatnonzero(np.abs(wave)>.08*peak)[0])
                if onset/44100>.015:rejections['slowStart']+=1;continue
                pcm=audio_hash(wave)
                if pcm in seen_pcm:rejections['duplicateSourcePcm']+=1;continue
                seen_pcm.add(pcm);path=ROOT/'bank'/(key+'.wav');sf.write(path,wave,44100,subtype='FLOAT')
                saved[key]=dict(id=key,split=split,source=source,parentRow=int(index),parentGenerator=row['generator'],
                    pcmHash=pcm,file=str(path),fileSha256=file_hash(path),samples=len(wave),onsetSample=onset)
                fills[split]+=1
                if dict(fills)==POOL:break
            print(json.dumps(dict(engine=name,bank=dict(fills))),flush=True)
            if dict(fills)!=POOL:
                _json_write(ROOT/'bank-failure.json',dict(engine=name,fills=dict(fills),retained=saved,rejections=dict(rejections)))
                raise ValueError('Insufficient predeclared source-bank coverage')
    protocol.update(complete=True,bank=saved,rejections=dict(rejections));assert bindings()==protocol['codeHashes']
    _json_write(ROOT/'protocol.json',protocol);_json_write(BASE/'evaluations/event-timing-v1-protocol.json',protocol)

def checked():
    p=json.loads((ROOT/'protocol.json').read_text());assert p['complete'] and p['codeHashes']==bindings()
    assert p['sourceManifestSha256']==file_hash(SOURCE/'manifest.json')
    assert all(file_hash(SOURCE/(n+'.json'))==h for n,h in p['parentMetadataSha256'].items())
    return p

def data():
    protocol=checked()
    if (ROOT/'data.npz').exists():raise FileExistsError('Preserve existing data')
    rng=np.random.default_rng(SEED+1);rows=[];xx=[];yy=[]
    with TimelineRenderer() as renderer:
        assert renderer.inventory==protocol['inventory']
        for split,total in COUNTS.items():
            pools={n:[k for k,b in protocol['bank'].items() if b['split']==split and b['source']['synth']==n] for n in ENGINES}
            for i in range(total):
                count=i%3+1;starts=[0.]
                for _ in range(1,count):starts.append(starts[-1]+float(rng.uniform(.08,.3)))
                ids=[];layers=[]
                for j,start in enumerate(starts):
                    name=ENGINES[int(rng.integers(len(ENGINES)))];key=pools[name][int(rng.integers(len(pools[name])))];ids.append(key)
                    source=deepcopy(protocol['bank'][key]['source'])
                    source.update(start=start,gain=float(rng.uniform(.2,.9)),pitch=float(rng.uniform(-6,6)))
                    layers.append(source)
                params,wave=renderer.render(dict(layers=json.dumps(layers),spacing=1,masterVolume=.5,seed=.5))
                if i%128==0:
                    pp,actual=renderer.render(params,uncached=True);assert pp==params and np.array_equal(actual,wave)
                heard=audition_pcm(wave)
                xx.append(features(heard));yy.append(targets(starts))
                rows.append(dict(id=f'{split}-{i:04d}',split=split,componentIds=ids,params=params,starts=starts,
                    samples=len(heard),nativeHash=audio_hash(wave),auditionHash=audio_hash(heard)))
            print(json.dumps(dict(generated=split,count=total)),flush=True)
    np.savez_compressed(ROOT/'data.npz',features=np.array(xx,np.float32),targets=np.array(yy,np.float32))
    _json_write(ROOT/'rows.json',rows)
    manifest=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),dataSha256=file_hash(ROOT/'data.npz'),
        rowsSha256=file_hash(ROOT/'rows.json'),splits={s:[i for i,r in enumerate(rows) if r['split']==s] for s in COUNTS},
        components={s:len({k for r in rows if r['split']==s for k in r['componentIds']}) for s in COUNTS})
    assert checked()==protocol;_json_write(ROOT/'data-manifest.json',manifest)
    _json_write(BASE/'evaluations/event-timing-v1-data-audit.json',manifest)

def load_data():
    protocol=checked();manifest=json.loads((ROOT/'data-manifest.json').read_text())
    assert manifest['complete'] and manifest['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert manifest['dataSha256']==file_hash(ROOT/'data.npz') and manifest['rowsSha256']==file_hash(ROOT/'rows.json')
    data=np.load(ROOT/'data.npz');rows=json.loads((ROOT/'rows.json').read_text())
    return protocol,manifest,rows,torch.from_numpy(data['features']),torch.from_numpy(data['targets'])

def loss(model,x,y,ids,batch=64,optimizer=None):
    total=0.;model.train(optimizer is not None)
    with torch.set_grad_enabled(optimizer is not None):
        for selection in ids.split(batch):
            logits=model(x[selection]);value=F.binary_cross_entropy_with_logits(logits,y[selection],pos_weight=torch.tensor(10.))
            assert torch.isfinite(value)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True);value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.,error_if_nonfinite=True);optimizer.step()
            total+=float(value.detach())*len(selection)
    return total/len(ids)

def train():
    protocol,manifest,rows,x,y=load_data();torch.set_num_threads(1);torch.manual_seed(SEED)
    if (ROOT/'best.pt').exists():raise FileExistsError('Preserve trained checkpoint')
    model=TimingNet();optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    train_ids=torch.tensor(manifest['splits']['train']);val_ids=torch.tensor(manifest['splits']['val'])
    history=[];best=float('inf');started=time.monotonic();bestEpoch=None
    for epoch in range(1,41):
        tr=loss(model,x,y,train_ids[torch.randperm(len(train_ids))],optimizer=optimizer)
        val=loss(model,x,y,val_ids)
        history.append(dict(epoch=epoch,train=tr,validation=val,seconds=time.monotonic()-started))
        if val<best:
            best=val;bestEpoch=epoch
            torch.save(dict(model=model.state_dict(),epoch=epoch,validation=val,manifestSha256=file_hash(ROOT/'data-manifest.json'),
                protocolSha256=file_hash(ROOT/'protocol.json')),ROOT/'best.pt')
        receipt=dict(complete=epoch==40,device='cpu',history=history,bestEpoch=bestEpoch,bestValidation=best,
            parameters=sum(p.numel() for p in model.parameters()),checkpointSha256=file_hash(ROOT/'best.pt'),
            manifestSha256=file_hash(ROOT/'data-manifest.json'),protocolSha256=file_hash(ROOT/'protocol.json'))
        _json_write(ROOT/'training.json',receipt)
        print(json.dumps(history[-1]),flush=True)
    model.load_state_dict(torch.load(ROOT/'best.pt',weights_only=False)['model'])
    reproduced=loss(model,x,y,val_ids);assert abs(reproduced-best)<1e-9
    receipt['reloadedValidation']=reproduced;_json_write(ROOT/'training.json',receipt)
    _json_write(BASE/'evaluations/event-timing-v1-training-audit.json',receipt)

def transform(wave,kind):
    if kind=='native':return wave
    if kind=='4bit':return (np.round(np.clip(wave/.5,-1,1)*7)/7*.5).astype(np.float32)
    if kind=='lowpass1500':
        spectrum=np.fft.rfft(wave);spectrum[np.fft.rfftfreq(len(wave),1/44100)>1500]=0
        return np.fft.irfft(spectrum,n=len(wave)).astype(np.float32)
    raise ValueError(kind)

def summarize(rows,arm):
    counts={k:sum(r[arm][k] for r in rows) for k in ('tp','fp','fn')}
    tp,fp,fn=(counts[k] for k in ('tp','fp','fn'))
    return dict(**counts,precision=tp/max(1,tp+fp),recall=tp/max(1,tp+fn),f1=2*tp/max(1,2*tp+fp+fn),
        countAccuracy=sum(r[arm]['countCorrect'] for r in rows)/len(rows),targets=len(rows))

def evaluate():
    protocol,manifest,rows,x,y=load_data();torch.set_num_threads(1)
    if (ROOT/'evaluation.json').exists():raise FileExistsError('Preserve single test evaluation')
    training=json.loads((ROOT/'training.json').read_text());assert training['complete']
    assert file_hash(ROOT/'best.pt')==training['checkpointSha256']
    checkpoint=torch.load(ROOT/'best.pt',weights_only=False);model=TimingNet();model.load_state_dict(checkpoint['model']);model.eval()
    assert checkpoint['manifestSha256']==file_hash(ROOT/'data-manifest.json') and checkpoint['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert abs(loss(model,x,y,torch.tensor(manifest['splits']['val']))-training['bestValidation'])<1e-9
    evaluated=[]
    with TimelineRenderer() as renderer,torch.no_grad():
        assert renderer.inventory==protocol['inventory']
        for i in manifest['splits']['test']:
            row=rows[i];params,wave=renderer.render(row['params']);heard=audition_pcm(wave)
            assert params==row['params'] and audio_hash(wave)==row['nativeHash'] and audio_hash(heard)==row['auditionHash']
            np.testing.assert_allclose(features(heard),x[i].numpy(),rtol=0,atol=0)
            for kind in ('native','4bit','lowpass1500'):
                audio=transform(heard,kind);prob=model(torch.from_numpy(features(audio))[None]).sigmoid()[0].numpy()
                learned=decode(prob,len(audio));heuristic=split_events(audio)
                result=dict(id=row['id'],kind=kind,trueStarts=row['starts'][1:])
                for arm,cuts in [('learned',learned),('heuristic',heuristic)]:
                    pred=[c/44100 for c in cuts[1:-1]]
                    result[arm]=dict(**match_events(row['starts'][1:],pred),predicted=pred,countCorrect=len(pred)==len(row['starts'])-1)
                evaluated.append(result)
    summaries={k:{a:summarize([r for r in evaluated if r['kind']==k],a) for a in ('learned','heuristic')} for k in ('native','4bit','lowpass1500')}
    n=summaries['native'];gate=bool(n['learned']['f1']>=.75 and n['learned']['f1']>=n['heuristic']['f1']+.10 and n['learned']['countAccuracy']>=.75 and all(summaries[k]['learned']['f1']>=summaries[k]['heuristic']['f1'] for k in ('4bit','lowpass1500')))
    evaluation=dict(complete=True,checkpointSha256=file_hash(ROOT/'best.pt'),protocolSha256=file_hash(ROOT/'protocol.json'),
        manifestSha256=file_hash(ROOT/'data-manifest.json'),summaries=summaries,gatePassed=gate,rows=evaluated,
        scope='First fixed component-disjoint native timing evaluation. Source families overlap. Correct native event boundaries are not proof of perceptual recreation or external transfer.')
    _json_write(ROOT/'evaluation.json',evaluation);_json_write(BASE/'evaluations/event-timing-v1-evaluation.json',evaluation)
    print(json.dumps(dict(gatePassed=gate,summaries=summaries)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['bank','data','train','evaluate']);globals()[p.parse_args().stage]()
