"""Brute-force matching: big retrieval, then CMA-ES on the most promising synths.

This is the ceiling probe. It asks what the synth pool can reach under the
fixed objective when compute is not the constraint, so that a failure can be
blamed on the synths or the objective rather than on a weak search.
"""
from functools import lru_cache
import json
from pathlib import Path

import cma
import numpy as np

from neural_invert.schema import ControlSchema
from .mel import describe
from .objective import INFEASIBLE, Score
from .render import RenderPool


class Library:
    """A sfxmatch.dataset directory as a nearest-neighbour index over whole-sound spectra."""

    def __init__(self, path):
        self.path = Path(path)
        meta = json.loads((self.path/'meta.json').read_text())
        self.specs, self.names = meta['specs'], list(meta['specs'])
        rel, duration, synth, seeds, where = [], [], [], [], []
        for shard in sorted(s for s in self.path.glob('*.npz') if not s.name.endswith('.tmp.npz')):
            with np.load(shard) as z:
                rel.append(z['rel'].reshape(len(z['rel']), -1)); duration.append(z['duration']); seeds.append(z['seed'])
            name = shard.stem.rsplit('-', 1)[0]
            synth.append(np.full(len(duration[-1]), self.names.index(name)))
            where += [(shard.with_suffix('.jsonl'), i) for i in range(len(duration[-1]))]
        self.rel, self.duration = np.concatenate(rel), np.concatenate(duration)
        self.synth, self.seeds, self.where = np.concatenate(synth), np.concatenate(seeds), where

    def __len__(self):
        return len(self.duration)

    @staticmethod
    @lru_cache(maxsize=64)
    def _lines(path):
        return path.read_text().splitlines()

    def row(self, index):
        path, line = self.where[index]
        return {'synth': self.names[self.synth[index]], 'params': json.loads(self._lines(path)[line]),
                'seed': int(self.seeds[index])}

    def nearest(self, wave, per_synth=48, chunk=65536):
        """Indices of the closest rows for each synth: spectral shape plus a duration term."""
        _, rel, duration = describe(wave)
        target = rel.reshape(-1).astype(np.int16)
        distance = np.empty(len(self), np.float32)
        for start in range(0, len(self), chunk):
            block = self.rel[start:start+chunk].astype(np.int16)
            distance[start:start+chunk] = np.abs(block-target).mean(axis=1)/255
        distance += .15*np.abs(self.duration-duration)
        picked = []
        for index in range(len(self.names)):
            rows = np.flatnonzero(self.synth == index)
            picked += rows[np.argsort(distance[rows])[:per_synth]].tolist()
        return picked


class Space:
    """One synth's controls as a point in the unit cube; categoricals are quantised axes."""

    def __init__(self, spec, anchor):
        self.schema, self.anchor = ControlSchema(spec), anchor
        self.sizes = [len(c['values']) for c in self.schema.categorical]

    def encode(self, params):
        unit, cat = self.schema.encode(params)
        return np.concatenate([unit, [(c+.5)/n for c, n in zip(cat, self.sizes)]])

    def decode(self, x):
        count = len(self.schema.continuous)
        cat = [min(n-1, int(v*n)) for v, n in zip(x[count:], self.sizes)]
        return self.schema.decode(np.asarray(x[:count], dtype=np.float32), cat, self.anchor)


def run_cma(evaluate, starts, specs, budget, popsize=36, sigma=.12, rng_seed=0):
    """CMA-ES from every start at once, so each batch keeps all workers busy.

    evaluate(tasks) -> [(canonical params or None, score)] for tasks of (synth, params, seed).
    starts: [{'synth','params','seed','score'}]. Returns the best row found from
    each start, with 'evaluations' added.
    """
    runs = []
    for start in starts:
        space = Space(specs[start['synth']], start['params'])
        options = {'bounds': [0, 1], 'popsize': popsize, 'seed': rng_seed+len(runs)+1, 'verbose': -9}
        runs.append({'space': space, 'best': dict(start), 'used': 0,
                     'es': cma.CMAEvolutionStrategy(space.encode(start['params']), sigma, options)})
    while True:
        live = [run for run in runs if run['used'] < budget and not run['es'].stop()]
        if not live:
            break
        asked = [run['es'].ask() for run in live]
        results = iter(evaluate([(run['best']['synth'], run['space'].decode(x), run['best']['seed'])
                                 for run, xs in zip(live, asked) for x in xs]))
        for run, xs in zip(live, asked):
            values = []
            for _ in xs:
                canonical, score = next(results)
                score = INFEASIBLE if canonical is None else score
                values.append(score)
                if score < run['best']['score']:
                    run['best'] = dict(run['best'], params=canonical, score=score)
            run['es'].tell(xs, values); run['used'] += len(xs)
    return [dict(run['best'], evaluations=run['used']) for run in runs]


def score_seeds(evaluate, seeds):
    """Render and score seeds; returns {synth: rows sorted best first}."""
    scored = [dict(seed, params=canonical, score=score)
              for seed, (canonical, score) in zip(seeds, evaluate([(s['synth'], s['params'], s['seed']) for s in seeds]))
              if canonical is not None and score < INFEASIBLE]
    by_synth = {}
    for row in sorted(scored, key=lambda r: r['score']):
        by_synth.setdefault(row['synth'], []).append(row)
    return by_synth


def search(target, seeds, specs, jobs=None, top_synths=5, restarts=3, budget=2000, popsize=36,
           sigma=.12, rng_seed=0, log=lambda text: print(text, flush=True)):
    """Score seed candidates, then run CMA-ES restarts on the best synths.

    seeds: [{'synth','params','seed'}]. Returns per-synth results sorted best first:
    [{'synth','params','seed','score','seedScore','seedParams','evaluations'}].
    """
    with RenderPool(Score(target), jobs) as pool:
        by_synth = score_seeds(pool.map, seeds)
        chosen = sorted(by_synth, key=lambda name: by_synth[name][0]['score'])[:top_synths]
        log(f'  seeds: {sum(map(len, by_synth.values()))} scored; best per synth ' +
            ', '.join(f'{name} {by_synth[name][0]["score"]:.3f}' for name in chosen))
        starts = [row for name in chosen for row in by_synth[name][:restarts]]
        finished = run_cma(pool.map, starts, specs, budget, popsize, sigma, rng_seed)
    results = []
    for name in chosen:
        mine = [row for row in finished if row['synth'] == name]
        best = min(mine, key=lambda row: row['score'])
        results.append({'synth': name, 'params': best['params'], 'seed': best['seed'], 'score': best['score'],
                        'seedScore': by_synth[name][0]['score'], 'seedParams': by_synth[name][0]['params'],
                        'evaluations': sum(row['evaluations'] for row in mine)})
        log(f'  {name}: {by_synth[name][0]["score"]:.3f} -> {best["score"]:.3f} ({results[-1]["evaluations"]} renders)')
    return sorted(results, key=lambda r: r['score'])
