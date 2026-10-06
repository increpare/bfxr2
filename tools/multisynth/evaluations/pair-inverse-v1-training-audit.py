"""Retain training history and independent CPU checkpoint validation."""
import json
from pathlib import Path
import torch
from neural_invert.pair_train import load, read_data, validation
from neural_invert.data import file_hash, _json_write

ROOT=Path('tools/multisynth/runs/pair-inverse-v1')
torch.set_num_threads(1)
model,meta=load(ROOT/'model')
manifest,_,_,shard,_=read_data(ROOT/'data')
report=json.loads((ROOT/'model/training.json').read_text())
replay=validation(model,shard,shard['val'],meta['normalization'],torch.device('cpu'))
difference=abs(replay['total']-report['bestValidation']['total'])
assert difference<1e-5
result=dict(complete=True,checkpointSha256=meta['checkpointHash'],trainingReportSha256=file_hash(ROOT/'model/training.json'),
    dataManifestSha256=file_hash(ROOT/'data/manifest.json'),parameters=sum(p.numel() for p in model.parameters()),
    recipe=meta['trainingRecipe'],modelPolicy=meta['modelPolicy'],lossPolicy=meta['lossPolicy'],codeBindings=meta['codeBindings'],
    bestEpoch=report['bestEpoch'],bestValidation=report['bestValidation'],nativeValidationReplay=report['validationReplay'],
    cpuValidation=replay,cpuAbsoluteDifference=difference,history=report['history'],device=meta['device'],
    torchVersion=meta['torchVersion'],scriptSha256=file_hash(__file__),
    scope='Synthetic exact control supervision for fixed Boomr+Transfxr. Best held-out parameter loss is an inversion diagnostic, not human likeness. Training loss continues falling after validation worsens; later checkpoint not selected.')
_json_write(Path('tools/multisynth/evaluations/pair-inverse-v1-training-audit.json'),result)
print(json.dumps(dict(bestEpoch=report['bestEpoch'],parameters=result['parameters'],cpuAbsoluteDifference=difference,validation=replay)),flush=True)
