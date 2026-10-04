"""Pitch-v4 inputs with frozen temporal-v3 architectures, losses and proposals."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
import torch

from .data import _json_write, file_hash
from .pitch_features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH, describe
from .pitch_data import load_dataset, code_bindings, hash_json as _hash_json, _read
from .schema import ControlSchema
from .train import choose_device
from .temporal import (ENGINES, MODEL_POLICY, LOSS_POLICY, TemporalExpert, _schema,
                       _recipe, _epoch, balanced_weights, categorical_beam)


def _code_bindings():
    files=code_bindings()
    for name in ('pitch_temporal.py','temporal.py','acoustic.py','train.py','model.py'):
        files['neural_invert/'+name]=file_hash(Path(__file__).with_name(name))
    return {'pitchTemporalCodeHash':files['neural_invert/pitch_temporal.py'],
            'codeFiles':files,'torchVersion':str(torch.__version__),'numpyVersion':np.__version__}


def _load_data(data,engines):
    result=load_dataset(data)
    for name in engines:
        if name not in result[1]:raise ValueError('Requested engine missing from pitch dataset')
        _schema(result[1][name])
    return result


def train_temporal(data,output,engines=ENGINES,epochs=90,modes=1,device=None,batch_size=128,
                   seed=20261009,threads=1,encoder_kind='temporal'):
    """Fit independent experts, preserving every row with split-global source weights."""
    data,output=Path(data).resolve(),Path(output)
    if output.exists():raise FileExistsError('Temporal output must be fresh: '+str(output))
    recipe=_recipe(epochs,batch_size,modes,seed,threads,encoder_kind)
    engines=list(engines)
    if not engines or len(engines)!=len(set(engines)) or any(n not in ENGINES for n in engines):raise ValueError('Unsupported or empty temporal engines')
    manifest,specs,shards,metas,normalization,splits=_load_data(data,engines)
    torch.set_num_threads(threads);device=choose_device(device)
    output.mkdir(parents=True,exist_ok=False)
    report={'version':4,'complete':False,'device':str(device),'engines':engines,'trainingRecipe':recipe,'perEngine':{}}
    mean,std=(torch.tensor(normalization[key],device=device) for key in ('mean','std'))
    for name in engines:
        engine_seed=(seed+ENGINES.index(name))%(2**32);torch.manual_seed(engine_seed);np.random.seed(engine_seed)
        spec,shard=specs[name],shards[name];engine_path=output/name;engine_path.mkdir()
        weights={}
        for key in ('train','val'):
            weights[key]=torch.zeros(len(shard['features']))
            weights[key][shard[key]]=balanced_weights(metas[name]['rows'],splits[name][key])
        metadata={'version':4,'engine':name,'spec':spec,'schemaHash':_hash_json(spec),'modes':modes,'encoderKind':encoder_kind,
                  'sourceHash':manifest['sourceHash'],'featureVersion':VERSION,'featureDim':DIM,
                  'featureHash':FEATURE_HASH,'featureCodeHash':FEATURE_CODE_HASH,'ignorePeakGain':True,
                  'modelPolicy':deepcopy(MODEL_POLICY),'lossPolicy':deepcopy(LOSS_POLICY),**_code_bindings(),
                  'trainingRecipe':deepcopy(recipe),'trainingRecipeHash':_hash_json(recipe),'engineSeed':engine_seed,
                  'normalization':normalization,'normalizationHash':_hash_json(normalization),
                  'sourceDataset':deepcopy(manifest['sourceDataset']),'datasetPath':str(data),'dataManifestHash':file_hash(data/'manifest.json'),'datasetFiles':manifest['files'],
                  'splitHash':_hash_json(splits),'rowWeightsHash':_hash_json({k:v.tolist() for k,v in weights.items()}),
                  'fixedRandomness':ControlSchema(spec).fixed_randomness,'randomAnchorPolicy':'schema-defaults; renderer seed supplied explicitly'}
        model=TemporalExpert(spec,modes,encoder_kind).to(device)
        optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
        scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,epochs,eta_min=.0001)
        engine_report={'complete':False,'metadata':metadata,'trainingRecipe':deepcopy(recipe),'history':[],
                       'bestValidation':None,'bestEpoch':None,'trainRows':len(shard['train']),'validationRows':len(shard['val']),
                       'parameters':sum(p.numel() for p in model.parameters())}
        started=time.monotonic()
        for epoch in range(1,epochs+1):
            order=shard['train'][torch.randperm(len(shard['train']))]
            training=_epoch(model,shard,order,weights['train'],mean,std,batch_size,device,optimizer)
            validation=_epoch(model,shard,shard['val'],weights['val'],mean,std,batch_size,device)
            row={'epoch':epoch,'train':training,'validation':validation,'trainRows':len(order),
                 'validationRows':len(shard['val']),'learningRate':optimizer.param_groups[0]['lr'],'elapsedSeconds':time.monotonic()-started}
            engine_report['history'].append(row);scheduler.step()
            if engine_report['bestValidation'] is None or validation['total']<engine_report['bestValidation']['total']:
                engine_report.update(bestValidation=validation,bestEpoch=epoch)
                torch.save({'model':{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                            'metadata':metadata,'epoch':epoch,'validation':validation},engine_path/'best.tmp.pt')
                (engine_path/'best.tmp.pt').replace(engine_path/'best.pt')
            engine_report['checkpointHash']=file_hash(engine_path/'best.pt')
            engine_report['complete']=epoch==epochs
            _json_write(engine_path/'training.json',engine_report)
            report['perEngine'][name]=engine_report
            report['complete']=len(report['perEngine'])==len(engines) and all(r['complete'] for r in report['perEngine'].values())
            _json_write(output/'training.json',report)
            print(json.dumps({'engine':name,'epoch':epoch,'encoder':encoder_kind,'modes':modes,
                              'trainLoss':training['total'],'validationLoss':validation['total'],
                              'utilization':validation['utilization'],'device':str(device)}),flush=True)
    return report


def _validate_history(report,recipe,checkpoint,train_rows,val_rows):
    history=report.get('history',[])
    if not isinstance(history,list) or len(history)!=recipe['epochs'] or [r.get('epoch') for r in history]!=list(range(1,recipe['epochs']+1)):
        raise ValueError('Pitch training history is incomplete')
    for i,row in enumerate(history):
        if row.get('trainRows')!=train_rows or row.get('validationRows')!=val_rows:
            raise ValueError('Pitch processed-row count is incompatible')
        lr=.0001+(.001-.0001)*(1+np.cos(np.pi*i/recipe['epochs']))/2
        if not isinstance(row.get('learningRate'),(float,int)) or not np.isclose(row['learningRate'],lr,rtol=1e-12,atol=1e-15):
            raise ValueError('Pitch scheduler history is incompatible')
        if not isinstance(row.get('elapsedSeconds'),(float,int)) or row['elapsedSeconds']<0:
            raise ValueError('Pitch training timing is invalid')
        for split in ('train','validation'):
            metrics=row.get(split,{})
            if set(metrics)!={'total','energy','routingKL','utilization'}:
                raise ValueError('Pitch history metric schema is incompatible')
            if any(type(metrics[k]) not in (float,int) or not np.isfinite(metrics[k]) for k in ('total','energy','routingKL')):
                raise ValueError('Pitch history metrics are invalid')
            utilization=np.asarray(metrics['utilization'])
            if utilization.shape!=(recipe['modes'],) or not np.isfinite(utilization).all() or (utilization<0).any() or not np.isclose(utilization.sum(),1,atol=1e-5):
                raise ValueError('Pitch history mode utilization is invalid')
            if not np.isclose(metrics['total'],metrics['energy']+.01*metrics['routingKL'],rtol=1e-5,atol=1e-6):
                raise ValueError('Pitch history loss components are inconsistent')
    best=min(history,key=lambda r:r['validation']['total'])
    if best['epoch']!=checkpoint.get('epoch') or best['validation']!=checkpoint.get('validation'):
        raise ValueError('Pitch best epoch binding is incompatible')


def load_temporal(path):
    """Require completed reports and exact checkpoint, source, data and code."""
    path=Path(path)
    if path.is_dir():path=path/'best.pt'
    path=path.resolve()
    report=_read(path.parent/'training.json')
    if not path.is_file() or report.get('checkpointHash')!=file_hash(path):
        raise ValueError('Pitch checkpoint hash binding is incompatible')
    try:
        checkpoint=torch.load(path,map_location='cpu',weights_only=True)
        metadata=checkpoint['metadata'];_hash_json(metadata)
    except (ValueError,TypeError,KeyError,RuntimeError) as error:
        raise ValueError('Pitch checkpoint schema is invalid') from error
    if (report.get('complete') is not True or report.get('metadata')!=metadata
            or report.get('bestEpoch')!=checkpoint.get('epoch') or report.get('bestValidation')!=checkpoint.get('validation')):
        raise ValueError('Pitch checkpoint report binding is incompatible')
    recipe=metadata.get('trainingRecipe',{})
    expected_recipe=_recipe(recipe.get('epochs'),recipe.get('batchSize'),recipe.get('modes'),recipe.get('seed'),recipe.get('threads'),recipe.get('encoderKind'))
    if recipe!=expected_recipe or report.get('trainingRecipe')!=recipe or metadata.get('trainingRecipeHash')!=_hash_json(recipe):
        raise ValueError('Pitch training recipe binding is incompatible')
    expected={'version':4,'featureVersion':VERSION,'featureDim':DIM,'featureHash':FEATURE_HASH,
              'featureCodeHash':FEATURE_CODE_HASH,'modelPolicy':MODEL_POLICY,'lossPolicy':LOSS_POLICY,
              'ignorePeakGain':True,'modes':recipe['modes'],'encoderKind':recipe['encoderKind'],**_code_bindings()}
    if any(metadata.get(k)!=v for k,v in expected.items()):
        raise ValueError('Pitch feature/model/code policy is incompatible')
    spec=metadata.get('spec',{});_schema(spec);name=spec['name']
    if metadata.get('engine')!=name or metadata.get('schemaHash')!=_hash_json(spec):
        raise ValueError('Pitch engine/schema binding is incompatible')
    if metadata.get('engineSeed')!=(recipe['seed']+ENGINES.index(name))%(2**32):
        raise ValueError('Pitch engine seed binding is incompatible')
    parent=_read(path.parent.parent/'training.json')
    engines=parent.get('engines',[])
    if (parent.get('version')!=4 or parent.get('complete') is not True or not engines or len(set(engines))!=len(engines)
            or any(n not in ENGINES for n in engines) or name not in engines or parent.get('trainingRecipe')!=recipe
            or set(parent.get('perEngine',{}))!=set(engines) or parent['perEngine'].get(name)!=report
            or any(r.get('complete') is not True for r in parent['perEngine'].values())):
        raise ValueError('Pitch parent training report is incomplete/incompatible')
    data=Path(metadata.get('datasetPath',''))
    if not (data/'manifest.json').is_file() or metadata.get('dataManifestHash')!=file_hash(data/'manifest.json'):
        raise ValueError('Pitch dataset manifest binding is incompatible')
    manifest,specs,shards,metas,normalization,splits=_load_data(data,[name])
    if (metadata.get('sourceHash')!=manifest['sourceHash'] or metadata.get('sourceDataset')!=manifest['sourceDataset']
            or spec!=specs[name] or metadata.get('datasetFiles')!=manifest['files'] or metadata.get('splitHash')!=_hash_json(splits)):
        raise ValueError('Pitch source/dataset/schema/DSP binding is incompatible')
    if metadata.get('normalization')!=normalization or metadata.get('normalizationHash')!=_hash_json(normalization):
        raise ValueError('Pitch normalization binding is incompatible')
    weights={}
    for key in ('train','val'):
        vector=torch.zeros(len(shards[name]['features']))
        vector[shards[name][key]]=balanced_weights(metas[name]['rows'],splits[name][key]);weights[key]=vector.tolist()
    if metadata.get('rowWeightsHash')!=_hash_json(weights):
        raise ValueError('Pitch row weight binding is incompatible')
    schema=ControlSchema(spec)
    if metadata.get('fixedRandomness')!=schema.fixed_randomness or metadata.get('randomAnchorPolicy')!='schema-defaults; renderer seed supplied explicitly':
        raise ValueError('Pitch randomness policy is incompatible')
    train_rows,val_rows=len(splits[name]['train']),len(splits[name]['val'])
    if report.get('trainRows')!=train_rows or report.get('validationRows')!=val_rows:
        raise ValueError('Pitch report row counts are incompatible')
    _validate_history(report,recipe,checkpoint,train_rows,val_rows)
    model=TemporalExpert(spec,recipe['modes'],recipe['encoderKind'])
    try:model.load_state_dict(checkpoint['model'],strict=True)
    except (KeyError,RuntimeError) as error:raise ValueError('Pitch model state is incompatible') from error
    model.eval()
    if report.get('parameters')!=sum(p.numel() for p in model.parameters()) or any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError('Pitch model weights/parameter count are invalid')
    return model,dict(metadata,checkpointHash=file_hash(path),checkpointEpoch=checkpoint['epoch'])


def predict_temporal(model,metadata,wave,renderer,count=4,seed=20261010):
    """Return renderer-compatible proposals, covering modes before categorical alternatives."""
    if type(count) is not int or count<1:raise ValueError('Proposal count must be a positive integer')
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('seed must be an integer in [0, 2**32)')
    name=metadata['engine'];spec=metadata['spec'];schema=_schema(spec)
    if metadata.get('sourceHash')!=renderer.inventory['sourceHash'] or spec!=renderer.specs.get(name):raise ValueError('Temporal renderer DSP/schema mismatch')
    if model.spec!=spec or model.modes!=metadata['modes'] or model.encoder_kind!=metadata['encoderKind']:raise ValueError('Temporal model metadata mismatch')
    mean,std=(np.asarray(metadata['normalization'][key],dtype=np.float32) for key in ('mean','std'))
    device=next(model.parameters()).device
    x=torch.from_numpy((describe(wave)-mean)/std).to(device)[None]
    model.eval()
    with torch.no_grad():prediction=model(x)
    mode_logp=prediction['mode_logits'][0].log_softmax(-1).cpu().tolist()
    base=[];alternatives=[]
    for mode in range(model.modes):
        proposals=categorical_beam([logits[0,mode] for logits in prediction['categorical']],count)
        for rank,(categorical,score) in enumerate(proposals):
            (base if rank==0 else alternatives).append((score+mode_logp[mode],mode,categorical,
                                                       'mode-primary' if rank==0 else 'categorical-alternative'))
    key=lambda item:(-item[0],item[1],item[2])
    # A high categorical confidence in one mode must not spend the entire
    # proposal budget before the other numeric explanations have been tried.
    selected=sorted(base,key=lambda item:(-mode_logp[item[1]],item[1]))+sorted(alternatives,key=key)
    candidates=[];seen=set()
    for joint,mode,categorical,source in selected:
        params=schema.decode(prediction['continuous'][0,mode].cpu().numpy(),categorical)
        provenance={'method':'neural-pitch-temporal-controls','neuralRaw':True,'mode':mode,'modeProbability':float(np.exp(mode_logp[mode])),
                    'categoricalProposal':categorical,'jointLogProbability':joint,'proposalRank':len(candidates),'proposalSource':source,
                    'checkpointHash':metadata.get('checkpointHash'),'anchorSeed':seed,'encoderKind':model.encoder_kind,
                    'fixedRandomness':schema.fixed_randomness,'randomAnchorPolicy':metadata['randomAnchorPolicy'],
                    'proposalPolicy':'distinct mode primaries ranked by mode probability; fill with joint categorical beam; deduplicate canonical controls'}
        try:canonical,_=renderer.render(name,params,seed)
        except (ValueError,RuntimeError) as error:
            provenance['renderError']=str(error);canonical=params
        unit,categories=schema.encode(canonical)
        identity=(tuple(unit.tolist()),tuple(categories.tolist()))
        if identity in seen:continue
        seen.add(identity)
        candidates.append({'synth':name,'params':canonical,'seed':seed,'provenance':provenance})
        if len(candidates)==count:break
    return candidates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--engines',nargs='+',choices=ENGINES,default=list(ENGINES))
    parser.add_argument('--epochs',type=int,default=90);parser.add_argument('--modes',type=int,choices=[1,4],default=1)
    parser.add_argument('--encoder-kind',choices=['temporal','flat'],default='temporal');parser.add_argument('--device')
    parser.add_argument('--batch-size',type=int,default=128);parser.add_argument('--seed',type=int,default=20261009)
    parser.add_argument('--threads',type=int,default=1)
    args=parser.parse_args()
    train_temporal(args.data,args.output,args.engines,args.epochs,args.modes,args.device,args.batch_size,args.seed,args.threads,args.encoder_kind)


if __name__=='__main__':main()
