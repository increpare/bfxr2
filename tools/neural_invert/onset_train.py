"""Train a matched pair of whole-sound/fine-onset inverse models."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .data import _json_write, file_hash
from .features import describe
from .onset import FEATURE_POLICY, onset_features
from .onset_inverse import OnsetExpert, MODEL_POLICY, fit
from .schema import ControlSchema
from .temporal import _load_data, _hash_json, _code_bindings, balanced_weights, categorical_beam, LOSS_POLICY
from .train import choose_device


def bindings():
    return {**_code_bindings(), **{n:file_hash(Path(__file__).with_name(n)) for n in
                                ('onset.py','onset_inverse.py','onset_train.py','features.py')}}


def train(data, output, engine, epochs=90, device=None, batch_size=128, seed=20261015):
    data,output=Path(data).resolve(),Path(output).resolve()
    if output.exists():
        raise FileExistsError('Use a fresh paired training directory')
    derived=json.loads((data/'manifest.json').read_text())
    if not derived.get('complete') or derived['featurePolicy']!=FEATURE_POLICY or derived['featureCodeSha256']!=file_hash(Path(__file__).with_name('onset.py')):
        raise ValueError('Incomplete/incompatible onset dataset')
    source=Path(derived['sourcePath'])
    if derived['sourceManifestSha256']!=file_hash(source/'manifest.json') or derived['files'][engine]['onsetSha256']!=file_hash(data/(engine+'.npy')):
        raise ValueError('Onset/source data changed')
    torch.set_num_threads(1)
    manifest,specs,shards,metas,normalization,splits=_load_data(source,[engine])
    shard=shards[engine]
    del shards
    onset=torch.from_numpy(np.load(data/(engine+'.npy')).astype(np.float32))
    if onset.shape!=(len(shard['features']),64,128) or not torch.isfinite(onset).all():
        raise ValueError('Invalid onset array')
    device=choose_device(device)
    mean,std=(torch.tensor(normalization[k]) for k in ('mean','std'))
    weights={}
    for key in ('train','val'):
        weights[key]=torch.zeros(len(onset))
        weights[key][shard[key]]=balanced_weights(metas[engine]['rows'],splits[engine][key])
    output.mkdir(parents=True)
    for use_onset in (False,True):
        torch.manual_seed(seed)
        np.random.seed(seed)
        model=OnsetExpert(specs[engine],use_onset=use_onset)
        metadata={'engine':engine,'spec':specs[engine],'useOnset':use_onset,
                  'modelPolicy':MODEL_POLICY,'lossPolicy':LOSS_POLICY,'featurePolicy':FEATURE_POLICY,
                  'codeBindings':bindings(),'sourceHash':manifest['sourceHash'],
                  'dataPath':str(data),'dataManifestSha256':file_hash(data/'manifest.json'),
                  'sourcePath':str(source),'sourceManifestSha256':file_hash(source/'manifest.json'),
                  'splitHash':_hash_json(splits[engine]),'normalization':normalization,
                  'epochs':epochs,'batchSize':batch_size,'seed':seed,'device':str(device),
                  'torchVersion':str(torch.__version__),'trainRows':len(shard['train']),
                  'validationRows':len(shard['val']),
                  'recipe':{'optimizer':'AdamW','lr':.001,'weightDecay':.0001,'cosineMinLr':.0001,'clipNorm':5.,'threads':1},
                  'initialWeightsHash':_hash_json({k:file_tensor_hash(v) for k,v in model.state_dict().items()})}
        fit(model,shard,onset,mean,std,weights,output/('onset' if use_onset else 'control'),metadata,
            epochs,batch_size,device)
    _json_write(output/'pair.json',{'complete':True,'engine':engine,'arms':['control','onset'],
                                  'selection':'lowest validation parameter loss per arm; no audible success claim'})


def file_tensor_hash(tensor):
    import hashlib
    return hashlib.sha256(tensor.detach().cpu().numpy().tobytes()).hexdigest()


def load(path):
    path=Path(path)
    report=json.loads((path/'training.json').read_text())
    if not report.get('complete') or report['checkpointSha256']!=file_hash(path/'best.pt'):
        raise ValueError('Incomplete or altered onset checkpoint')
    saved=torch.load(path/'best.pt',map_location='cpu',weights_only=True)
    meta=saved['metadata']
    if meta!=report['metadata'] or meta['codeBindings']!=bindings() or meta['modelPolicy']!=MODEL_POLICY or meta['featurePolicy']!=FEATURE_POLICY or meta['lossPolicy']!=LOSS_POLICY:
        raise ValueError('Incompatible onset model metadata')
    if (saved['epoch']!=report['bestEpoch'] or saved['validation']!=report['bestValidation']
            or len(report['history'])!=meta['epochs'] or report['bestValidation']!=min(x['validation'] for x in report['history'])):
        raise ValueError('Invalid onset training history')
    data,source=Path(meta['dataPath']),Path(meta['sourcePath'])
    if file_hash(data/'manifest.json')!=meta['dataManifestSha256'] or file_hash(source/'manifest.json')!=meta['sourceManifestSha256']:
        raise ValueError('Onset dataset binding changed')
    derived=json.loads((data/'manifest.json').read_text())
    if file_hash(data/(meta['engine']+'.npy'))!=derived['files'][meta['engine']]['onsetSha256']:
        raise ValueError('Onset array changed')
    model=OnsetExpert(meta['spec'],meta['useOnset'])
    model.load_state_dict(saved['model'],strict=True)
    if any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError('Nonfinite model parameters')
    model.eval()
    return model,{**meta,'checkpointSha256':file_hash(path/'best.pt')}


def predict(model,meta,wave,renderer,count=4,seed=20261015):
    if count<1 or renderer.inventory['sourceHash']!=meta['sourceHash'] or renderer.specs[meta['engine']]!=meta['spec']:
        raise ValueError('Invalid budget or renderer mismatch')
    mean,std=(np.asarray(meta['normalization'][k],np.float32) for k in ('mean','std'))
    coarse=torch.from_numpy((describe(wave)-mean)/std)[None]
    fine=torch.from_numpy(onset_features(wave))[None]
    with torch.no_grad():
        pred=model(coarse,fine)
    schema=ControlSchema(meta['spec'])
    return [{'synth':meta['engine'],'params':schema.decode(pred['continuous'][0,0].numpy(),cats),
             'seed':seed,'provenance':{'method':'neural-onset-ablation','useOnset':model.use_onset,
                                     'checkpointHash':meta['checkpointSha256'],'categoryLogProbability':score}}
            for cats,score in categorical_beam([x[0,0] for x in pred['categorical']],count)]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True);p.add_argument('--output',required=True)
    p.add_argument('--engine',required=True,choices=['Bfxr','Transfxr'])
    p.add_argument('--epochs',type=int,default=90);p.add_argument('--device');p.add_argument('--batch-size',type=int,default=128)
    p.add_argument('--seed',type=int,default=20261015)
    a=p.parse_args();train(a.data,a.output,a.engine,a.epochs,a.device,a.batch_size,a.seed)
