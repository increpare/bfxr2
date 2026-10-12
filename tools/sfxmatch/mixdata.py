"""Synthetic Mixr data: one or two sources, real Mixr output, controls as labels.

Every pair of the 22 sources is equally likely, including a synth with itself;
one row in five is a single sound. Two sources are stored in synth order, since
a mix is the same whichever way round they are listed. The balance is chosen so
the second source sits a random number of dB above or below the first, which
keeps both audible: a source 30 dB down cannot be recovered and teaches nothing.

    python -m sfxmatch.mixdata --out runs/mix-1m --total 1000000
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from neural_invert.schema import ControlSchema
from .dataset import MODES, MODE_SHARES, perturb
from .mel import describe
from .render import FastRenderer, RenderPool, active_synths

SINGLE_SHARE = .2
OFFSET_DB = (8., 20.)     # spread and limit of the level difference between the two sources
QUIET = 1e-4              # a source this quiet is effectively absent


class MixDraw:
    def __init__(self, names):
        self.names, self.schemas = names, {}

    def __call__(self, renderer, seed):
        rng = np.random.default_rng(seed)
        count = 1 if rng.random() < SINGLE_SHARE else 2
        picked = sorted(int(i) for i in rng.integers(0, len(self.names), count))
        sources, generators = [], []
        for index in picked:
            name = self.names[index]
            if name not in self.schemas:
                self.schemas[name] = ControlSchema(renderer.specs[name])
            presets = renderer.specs[name]['presets']
            generator = int(rng.integers(len(presets)))
            mode = MODES[int(rng.choice(len(MODES), p=MODE_SHARES))]
            params = perturb(self.schemas[name], renderer.sample(name, presets[generator], int(rng.integers(2**32))), rng, mode)
            sources.append({'synth': name, 'params': params, 'seed': float(rng.random())})
            generators.append(generator)
        offset = float(np.clip(rng.normal(0, OFFSET_DB[0]), -OFFSET_DB[1], OFFSET_DB[1])) if count == 2 else None
        canonical, balance, wave, rms = renderer.mix(sources, offset_db=offset)
        if min(rms) < QUIET:
            raise ValueError('Silent source')
        mel, rel, duration = describe(wave)
        synth = np.full(2, -1, np.int8); unit = np.zeros((2, 32), np.float32)
        cat = np.zeros((2, 8), np.int16); generator = np.zeros(2, np.int16)
        for slot, (index, source) in enumerate(zip(picked, canonical)):
            u, c = self.schemas[source['synth']].encode(source['params'])
            synth[slot] = index; unit[slot, :len(u)] = u; cat[slot, :len(c)] = c; generator[slot] = generators[slot]
        return {'sources': canonical, 'balance': balance}, (mel, rel, duration, synth, unit, cat, generator,
                                                            np.float32(balance if count == 2 else .5))


COLUMNS = ('mel', 'rel', 'duration', 'synth', 'continuous', 'categorical', 'generator', 'balance')


def generate(output, total, shard_rows=5000, jobs=None, seed=1):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with FastRenderer() as renderer:
        names = active_synths(renderer)
        specs = {name: renderer.specs[name] for name in names}
    meta = {'seed': seed, 'shardRows': shard_rows, 'specs': specs,
            'sampling': {'single': SINGLE_SHARE, 'offsetDb': OFFSET_DB, 'modes': dict(zip(MODES, MODE_SHARES))}}
    path = output/'meta.json'
    if path.exists() and any(json.loads(path.read_text())[k] != meta[k] for k in ('seed', 'shardRows')):
        raise ValueError(f'{output} holds a dataset with different settings')
    path.write_text(json.dumps(meta))
    started, done = time.monotonic(), 0
    with RenderPool(MixDraw(names), jobs) as pool:
        for index in range(-(-total//shard_rows)):
            shard = output/f'mix-{index:04d}.npz'
            if shard.exists():
                continue
            count = min(shard_rows, total-index*shard_rows)
            rows, attempts = [], 0
            while len(rows) < count:
                batch = (count-len(rows))*21//20+8
                rows += [r for r in pool.map([[seed, index, attempts+i] for i in range(batch)]) if r[0] is not None]
                attempts += batch
            rows = rows[:count]
            temp = shard.with_suffix('.tmp.npz')
            np.savez(temp, **{key: np.stack([row[1][i] for row in rows]) for i, key in enumerate(COLUMNS)})
            shard.with_suffix('.jsonl').write_text(''.join(json.dumps(row[0], separators=(',', ':'))+'\n' for row in rows))
            temp.replace(shard)
            done += count
            print(json.dumps({'shard': shard.name, 'rowsPerSecond': round(done/(time.monotonic()-started), 1),
                              'minutes': round((time.monotonic()-started)/60, 1)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', required=True); parser.add_argument('--total', type=int, default=1_000_000)
    parser.add_argument('--shard-rows', type=int, default=5000); parser.add_argument('--jobs', type=int)
    parser.add_argument('--seed', type=int, default=1)
    args = parser.parse_args()
    generate(args.out, args.total, args.shard_rows, args.jobs, args.seed)


if __name__ == '__main__':
    main()
