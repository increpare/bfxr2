"""Recompute fixed-final validation on CPU; no actual-DSP or human quality claim."""
import json
from pathlib import Path
import torch
from neural_invert.data import file_hash,_json_write
from neural_invert.gesture_train import load,epoch
from neural_invert.gesture import curve_bank,CURVES
from neural_invert.temporal import _load_data,balanced_weights

torch.set_num_threads(1)
output=Path('tools/multisynth/evaluations/gesture-v2-training-audit.json')
if output.exists():raise FileExistsError('Fresh audit required')
result=dict(complete=False,scriptSha256=file_hash(__file__),
    scope='Saved fixed-final weights; CPU and training-device validation replay using shared loss implementation; not independent formula or perceptual validation.',arms={})
data=Path('tools/multisynth/runs/temporal-v3/data')
manifest,specs,shards,metas,normalization,splits=_load_data(data,['Transfxr'])
shard=shards['Transfxr'];del shards
weights=torch.zeros(len(shard['features']))
weights[shard['val']]=balanced_weights(metas['Transfxr']['rows'],splits['Transfxr']['val'])
mean,std=(torch.tensor(normalization[k]) for k in ('mean','std'))
for arm in ('control','gesture'):
    path=Path('tools/multisynth/runs/gesture-v2/models')/arm
    model,meta=load(path);report=json.loads((path/'training.json').read_text())
    actual=epoch(model,shard,shard['val'],weights,mean,std,128,'cpu',meta['gestureExperiment']['gestureWeight'])
    saved=report['history'][-1]['validation']
    error=max(abs(actual[k]-saved[k]) for k in actual)
    print(json.dumps(dict(arm=arm,cpu=actual,saved=saved,maxError=error)),flush=True)
    # A discontinuous Steps quadrature sample differs at t=.6 between CPU/MPS
    # linspace; report CPU error rather than hiding it with a looser tolerance.
    device=meta['gestureExperiment']['device']
    model.to(device)
    replay=epoch(model,shard,shard['val'],weights,mean.to(device),std.to(device),128,device,meta['gestureExperiment']['gestureWeight'])
    replay_error=max(abs(replay[k]-saved[k]) for k in replay)
    assert replay_error<1e-6
    result['arms'][arm]=dict(checkpointSha256=meta['checkpointHash'],trainingReportSha256=file_hash(path/'training.json'),
        validationRows=len(shard['val']),epochs=len(report['history']),cpu=actual,saved=saved,maxCpuError=error,
        trainingDeviceReplay=replay,maxTrainingDeviceError=replay_error)
    print(json.dumps({arm:result['arms'][arm]}),flush=True)
cpu_bank=curve_bank(torch.linspace(0,1,256))
device_bank=curve_bank(torch.linspace(0,1,256,device=device)).cpu()
result['quadratureDeviceDifference']={name:dict(maxAbsolute=float((cpu_bank[i]-device_bank[i]).abs().max()),
    indicesOver1e5=((cpu_bank[i]-device_bank[i]).abs()>1e-5).nonzero().flatten().tolist()) for i,name in enumerate(CURVES)}
result['cpuCaveat']='CPU and MPS differ at the discontinuous Steps sample153 (t approximately .6), explaining a small CPU gesture-loss discrepancy. Saved weights reproduce on their training device; CPU totals are reported, not claimed identical.'
result['complete']=True;_json_write(output,result)
