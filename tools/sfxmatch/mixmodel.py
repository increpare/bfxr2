"""Inverse model for Mixr: which one or two synths, each one's controls, and the balance.

A mix is a set, so nothing here depends on the order of its sources. Which
synths are present is a multi-label output. Each synth's head reads the sound
plus an embedding of its partner and predicts that synth's controls. When the
same synth appears twice its head fills two slots and the loss takes whichever
assignment of slots to sources fits better, flipping the balance to match.

    python -m sfxmatch.mixmodel --data runs/mix-1m --val runs/mix-val --out runs/mixmodel \
        --init runs/model-1m/best.pt
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from neural_invert.schema import ControlSchema
from .mel import BANDS, FRAMES, REL_FRAMES, describe
from .model import BINS, InverseModel, expected_unit, proposals, soft_bins
from .train import augment

SINGLE, PAIR, TWIN = 0, 1, 2      # one sound, two different synths, the same synth twice


class MixModel(InverseModel):
    def __init__(self, specs, width=1024):
        super().__init__(specs, width=512)
        synths = len(self.names)
        del self.synth
        flat = 384*(BANDS//32)*(FRAMES//32) + 256*(BANDS//8)*(REL_FRAMES//8)
        self.embed = nn.Sequential(nn.Linear(flat+1, width), nn.GELU(), nn.Dropout(.1))
        self.kind = nn.Linear(width, 3)
        self.present = nn.Linear(width, synths)
        self.partner = nn.Embedding(synths+1, 64)          # the other source; the last row means "none"
        self.slot = self.G + self.C*BINS + self.K*self.V
        self.heads = nn.ModuleList(nn.Sequential(nn.Linear(width+64, 512), nn.GELU(), nn.Linear(512, 2*self.slot))
                                   for _ in range(synths))
        self.balance = nn.Sequential(nn.Linear(width+128, 256), nn.GELU(), nn.Linear(256, BINS))

    def slots(self, embedding, synth, partner, counts=None):
        """Both slots of each row's head. With counts, rows are sorted by synth; otherwise synth is one index."""
        x = torch.cat((embedding, self.partner(partner)), 1)
        if counts is None:
            raw = self.heads[synth](x)
            synth = torch.full((len(x),), synth, device=x.device)
        else:
            parts, start = [], 0
            for index, count in enumerate(counts):
                if count:
                    parts.append(self.heads[index](x[start:start+count]))
                start += count
            raw = torch.cat(parts)
        raw = raw.view(len(x), 2, self.slot)
        return self.split(raw[:, 0], synth), self.split(raw[:, 1], synth)

    def balance_logits(self, embedding, first, second):
        return self.balance(torch.cat((embedding, self.partner(first), self.partner(second)), 1))

    def loss(self, batch, counts, embedding):
        """-> (loss, parts for metrics). `batch` comes from prepare()."""
        none = len(self.names)
        synth, kind, rows = batch['synth'], batch['kind'], len(embedding)
        present = torch.zeros(rows, none+1, device=embedding.device)
        present.scatter_(1, torch.where(synth < 0, none, synth), 1.)
        structure = F.cross_entropy(self.kind(embedding), kind) + \
            4*F.binary_cross_entropy_with_logits(self.present(embedding), present[:, :none])

        row, source, same = batch['item_row'], batch['item_source'], batch['item_same']
        first, second = self.slots(embedding[row], batch['item_synth'], batch['item_partner'], counts)
        target = lambda which: (batch['continuous'][row, which], batch['categorical'][row, which], batch['generator'][row, which])
        straight = self.row_loss(first, batch['item_synth'], *target(source))
        controls = torch.zeros(rows, device=embedding.device).index_add_(0, row[~same], straight[~same])
        controls = controls/(kind == PAIR).float().add(1)          # a pair has two items, average them

        logits = self.balance_logits(embedding, torch.where(synth[:, 0] < 0, none, synth[:, 0]),
                                     torch.where(synth[:, 1] < 0, none, synth[:, 1])).log_softmax(-1)
        level = -(soft_bins(batch['balance'])*logits).sum(-1)
        flipped = -(soft_bins(1-batch['balance'])*logits).sum(-1)
        total = controls + level*(kind == PAIR)
        if same.any():
            pick = lambda out: {key: value[same] for key, value in out.items()}
            twin, other = batch['item_synth'][same], 1-source
            cut = lambda which: tuple(value[same] for value in target(which))
            as_listed = (straight[same] + self.row_loss(pick(second), twin, *cut(other)))/2 + level[row[same]]
            swapped = (self.row_loss(pick(first), twin, *cut(other)) + self.row_loss(pick(second), twin, *cut(source)))/2 \
                + flipped[row[same]]
            total = total.index_add(0, row[same], torch.minimum(as_listed, swapped))
        return structure + total.mean(), (first, logits)


def prepare(data, ids, device):
    """A batch plus its head items: one per source, sorted by synth so each head sees one slice."""
    batch = {key: value[ids] for key, value in data.items() if key != 'synths'}
    synth = batch['synth'] = batch['synth'].long()
    batch['categorical'], batch['generator'] = batch['categorical'].long(), batch['generator'].long()
    two = synth[:, 1] >= 0
    same = two & (synth[:, 0] == synth[:, 1])
    pair = two & ~same
    batch['kind'] = two.long() + same.long()
    rows, none = torch.arange(len(ids)), int(data['synths'])
    item = {'item_row': torch.cat((rows, rows[pair])),
            'item_source': torch.cat((torch.zeros(len(ids), dtype=torch.long), torch.ones(int(pair.sum()), dtype=torch.long))),
            'item_synth': torch.cat((synth[:, 0], synth[pair, 1])),
            'item_partner': torch.cat((torch.where(two, synth[:, 1], none), synth[pair, 0])),
            'item_same': torch.cat((same, torch.zeros(int(pair.sum()), dtype=torch.bool)))}
    order = item['item_synth'].argsort(stable=True)
    batch.update({key: value[order] for key, value in item.items()})
    counts = torch.bincount(batch['item_synth'], minlength=none).tolist()
    return {key: value.to(device) for key, value in batch.items()}, counts


def load_dataset(path, limit=None):
    path = Path(path)
    specs = json.loads((path/'meta.json').read_text())['specs']
    shards = sorted(s for s in path.glob('mix-*.npz') if not s.name.endswith('.tmp.npz'))
    if limit:
        shards = shards[:limit]
    parts = {}
    for shard in shards:
        with np.load(shard) as z:
            for key in ('mel', 'rel', 'duration', 'synth', 'continuous', 'categorical', 'generator', 'balance'):
                parts.setdefault(key, []).append(z[key])
    data = {key: torch.from_numpy(np.concatenate(value)) for key, value in parts.items()}
    data['synths'] = len(specs)
    return specs, data


def structure(model, embedding):
    """Most likely kind and synths for each row: (kind, first synth, second synth or -1)."""
    kind = model.kind(embedding).argmax(1)
    top = model.present(embedding).topk(2, dim=1).indices
    second = torch.where(kind == PAIR, top[:, 1], torch.where(kind == TWIN, top[:, 0], -1))
    low, high = torch.minimum(top[:, 0], top[:, 1]), torch.maximum(top[:, 0], top[:, 1])
    return kind, torch.where(kind == PAIR, low, top[:, 0]), torch.where(kind == PAIR, high, second)


@torch.no_grad()
def evaluate(model, val, device, batch_size=1024):
    model.eval()
    count = len(val['duration'])
    total = dict.fromkeys(('loss', 'kind', 'exact', 'error', 'controls', 'balance', 'pairs'), 0.)
    for ids in torch.arange(count).split(batch_size):
        batch, counts = prepare(val, ids, device)
        embedding = model.encode(batch['mel'], batch['rel'], batch['duration'])
        loss, (first, logits) = model.loss(batch, counts, embedding)
        kind, low, high = structure(model, embedding)
        truth = batch['synth']
        plain = ~batch['item_same']
        pick = {key: value[plain] for key, value in first.items()}
        row, source = batch['item_row'][plain], batch['item_source'][plain]
        error, controls = model.control_error(pick, batch['item_synth'][plain], batch['continuous'][row, source])
        pair = batch['kind'] == PAIR
        total['loss'] += float(loss)*len(ids)
        total['kind'] += float((kind == batch['kind']).sum())
        total['exact'] += float(((kind == batch['kind']) & (low == truth[:, 0]) & (high == truth[:, 1])).sum())
        total['error'] += error; total['controls'] += controls
        total['balance'] += float((expected_unit(logits[:, None])[:, 0]-batch['balance']).abs()[pair].sum())
        total['pairs'] += float(pair.sum())
    return {'valLoss': total['loss']/count, 'kindAccuracy': total['kind']/count, 'structureExact': total['exact']/count,
            'controlMAE': total['error']/total['controls'], 'balanceMAE': total['balance']/max(total['pairs'], 1)}


def train(data_path, val_path, output, epochs=8, batch_size=512, lr=1.5e-3, init=None, limit=None, device=None, seed=0):
    torch.manual_seed(seed)
    device = torch.device(device or ('mps' if torch.backends.mps.is_available() else 'cpu'))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    specs, data = load_dataset(data_path, limit)
    _, val = load_dataset(val_path)
    model = MixModel(specs)
    if init:   # start the spectrogram towers from a single-synth model, or everything from a mix model
        state = torch.load(init, map_location='cpu', weights_only=False)['model']
        own = model.state_dict()
        kept = {k: v for k, v in state.items() if k in own and own[k].shape == v.shape and
                (k.startswith(('absolute.', 'relative.')) or 'kind.weight' in state)}
        model.load_state_dict(kept, strict=False)
        print(json.dumps({'initialised': len(kept), 'of': len(own)}), flush=True)
    model = model.to(device)
    count = len(data['duration'])
    steps = epochs*(count//batch_size)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=.02)
    schedule = torch.optim.lr_scheduler.OneCycleLR(optimizer, lr, total_steps=steps, pct_start=.06)
    noise = torch.Generator(device=device).manual_seed(seed)
    print(json.dumps({'rows': count, 'valRows': len(val['duration']), 'steps': steps, 'device': str(device),
                      'parameters': sum(p.numel() for p in model.parameters())}), flush=True)
    history, best, started, step = [], float('inf'), time.monotonic(), 0
    for epoch in range(epochs):
        model.train()
        running, seen = 0., 0
        for ids in torch.randperm(count).split(batch_size):
            if len(ids) < batch_size:
                continue
            batch, counts = prepare(data, ids, device)
            mel, rel = augment(batch['mel'], batch['rel'], noise)
            loss, _ = model.loss(batch, counts, model.encode(mel, rel, batch['duration']))
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
        state = {'model': {k: v.detach().cpu() for k, v in model.state_dict().items()}, 'specs': specs, 'val': row}
        torch.save(state, output/'last.pt')
        if row['valLoss'] < best:
            best = row['valLoss']; torch.save(state, output/'best.pt')
        (output/'history.json').write_text(json.dumps(history, indent=1))
    return history


class MixInverter:
    """Sound in, ranked Mixr proposals out."""

    def __init__(self, checkpoint, device='cpu'):
        state = torch.load(checkpoint, map_location='cpu', weights_only=False)
        self.specs, self.device = state['specs'], device
        self.model = MixModel(self.specs)
        self.model.load_state_dict(state['model']); self.model.eval().to(device)
        self.schemas = [ControlSchema(spec) for spec in self.specs.values()]

    @torch.no_grad()
    def hypotheses(self, embedding, count):
        """The likeliest structures as (probability, first synth, second synth or None), best first."""
        kind = self.model.kind(embedding)[0].softmax(-1).tolist()
        here = self.model.present(embedding)[0].sigmoid().tolist()
        best = sorted(range(len(here)), key=lambda i: -here[i])[:6]
        options = [(kind[SINGLE]*here[i], i, None) for i in best] + [(kind[TWIN]*here[i], i, i) for i in best]
        options += [(kind[PAIR]*here[i]*here[j], min(i, j), max(i, j)) for n, i in enumerate(best) for j in best[n+1:]]
        return sorted(options, key=lambda option: -option[0])[:count]

    @torch.no_grad()
    def propose(self, wave, renderer, structures=6, per_structure=4, seed=0):
        """-> [{'sources': [{'synth','params','seed'}, ...], 'balance', 'probability'}], likeliest structure first.
        The first proposal of each structure is its most likely setting; the rest are samples."""
        torch.manual_seed(seed)
        mel, rel, duration = describe(wave)
        to = lambda a: torch.as_tensor(a, device=self.device)[None]
        embedding = self.model.encode(to(mel), to(rel), to(duration))
        names, none = self.model.names, len(self.model.names)
        index = lambda value: torch.tensor([none if value is None else value], device=self.device)
        result = []
        for probability, a, b in self.hypotheses(embedding, structures):
            if b == a:       # the same synth twice: one head, both slots
                slots = [(a, out) for out in self.model.slots(embedding, a, index(a))]
            else:
                slots = [(a, self.model.slots(embedding, a, index(b))[0])]
                if b is not None:
                    slots.append((b, self.model.slots(embedding, b, index(a))[0]))
            drawn = [proposals(self.model, out, synth, per_structure) for synth, out in slots]
            logits = self.model.balance_logits(embedding, index(a), index(b))
            for rank in range(per_structure):
                sources = []
                for (synth, _), (unit, cats, gens) in zip(slots, drawn):
                    spec = self.specs[names[synth]]
                    anchor = renderer.sample(names[synth], spec['presets'][int(gens[rank])], 1+rank)
                    sources.append({'synth': names[synth], 'params': self.schemas[synth].decode(unit[rank], cats[rank], anchor),
                                    'seed': .5})
                if rank == 0:
                    balance = float(expected_unit(logits[:, None])[0, 0])
                else:
                    balance = float((torch.multinomial((logits[0]/.8).softmax(-1), 1)+torch.rand(1, device=self.device))/BINS)
                result.append({'sources': sources, 'balance': min(1., max(0., balance)), 'probability': probability})
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', required=True); parser.add_argument('--val', required=True)
    parser.add_argument('--out', required=True); parser.add_argument('--epochs', type=int, default=8)
    parser.add_argument('--batch-size', type=int, default=512); parser.add_argument('--lr', type=float, default=1.5e-3)
    parser.add_argument('--init', help='single-synth or mix checkpoint to start from')
    parser.add_argument('--limit', type=int, help='use only the first N shards'); parser.add_argument('--device')
    args = parser.parse_args()
    train(args.data, args.val, args.out, args.epochs, args.batch_size, args.lr, args.init, args.limit, args.device)


if __name__ == '__main__':
    main()
