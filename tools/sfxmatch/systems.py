"""Run a matching system over the frozen benchmark.

Each system writes <out>/<target id>.wav plus a .json with the patch, ready for
`python -m sfxmatch.benchmark page`.

    python -m sfxmatch.systems oneshot    --checkpoint runs/model-1m/best.pt --out runs/systems/oneshot
    python -m sfxmatch.systems search     --library runs/data-1m --checkpoint ... --out runs/systems/search
    python -m sfxmatch.systems old-branch --out runs/systems/old-branch
    python -m sfxmatch.systems bfxr       --out runs/systems/bfxr
    python -m sfxmatch.systems compare    old=runs/systems/old-branch new=runs/systems/search
"""
import argparse
import json
import os
from pathlib import Path
import time

import numpy as np
import soundfile as sf

from . import benchmark
from .objective import INFEASIBLE, Objective
from .render import FastRenderer, RenderPool

OLD_MODEL = Path(__file__).resolve().parents[1]/'multisynth/runs/neural-v2/acoustic-model/best.pt'
BFXR_MODEL = Path(os.environ.get('BFXR_INVERSE_CHECKPOINT',
                  '/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt'))


def save(out, target_id, wave, info):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    wave = np.asarray(wave, dtype=np.float32)
    sf.write(out/f'{target_id}.wav', wave/max(float(np.max(np.abs(wave))), 1e-9)*.5, 44100, subtype='PCM_16')
    (out/f'{target_id}.json').write_text(json.dumps(info))


def best_rendered(candidates, renderer, objective):
    """Render every candidate, return the closest as (info, wave) or None."""
    best = None
    for candidate in candidates:
        try:
            canonical, wave = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
        except (ValueError, RuntimeError):
            continue
        score = objective.score(wave)
        if score < INFEASIBLE and (best is None or score < best[0]['score']):
            best = ({'synth': candidate['synth'], 'params': canonical, 'seed': candidate['seed'], 'score': score}, wave)
    return best


class OneShot:
    """Inverse model only: a few sampled proposals per likely synth, keep the closest."""

    def __init__(self, checkpoint, top_synths=3, per_synth=8):
        self.checkpoint, self.top_synths, self.per_synth, self.inverter = str(checkpoint), top_synths, per_synth, None

    def __call__(self, renderer, target):
        if self.inverter is None:
            from .infer import Inverter
            self.inverter = Inverter(self.checkpoint)
        reference = benchmark.reference(target, renderer)
        proposals = self.inverter.propose(reference, renderer, top_synths=self.top_synths, per_synth=self.per_synth)
        found = best_rendered(proposals, renderer, Objective(reference))
        return target['id'], found


class OldBranch:
    """The branch's standard recipe before this work: shared 22-synth MLP proposals,
    then a 128-step accept-if-better hill climb from the two best distinct synths."""

    def __init__(self, starts=2, budget=128):
        self.starts, self.budget, self.model = starts, budget, None

    def __call__(self, renderer, target):
        from neural_invert.evaluate import mutate_controls
        from neural_invert.predict import load_model, predict
        if self.model is None:
            self.model = load_model(OLD_MODEL)
        reference = benchmark.reference(target, renderer)
        objective = Objective(reference)
        scored = []
        for candidate in predict(*self.model, reference, renderer, per_synth=2):
            found = best_rendered([candidate], renderer, objective)
            if found:
                scored.append(found)
        scored.sort(key=lambda item: item[0]['score'])
        starts, seen = [], set()
        for item in scored:
            if item[0]['synth'] not in seen:
                seen.add(item[0]['synth']); starts.append(item)
            if len(starts) == self.starts:
                break
        rng = np.random.default_rng(0)
        results = []
        for best in starts:
            for step in range(self.budget):
                sigma = (.25, .12, .06, .025)[min(3, step*4//self.budget)]
                trial = dict(best[0], params=mutate_controls(best[0]['params'], renderer.specs[best[0]['synth']], rng, sigma))
                found = best_rendered([trial], renderer, objective)
                if found and found[0]['score'] < best[0]['score']:
                    best = found
            results.append(best)
        return target['id'], min(results, key=lambda item: item[0]['score']) if results else None


def run_pool(fn, out, targets, jobs):
    started = time.monotonic()
    with RenderPool(fn, jobs) as pool:
        scores = {}
        for target, result in zip(targets, pool.map(targets)):
            if result[0] is None or result[1] is None:
                print(f'{target["id"]}: failed {result[1]}', flush=True)
                continue
            info, wave = result[1]
            save(out, target['id'], wave, info); scores[target['id']] = info['score']
            print(f'{target["id"]}: {info["synth"]} {info["score"]:.3f}', flush=True)
    summarise(out, scores, started)


def summarise(out, scores, started):
    if not scores:
        raise SystemExit('No targets produced a result; check --only and --kind')
    Path(out, 'summary.json').write_text(json.dumps({'scores': scores, 'minutes': (time.monotonic()-started)/60}))
    values = np.asarray(list(scores.values()))
    print(f'{len(values)} targets, mean objective {values.mean():.3f}, median {np.median(values):.3f}, '
          f'{(time.monotonic()-started)/60:.1f} min', flush=True)


def run_bfxr(out, targets, budget=2000):
    """The original single-synth pipeline, unchanged: its own inverse model, objective and optimizer."""
    from match.objective import MatchObjective
    from match.renderer import BfxrRenderer
    from neural_invert.evaluate import OriginalBfxr
    started, scores = time.monotonic(), {}
    with FastRenderer() as renderer, BfxrRenderer() as bfxr:
        original = OriginalBfxr(BFXR_MODEL, bfxr)
        for target in targets:
            done = Path(out, f'{target["id"]}.json')
            if done.exists():
                scores[target['id']] = json.loads(done.read_text())['score']
                continue
            reference = benchmark.reference(target, renderer)
            try:
                result = original.approximate(reference, MatchObjective(reference), budget=budget)
            except ValueError as error:
                print(f'{target["id"]}: failed {error}', flush=True)
                continue
            score = Objective(reference).score(result['wave'])
            save(out, target['id'], result['wave'], {'synth': 'Bfxr', 'params': result['params'], 'seed': result['seed'],
                                                     'score': score, 'backend': 'bfxr_native'})
            scores[target['id']] = score
            print(f'{target["id"]}: Bfxr {score:.3f}', flush=True)
    summarise(out, scores, started)


def run_search(out, targets, library, checkpoint=None, jobs=None, per_synth=48, **settings):
    """Retrieval (and model proposals, if a checkpoint is given) seeding CMA-ES.

    Also writes <out>-alt2 / <out>-alt3 (the next best distinct synths) and
    <out>-seed (best candidate before any optimisation).
    """
    from .search import Library, search
    started, scores = time.monotonic(), {}
    index = Library(library)
    inverter = None
    if checkpoint:
        from .infer import Inverter
        inverter = Inverter(checkpoint)
    out = Path(out)
    with FastRenderer() as renderer:
        for target in targets:
            if (out/f'{target["id"]}.json').exists():
                scores[target['id']] = json.loads((out/f'{target["id"]}.json').read_text())['score']
                continue
            reference = benchmark.reference(target, renderer)
            seeds = [index.row(i) for i in index.nearest(reference, per_synth)]
            if inverter:
                seeds += inverter.propose(reference, renderer, top_synths=6, per_synth=16)
            print(f'{target["id"]} {target.get("file") or target["synth"]}: {len(seeds)} seeds', flush=True)
            results = search(reference, seeds, index.specs, jobs=jobs, **settings)
            objective = Objective(reference)
            seed_best = min(results, key=lambda r: r['seedScore'])
            for suffix, row in zip(('', '-alt2', '-alt3'), results):
                _, wave = renderer.render(row['synth'], row['params'], row['seed'])
                save(str(out)+suffix, target['id'], wave, {k: row[k] for k in ('synth', 'params', 'seed', 'score', 'seedScore', 'evaluations')})
            _, wave = renderer.render(seed_best['synth'], seed_best['seedParams'], seed_best['seed'])
            save(str(out)+'-seed', target['id'], wave, {'synth': seed_best['synth'], 'params': seed_best['seedParams'],
                                                        'seed': seed_best['seed'], 'score': objective.score(wave)})
            scores[target['id']] = results[0]['score']
    summarise(out, scores, started)


def compare(systems):
    """Score every system's saved audio under the current objective, on the targets all of them have."""
    names = list(systems)
    shared = [t for t in benchmark.targets() if all(Path(d, f'{t["id"]}.wav').exists() for d in systems.values())]
    scores = {name: {} for name in names}
    with FastRenderer() as renderer:
        for target in shared:
            objective = Objective(benchmark.reference(target, renderer))
            for name in names:
                wave, _ = sf.read(Path(systems[name], f'{target["id"]}.wav'), dtype='float32', always_2d=True)
                scores[name][target['id']] = objective.score(wave[:, 0])
    for kind, prefix in (('external', 'ext'), ('native', 'nat')):
        ids = [t['id'] for t in shared if t['id'].startswith(prefix)]
        if not ids:
            continue
        print(f'{kind}: {len(ids)} targets, mean objective (lower is closer) and share of targets where each system is best')
        for name in names:
            values = np.asarray([scores[name][i] for i in ids])
            best = np.mean([scores[name][i] == min(scores[n][i] for n in names) for i in ids])
            print(f'  {name:24s} mean {values.mean():.3f}  median {np.median(values):.3f}  best on {best*100:3.0f}%')
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('system', choices=['oneshot', 'search', 'old-branch', 'bfxr', 'compare'])
    parser.add_argument('systems', nargs='*', help='for compare: label=directory ...')
    parser.add_argument('--out')
    parser.add_argument('--checkpoint'); parser.add_argument('--library')
    parser.add_argument('--kind', choices=['external', 'native']); parser.add_argument('--only', nargs='+')
    parser.add_argument('--jobs', type=int)
    parser.add_argument('--top-synths', type=int, default=5); parser.add_argument('--restarts', type=int, default=3)
    parser.add_argument('--budget', type=int, default=2000, help='renders per CMA-ES restart (search) or total (bfxr)')
    args = parser.parse_args()
    if args.system == 'compare':
        compare(dict(item.split('=', 1) for item in args.systems))
        return
    if not args.out:
        parser.error('--out is required')
    targets = [t for t in benchmark.targets(args.kind) if not args.only or t['id'] in args.only]
    if args.system == 'oneshot':
        run_pool(OneShot(args.checkpoint), args.out, targets, args.jobs)
    elif args.system == 'old-branch':
        run_pool(OldBranch(), args.out, targets, args.jobs)
    elif args.system == 'bfxr':
        run_bfxr(args.out, targets, args.budget)
    else:
        run_search(args.out, targets, args.library, args.checkpoint, args.jobs,
                   top_synths=args.top_synths, restarts=args.restarts, budget=args.budget)


if __name__ == '__main__':
    main()
