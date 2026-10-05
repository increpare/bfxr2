"""Fixed-epoch paired fine-tuning with commanded Transfxr pitch trajectories."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
import torch

from .data import _json_write, file_hash
from .gesture import gesture_energy, POLICY
from .temporal import load_temporal, _load_data, acoustic_energy, balanced_weights, _hash_json, TemporalExpert
from .train import choose_device


def epoch(model,shard,ids,weights,mean,std,batch_size,device,gesture_weight,optimizer=None):
    model.train(optimizer is not None)
    totals=np.zeros(3);count=0
    with torch.set_grad_enabled(optimizer is not None):
        for batch in ids.split(batch_size):
            x=(shard['features'][batch].to(device)-mean)/std
            labels={k:shard[k][batch].to(device) for k in ('continuous','categorical')}
            pred=model(x)
            acoustic=acoustic_energy(pred,labels,model.spec)[:,0]
            gesture=gesture_energy(pred,labels,model.spec)[:,0]
            w=weights[batch].to(device)
            a,g=(acoustic*w).mean(),(gesture*w).mean()
            loss=a+gesture_weight*g
            if not torch.isfinite(loss):raise ValueError('Nonfinite gesture training loss')
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),5.,error_if_nonfinite=True)
                optimizer.step()
            totals+=np.array([float(loss.detach()),float(a.detach()),float(g.detach())])*len(batch)
            count+=len(batch)
    return dict(zip(('total','acoustic','gesture'),(totals/count).tolist()))


def fit(model,shard,weights,normalization,output,metadata,gesture_weight,epochs=20,batch_size=128,device='cpu'):
    output=Path(output)
    output.mkdir(exist_ok=True,parents=True)
    if (output/'training.json').exists():raise FileExistsError('Fresh training output required')
    model.to(device)
    mean,std=(torch.tensor(normalization[k],device=device) for k in ('mean','std'))
    optimizer=torch.optim.AdamW(model.parameters(),lr=.0001,weight_decay=.0001)
    report=dict(complete=False,metadata=metadata,history=[],selection='fixed final epoch')
    started=time.monotonic()
    generator=torch.Generator().manual_seed(20261019)
    for i in range(1,epochs+1):
        ids=shard['train'][torch.randperm(len(shard['train']),generator=generator)]
        train=epoch(model,shard,ids,weights['train'],mean,std,batch_size,device,gesture_weight,optimizer)
        val=epoch(model,shard,shard['val'],weights['val'],mean,std,batch_size,device,gesture_weight)
        row=dict(epoch=i,train=train,validation=val,seconds=time.monotonic()-started)
        report['history'].append(row)
        _json_write(output/'training.json',report)
        print(json.dumps(dict(gestureWeight=gesture_weight,**row)),flush=True)
    torch.save(dict(model={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                    metadata=metadata,epoch=epochs,validation=val),output/'last.pt')
    report.update(complete=True,checkpointSha256=file_hash(output/'last.pt'))
    _json_write(output/'training.json',report)
    return report


def train(output,device=None):
    torch.set_num_threads(1)
    output=Path(output)
    if output.exists():raise FileExistsError('Fresh paired output required')
    device=choose_device(device)
    base,base_meta=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    data=Path(base_meta['datasetPath'])
    manifest,specs,shards,metas,normalization,splits=_load_data(data,['Transfxr'])
    shard=shards['Transfxr'];del shards
    weights={}
    for key in ('train','val'):
        weights[key]=torch.zeros(len(shard['features']))
        weights[key][shard[key]]=balanced_weights(metas['Transfxr']['rows'],splits['Transfxr'][key])
    for name,weight in (('control',0.),('gesture',1.)):
        torch.manual_seed(20261019);np.random.seed(20261019)
        metadata=dict(base=base_meta,sourceManifestSha256=file_hash(data/'manifest.json'),
            splitHash=_hash_json(splits['Transfxr']),gesturePolicy=POLICY,
            gestureCodeSha256=file_hash(Path(__file__).with_name('gesture.py')),trainingCodeSha256=file_hash(__file__),
            gestureWeight=weight,epochs=20,batchSize=128,seed=20261019,device=str(device),
            torchVersion=str(torch.__version__),initialCheckpointSha256=base_meta['checkpointHash'],
            recipe=dict(optimizer='AdamW',lr=.0001,weightDecay=.0001,clipNorm=5.,selection='fixed final epoch'))
        fit(deepcopy(base),shard,weights,normalization,output/name,metadata,weight,device=device)
    _json_write(output/'pair.json',dict(complete=True,arms=['control','gesture']))


def load(path):
    path=Path(path);report=json.loads((path/'training.json').read_text())
    if not report['complete'] or file_hash(path/'last.pt')!=report['checkpointSha256']:
        raise ValueError('Incomplete or altered gesture checkpoint')
    ck=torch.load(path/'last.pt',map_location='cpu',weights_only=True);meta=ck['metadata']
    if (meta!=report['metadata'] or ck['epoch']!=meta['epochs'] or len(report['history'])!=meta['epochs']
        or ck['validation']!=report['history'][-1]['validation']
        or meta['gesturePolicy']!=POLICY or meta['gestureCodeSha256']!=file_hash(Path(__file__).with_name('gesture.py'))
        or meta['trainingCodeSha256']!=file_hash(__file__)):
        raise ValueError('Incompatible gesture experiment binding')
    base=meta['base']
    _,current_base=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    if current_base!=base:raise ValueError('Frozen base bindings changed')
    model=TemporalExpert(base['spec'],base['modes'],base['encoderKind'])
    model.load_state_dict(ck['model'],strict=True);model.eval()
    if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Nonfinite checkpoint')
    return model,{**base,'checkpointHash':file_hash(path/'last.pt'),'gestureExperiment':meta}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--device')
    a=p.parse_args();train(a.output,a.device)
