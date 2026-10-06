"""Actual native Mixr training mixtures, split by canonical constituent controls."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from multisynth.composition import CompositionRenderer
from .features import describe, FEATURE_HASH, FEATURE_CODE_HASH
from .data import file_hash, _json_write
from .experiment import audition_pcm
from .benchmark import audio_hash

ENGINES=('Boomr','Transfxr')
ROOT=Path('tools/multisynth/runs/pair-inverse-v1/data')
SOURCE=Path('tools/multisynth/runs/neural-v2/data-certified-v2')
POOL={'train':512,'val':128,'test':64}
COUNTS={'train':(4096,1024,1024),'val':(512,128,128),'test':(64,16,16)}
SEED=20261020


def component_id(source):
    value={k:source[k] for k in ('synth','params','renderSeed')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def split_for_id(key):
    bucket=int(key[:8],16)%100
    return 'train' if bucket<70 else 'val' if bucket<85 else 'test'


def check_component_splits(bank,rows):
    for row in rows:
        for key in row['componentIds']:
            if key is not None and bank[key]['split']!=row['split']:
                raise ValueError('A source component crosses dataset splits')


def code_bindings():
    files=['pair_data.py','pair_model.py','temporal.py','schema.py','features.py','data.py','experiment.py','benchmark.py']
    paths=[Path(__file__).with_name(n) for n in files]+[Path('tools/match/audio.py'),Path('tools/multisynth/renderer.py')]
    return {str(p):file_hash(p) for p in paths}


def make_bank():
    if ROOT.exists():raise FileExistsError('Preserve prior dataset')
    parent_manifest=json.loads((SOURCE/'manifest.json').read_text())
    assert parent_manifest['complete']
    parent_hashes={name:file_hash(SOURCE/(name+'.json')) for name in ENGINES}
    assert all(parent_hashes[n]==parent_manifest['files'][n]['metadataSha256'] for n in ENGINES)
    ROOT.mkdir(parents=True);bankdir=ROOT/'bank';bankdir.mkdir()
    rng=np.random.default_rng(SEED);bank={};specs={};parents={};rejections=Counter()
    with CompositionRenderer() as renderer:
        inventory=renderer.inventory
        assert parent_manifest['sourceHash']==inventory['baseSourceHash']
        frozen=dict(complete=False,inventory=inventory,codeBindings=code_bindings(),seed=SEED,
            sourceManifestSha256=file_hash(SOURCE/'manifest.json'),parentMetadataSha256=parent_hashes,featureHash=FEATURE_HASH,featureCodeHash=FEATURE_CODE_HASH,
            poolSizes=POOL,exampleCounts=COUNTS,split='canonical constituent control hash modulo100:70train15val15test',
            fixedSeeds=.5,masterVolume=.5,durationBounds=[.08,2.5])
        _json_write(ROOT/'generation.json',frozen)
        for name in ENGINES:
            path=SOURCE/(name+'.json');meta=json.loads(path.read_text());parents[name]=file_hash(path);specs[name]=meta['spec']
            assert meta['sourceHash']==inventory['baseSourceHash']
            filled=Counter()
            for i in rng.permutation(len(meta['rows'])):
                row=meta['rows'][int(i)]
                if not .08<=row['audioSamples']/44100<=2.5:rejections['parentDuration']+=1;continue
                params=deepcopy(row['params']);params['masterVolume']=.5
                for key in ('seed','instrumentSeed'):
                    if key in params:params[key]=.5
                source,wave=renderer.source(dict(synth=name,name=name,params=params,renderSeed=.5))
                key=component_id(source);split=split_for_id(key)
                if key in bank:rejections['duplicateControls']+=1;continue
                if filled[split]>=POOL[split]:continue
                if not .08<=len(wave)/44100<=2.5 or np.max(np.abs(wave))<1e-6:
                    rejections['actualDurationOrSilence']+=1;continue
                path=bankdir/(key+'.wav');sf.write(path,wave,44100,subtype='FLOAT')
                saved,rate=sf.read(path,dtype='float32');assert rate==44100 and np.array_equal(saved,wave)
                bank[key]=dict(id=key,split=split,source=source,parentRow=int(i),parentGenerator=row['generator'],
                    file=str(path),fileSha256=file_hash(path),audioHash=audio_hash(wave),samples=len(wave))
                filled[split]+=1
                if sum(filled.values())%128==0:print(json.dumps(dict(engine=name,bank=dict(filled))),flush=True)
                if all(filled[k]==v for k,v in POOL.items()):break
            if dict(filled)!=POOL:raise ValueError(f'Insufficient canonical components: {name} {filled}')
        assert frozen['codeBindings']==code_bindings() and parents==parent_hashes
        frozen.update(complete=True,specs=specs,parentMetadataSha256=parents,bank=bank,rejections=dict(rejections))
        _json_write(ROOT/'bank.json',frozen)
    print(json.dumps(dict(bankComplete=True,components=len(bank))),flush=True)


def make_rows(bank):
    rng=np.random.default_rng(SEED+1);rows=[]
    for split,counts in COUNTS.items():
        pools=[[k for k,v in bank.items() if v['split']==split and v['source']['synth']==name] for name in ENGINES]
        for kind,count in zip(('both','Boomr','Transfxr'),counts):
            for i in range(count):
                # Test mixtures pair each of the64 held-out components exactly once.
                if split=='test':ids=[pools[0][i],pools[1][i]]
                else:ids=[p[int(rng.integers(len(p)))] for p in pools]
                if kind=='Boomr':ids[1]=None
                if kind=='Transfxr':ids[0]=None
                sources=[bank[k]['source'] if k else None for k in ids]
                balance=float(rng.uniform(.2,.8)) if kind=='both' else .5
                rows.append(dict(id=f'{split}-{kind}-{i:05d}',split=split,kind=kind,componentIds=ids,
                    params=dict(sources=json.dumps(sources),balance=balance,masterVolume=.5,seed=.5)))
    check_component_splits(bank,rows);return rows


def generate_chunk(task):
    from .pair_model import PairCodec
    index,rows,specs,expected_inventory,expected_code=task
    assert expected_code==code_bindings();codec=PairCodec(specs);features=[];continuous=[];categorical=[];output=[]
    with CompositionRenderer() as renderer:
        assert renderer.inventory==expected_inventory
        for i,row in enumerate(rows):
            params,wave=renderer.render(row['params']);heard=audition_pcm(wave)
            if not len(heard) or np.max(np.abs(heard))<1e-6:raise ValueError('Silent mixture')
            unit,cat=codec.encode(params)
            # float32 knob encoding has rounding; exact label means native controls retained.
            if i%256==0:
                canonical,actual=renderer.render(params,uncached=True)
                assert canonical==params and np.array_equal(actual,wave)
            features.append(describe(heard));continuous.append(unit);categorical.append(cat)
            output.append({**row,'params':params,'audioHash':audio_hash(wave),'auditionHash':audio_hash(heard),
                           'samples':len(wave),'nativeReplayChecked':i%256==0})
            if (i+1)%256==0:print(json.dumps(dict(chunk=index,done=i+1,total=len(rows))),flush=True)
    path=ROOT/f'chunk-{index:02d}.npz'
    np.savez_compressed(path,features=np.array(features,np.float32),continuous=np.array(continuous,np.float32),categorical=np.array(categorical,np.int64))
    _json_write(path.with_suffix('.json'),output)
    assert expected_code==code_bindings()
    return index,dict(path=str(path),sha256=file_hash(path),rowsPath=str(path.with_suffix('.json')),rowsSha256=file_hash(path.with_suffix('.json')))


def generate():
    frozen=json.loads((ROOT/'bank.json').read_text());assert frozen['complete'] and frozen['codeBindings']==code_bindings()
    if (ROOT/'manifest.json').exists():raise FileExistsError('Preserve generated data')
    rows=make_rows(frozen['bank']);_json_write(ROOT/'frozen-rows.json',rows)
    tasks=[(i,rows[start:start+1536],frozen['specs'],frozen['inventory'],frozen['codeBindings']) for i,start in enumerate(range(0,len(rows),1536))]
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(generate_chunk,t) for t in tasks];chunks={}
        for f in as_completed(futures):i,value=f.result();chunks[i]=value
    arrays={k:[] for k in ('features','continuous','categorical')};outrows=[]
    for i in sorted(chunks):
        c=chunks[i];assert file_hash(c['path'])==c['sha256']
        with np.load(c['path']) as data:
            for k in arrays:arrays[k].append(data[k])
        outrows+=json.loads(Path(c['rowsPath']).read_text())
    np.savez_compressed(ROOT/'data.npz',**{k:np.concatenate(v) for k,v in arrays.items()})
    check_component_splits(frozen['bank'],outrows);_json_write(ROOT/'rows.json',outrows)
    manifest=dict(complete=True,examples=len(outrows),splits={s:[i for i,r in enumerate(outrows) if r['split']==s] for s in COUNTS},
        specs=frozen['specs'],inventory=frozen['inventory'],codeBindings=code_bindings(),bankSha256=file_hash(ROOT/'bank.json'),
        dataSha256=file_hash(ROOT/'data.npz'),rowsSha256=file_hash(ROOT/'rows.json'),frozenRowsSha256=file_hash(ROOT/'frozen-rows.json'),
        featureHash=FEATURE_HASH,featureCodeHash=FEATURE_CODE_HASH,seed=SEED,
        scope='Fixed Boomr+Transfxr pair and singletons, exact generated control labels. Component-disjoint splits; native families overlap; old baseline experts may know components. No real reference or fitted real pseudo-label enters training.')
    assert manifest['codeBindings']==frozen['codeBindings'];_json_write(ROOT/'manifest.json',manifest)
    print(json.dumps(dict(complete=True,examples=len(outrows),splits={k:len(v) for k,v in manifest['splits'].items()})),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['bank','generate']);args=parser.parse_args()
    {'bank':make_bank,'generate':generate}[args.stage]()
