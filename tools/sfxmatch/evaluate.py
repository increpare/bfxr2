"""Judge inverse models by the audio they produce, on held-out native sounds.

For each held-out sound: predict controls, render them, and measure the fixed
objective against the original. Parameter error is not reported because many
controls are inaudible; only the re-rendered sound counts.

    python -m sfxmatch.evaluate --checkpoint runs/model-1m/best.pt --val runs/data-val
"""
import argparse
import json
from pathlib import Path

import numpy as np

from .objective import INFEASIBLE, Objective
from .render import RenderPool
from .systems import OLD_MODEL


class Native:
    def __init__(self, checkpoint, per_synth=8):
        self.checkpoint, self.per_synth, self.inverter, self.old = str(checkpoint), per_synth, None, None

    def __call__(self, renderer, task):
        from neural_invert.predict import load_model, predict
        if self.inverter is None:
            from .infer import Inverter
            self.inverter, self.old = Inverter(self.checkpoint), load_model(OLD_MODEL)
        synth, params, seed = task
        _, target = renderer.render(synth, params, seed)
        objective = Objective(target)

        def scores(candidates):
            values = []
            for c in candidates:
                try:
                    values.append(objective.score(renderer.render(c['synth'], c['params'], c['seed'])[1]))
                except (ValueError, RuntimeError):
                    values.append(INFEASIBLE)
            return values

        embedding = self.inverter.embed(target)
        names = self.inverter.model.names
        ranked = [names[i] for i in self.inverter.model.synth(embedding)[0].argsort(descending=True)[:3].tolist()]
        own = self.inverter.propose(target, renderer, synths=[synth], per_synth=self.per_synth)
        own_scores = scores(own)
        guess = [c for c in self.inverter.propose(target, renderer, synths=[n for n in ranked if n != synth],
                                                  per_synth=self.per_synth)]
        guess_scores = dict(zip(range(len(guess)), scores(guess)))
        by_synth = {synth: own_scores}
        for i, c in enumerate(guess):
            by_synth.setdefault(c['synth'], []).append(guess_scores[i])
        old = predict(*self.old, target, renderer, per_synth=2)
        old_scores = scores(old)
        old_own = [s for c, s in zip(old, old_scores) if c['synth'] == synth]
        presets = renderer.specs[synth]['presets']
        prior = scores([{'synth': synth, 'params': renderer.sample(synth, presets[seed % len(presets)], seed % 9973), 'seed': 1}])
        reseeded = scores([{'synth': synth, 'params': params, 'seed': (seed+1) % 2**32}])
        return task, {'synth': synth, 'synthCorrect': ranked[0] == synth,
                      'new one-shot, synth given': own_scores[0],
                      'new best of 8, synth given': min(own_scores),
                      'new one-shot, synth predicted': by_synth[ranked[0]][0],
                      'new best of 24, synth predicted': min(min(by_synth[n]) for n in ranked),
                      'old MLP one-shot, synth given': old_own[0] if old_own else INFEASIBLE,
                      'old MLP best of 44, all synths': min(old_scores),
                      'random preset of the right synth': prior[0],
                      'true controls, different noise seed': reseeded[0]}


def held_out(val, per_synth, seed=0):
    rng = np.random.default_rng(seed)
    tasks = []
    for shard in sorted(Path(val).glob('*.npz')):
        name = shard.stem.rsplit('-', 1)[0]
        lines = shard.with_suffix('.jsonl').read_text().splitlines()
        with np.load(shard) as z:
            seeds = z['seed']
        mine = sum(1 for t in tasks if t[0] == name)
        for i in rng.permutation(len(lines))[:max(0, per_synth-mine)]:
            tasks.append((name, json.loads(lines[i]), int(seeds[i])))
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--checkpoint', required=True); parser.add_argument('--val', required=True)
    parser.add_argument('--per-synth', type=int, default=20); parser.add_argument('--jobs', type=int)
    parser.add_argument('--out')
    args = parser.parse_args()
    tasks = held_out(args.val, args.per_synth)
    with RenderPool(Native(args.checkpoint), args.jobs) as pool:
        rows = [r[1] for r in pool.map(tasks) if r[0] is not None]
    keys = [k for k in rows[0] if k not in ('synth', 'synthCorrect')]
    table = {k: np.asarray([r[k] for r in rows]) for k in keys}
    print(f'{len(rows)} held-out native sounds; synth identified correctly {np.mean([r["synthCorrect"] for r in rows])*100:.1f}%')
    print('objective distance to the original (lower is closer):')
    for k in keys:
        print(f'  {k:36s} mean {table[k].mean():.3f}  median {np.median(table[k]):.3f}')
    a, b = table['new one-shot, synth given'], table['old MLP one-shot, synth given']
    print(f'new beats old one-shot (synth given) on {np.mean(a < b)*100:.0f}% of sounds')
    a, b = table['new best of 24, synth predicted'], table['old MLP best of 44, all synths']
    print(f'new best-of-24 beats old best-of-44 on {np.mean(a < b)*100:.0f}% of sounds')
    if args.out:
        Path(args.out).write_text(json.dumps(rows))


if __name__ == '__main__':
    main()
