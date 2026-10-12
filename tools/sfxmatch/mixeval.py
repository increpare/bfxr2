"""Can the mix model reproduce Mixr's own output? Judged by re-rendered audio.

    python -m sfxmatch.mixeval --checkpoint runs/mixmodel/best.pt --single runs/model-1m/best.pt --val runs/mix-val
    python -m sfxmatch.mixeval ... --bench NAME     # also write the frozen mix benchmark's audio and listening page

Each held-out mix is predicted, rendered through the real Mixr and scored
with the fixed objective. The single-synth model is the comparison: what a
system that cannot layer does with the same sound.
"""
import argparse
import json
from pathlib import Path

import cma
import numpy as np

from . import benchmark
from .objective import INFEASIBLE, Objective
from .render import FastRenderer, RenderPool
from .search import Space
from .systems import save

HERE = Path(__file__).resolve().parent


def refine(start, specs, score, budget, sigma=.1, popsize=16, seed=1):
    """CMA-ES over every control of both sources and the balance at once, from one proposal."""
    spaces = [Space(specs[s['synth']], s['params']) for s in start['sources']]
    sizes = [len(space.encode(s['params'])) for space, s in zip(spaces, start['sources'])]
    pair = len(spaces) == 2

    def decode(x):
        sources, at = [], 0
        for space, size, source in zip(spaces, sizes, start['sources']):
            sources.append(dict(source, params=space.decode(x[at:at+size]))); at += size
        return {'sources': sources, 'balance': float(x[-1]) if pair else .5}

    x0 = np.concatenate([space.encode(s['params']) for space, s in zip(spaces, start['sources'])] +
                        ([[start['balance']]] if pair else []))
    es = cma.CMAEvolutionStrategy(x0, sigma, {'bounds': [0, 1], 'popsize': popsize, 'seed': seed, 'verbose': -9})
    best, best_score, used = start, score(start), 0
    while used < budget and not es.stop():
        xs = es.ask()
        values = []
        for x in xs:
            candidate = decode(x)
            values.append(score(candidate))
            if values[-1] < best_score:
                best, best_score = candidate, values[-1]
        es.tell(xs, values); used += len(xs)
    return best, best_score


class MixEval:
    def __init__(self, checkpoint, single, keep_audio=False, search=0):
        self.checkpoint, self.single, self.keep_audio = str(checkpoint), single and str(single), keep_audio
        self.search = search
        self.mixer = self.inverter = None

    def __call__(self, renderer, task):
        if self.mixer is None:
            from .infer import Inverter
            from .mixmodel import MixInverter
            self.mixer = MixInverter(self.checkpoint)
            self.inverter = Inverter(self.single) if self.single else None
        _, _, target, _ = renderer.mix(task['sources'], task['balance'])
        objective = Objective(target)

        def mixed(proposal):
            try:
                return objective.score(renderer.mix(proposal['sources'], proposal['balance'])[2])
            except (ValueError, RuntimeError):
                return INFEASIBLE

        proposals = self.mixer.propose(target, renderer)
        scores = [mixed(p) for p in proposals]
        best = proposals[int(np.argmin(scores))]
        truth = sorted(s['synth'] for s in task['sources'])
        row = {'kind': 'single' if len(truth) == 1 else 'twin' if truth[0] == truth[1] else 'pair',
               'structureCorrect': sorted(s['synth'] for s in proposals[0]['sources']) == truth,
               'structureInTop6': any(sorted(s['synth'] for s in p['sources']) == truth for p in proposals),
               'mix model, one-shot': scores[0], 'mix model, best of 24': min(scores),
               'true controls, new noise seeds': mixed({'sources': [dict(s, seed=(s['seed']+.37) % 1) for s in task['sources']],
                                                        'balance': task['balance']})}
        audio = {'mix model': renderer.mix(best['sources'], best['balance'])[2]} if self.keep_audio else {}
        if self.search:
            # Refine the two best proposals with different structures, then keep the closer.
            starts, seen = [], set()
            for i in np.argsort(scores):
                key = tuple(sorted(s['synth'] for s in proposals[i]['sources']))
                if key not in seen and scores[i] < INFEASIBLE:
                    seen.add(key); starts.append(proposals[i])
                if len(starts) == 2:
                    break
            refined = [refine(start, renderer.specs, mixed, self.search//2, seed=n+1) for n, start in enumerate(starts)]
            best, row['mix model + search'] = min(refined, key=lambda item: item[1])
            if self.keep_audio:
                audio['mix model + search'] = renderer.mix(best['sources'], best['balance'])[2]
        if self.inverter:
            singles = self.inverter.propose(target, renderer, top_synths=3, per_synth=8)
            single_scores = [mixed({'sources': [{'synth': c['synth'], 'params': c['params'], 'seed': .5}], 'balance': .5})
                             for c in singles]
            row['single-synth model, best of 24'] = min(single_scores)
            if self.keep_audio:
                chosen = singles[int(np.argmin(single_scores))]
                audio['single-synth model'] = renderer.mix([{'synth': chosen['synth'], 'params': chosen['params'], 'seed': .5}])[2]
        return task.get('id'), (row, {'target': target, **audio} if self.keep_audio else None,
                                {'sources': best['sources'], 'balance': best['balance']})


def held_out(val, count, seed=0):
    rows = []
    for shard in sorted(Path(val).glob('mix-*.jsonl')):
        rows += [json.loads(line) for line in shard.read_text().splitlines()]
    order = np.random.default_rng(seed).permutation(len(rows))[:count]
    return [rows[i] for i in order]


def report(rows):
    keys = [k for k in rows[0] if k not in ('kind', 'structureCorrect', 'structureInTop6')]
    for kind in ('all', 'single', 'pair', 'twin'):
        mine = [r for r in rows if kind in ('all', r['kind'])]
        if not mine:
            continue
        print(f'{kind}: {len(mine)} sounds; structure right first time {np.mean([r["structureCorrect"] for r in mine])*100:.0f}%, '
              f'within six guesses {np.mean([r["structureInTop6"] for r in mine])*100:.0f}%')
        for key in keys:
            values = np.asarray([r[key] for r in mine])
            print(f'    {key:34s} mean {values[values < INFEASIBLE].mean():.3f}  median {np.median(values):.3f}')
    if 'single-synth model, best of 24' in rows[0]:
        wins = np.mean([r['mix model, best of 24'] < r['single-synth model, best of 24'] for r in rows if r['kind'] != 'single'])
        print(f'on two-source sounds the mix model beats the single-synth model on {wins*100:.0f}%')


def freeze_bench(count=40, seed=3):
    """Write mixbench.json once: held-out mixes drawn with a seed no training set uses."""
    from .mixdata import MixDraw
    from .render import active_synths
    path = HERE/'mixbench.json'
    if path.exists():
        raise FileExistsError(f'{path} already exists; the mix benchmark is frozen')
    targets = []
    with FastRenderer() as renderer:
        draw, attempt = MixDraw(active_synths(renderer)), 0
        while len(targets) < count:
            attempt += 1
            try:
                row, _ = draw(renderer, [seed, 0, attempt])
            except ValueError:
                continue
            targets.append({'id': f'mix-{len(targets)+1:03d}', **row})
    path.write_text(json.dumps({'version': 1, 'seed': seed, 'targets': targets}, indent=1)+'\n')
    return targets


def recordings(name, checkpoint, only, structures=12, per_structure=8):
    """Mix-model proposals for benchmark recordings, with no search, picked two ways.

    The objective and CLAP each choose their favourite among the same proposals,
    so a listener can say which judge to trust. Round 2's searched single-synth
    result is included as the anchor.
    """
    import torch
    import torchaudio
    from .mixmodel import MixInverter
    from .tags import RATE, clap, vector
    mixer = MixInverter(checkpoint)
    model, processor = clap()

    def embed(waves):
        clips = [torchaudio.functional.resample(torch.from_numpy(w/max(float(np.max(np.abs(w))), 1e-9)), 44100, RATE).numpy()[:RATE*10]
                 for w in waves]
        with torch.no_grad():
            parts = [vector(model.get_audio_features(**processor(audio=clips[at:at+32], sampling_rate=RATE, return_tensors='pt')))
                     for at in range(0, len(clips), 32)]
        return torch.nn.functional.normalize(torch.cat(parts), dim=-1).numpy()

    root = HERE/'runs/systems'
    with FastRenderer() as renderer:
        for target in benchmark.targets('external'):
            if only and target['id'] not in only:
                continue
            reference = benchmark.reference(target, renderer)
            objective = Objective(reference)
            rendered = []
            for proposal in mixer.propose(reference, renderer, structures=structures, per_structure=per_structure):
                try:
                    wave = renderer.mix(proposal['sources'], proposal['balance'])[2]
                except (ValueError, RuntimeError):
                    continue
                score = objective.score(wave)
                if score < INFEASIBLE:
                    rendered.append((proposal, wave, score))
            vectors = embed([reference]+[wave for _, wave, _ in rendered])
            likeness = vectors[1:] @ vectors[0]
            picks = {'objective': int(np.argmin([score for _, _, score in rendered])), 'clap': int(np.argmax(likeness))}
            for judge, index in picks.items():
                proposal, wave, score = rendered[index]
                save(root/f'{name}-{judge}', target['id'], wave, {'sources': proposal['sources'], 'balance': proposal['balance'],
                                                                  'score': score, 'clap': float(likeness[index])})
            describe = lambda i: ' + '.join(s['synth'] for s in rendered[i][0]['sources'])
            print(f'{target["id"]} {target["file"][:34]:34s} {len(rendered)} proposals | objective picks {describe(picks["objective"])} '
                  f'({rendered[picks["objective"]][2]:.2f}) | CLAP picks {describe(picks["clap"])} ({likeness[picks["clap"]]:.2f})'
                  f'{" (same)" if picks["objective"] == picks["clap"] else ""}', flush=True)
    systems = {'mix model, picked by objective': root/f'{name}-objective', 'mix model, picked by CLAP': root/f'{name}-clap',
               'round 2 search (single synth)': root/'reach2'}
    index, count = benchmark.page(name, systems, only=only, inline=True)
    print(f'{count} targets -> {index}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--checkpoint', required=True); parser.add_argument('--single')
    parser.add_argument('--val'); parser.add_argument('--count', type=int, default=300)
    parser.add_argument('--bench', help='name for a listening page over the frozen mix benchmark')
    parser.add_argument('--jobs', type=int); parser.add_argument('--out')
    parser.add_argument('--search', type=int, default=0, help='also refine with this many Mixr renders per sound')
    parser.add_argument('--recordings', help='name for a page of mix-model proposals for benchmark recordings')
    parser.add_argument('--only', nargs='+')
    args = parser.parse_args()
    if args.recordings:
        recordings(args.recordings, args.checkpoint, args.only)
    elif args.bench:
        targets = benchmark.mix_targets() or freeze_bench()
        with RenderPool(MixEval(args.checkpoint, args.single, keep_audio=True, search=args.search), args.jobs) as pool:
            results = [r for r in pool.map(targets) if r[0] is not None]
        root = HERE/'runs/systems'
        with_audio = []
        for target, (target_id, (row, audio, patch)) in zip(targets, results):
            title = ' + '.join(s['synth'] for s in target['sources'])
            with_audio.append((target_id, title, audio['target']))
            for label, sound in audio.items():
                if label != 'target':
                    save(root/f'{args.bench}-{label.replace(" ", "-")}', target_id, sound, patch if label != 'single-synth model' else {})
        systems = {label: root/f'{args.bench}-{label.replace(" ", "-")}' for label in results[0][1][1] if label != 'target'}
        index, count = benchmark.page(args.bench, systems, targets_with_audio=with_audio)
        print(f'{count} targets -> {index}')
        report([r[1][0] for r in results])
    else:
        with RenderPool(MixEval(args.checkpoint, args.single, search=args.search), args.jobs) as pool:
            rows = [r[1][0] for r in pool.map(held_out(args.val, args.count)) if r[0] is not None or isinstance(r[1], tuple)]
        report(rows)
        if args.out:
            Path(args.out).write_text(json.dumps(rows))


if __name__ == '__main__':
    main()
