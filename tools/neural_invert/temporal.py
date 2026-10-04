"""Independent temporal inverse experts and a matched flat-encoder ablation.

Frozen descriptors only; control reconstruction is not an audio quality metric.
There are no generator targets, generator heads, or shared pretraining stages.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from multisynth.renderer import Renderer
from .acoustic import POLICY as ACOUSTIC_POLICY
from .data import _json_write, file_hash, verify_dataset_files
from .features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH, describe
from .schema import ControlSchema
from .train import _load_dataset, choose_device

ENGINES = ('Bfxr', 'Transfxr', 'Pluckr')
MODEL_POLICY = {'version': 'independent-temporal-inverse-v1', 'channels': [51, 64, 128],
                'kernel': 5, 'stride': 2, 'padding': 2, 'relativeFrames': 48, 'absoluteFrames': 32,
                'hidden': 256, 'activation': 'GELU', 'pooling': 'ordered-flatten',
                'scalars': [4080, 4082], 'ignoredIndices': [4081],
                'flatEncoder': '4083-256-LayerNorm-GELU-256-LayerNorm-GELU',
                'heads': 'independent-mode-numeric-sigmoid-and-categorical-logits', 'pretraining': None}
LOSS_POLICY = {'version': 'temporal-mixture-acoustic-v1', 'temperature': .1, 'routingKLWeight': .01,
               'routing': 'unweighted-batch-mean-posterior-KL-to-uniform',
               'energy': 'per-row-per-mode-active-control-mean',
               'acoustic': {k: deepcopy(v) for k,v in ACOUSTIC_POLICY.items() if k != 'generatorWeight'},
               'generatorWeight': 0., 'normalizationStdFloor': .025,
               'rowBalance': 'split-global-mean-one-weights-native-structured-50-50; missing-stratum-full-mass'}


def _hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _schema(spec):
    schema = ControlSchema(spec)
    if spec.get('name') not in ENGINES or schema.fixed_text or not schema.continuous:
        raise ValueError('Unsupported temporal engine or control schema')
    return schema


def pack_features(features):
    """Pack frozen band-major descriptors as B×51×time and two scalars."""
    if features.ndim != 2 or features.shape[1] != DIM or not features.is_floating_point() or not torch.isfinite(features).all():
        raise ValueError('Features must be finite floating point B x 4083')
    batch = len(features)
    relative = torch.cat((features[:, :2304].reshape(batch,48,48), features[:,3840:3984].reshape(batch,3,48)), 1)
    absolute = torch.cat((features[:,2304:3840].reshape(batch,48,32), features[:,3984:4080].reshape(batch,3,32)), 1)
    return relative, absolute, features[:, [4080,4082]]


class TemporalExpert(nn.Module):
    def __init__(self, spec, modes=1, encoder_kind='temporal'):
        super().__init__()
        schema = _schema(spec)
        if type(modes) is not int or modes not in (1,4):
            raise ValueError('Temporal modes must be 1 or 4')
        if encoder_kind not in ('temporal','flat'):
            raise ValueError('Unknown encoder kind')
        self.spec, self.modes, self.encoder_kind = deepcopy(spec), modes, encoder_kind
        if encoder_kind == 'temporal':
            def stream():
                return nn.Sequential(nn.Conv1d(51,64,5,stride=2,padding=2), nn.GELU(),
                                     nn.Conv1d(64,128,5,stride=2,padding=2), nn.GELU(), nn.Flatten(1))
            self.relative, self.absolute = stream(), stream()
            self.encoder = nn.Sequential(nn.Linear(128*(12+8)+2,256),nn.GELU())
        else:
            self.encoder = nn.Sequential(nn.Linear(DIM,256),nn.LayerNorm(256),nn.GELU(),
                                         nn.Linear(256,256),nn.LayerNorm(256),nn.GELU())
        self.numeric_heads = nn.ModuleList([nn.Linear(256,len(schema.continuous)) for _ in range(modes)])
        self.category_heads = nn.ModuleList([nn.ModuleList([nn.Linear(256,len(c['values'])) for c in schema.categorical]) for _ in range(modes)])
        self.mode_head = nn.Linear(256,modes)

    def forward(self, features):
        relative, absolute, scalars = pack_features(features)
        if self.encoder_kind == 'temporal':
            hidden = self.encoder(torch.cat((self.relative(relative),self.absolute(absolute),scalars),-1))
        else:
            features = features.clone(); features[:,4081] = 0
            hidden = self.encoder(features)
        return {'continuous': torch.stack([head(hidden).sigmoid() for head in self.numeric_heads],1),
                'categorical': [torch.stack([heads[i](hidden) for heads in self.category_heads],1)
                                for i in range(len(self.category_heads[0]))],
                'mode_logits': self.mode_head(hidden)}


def acoustic_energy(prediction, labels, spec):
    """Acoustic policy, reduced over active controls independently for each row/mode."""
    schema = _schema(spec)
    names = {c['name']:i for i,c in enumerate(schema.continuous)}
    cats = {c['name']:i for i,c in enumerate(schema.categorical)}
    true, estimated = labels['continuous'], prediction['continuous']
    mask = torch.ones_like(true)
    def value(name):
        c = schema.continuous[names[name]]
        return true[:,names[name]]*(c['max']-c['min'])+c['min']
    def category(name):
        c = schema.categorical[cats[name]]
        return torch.tensor(c['values'],device=true.device)[labels['categorical'][:,cats[name]]]
    def gate(name, active):
        mask[:,names[name]] = active.to(true.dtype)
    if spec['name'] == 'Bfxr':
        for name in ('squareDuty','dutySweep'):gate(name,category('waveType')==0)
        gate('vibratoSpeed',value('vibratoDepth').abs()>1e-6)
        gate('pitch_jump_onset_percent',value('pitch_jump_amount').abs()>1e-6)
        gate('pitch_jump_onset2_percent',value('pitch_jump_2_amount').abs()>1e-6)
        gate('pitch_jump_repeat_speed',(value('pitch_jump_amount').abs()>1e-6)|(value('pitch_jump_2_amount').abs()>1e-6))
    elif spec['name'] == 'Pluckr':
        gate('tremoloRate',(value('tremolo').abs()>1e-6)|(value('vibrato').abs()>1e-6))
        gate('strum',value('strings')>1)
    elif spec['name'] == 'Transfxr':
        for name in ('morph.start','morph.end'):gate(name,category('waveTo')!=-1)
    priorities = []
    for c in schema.continuous:
        name=c['name'].lower()
        priorities.append(4. if any(k in name for k in ('pitch','frequency','vibrato')) else
                          2. if any(k in name for k in ('attack','sustain','decay','duration','release','repeat','strum')) else 1.)
    effective = mask*true.new_tensor(priorities)
    numeric = ((estimated-true[:,None]).square()*effective[:,None]).sum(-1)/effective.sum(-1).clamp(min=1)[:,None]
    octave = []
    pitch_names = ('frequency_start',) if spec['name']=='Bfxr' else ('pitch.start','pitch.end') if spec['name']=='Transfxr' else ('pitch',)
    for name in pitch_names:
        i=names[name]; c=schema.continuous[i]
        if spec['name']=='Bfxr':
            p=estimated[:,:,i]*(c['max']-c['min'])+c['min']
            delta=torch.log2((p.square()+.001)/(value(name)[:,None].square()+.001))
            active=~torch.isin(category('waveType'),torch.tensor([3,5,9],device=true.device))
            octave.append(delta.square()*active[:,None])
        else:
            octave.append(((estimated[:,:,i]-true[:,None,i])*(c['max']-c['min'])*(7 if spec['name']=='Transfxr' else 4)).square())
    discrete, active_categories = [], []
    for i,c in enumerate(schema.categorical):
        active=torch.ones(len(true),device=true.device,dtype=torch.bool)
        if c['name'].endswith('.curve'):
            prefix=c['name'][:-6]
            if prefix+'.start' in names:active=(value(prefix+'.start')-value(prefix+'.end')).abs()>1e-6
            if spec['name']=='Transfxr' and prefix=='morph':active &= category('waveTo')!=-1
        logits=prediction['categorical'][i]
        losses=-logits.log_softmax(-1).gather(-1,labels['categorical'][:,i,None,None].expand(-1,estimated.shape[1],1)).squeeze(-1)
        discrete.append(losses*active[:,None]); active_categories.append(active)
    categorical = torch.stack(discrete).sum(0)/torch.stack(active_categories).sum(0).clamp(min=1)[:,None] if discrete else torch.zeros_like(numeric)
    return 8*numeric+torch.stack(octave).mean(0)+.2*categorical


def mixture_loss(energy, mode_logits, weights=None):
    """Split-global row weights must have mean one over the complete split."""
    if energy.shape != mode_logits.shape or energy.ndim != 2 or not torch.isfinite(energy).all() or not torch.isfinite(mode_logits).all():
        raise ValueError('Mixture energies/logits must be finite B x modes')
    joint = mode_logits.log_softmax(-1)-energy/.1
    rows = -.1*joint.logsumexp(-1)
    posterior = joint.softmax(-1)
    utilization = posterior.mean(0)
    kl = (utilization*(utilization.clamp(min=1e-30).log()+np.log(energy.shape[1]))).sum() if energy.shape[1]>1 else rows.new_zeros(())
    if weights is not None:
        if weights.shape != rows.shape or not torch.isfinite(weights).all() or (weights<0).any():
            raise ValueError('Mixture weights must be finite nonnegative row values')
        rows = rows*weights
    return rows.mean()+.01*kl, {'utilization':utilization, 'routingKL':kl, 'energy':rows.mean()}


def balanced_weights(rows, indices):
    """One weight per supplied index; old/new structured rows form one stratum."""
    structured=torch.tensor([bool(rows[i].get('structured')) or rows[i].get('origin')=='structured' or rows[i].get('mode')=='structured' for i in indices])
    weights=torch.ones(len(indices),dtype=torch.float32)
    count=int(structured.sum())
    if count and count<len(indices):
        weights[structured]=len(indices)/(2*count)
        weights[~structured]=len(indices)/(2*(len(indices)-count))
    return weights


def _recipe(epochs, batch_size, modes, seed, threads, encoder_kind):
    for name,value in (('epochs',epochs),('batchSize',batch_size),('threads',threads)):
        if type(value) is not int or value<1:raise ValueError(name+' must be a positive integer')
    if type(seed) is not int or not 0<=seed<2**32:raise ValueError('seed must be an integer in [0, 2**32)')
    if type(modes) is not int or modes not in (1,4):raise ValueError('modes must be 1 or 4')
    if encoder_kind not in ('temporal','flat'):raise ValueError('Unknown encoder kind')
    return {'epochs':epochs,'batchSize':batch_size,'modes':modes,'seed':seed,'threads':threads,
            'encoderKind':encoder_kind,'learningRate':.001,
            'optimizer':{'name':'AdamW','weightDecay':.0001,'scheduler':'cosine','minimumLearningRate':.0001},
            'engineSeed':'(seed + index in Bfxr,Transfxr,Pluckr) modulo 2**32', 'gradientClipNorm':5.}


def _code_bindings():
    return {key:file_hash(Path(__file__).with_name(name)) for key,name in
            (('temporalCodeHash','temporal.py'),('acousticCodeHash','acoustic.py'),('schemaCodeHash','schema.py'),
             ('datasetCodeHash','data.py'),('originalTrainingCodeHash','train.py'),('originalModelCodeHash','model.py'))}


def _load_data(data, engines):
    """Reuse the frozen global training normalization; validate every donor shard."""
    try:
        manifest,specs,shards,mean,std=_load_dataset(data)
    except (IndexError,KeyError,TypeError) as error:
        raise ValueError('Dataset arrays or split metadata are invalid') from error
    if not set(engines)<=set(specs):raise ValueError('Requested temporal engine missing from dataset')
    metadata={}; all_splits={}
    with Renderer() as renderer:
        if renderer.inventory['sourceHash']!=manifest.get('sourceHash'):raise ValueError('Dataset DSP source is incompatible')
        for name,spec in specs.items():
            if spec!=renderer.specs.get(name) or spec.get('name')!=name:raise ValueError('Dataset control schema is incompatible')
            if name in engines:_schema(spec)
            schema=ControlSchema(spec);shard=shards[name]
            meta=json.loads((data/(name+'.json')).read_text());metadata[name]=meta
            count=len(shard['features'])
            expected={'features':(count,DIM),'continuous':(count,len(schema.continuous)),
                      'categorical':(count,len(schema.categorical))}
            for key,shape in expected.items():
                if shard[key].shape!=shape or not torch.isfinite(shard[key]).all():raise ValueError('Dataset arrays are invalid')
            if ((shard['continuous']<0)|(shard['continuous']>1)).any():raise ValueError('Dataset unit controls are invalid')
            with np.load(data/(name+'.npz'),allow_pickle=False) as raw:
                if raw['categorical'].dtype.kind not in 'iu':raise ValueError('Dataset categories must have integer dtype')
            for i,c in enumerate(schema.categorical):
                if ((shard['categorical'][:,i]<0)|(shard['categorical'][:,i]>=len(c['values']))).any():raise ValueError('Dataset categories are invalid')
            splits={key:meta[key] for key in ('train','val')};all_splits[name]=splits
            for ids in splits.values():
                if not ids or any(type(i) is not int or i<0 or i>=count for i in ids) or len(ids)!=len(set(ids)):
                    raise ValueError('Dataset split indices must be nonempty valid integers')
            if set(splits['train'])&set(splits['val']) or set(splits['train']+splits['val'])!=set(range(count)):
                raise ValueError('Dataset splits must cover rows without overlap')
            if manifest.get('splits',{}).get(name)!=splits:raise ValueError('Dataset manifest and shard split binding disagree')
            rows=meta.get('rows',[])
            if len(rows)!=count or any(not isinstance(r.get('parameterHash'),str) for r in rows):raise ValueError('Dataset row grouping is invalid')
            if {rows[i]['parameterHash'] for i in splits['train']}&{rows[i]['parameterHash'] for i in splits['val']}:
                raise ValueError('Dataset canonical controls leak across splits')
    if not np.isfinite(mean).all() or not np.isfinite(std).all():raise ValueError('Dataset normalization is invalid')
    normalization={'mean':mean.tolist(),'std':std.tolist(),'scope':'all-engine-training-rows-only','stdFloor':.025,
                   'engines':manifest['engines'],'trainRows':sum(len(s['train']) for s in shards.values()),
                   'trainingIndicesHash':_hash_json({n:s['train'] for n,s in all_splits.items()})}
    return manifest,specs,shards,metadata,normalization,all_splits


def _epoch(model,shard,ids,weights,mean,std,batch_size,device,optimizer=None):
    total=0.;energy_total=0.;routing_total=0.;utilization=np.zeros(model.modes);count=0
    model.train(optimizer is not None)
    with torch.set_grad_enabled(optimizer is not None):
        for batch in ids.split(batch_size):
            x=(shard['features'][batch].to(device)-mean)/std
            labels={key:shard[key][batch].to(device) for key in ('continuous','categorical')}
            prediction=model(x)
            loss,info=mixture_loss(acoustic_energy(prediction,labels,model.spec),prediction['mode_logits'],weights[batch].to(device))
            if not torch.isfinite(loss):raise ValueError('Nonfinite temporal training loss')
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(),5.,error_if_nonfinite=True);optimizer.step()
            total+=float(loss.detach())*len(batch)
            energy_total+=float(info['energy'].detach())*len(batch)
            routing_total+=float(info['routingKL'].detach())*len(batch)
            utilization+=info['utilization'].detach().cpu().numpy()*len(batch);count+=len(batch)
    return {'total':total/count,'energy':energy_total/count,'routingKL':routing_total/count,
            'utilization':(utilization/count).tolist()}


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
    report={'version':1,'complete':False,'device':str(device),'engines':engines,'trainingRecipe':recipe,'perEngine':{}}
    mean,std=(torch.tensor(normalization[key],device=device) for key in ('mean','std'))
    for name in engines:
        engine_seed=(seed+ENGINES.index(name))%(2**32);torch.manual_seed(engine_seed);np.random.seed(engine_seed)
        spec,shard=specs[name],shards[name];engine_path=output/name;engine_path.mkdir()
        weights={}
        for key in ('train','val'):
            weights[key]=torch.zeros(len(shard['features']))
            weights[key][shard[key]]=balanced_weights(metas[name]['rows'],splits[name][key])
        metadata={'version':1,'engine':name,'spec':spec,'schemaHash':_hash_json(spec),'modes':modes,'encoderKind':encoder_kind,
                  'sourceHash':manifest['sourceHash'],'featureVersion':VERSION,'featureDim':DIM,
                  'featureHash':FEATURE_HASH,'featureCodeHash':FEATURE_CODE_HASH,'ignorePeakGain':True,
                  'modelPolicy':deepcopy(MODEL_POLICY),'lossPolicy':deepcopy(LOSS_POLICY),**_code_bindings(),
                  'trainingRecipe':deepcopy(recipe),'trainingRecipeHash':_hash_json(recipe),'engineSeed':engine_seed,
                  'normalization':normalization,'normalizationHash':_hash_json(normalization),
                  'datasetPath':str(data),'dataManifestHash':file_hash(data/'manifest.json'),'datasetFiles':manifest['files'],
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
                            'metadata':metadata,'epoch':epoch,'validation':validation},engine_path/'best.pt')
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


def load_temporal(path):
    """Require report, exact code/DSP provenance and the bound original dataset."""
    path=Path(path)
    if path.is_dir():path=path/'best.pt'
    checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    metadata=checkpoint['metadata'];report_path=path.parent/'training.json'
    if not report_path.exists():raise ValueError('Temporal report binding is missing')
    report=json.loads(report_path.read_text())
    try:_hash_json(report)
    except (ValueError,TypeError) as error:raise ValueError('Temporal report must contain finite JSON values') from error
    if (not report.get('complete') or report.get('checkpointHash')!=file_hash(path) or report.get('metadata')!=metadata
            or report.get('bestEpoch')!=checkpoint.get('epoch') or report.get('bestValidation')!=checkpoint.get('validation')):
        raise ValueError('Temporal checkpoint report binding is incompatible')
    recipe=metadata.get('trainingRecipe',{})
    expected_recipe=_recipe(recipe.get('epochs'),recipe.get('batchSize'),recipe.get('modes'),recipe.get('seed'),recipe.get('threads'),recipe.get('encoderKind'))
    if recipe!=expected_recipe or report.get('trainingRecipe')!=recipe or metadata.get('trainingRecipeHash')!=_hash_json(recipe):
        raise ValueError('Temporal training recipe binding is incompatible')
    history=report.get('history',[])
    if len(history)!=recipe['epochs'] or [r.get('epoch') for r in history]!=list(range(1,recipe['epochs']+1)):
        raise ValueError('Temporal training history is incomplete')
    best=min(history,key=lambda r:r['validation']['total'])
    if best['epoch']!=checkpoint['epoch'] or best['validation']!=checkpoint['validation']:
        raise ValueError('Temporal best epoch binding is incompatible')
    expected={'version':1,'featureVersion':VERSION,'featureDim':DIM,'featureHash':FEATURE_HASH,
              'featureCodeHash':FEATURE_CODE_HASH,'modelPolicy':MODEL_POLICY,'lossPolicy':LOSS_POLICY,
              'ignorePeakGain':True,'modes':recipe['modes'],'encoderKind':recipe['encoderKind'],**_code_bindings()}
    if any(metadata.get(k)!=v for k,v in expected.items()):raise ValueError('Temporal feature/model/code policy is incompatible')
    spec=metadata.get('spec',{});_schema(spec);name=spec['name']
    if metadata.get('engine')!=name or metadata.get('schemaHash')!=_hash_json(spec):raise ValueError('Temporal schema binding is incompatible')
    if metadata.get('engineSeed')!=(recipe['seed']+ENGINES.index(name))%(2**32):raise ValueError('Temporal engine seed binding is incompatible')
    data=Path(metadata.get('datasetPath',''))
    if not (data/'manifest.json').is_file() or metadata.get('dataManifestHash')!=file_hash(data/'manifest.json'):
        raise ValueError('Temporal dataset manifest binding is incompatible')
    manifest,specs,shards,metas,normalization,splits=_load_data(data,[name])
    if metadata.get('sourceHash')!=manifest['sourceHash'] or spec!=specs[name] or metadata.get('datasetFiles')!=manifest['files'] or metadata.get('splitHash')!=_hash_json(splits):
        raise ValueError('Temporal dataset/schema/DSP binding is incompatible')
    if metadata.get('normalization')!=normalization or metadata.get('normalizationHash')!=_hash_json(normalization):
        raise ValueError('Temporal normalization binding is incompatible')
    weights={}
    for key in ('train','val'):
        vector=torch.zeros(len(shards[name]['features']))
        vector[shards[name][key]]=balanced_weights(metas[name]['rows'],splits[name][key]);weights[key]=vector.tolist()
    if metadata.get('rowWeightsHash')!=_hash_json(weights):raise ValueError('Temporal row weight binding is incompatible')
    schema=ControlSchema(spec)
    if metadata.get('fixedRandomness')!=schema.fixed_randomness or metadata.get('randomAnchorPolicy')!='schema-defaults; renderer seed supplied explicitly':
        raise ValueError('Temporal randomness policy is incompatible')
    for row in history:
        if row.get('trainRows')!=len(splits[name]['train']) or row.get('validationRows')!=len(splits[name]['val']):
            raise ValueError('Temporal processed-row count binding is incompatible')
    model=TemporalExpert(spec,recipe['modes'],recipe['encoderKind'])
    model.load_state_dict(checkpoint['model'],strict=True);model.eval()
    if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Temporal model weights are invalid')
    return model,dict(metadata,checkpointHash=file_hash(path),checkpointEpoch=checkpoint['epoch'])


def categorical_beam(logits,count):
    """Exact top-k joint categorical vectors for conditionally independent heads."""
    if type(count) is not int or count<1:raise ValueError('Proposal count must be a positive integer')
    beam=[([],0.)]
    for logit in logits:
        probabilities=logit.log_softmax(-1).detach().cpu()
        if probabilities.ndim!=1 or not torch.isfinite(probabilities).all():raise ValueError('Categorical logits are invalid')
        choices=sorted(enumerate(probabilities.tolist()),key=lambda pair:(-pair[1],pair[0]))[:count]
        beam=sorted([(row+[i],score+value) for row,score in beam for i,value in choices],key=lambda pair:(-pair[1],pair[0]))[:count]
    return beam


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
        provenance={'method':'neural-temporal-controls','neuralRaw':True,'mode':mode,'modeProbability':float(np.exp(mode_logp[mode])),
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
