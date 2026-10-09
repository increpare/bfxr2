"""Train the inverse model on a sfxmatch.dataset directory.

    python -m sfxmatch.train --data runs/data-1m --val runs/data-val --out runs/model-1m
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn import functional as F

from .model import InverseModel


def load_dataset(path, limit=None):
    """All shards in memory: mel/rel stay uint8, labels are padded to the widest synth."""
    path = Path(path)
    meta = json.loads((path/'meta.json').read_text())
    names = list(meta['specs'])
    parts = {key: [] for key in ('mel', 'rel', 'duration', 'continuous', 'categorical', 'generator', 'synth')}
    shards = sorted(s for s in path.glob('*.npz') if not s.name.endswith('.tmp.npz'))
    for shard in shards:
        name = shard.stem.rsplit('-', 1)[0]
        with np.load(shard) as z:
            count = len(z['duration'])
            for key in ('mel', 'rel', 'duration', 'generator'):
                parts[key].append(z[key])
            cont, cat = np.zeros((count, 32), np.float32), np.zeros((count, 8), np.int64)
            cont[:, :z['continuous'].shape[1]] = z['continuous']
            cat[:, :z['categorical'].shape[1]] = z['categorical']
            parts['continuous'].append(cont); parts['categorical'].append(cat)
            parts['synth'].append(np.full(count, names.index(name), np.int64))
    data = {key: torch.from_numpy(np.concatenate(value)) for key, value in parts.items()}
    data['generator'] = data['generator'].long()
    if limit and limit < len(data['synth']):
        keep = torch.randperm(len(data['synth']), generator=torch.Generator().manual_seed(0))[:limit]
        data = {key: value[keep] for key, value in data.items()}
    return meta['specs'], data


def augment(mel, rel, generator):
    """Feature-domain stand-ins for what real recordings add: EQ, a noise floor, onset slack."""
    batch, device = len(mel), mel.device
    chosen = torch.rand(batch, device=device, generator=generator) < .5
    freq = torch.linspace(-1, 1, mel.shape[1], device=device)
    tilt = torch.randn(batch, 1, device=device, generator=generator)*.04*freq \
        + torch.randn(batch, 1, device=device, generator=generator)*.03*torch.cos(freq*3.14159*torch.rand(batch, 1, device=device, generator=generator)*2)
    floor = torch.rand(batch, 1, 1, device=device, generator=generator)*.25*(torch.rand(batch, 1, 1, device=device, generator=generator) < .4)
    shift = int(torch.randint(0, 3, (1,), device=device, generator=generator))
    def apply(x, roll):
        y = x.float()/255 + tilt.unsqueeze(-1)
        y = (y - y.amax(dim=(1, 2), keepdim=True) + 1).clamp(0, 1)
        y = torch.maximum(y, floor)
        if roll:
            y = torch.cat((y[:, :, :roll]*0 + floor, y[:, :, :-roll]), 2)
        return torch.where(chosen[:, None, None], y*255, x.float())
    return apply(mel, shift), apply(rel, 0)


def take(data, ids, device):
    """A batch sorted by synth (so each head sees one contiguous slice) plus rows per synth."""
    ids = ids[data['synth'][ids].argsort()]
    counts = torch.bincount(data['synth'][ids], minlength=int(data['synth'].max())+1).tolist()
    return {key: value[ids].to(device) for key, value in data.items()}, counts


def step_loss(model, batch, counts, embedding):
    out = model.controls_for(embedding, batch['synth'], counts)
    loss = F.cross_entropy(model.synth(embedding), batch['synth']) + model.control_loss(
        out, batch['synth'], batch['continuous'], batch['categorical'], batch['generator'])
    return loss, out


def train(data_path, val_path, output, epochs=14, batch_size=512, lr=2e-3, limit=None, device=None, seed=0, init=None):
    torch.manual_seed(seed)
    device = torch.device(device or ('mps' if torch.backends.mps.is_available() else 'cpu'))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    specs, data = load_dataset(data_path, limit)
    _, val = load_dataset(val_path)
    model = InverseModel(specs)
    if init:  # continue from an earlier checkpoint, e.g. one trained on part of the data
        model.load_state_dict(torch.load(init, map_location='cpu', weights_only=False)['model'])
    model = model.to(device)
    count = len(data['synth'])
    steps = epochs*(count//batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=.02)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimizer, lr, total_steps=steps, pct_start=.06)
    noise = torch.Generator(device=device).manual_seed(seed)
    print(json.dumps({'rows': count, 'valRows': len(val['synth']), 'steps': steps, 'device': str(device),
                      'parameters': sum(p.numel() for p in model.parameters())}), flush=True)
    history, best, started, step = [], float('inf'), time.monotonic(), 0
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(count)
        running, seen = 0., 0
        for ids in order.split(batch_size):
            if len(ids) < batch_size:
                continue
            batch, counts = take(data, ids, device)
            mel, rel = augment(batch['mel'], batch['rel'], noise)
            loss, _ = step_loss(model, batch, counts, model.encode(mel, rel, batch['duration']))
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
            optimizer.step(); schedule.step(); step += 1
            running += float(loss.detach())*len(ids); seen += len(ids)
            if step % 200 == 0:
                print(json.dumps({'step': step, 'of': steps, 'trainLoss': round(running/seen, 4),
                                  'rowsPerSecond': round(step*batch_size/(time.monotonic()-started)),
                                  'minutes': round((time.monotonic()-started)/60, 1)}), flush=True)
        row = {'epoch': epoch+1, 'trainLoss': running/max(seen, 1), **evaluate(model, val, device),
               'minutes': (time.monotonic()-started)/60}
        history.append(row)
        print(json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in row.items()}), flush=True)
        state = {'model': {k: v.detach().cpu() for k, v in model.state_dict().items()}, 'specs': specs,
                 'epoch': epoch+1, 'val': row}
        torch.save(state, output/'last.pt')
        if row['valLoss'] < best:
            best = row['valLoss']; torch.save(state, output/'best.pt')
        (output/'history.json').write_text(json.dumps(history, indent=1))
    return history


@torch.no_grad()
def evaluate(model, val, device, batch_size=1024):
    model.eval()
    loss, correct, error, controls, count = 0., 0, 0., 0., len(val['synth'])
    for ids in torch.arange(count).split(batch_size):
        batch, counts = take(val, ids, device)
        embedding = model.encode(batch['mel'], batch['rel'], batch['duration'])
        value, out = step_loss(model, batch, counts, embedding)
        loss += float(value)*len(ids)
        correct += int((model.synth(embedding).argmax(1) == batch['synth']).sum())
        e, c = model.control_error(out, batch['synth'], batch['continuous'])
        error += e; controls += c
    return {'valLoss': loss/count, 'synthAccuracy': correct/count, 'controlMAE': error/controls}


def load(path, device='cpu'):
    state = torch.load(path, map_location='cpu', weights_only=False)
    model = InverseModel(state['specs'])
    model.load_state_dict(state['model']); model.eval()
    return model.to(device), state['specs']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True); parser.add_argument('--val', required=True)
    parser.add_argument('--out', required=True); parser.add_argument('--epochs', type=int, default=14)
    parser.add_argument('--batch-size', type=int, default=512); parser.add_argument('--lr', type=float, default=2e-3)
    parser.add_argument('--limit', type=int); parser.add_argument('--device')
    parser.add_argument('--init', help='checkpoint to continue from')
    args = parser.parse_args()
    train(args.data, args.val, args.out, args.epochs, args.batch_size, args.lr, args.limit, args.device, init=args.init)


if __name__ == '__main__':
    main()
