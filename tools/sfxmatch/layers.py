"""Two-layer matching in Mixr's terms: (1 - balance) * A + balance * B, both starting together.

A probe for whether layering extends reach. Layer A is a finished single-synth
match; layer B and the balance are searched so the mix scores best. Mixing is
done here on the two real renders, which is what Mixr does, so a winning pair
can be rebuilt as a Mixr preset.

    python -m sfxmatch.layers --singles runs/systems/reach2 --library runs/data-1m \
        --out runs/systems/layers --only ext-001 ext-005
"""
import argparse
import json
from pathlib import Path
import time

import cma
import numpy as np

from . import benchmark
from .objective import INFEASIBLE, Objective
from .render import FastRenderer, RenderPool
from .search import Library, Space
from .systems import save, summarise

BALANCE = (.05, .95)


def mix(a, b, balance):
    out = np.zeros(max(len(a), len(b)), np.float32)
    out[:len(a)] += (1-balance)*a
    out[:len(b)] += balance*b
    return out


class MixScore:
    """Pool task (synth, params, seed, [(base index, balance), ...]) -> (canonical params, [scores])."""

    def __init__(self, target, bases):
        self.target, self.bases, self.objective = np.asarray(target, np.float32), bases, None

    def __call__(self, renderer, task):
        if self.objective is None:
            self.objective = Objective(self.target)
        synth, params, seed, mixes = task
        canonical, wave = renderer.render(synth, params, seed)
        return canonical, [self.objective.score(mix(self.bases[base], wave, balance)) for base, balance in mixes]


def second_layer(target, bases, seeds, specs, jobs=None, top_synths=3, budget=2000, popsize=36, sigma=.12,
                 log=lambda text: print(text, flush=True)):
    """bases: single-layer results with 'wave'. Returns the best mix found on each base, best first."""
    with RenderPool(MixScore(target, [b['wave'] for b in bases]), jobs) as pool:
        everywhere = [(index, .5) for index in range(len(bases))]
        scored = pool.map([(s['synth'], s['params'], s['seed'], everywhere) for s in seeds])
        runs = []
        for index in range(len(bases)):
            best = {}
            for seed, (canonical, values) in zip(seeds, scored):
                if canonical is not None and values[index] < best.get(seed['synth'], (INFEASIBLE,))[0]:
                    best[seed['synth']] = (values[index], dict(seed, params=canonical))
            for score, start in sorted(best.values(), key=lambda item: item[0])[:top_synths]:
                space = Space(specs[start['synth']], start['params'])
                x0 = np.append(space.encode(start['params']), .5)
                options = {'bounds': [0, 1], 'popsize': popsize, 'seed': len(runs)+1, 'verbose': -9}
                runs.append({'base': index, 'space': space, 'layer': start, 'balance': .5, 'score': score, 'used': 0,
                             'es': cma.CMAEvolutionStrategy(x0, sigma, options)})
        balance_of = lambda x: BALANCE[0]+float(x[-1])*(BALANCE[1]-BALANCE[0])
        while True:
            live = [run for run in runs if run['used'] < budget and not run['es'].stop()]
            if not live:
                break
            asked = [run['es'].ask() for run in live]
            results = iter(pool.map([(run['layer']['synth'], run['space'].decode(x[:-1]), run['layer']['seed'],
                                      [(run['base'], balance_of(x))]) for run, xs in zip(live, asked) for x in xs]))
            for run, xs in zip(live, asked):
                values = []
                for x in xs:
                    canonical, scores = next(results)
                    value = INFEASIBLE if canonical is None else scores[0]
                    values.append(value)
                    if value < run['score']:
                        run.update(score=value, balance=balance_of(x), layer=dict(run['layer'], params=canonical))
                run['es'].tell(xs, values); run['used'] += len(xs)
    results = []
    for index, base in enumerate(bases):
        mine = [run for run in runs if run['base'] == index]
        if not mine:
            continue
        best = min(mine, key=lambda run: run['score'])
        results.append({'base': index, 'score': best['score'], 'singleScore': base['score'], 'balance': best['balance'],
                        'layers': [{k: base[k] for k in ('synth', 'params', 'seed')},
                                   {k: best['layer'][k] for k in ('synth', 'params', 'seed')}],
                        'evaluations': sum(run['used'] for run in mine)})
        log(f'  on {base["synth"]}: single {base["score"]:.3f} -> with {best["layer"]["synth"]} at balance '
            f'{best["balance"]:.2f}: {best["score"]:.3f}')
    return sorted(results, key=lambda r: r['score'])


def run(singles, library, out, targets, jobs=None, **settings):
    started, scores = time.monotonic(), {}
    index = Library(library)
    with FastRenderer() as renderer:
        for target in targets:
            reference = benchmark.reference(target, renderer)
            objective = Objective(reference)
            bases = []
            for suffix in ('', '-alt2', '-alt3'):
                path = Path(str(singles)+suffix, f'{target["id"]}.json')
                if path.exists():
                    row = json.loads(path.read_text())
                    _, wave = renderer.render(row['synth'], row['params'], row['seed'])
                    bases.append(dict(row, wave=wave, score=objective.score(wave)))
            if not bases:
                continue
            print(f'{target["id"]} {target.get("file") or target["synth"]}', flush=True)
            seeds = [index.row(i) for i in index.nearest(reference, 48)]
            results = second_layer(reference, bases, seeds, index.specs, jobs, **settings)
            for suffix, row in zip(('', '-alt2'), results):
                waves = [renderer.render(layer['synth'], layer['params'], layer['seed'])[1] for layer in row['layers']]
                save(str(out)+suffix, target['id'], mix(waves[0], waves[1], row['balance']), row)
            scores[target['id']] = results[0]['score']
    summarise(out, scores, started)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--singles', required=True, help='system directory of single-layer results (with -alt2/-alt3)')
    parser.add_argument('--library', required=True); parser.add_argument('--out', required=True)
    parser.add_argument('--only', nargs='+'); parser.add_argument('--jobs', type=int)
    parser.add_argument('--top-synths', type=int, default=3); parser.add_argument('--budget', type=int, default=2000)
    args = parser.parse_args()
    targets = [t for t in benchmark.targets() if not args.only or t['id'] in args.only]
    run(args.singles, args.library, args.out, targets, args.jobs, top_synths=args.top_synths, budget=args.budget)


if __name__ == '__main__':
    main()
