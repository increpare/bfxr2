"""Large synthetic (audio features, controls) dataset from the real DSP.

Shards are per synth and written round-robin, so a partly finished run is
already balanced and usable. Each shard keeps the exact canonical controls and
render seed (rows.jsonl) so any row can be re-rendered for retrieval.
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from neural_invert.schema import ControlSchema
from .mel import describe
from .render import FastRenderer, RenderPool, active_synths

MODES = ('original', 'jitter', 'sparse')
MODE_SHARES = (.6, .25, .15)


def perturb(schema, params, rng, mode):
    """Stay near designed presets: most rows are untouched or locally jittered."""
    if mode == 'original':
        return params
    if mode == 'sparse':
        return schema.mutate(params, rng, 'sparse')
    unit, cat = schema.encode(params)
    moved = rng.choice(len(unit), size=max(1, len(unit)//3), replace=False)
    unit[moved] = np.clip(unit[moved] + rng.normal(0, .1, len(moved)), 0, 1)
    return schema.decode(unit, cat, params)


class Draw:
    """Worker task: sample a preset, perturb it, render it, featurise it."""

    def __init__(self):
        self.schemas = {}

    def __call__(self, renderer, task):
        synth, generator, seed = task
        if synth not in self.schemas:
            self.schemas[synth] = ControlSchema(renderer.specs[synth])
        schema = self.schemas[synth]
        rng = np.random.default_rng(seed)
        presets = renderer.specs[synth]['presets']
        mode = int(rng.choice(len(MODES), p=MODE_SHARES))
        sample_seed, render_seed = (int(v) for v in rng.integers(0, 2**32, 2))
        params = perturb(schema, renderer.sample(synth, presets[generator], sample_seed), rng, MODES[mode])
        canonical, wave = renderer.render(synth, params, render_seed)
        mel, rel, duration = describe(wave)
        unit, cat = schema.encode(canonical)
        return canonical, (mel, rel, duration, unit, cat, generator, mode, render_seed)


def quotas(specs, names, total):
    """Rows per synth, mildly weighted towards engines with more controls."""
    weight = {}
    for name in names:
        schema = ControlSchema(specs[name])
        weight[name] = len(schema.continuous) + len(schema.categorical) + 8
    scale = total/sum(weight.values())
    return {name: int(round(weight[name]*scale)) for name in names}


def write_shard(path, rows):
    canonical = [row[0] for row in rows]
    columns = list(zip(*[row[1] for row in rows]))
    temp = path.with_suffix('.tmp.npz')
    np.savez(temp, mel=np.stack(columns[0]), rel=np.stack(columns[1]),
             duration=np.asarray(columns[2], dtype=np.float32),
             continuous=np.stack(columns[3]).astype(np.float32),
             categorical=np.stack(columns[4]).astype(np.int16),
             generator=np.asarray(columns[5], dtype=np.int16),
             mode=np.asarray(columns[6], dtype=np.uint8),
             seed=np.asarray(columns[7], dtype=np.uint32))
    path.with_suffix('.jsonl').write_text(''.join(json.dumps(p, separators=(',', ':'))+'\n' for p in canonical))
    temp.replace(path)


def generate(output, total, shard_rows=5000, jobs=None, seed=1, synths=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with FastRenderer() as renderer:
        names = synths or active_synths(renderer)
        specs = {name: renderer.specs[name] for name in names}
        source_hash = renderer.inventory['sourceHash']
    plan = quotas(specs, names, total)
    meta = {'sourceHash': source_hash, 'seed': seed, 'shardRows': shard_rows, 'rows': plan,
            'modes': dict(zip(MODES, MODE_SHARES)), 'specs': specs}
    meta_path = output/'meta.json'
    if meta_path.exists():
        old = json.loads(meta_path.read_text())
        if any(old[k] != meta[k] for k in ('sourceHash', 'seed', 'shardRows', 'rows')):
            raise ValueError(f'{output} holds a dataset with different settings')
    meta_path.write_text(json.dumps(meta))
    shards = [(index, name, min(shard_rows, plan[name]-index*shard_rows))
              for index in range(max(plan.values())//shard_rows+1)
              for name in names if plan[name] > index*shard_rows]
    started, done = time.monotonic(), 0
    with RenderPool(Draw(), jobs) as pool:
        for index, name, count in shards:
            path = output/f'{name}-{index:03d}.npz'
            if path.exists():
                continue
            rng = np.random.default_rng([seed, names.index(name), index])
            generators = len(specs[name]['presets'])
            rows, attempts = [], 0
            while len(rows) < count:
                need = count-len(rows)
                batch = need + need//20 + 8
                if attempts > count*4:
                    raise RuntimeError(f'Too many failed draws for {name}')
                tasks = [(name, (attempts+i) % generators, [seed, names.index(name), index, attempts+i])
                         for i in range(batch)]
                attempts += batch
                rows += [r for r in pool.map(tasks) if r[0] is not None][:need]
            write_shard(path, rows)
            done += count
            rate = done/(time.monotonic()-started)
            print(json.dumps({'shard': path.name, 'rows': count, 'rowsPerSecond': round(rate, 1),
                              'elapsedMinutes': round((time.monotonic()-started)/60, 1)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--total', type=int, default=1_000_000)
    parser.add_argument('--shard-rows', type=int, default=5000)
    parser.add_argument('--jobs', type=int)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--synths', nargs='+')
    args = parser.parse_args()
    generate(args.out, args.total, args.shard_rows, args.jobs, args.seed, args.synths)


if __name__ == '__main__':
    main()
