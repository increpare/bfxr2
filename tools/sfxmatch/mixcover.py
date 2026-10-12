"""Coverage sampling for Mixr. Build targets with sfxmatch.covereval holes first.

    uv run python -m sfxmatch.mixcover --holes sfxmatch/runs/cover-holes.npz
    uv run python -m sfxmatch.mixcover --out sfxmatch/runs/mix-cover --total 20000 --jobs 3
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

from neural_invert.schema import ControlSchema
from .mel import SAMPLE_RATE, describe, trim
from .mixdata import COLUMNS as BASE_COLUMNS, OFFSET_DB, QUIET
from .render import FastRenderer, RenderPool, active_synths

COLUMNS = BASE_COLUMNS + ('mode',)
MODES = ('both-uniform', 'generator-uniform', 'hole')
SHARES = (.4, .3, .3)
POINTS = (.25, .5, .75)


def uniform(schema, anchor, rng):
    return schema.decode(rng.random(len(schema.continuous)),
                         [rng.integers(len(c['values'])) for c in schema.categorical], anchor)


def cap_source(source):
    source = deepcopy(source)
    if source['synth'] == 'Bfxr':
        p = source['params']; keys = ('attackTime', 'sustainTime', 'decayTime')
        length = sum(float(p.get(k, 0))**2 for k in keys)
        limit = (4*SAMPLE_RATE-32)/100000
        if length > limit:
            scale = np.sqrt(limit/length)
            for key in keys:
                p[key] = float(p.get(key, 0))*scale
    return source


def audio_reason(wave, rms):
    wave = np.asarray(wave)
    if not wave.size or not np.isfinite(wave).all() or not np.isfinite(rms).all():
        return 'nonfinite'
    if len(rms) == 0 or min(rms) < QUIET:
        return 'source_rms'
    if float(np.sqrt(np.mean(wave.astype(np.float64)**2))) < QUIET:
        return 'mix_rms'
    try:
        duration = len(trim(wave))/SAMPLE_RATE
    except ValueError:
        return 'mix_rms'
    return None if .05 <= duration <= 4 else 'duration'


def interpolate(left, right, specs, point, rng, recipe='shared-interpolation'):
    """Correspond matching slots; cross overlapping pairs, rejecting disjoint pairs."""
    a = sorted(left['sources'], key=lambda s: s['synth'])
    b = sorted(right['sources'], key=lambda s: s['synth'])
    left_balance = left.get('balance', .5)
    right_balance = right.get('balance', .5)
    if len(a) == 2 and a[0] != left['sources'][0]:
        left_balance = 1-left_balance
    if len(b) == 2 and b[0] != right['sources'][0]:
        right_balance = 1-right_balance
    shared = set(s['synth'] for s in a) & set(s['synth'] for s in b)
    if not shared:
        return None
    if recipe == 'cross-ingredients':
        extra_left = [source for source in left['sources'] if source['synth'] not in shared]
        extra_right = [source for source in right['sources'] if source['synth'] not in shared]
        if not extra_left or not extra_right:
            return None
        first, second = deepcopy(extra_left[0]), deepcopy(extra_right[0])
        left_level = left.get('balance', .5) if left['sources'][1] == first else 1-left.get('balance', .5)
        right_level = right.get('balance', .5) if right['sources'][1] == second else 1-right.get('balance', .5)
        first_level, second_level = (1-point)*left_level, point*right_level
        balance = second_level/max(first_level+second_level, 1e-12)
        if first['synth'] > second['synth']:
            first, second = second, first; balance = 1-balance
        return {'sources': [first, second], 'balance': float(balance)}
    out = []
    remaining = list(b)
    for source in a:
        match = next((s for s in remaining if s['synth'] == source['synth']), None)
        if match is None:
            continue
        remaining.remove(match)
        schema = ControlSchema(specs[source['synth']])
        u, c = schema.encode(source['params']); v, d = schema.encode(match['params'])
        anchor = source if rng.random() >= point else match
        cats = np.where(rng.random(len(c)) < point, d, c)
        out.append({'synth': source['synth'], 'params': schema.decode((1-point)*u+point*v, cats, anchor['params']),
                    'seed': anchor['seed']})
    balance = float((1-point)*left_balance+point*right_balance)
    if len(out) == 1 and max(len(a), len(b)) == 2:
        extras = [s for s in a+b if s['synth'] not in shared]
        if extras:
            name = out[0]['synth']
            left_weight = (1-left.get('balance', .5)) if left['sources'][0]['synth'] == name else left.get('balance', .5)
            right_weight = (1-right.get('balance', .5)) if right['sources'][0]['synth'] == name else right.get('balance', .5)
            balance = 1-((1-point)*left_weight+point*right_weight)
            out.append(deepcopy(extras[int(rng.integers(len(extras)))]))
    ordered = sorted(out, key=lambda s: s['synth'])
    if len(out) == 2 and ordered[0] != out[0]:
        balance = 1-balance
    return {'sources': ordered, 'balance': balance}


def hole_key(hole):
    if 'endpoints' in hole:
        return tuple(sorted(int(row) for row in hole['endpoints']))
    return tuple(sorted(json.dumps(hole[side], sort_keys=True) for side in ('left', 'right')))


class CoverDraw:
    """Bounded row task; statistics travel back even when no feasible row is found."""
    def __init__(self, names, holes, source_retries=12):
        self.names, self.holes, self.source_retries = names, holes, source_retries
        self.schemas = {}

    def source(self, renderer, name, rng, direct, stats, mode):
        schema = self.schemas.setdefault(name, ControlSchema(renderer.specs[name]))
        presets = renderer.specs[name]['presets']
        for _ in range(self.source_retries):
            stats[f'{mode}/{name}/attempt'] += 1
            try:
                gen = int(rng.integers(len(presets)))
                params = renderer.sample(name, presets[gen], int(rng.integers(2**32)))
                if not direct:
                    params = uniform(schema, params, rng); gen = -1
                source = cap_source({'synth': name, 'params': params, 'seed': float(rng.random())})
                canonical, _, wave, rms = renderer.mix([source])
                reason = audio_reason(wave, rms)
                if reason:
                    stats[f'{mode}/{name}/source_{reason}'] += 1
                    continue
                stats[f'{mode}/{name}/source_accepted'] += 1
                return canonical[0], gen
            except (ValueError, RuntimeError) as error:
                reason = 'timeout' if 'exceeded' in str(error) else 'render_error'
                stats[f'{mode}/{name}/source_{reason}'] += 1
        stats[f'{mode}/{name}/source_exhausted'] += 1
        raise ValueError('Source retry budget exhausted')

    def __call__(self, renderer, task):
        rng = np.random.default_rng(task['seed']); stats = Counter(); mode = task['mode']
        count = 1 if task['single'] else 2
        # Fixed across retries: rejection must not change the pair distribution.
        picked = sorted(int(i) for i in rng.integers(0, len(self.names), count))
        selected = None
        if mode == 'hole':
            eligible = [h for h in self.holes if (len(h['left']['sources']) == len(h['right']['sources']) == count)]
            if not eligible:
                stats[f'{mode}/pool/no_compatible_hole'] += 1
                return None, None, dict(stats)
            selected = eligible[int(rng.integers(len(eligible)))]
        tried = set()
        def skip_hole():
            tried.add(hole_key(selected))
            stats[f'{mode}/pool/skipped_infeasible'] += 1
            stats[f'{mode}/skipped/{selected["id"]}'] += 1
        row_budget = self.source_retries * (4 if selected is not None else 1)
        for attempt in range(row_budget):
            if selected is not None and attempt and attempt % self.source_retries == 0:
                skip_hole()
                remaining = [hole for hole in eligible if hole_key(hole) not in tried]
                if not remaining:
                    selected = None
                    break
                selected = remaining[int(rng.integers(len(remaining)))]
            stats[f'{mode}/row/attempt'] += 1
            try:
                if selected is not None:
                    point = POINTS[int(rng.integers(len(POINTS)))]
                    left, right = selected['left'], selected['right']
                    left_names = {s['synth'] for s in left['sources']}
                    right_names = {s['synth'] for s in right['sources']}
                    crossing = count == 2 and bool(left_names-right_names) and bool(right_names-left_names)
                    recipe_type = 'cross-ingredients' if crossing and rng.random() < .5 else 'shared-interpolation'
                    patch = interpolate(left, right, renderer.specs, point, rng, recipe_type)
                    if patch is None:
                        stats[f'{mode}/pool/disjoint'] += 1
                        continue
                    sources = patch['sources']; generators = [-1]*len(sources)
                    balance, offset = patch['balance'], None
                    order = sorted(range(len(sources)), key=lambda i: self.names.index(sources[i]['synth']))
                    if len(order) == 2 and order == [1, 0]:
                        balance = 1-balance
                    sources = [sources[i] for i in order]
                    picked = [self.names.index(s['synth']) for s in sources]
                else:
                    sources, generators = [], []
                    direct = int(rng.integers(count)) if mode == 'generator-uniform' and count == 2 else -1
                    for slot, index in enumerate(picked):
                        name = self.names[index]
                        source, gen = self.source(renderer, name, rng, slot == direct, stats, mode)
                        sources.append(source); generators.append(gen)
                    balance = .5
                    offset = float(np.clip(rng.normal(0, OFFSET_DB[0]), -OFFSET_DB[1], OFFSET_DB[1])) if count == 2 else None
                sources = [cap_source(s) for s in sources]
                source_bad = False
                if selected is not None:
                    for source in sources:
                        name = source['synth']; stats[f'{mode}/{name}/attempt'] += 1
                        _, _, solo, levels = renderer.mix([source])
                        reason = audio_reason(solo, levels)
                        if reason:
                            stats[f'{mode}/{name}/source_{reason}'] += 1; source_bad = True
                        else:
                            stats[f'{mode}/{name}/source_accepted'] += 1
                    if source_bad:
                        stats[f'{mode}/row/source_rejected'] += 1
                        continue
                canonical, balance, wave, rms = renderer.mix(sources, balance, offset_db=offset)
                reason = audio_reason(wave, rms)
                if reason:
                    stats[f'{mode}/row/{reason}'] += 1
                    for s, level in zip(sources, rms):
                        stats[f'{mode}/{s["synth"]}/row_rejected_{reason}'] += 1
                    continue
                feature = describe(wave)
                synth = np.full(2, -1, np.int8); unit = np.zeros((2, 32), np.float32)
                cat = np.zeros((2, 8), np.int16); generator = np.full(2, -1, np.int16)
                for slot, (index, source) in enumerate(zip(picked, canonical)):
                    name = source['synth']; schema = self.schemas.setdefault(name, ControlSchema(renderer.specs[name]))
                    u, c = schema.encode(source['params'])
                    synth[slot] = index; unit[slot, :len(u)] = u; cat[slot, :len(c)] = c; generator[slot] = generators[slot]
                    stats[f'{mode}/{name}/accepted'] += 1
                patch = {'sources': canonical, 'balance': balance, 'mode': mode}
                if selected is not None:
                    patch['hole'] = {'id': selected['id'], 'point': point, 'label': selected['label'], 'recipe': recipe_type}
                stats[f'{mode}/row/accepted'] += 1
                return patch, (*feature, synth, unit, cat, generator, np.float32(balance if count == 2 else .5), mode), dict(stats)
            except (ValueError, RuntimeError) as error:
                reason = 'source_exhausted' if 'Source retry' in str(error) else ('timeout' if 'exceeded' in str(error) else 'render_error')
                stats[f'{mode}/row/{reason}'] += 1
                for index in picked:
                    stats[f'{mode}/{self.names[index]}/{reason}'] += 1
        if selected is not None:
            skip_hole()
        stats[f'{mode}/pool/exhausted'] += 1
        return None, None, dict(stats)


def generate(output, total=20000, shard_rows=1000, jobs=3, seed=1, holes=None, source_retries=12, batch=64):
    if total < 1 or shard_rows < 1 or batch < 1 or source_retries < 1:
        raise ValueError('Counts and retry budget must be positive')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    shard_count = -(-total//shard_rows)
    trailing = [p for p in output.glob('mix-*.npz') if not p.name.endswith('.tmp.npz')
                and int(p.stem.split('-')[1]) >= shard_count]
    if trailing:
        raise ValueError(f'Requested total omits completed trailing shards in {output}')
    hole_rows, digest = [], None
    if holes is not None:
        payload = Path(holes).read_bytes(); digest = hashlib.sha256(payload).hexdigest()
        with np.load(holes) as z:
            hole_rows = [json.loads(v) for v in z['recipes']]
    shares = SHARES if hole_rows else (.5, .5, 0.)
    with FastRenderer() as renderer:
        names = active_synths(renderer); specs = {n: renderer.specs[n] for n in names}
    meta = {'version': 4, 'seed': seed, 'shardRows': shard_rows, 'specs': specs, 'holes': digest,
            'sourceRetries': source_retries, 'sampling': {'modes': dict(zip(MODES, shares)), 'single': .2,
            'offsetDb': list(OFFSET_DB), 'minRms': QUIET, 'seconds': [.05, 4.]}}
    path = output/'meta.json'
    if path.exists() and json.loads(path.read_text()) != meta:
        raise ValueError(f'{output} holds a dataset with different settings')
    path.write_text(json.dumps(meta))
    cumulative = Counter(); existing = 0
    with RenderPool(CoverDraw(names, hole_rows, source_retries), jobs) as pool:
        for index in range(-(-total//shard_rows)):
            shard = output/f'mix-{index:04d}.npz'; count = min(shard_rows, total-index*shard_rows)
            statfile = shard.with_suffix('.stats.json')
            if shard.exists():
                with np.load(shard) as z:
                    if len(z['mode']) != count or not shard.with_suffix('.jsonl').exists():
                        raise ValueError(f'Existing partial shard {shard}: retain total boundary or start another output')
                if not statfile.exists():
                    raise ValueError(f'Missing statistics for {shard}')
                cumulative.update(json.loads(statfile.read_text())); existing += count
                continue
            rows, stats = [], Counter()
            # Stratified 100-row cycle: 40/30/30 and exactly one single in five per strategy.
            for start in range(0, count, batch):
                tasks = []
                for row in range(start, min(start+batch, count)):
                    global_row = index*shard_rows+row; cycle = global_row % 100
                    cut = np.cumsum(np.asarray(shares)*100)
                    mode_index = int(np.searchsorted(cut, cycle, side='right'))
                    tasks.append({'seed': [seed, index, row], 'mode': MODES[mode_index], 'single': global_row % 5 == 0})
                try:
                    results = pool.map(tasks)
                except Exception:
                    for task in tasks:
                        stats[f'{task["mode"]}/pool/worker_failure'] += 1
                    statfile.write_text(json.dumps(dict(stats)))
                    raise
                for task, result in zip(tasks, results):
                    if len(result) != 3:
                        stats[f'{task["mode"]}/pool/worker_failure'] += 1
                        statfile.write_text(json.dumps(dict(stats)))
                        raise RuntimeError(f'Pool failed: {result[1]}')
                    patch, values, detail = result; stats.update(detail)
                    if patch is None:
                        statfile.write_text(json.dumps(dict(stats)))
                        raise RuntimeError(f'Finite retry budget exhausted at shard {index} row {len(rows)}: {detail}')
                    rows.append((patch, values))
            temp = shard.with_suffix('.tmp.npz')
            np.savez(temp, **{key: np.stack([r[1][i] for r in rows]) for i, key in enumerate(COLUMNS)})
            shard.with_suffix('.jsonl').write_text(''.join(json.dumps(r[0], separators=(',', ':'))+'\n' for r in rows))
            statfile.write_text(json.dumps(dict(stats))); temp.replace(shard)
            cumulative.update(stats)
            print(json.dumps({'shard': shard.name, 'newRows': count, 'statistics': dict(stats)}), flush=True)
    report = {'existingRows': existing, 'newRows': total-existing, 'totalRows': total, 'statistics': dict(cumulative)}
    (output/'report.json').write_text(json.dumps(report, indent=2)); print(json.dumps(report), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', default='sfxmatch/runs/mix-cover'); p.add_argument('--total', type=int, default=20000)
    p.add_argument('--shard-rows', type=int, default=1000); p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--seed', type=int, default=1); p.add_argument('--holes'); p.add_argument('--source-retries', type=int, default=12)
    p.add_argument('--batch', type=int, default=64)
    a = p.parse_args(); generate(a.out, a.total, a.shard_rows, a.jobs, a.seed, a.holes, a.source_retries, a.batch)


if __name__ == '__main__':
    main()
