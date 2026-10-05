"""Matched old/expanded native-data fine-tuning with equal update budgets."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import torch

from .data import file_hash,_json_write
from .temporal import load_temporal,acoustic_energy,balanced_weights,TemporalExpert
from .train import choose_device

RECIPE=dict(updates=4000,batchSize=128,nativePerBatch=64,structuredPerBatch=64,
            learningRate=.0001,weightDecay=.0001,clipNorm=5.,validateEvery=200,
            nativeSeed=20261025,structuredSeed=20261026,
            selection='lowest original balanced validation acoustic energy, including step zero')


def balanced_batch(native,structured,size,generators):
    if size<2 or size%2 or not len(native) or not len(structured):raise ValueError('Invalid balanced pools/batch')
    return torch.cat([pool[torch.randint(len(pool),(size//2,),generator=rng)] for pool,rng in zip((native,structured),generators)])


def validation(model,shard,ids,weights,mean,std,device):
    model.eval();total=0.
    with torch.no_grad():
        for batch in ids.split(128):
            labels={k:shard[k][batch].to(device) for k in ('continuous','categorical')}
            pred=model((shard['features'][batch].to(device)-mean)/std)
            total+=float((acoustic_energy(pred,labels,model.spec)[:,0]*weights[batch].to(device)).sum())
    return total/len(ids)


def read_data(path):
    path=Path(path);manifest=json.loads((path/'manifest.json').read_text())
    if (not manifest['complete'] or file_hash(path/'Transfxr.npz')!=manifest['npzSha256']
        or file_hash(path/'Transfxr.json')!=manifest['metadataSha256']
        or file_hash(Path(__file__).with_name('coverage_data.py'))!=manifest['buildCodeSha256']):
        raise ValueError('Expanded data integrity changed')
    source=Path(manifest['originalSource'])
    if (file_hash(source/'manifest.json')!=manifest['originalManifestSha256']
        or file_hash(source/'Transfxr.json')!=manifest['originalMetadataSha256']):raise ValueError('Original data changed')
    meta=json.loads((path/'Transfxr.json').read_text())
    with np.load(path/'Transfxr.npz') as packed:
        shard={k:torch.from_numpy(packed[k].astype(np.float32 if k!='categorical' else np.int64))
               for k in ('features','continuous','categorical')}
    if any(not torch.isfinite(v).all() for v in shard.values()):raise ValueError('Nonfinite expanded arrays')
    return manifest,meta,shard


def train(data,output,device=None):
    torch.set_num_threads(1);output=Path(output);data=Path(data)
    if output.exists():raise FileExistsError('Fresh matched output required')
    device=choose_device(device)
    base,base_meta=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    manifest,meta,shard=read_data(data)
    assert meta['spec']==base_meta['spec'] and manifest['sourceHash']==base_meta['sourceHash']
    splits=meta['splits'];rows=meta['rows']
    structured=lambda i:bool(rows[i].get('structured'))
    old_native=torch.tensor([i for i in splits['oldTrain'] if not structured(i)])
    old_structured=torch.tensor([i for i in splits['oldTrain'] if structured(i)])
    assert all(not structured(i) for i in splits['newTrain']+splits['newVal'])
    new_native=torch.cat((old_native,torch.tensor(splits['newTrain'])))
    validation_ids=torch.tensor(splits['oldVal']);fresh_ids=torch.tensor(splits['newVal'])
    native_val=torch.tensor([i for i in splits['oldVal'] if not structured(i)])
    structured_val=torch.tensor([i for i in splits['oldVal'] if structured(i)])
    weights=torch.zeros(len(rows));weights[validation_ids]=balanced_weights(rows,splits['oldVal'])
    fresh_weights=torch.ones(len(rows))
    mean,std=(torch.tensor(base_meta['normalization'][k],device=device) for k in ('mean','std'))
    # Freeze distinct fresh native render references before the first update.
    rng=np.random.default_rng(20261026);indices=rng.permutation(splits['newVal']);chosen=[];seen=set()
    for i in indices:
        row=rows[int(i)]
        if row['parameterHash'] in seen:continue
        seen.add(row['parameterHash']);chosen.append(dict(id=f'Transfxr-fresh-{int(i):05d}',sourceSynth='Transfxr',
            sourceParams=row['params'],sourceSeed=row['seed'],audioHash=row['audioHash'],parameterHash=row['parameterHash'],
            sourceHash=manifest['sourceHash'],sourceRow=int(i)))
        if len(chosen)==32:break
    assert len(chosen)==32
    output.mkdir(parents=True)
    _json_write(output/'fresh-targets.json',dict(dataManifestSha256=file_hash(data/'manifest.json'),rows=chosen,
        scope='Fresh native control groups; no preset-family or real-recording generalization claim'))
    for arm,native in (('control',old_native),('expanded',new_native)):
        torch.manual_seed(20261025);model=deepcopy(base).to(device)
        path=output/arm;path.mkdir()
        metadata=dict(base=base_meta,recipe=RECIPE,dataPath=str(data.resolve()),dataManifestSha256=file_hash(data/'manifest.json'),
            trainingCodeSha256=file_hash(__file__),device=str(device),torchVersion=str(torch.__version__),
            arm=arm,nativePoolRows=len(native),structuredPoolRows=len(old_structured),originalValidationRows=len(validation_ids),
            freshValidationRows=len(fresh_ids),initialCheckpointSha256=base_meta['checkpointHash'])
        report=dict(complete=False,metadata=metadata,history=[],bestStep=None,bestValidation=None)
        optimizer=torch.optim.AdamW(model.parameters(),lr=RECIPE['learningRate'],weight_decay=RECIPE['weightDecay'])
        generators=[torch.Generator().manual_seed(RECIPE[k]) for k in ('nativeSeed','structuredSeed')]
        started=time.monotonic();train_total=0.
        for step in range(RECIPE['updates']+1):
            if step:
                model.train();batch=balanced_batch(native,old_structured,RECIPE['batchSize'],generators)
                labels={k:shard[k][batch].to(device) for k in ('continuous','categorical')}
                pred=model((shard['features'][batch].to(device)-mean)/std)
                loss=acoustic_energy(pred,labels,model.spec).mean()
                if not torch.isfinite(loss):raise ValueError('Nonfinite coverage loss')
                optimizer.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),RECIPE['clipNorm'],error_if_nonfinite=True);optimizer.step()
                train_total+=float(loss.detach())
            if step%RECIPE['validateEvery']==0:
                val=validation(model,shard,validation_ids,weights,mean,std,device)
                fresh=validation(model,shard,fresh_ids,fresh_weights,mean,std,device)
                native_error=validation(model,shard,native_val,fresh_weights,mean,std,device)
                structured_error=validation(model,shard,structured_val,fresh_weights,mean,std,device)
                record=dict(step=step,originalValidation=val,freshNativeValidation=fresh,
                    originalNativeValidation=native_error,originalStructuredValidation=structured_error,
                    trainSinceLast=train_total/RECIPE['validateEvery'] if step else None,seconds=time.monotonic()-started)
                report['history'].append(record);train_total=0.
                if report['bestValidation'] is None or val<report['bestValidation']:
                    report.update(bestValidation=val,bestStep=step)
                    torch.save(dict(model={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                                    metadata=metadata,step=step,validation=val),path/'best.pt')
                report.update(complete=step==RECIPE['updates'],checkpointSha256=file_hash(path/'best.pt'))
                _json_write(path/'training.json',report)
                print(json.dumps(dict(arm=arm,**record)),flush=True)
    _json_write(output/'pair.json',dict(complete=True,arms=['control','expanded'],recipe=RECIPE))


def load(path):
    path=Path(path);report=json.loads((path/'training.json').read_text())
    if not report['complete'] or report['checkpointSha256']!=file_hash(path/'best.pt'):raise ValueError('Incomplete coverage model')
    saved=torch.load(path/'best.pt',map_location='cpu',weights_only=True);meta=saved['metadata']
    _,base_meta=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    if (meta!=report['metadata'] or meta['base']!=base_meta or meta['recipe']!=RECIPE
        or meta['trainingCodeSha256']!=file_hash(__file__) or saved['step']!=report['bestStep']
        or saved['validation']!=report['bestValidation'] or report['bestValidation']!=min(r['originalValidation'] for r in report['history'])
        or [r['step'] for r in report['history']]!=list(range(0,RECIPE['updates']+1,RECIPE['validateEvery']))):
        raise ValueError('Coverage training bindings changed')
    manifest,_,_=read_data(meta['dataPath'])
    if file_hash(Path(meta['dataPath'])/'manifest.json')!=meta['dataManifestSha256']:raise ValueError('Coverage data changed')
    model=TemporalExpert(base_meta['spec'],base_meta['modes'],base_meta['encoderKind']);model.load_state_dict(saved['model'],strict=True)
    model.eval()
    if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Nonfinite coverage checkpoint')
    return model,{**base_meta,'checkpointHash':file_hash(path/'best.pt'),'coverageExperiment':meta}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',required=True);p.add_argument('--output',required=True);p.add_argument('--device')
    a=p.parse_args();train(a.data,a.output,a.device)
