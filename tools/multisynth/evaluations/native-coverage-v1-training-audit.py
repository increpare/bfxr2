"""CPU replay of selected checkpoints on original/fresh validation populations."""
import json
from pathlib import Path
import torch
from neural_invert.data import file_hash,_json_write
from neural_invert.coverage_train import load,read_data,validation
from neural_invert.temporal import balanced_weights,load_temporal

torch.set_num_threads(1)
root=Path('tools/multisynth/runs/native-coverage-v1')
output=Path('tools/multisynth/evaluations/native-coverage-v1-training-audit.json')
if output.exists():raise FileExistsError('Fresh audit required')
manifest,meta,shard=read_data(root/'data');rows=meta['rows'];splits=meta['splits']
ids={k:torch.tensor(v) for k,v in splits.items()}
weights=torch.zeros(len(rows));weights[ids['oldVal']]=balanced_weights(rows,splits['oldVal'])
uniform=torch.ones(len(rows))
native=torch.tensor([i for i in splits['oldVal'] if not rows[i].get('structured')])
structured=torch.tensor([i for i in splits['oldVal'] if rows[i].get('structured')])
audit=dict(complete=False,scriptSha256=file_hash(__file__),dataManifestSha256=file_hash(root/'data/manifest.json'),
    scope='Saved-checkpoint CPU replay using shared acoustic energy; not independent formula or perceptual validation.',arms={})
base,base_meta=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
mean,std=(torch.tensor(base_meta['normalization'][k]) for k in ('mean','std'))
for arm in ('control','expanded'):
    path=root/'models'/arm;model,m=load(path);report=json.loads((path/'training.json').read_text())
    best=next(r for r in report['history'] if r['step']==report['bestStep'])
    values={key:validation(model,shard,index,w,mean,std,'cpu') for key,index,w in [
        ('originalValidation',ids['oldVal'],weights),('freshNativeValidation',ids['newVal'],uniform),
        ('originalNativeValidation',native,uniform),('originalStructuredValidation',structured,uniform)]}
    error=max(abs(values[k]-best[k]) for k in values);assert error<1e-6
    unchanged=all(torch.equal(v,base.state_dict()[k]) for k,v in model.state_dict().items())
    if report['bestStep']==0:assert unchanged
    audit['arms'][arm]=dict(checkpointSha256=m['checkpointHash'],trainingReportSha256=file_hash(path/'training.json'),
        selectedStep=report['bestStep'],updates=report['history'][-1]['step'],nativePoolRows=m['coverageExperiment']['nativePoolRows'],
        structuredPoolRows=m['coverageExperiment']['structuredPoolRows'],cpu=values,saved={k:best[k] for k in values},
        maxError=error,weightsEqualFrozenV3=unchanged)
    print(json.dumps({arm:audit['arms'][arm]}),flush=True)
targets=json.loads((root/'models/fresh-targets.json').read_text())
train={rows[i]['parameterHash'] for i in splits['oldTrain']+splits['newTrain']}
assert len(targets['rows'])==32 and len({r['parameterHash'] for r in targets['rows']})==32
assert all(r['parameterHash'] not in train and r['sourceRow'] in splits['newVal'] for r in targets['rows'])
audit.update(complete=True,freshTargetManifestSha256=file_hash(root/'models/fresh-targets.json'),freshTargetsExcluded=True)
_json_write(output,audit)
