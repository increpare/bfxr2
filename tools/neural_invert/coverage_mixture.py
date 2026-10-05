"""Controlled one-versus-four complete patch predictions on expanded native data."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import torch

from .coverage_train import load as load_base, read_data, balanced_batch
from .data import file_hash, _json_write
from .temporal import TemporalExpert, acoustic_energy, mixture_loss, balanced_weights
from .train import choose_device

BASE = Path('tools/multisynth/runs/native-coverage-v1/models/expanded')
DATA = Path('tools/multisynth/runs/native-coverage-v1/data')
RECIPE = dict(updates=4000, batchSize=128, learningRate=.0001, weightDecay=.0001,
              clipNorm=5., validateEvery=200, seed=20261101, nativeSeed=20261102,
              structuredSeed=20261103, headJitter=.02, temperature=.1, routingKL=.01,
              selection='minimum original balanced validation mixture loss including step zero',
              strata='half native including expansion; half original structured')


def expand_expert(base, seed=20261101):
    if base.modes != 1:
        raise ValueError('Expansion requires a one-mode donor')
    # Preserve ambient RNG and donor. Exactly retain mode zero as an anchor.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = TemporalExpert(base.spec, 4, base.encoder_kind)
        for name in ('relative', 'absolute', 'encoder'):
            if hasattr(base, name): getattr(model, name).load_state_dict(getattr(base, name).state_dict())
        with torch.no_grad():
            for i in range(4):
                model.numeric_heads[i].load_state_dict(base.numeric_heads[0].state_dict())
                model.category_heads[i].load_state_dict(base.category_heads[0].state_dict())
                if i:
                    for p in [*model.numeric_heads[i].parameters(), *model.category_heads[i].parameters()]:
                        p.add_(torch.randn_like(p)*RECIPE['headJitter'])
            model.mode_head.weight.zero_(); model.mode_head.bias.zero_()
    return model.eval()


def energy_statistics(energy, logits, weights):
    if (energy.shape != logits.shape or energy.ndim != 2 or weights.shape != energy.shape[:1]
            or not all(torch.isfinite(x).all() for x in (energy, logits, weights)) or (weights < 0).any()):
        raise ValueError('Invalid validation energies, logits or weights')
    joint = logits.log_softmax(-1) - energy/RECIPE['temperature']
    rows = -RECIPE['temperature']*joint.logsumexp(-1)
    return dict(lossSum=float((rows*weights).sum()), bestEnergySum=float((energy.min(-1).values*weights).sum()),
                responsibilitySum=joint.softmax(-1).sum(0).cpu().tolist(),
                winnerCounts=torch.bincount(energy.argmin(-1), minlength=energy.shape[1]).cpu().tolist())


def validation(model, shard, ids, weights, mean, std, device):
    model.eval(); loss=best=0.; responsibility=np.zeros(model.modes); winners=np.zeros(model.modes, dtype=int)
    with torch.no_grad():
        for batch in ids.split(128):
            labels={k:shard[k][batch].to(device) for k in ('continuous','categorical')}
            pred=model((shard['features'][batch].to(device)-mean)/std)
            stats=energy_statistics(acoustic_energy(pred, labels, model.spec), pred['mode_logits'], weights[batch].to(device))
            loss+=stats['lossSum']; best+=stats['bestEnergySum']
            responsibility+=stats['responsibilitySum']; winners+=stats['winnerCounts']
    utilization=responsibility/len(ids)
    kl=float(np.sum(utilization*np.log(np.maximum(utilization,1e-30)*model.modes)))
    return dict(loss=loss/len(ids)+RECIPE['routingKL']*kl, bestEnergy=best/len(ids),
                responsibility=utilization.tolist(), winnerCounts=winners.tolist(), rows=len(ids))


def train(output, device=None):
    torch.set_num_threads(1); output=Path(output)
    if output.exists(): raise FileExistsError('Fresh experiment output required')
    device=choose_device(device)
    base, meta=load_base(BASE)
    manifest, data_meta, shard=read_data(DATA)
    if data_meta['spec'] != meta['spec'] or manifest['sourceHash'] != meta['sourceHash']:
        raise ValueError('Data/model incompatibility')
    splits=data_meta['splits']; rows=data_meta['rows']
    native=torch.tensor([i for i in splits['oldTrain']+splits['newTrain'] if not rows[i].get('structured')])
    structured=torch.tensor([i for i in splits['oldTrain'] if rows[i].get('structured')])
    groups=dict(original=torch.tensor(splits['oldVal']), fresh=torch.tensor(splits['newVal']),
                native=torch.tensor([i for i in splits['oldVal'] if not rows[i].get('structured')]),
                structured=torch.tensor([i for i in splits['oldVal'] if rows[i].get('structured')]))
    weights=torch.ones(len(rows)); weights[groups['original']]=balanced_weights(rows, splits['oldVal'])
    unit_weights=torch.ones(len(rows))
    mean,std=(torch.tensor(meta['normalization'][k], device=device) for k in ('mean','std'))
    output.mkdir(parents=True)
    for arm in ('single','mixture'):
        torch.manual_seed(RECIPE['seed'])
        model=(deepcopy(base) if arm=='single' else expand_expert(base, RECIPE['seed'])).to(device)
        metadata=dict(base=meta, basePath=str(BASE.resolve()), dataPath=str(DATA.resolve()),
                      dataManifestSha256=file_hash(DATA/'manifest.json'), trainingCodeSha256=file_hash(__file__),
                      recipe=RECIPE, arm=arm, modes=model.modes, device=str(device), torchVersion=str(torch.__version__),
                      nativeRows=len(native), structuredRows=len(structured))
        path=output/arm;path.mkdir()
        report=dict(complete=False,metadata=metadata,history=[],bestStep=None,bestValidation=None)
        optimizer=torch.optim.AdamW(model.parameters(), lr=RECIPE['learningRate'], weight_decay=RECIPE['weightDecay'])
        generators=[torch.Generator().manual_seed(RECIPE[k]) for k in ('nativeSeed','structuredSeed')]
        start=time.monotonic(); total=0.
        for step in range(RECIPE['updates']+1):
            if step:
                model.train();batch=balanced_batch(native, structured, RECIPE['batchSize'], generators)
                pred=model((shard['features'][batch].to(device)-mean)/std)
                labels={k:shard[k][batch].to(device) for k in ('continuous','categorical')}
                loss,_=mixture_loss(acoustic_energy(pred,labels,model.spec),pred['mode_logits'])
                if not torch.isfinite(loss): raise ValueError('Nonfinite training loss')
                optimizer.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), RECIPE['clipNorm'], error_if_nonfinite=True)
                optimizer.step();total+=float(loss.detach())
            if step % RECIPE['validateEvery'] == 0:
                values={name:validation(model,shard,ids,weights if name=='original' else unit_weights,mean,std,device)
                        for name,ids in groups.items()}
                record=dict(step=step,validation=values,trainSinceLast=total/RECIPE['validateEvery'] if step else None,
                            seconds=time.monotonic()-start)
                total=0.;report['history'].append(record);val=values['original']['loss']
                if report['bestValidation'] is None or val<report['bestValidation']:
                    report.update(bestStep=step,bestValidation=val)
                    torch.save(dict(model={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
                                    metadata=metadata,step=step,validation=val),path/'best.pt')
                report.update(complete=step==RECIPE['updates'],checkpointSha256=file_hash(path/'best.pt'))
                _json_write(path/'training.json',report)
                print(json.dumps(dict(arm=arm,step=step,original=val,fresh=values['fresh']['loss'],
                                      utilization=values['original']['responsibility'],seconds=record['seconds'])),flush=True)
    _json_write(output/'pair.json',dict(complete=True,recipe=RECIPE,arms=['single','mixture']))


def load(path):
    path=Path(path);report=json.loads((path/'training.json').read_text())
    if not report['complete'] or file_hash(path/'best.pt')!=report['checkpointSha256']:
        raise ValueError('Incomplete or altered mixture run')
    saved=torch.load(path/'best.pt',map_location='cpu',weights_only=True);meta=saved['metadata']
    expected_modes={'single':1,'mixture':4}.get(meta['arm'])
    if (meta!=report['metadata'] or meta['recipe']!=RECIPE or meta['modes']!=expected_modes
            or meta['trainingCodeSha256']!=file_hash(__file__)
            or saved['step']!=report['bestStep'] or saved['validation']!=report['bestValidation']
            or report['bestValidation']!=min(r['validation']['original']['loss'] for r in report['history'])
            or [r['step'] for r in report['history']]!=list(range(0,RECIPE['updates']+1,RECIPE['validateEvery']))):
        raise ValueError('Mixture training bindings changed')
    _,base_meta=load_base(meta['basePath'])
    if meta['base']!=base_meta or file_hash(Path(meta['dataPath'])/'manifest.json')!=meta['dataManifestSha256']:
        raise ValueError('Mixture donor/data changed')
    read_data(meta['dataPath'])
    model=TemporalExpert(base_meta['spec'],meta['modes'],base_meta['encoderKind'])
    model.load_state_dict(saved['model'],strict=True);model.eval()
    if any(not torch.isfinite(p).all() for p in model.parameters()):raise ValueError('Nonfinite mixture checkpoint')
    return model,{**base_meta,'modes':meta['modes'],'checkpointHash':file_hash(path/'best.pt'),'mixtureExperiment':meta}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--device')
    a=p.parse_args();train(a.output,a.device)
