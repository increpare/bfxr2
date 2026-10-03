"""Synth-specific bounded search experts and an automatic perceptual selector."""
from copy import deepcopy
import time
import numpy as np
from .features import describe, distances, components, prepare


class ControlSpace:
    def __init__(self, spec):
        self.controls = []
        for p in spec['params']:
            name = p['name']
            if name in ('masterVolume', 'seed') or (spec.get('name') == 'Jinglr' and name in ('noteCount','contour','rhythm')):
                continue
            if p['type'] == 'BUTTONSELECT':
                self.controls.append(((name,), p['values']))
            elif p['type'] == 'KNOB_TRANSITION':
                for side in ('start','end'):
                    self.controls.append(((name,side), (p['min'],p['max'])))
                if p.get('values'):
                    self.controls.append(((name,'curve'),p['values']))
            elif isinstance(p.get('min'), (int,float)) and p.get('max',0) > p['min']:
                self.controls.append(((name,), (p['min'],p['max'])))

    def mutate(self, params, rng, sigma):
        result = deepcopy(params)
        if not self.controls:
            return result
        count = min(len(self.controls), int(rng.integers(1,5)))
        for index in rng.choice(len(self.controls), size=count, replace=False):
            path, bounds = self.controls[index]
            obj = result
            for key in path[:-1]:
                obj = obj[key]
            key = path[-1]
            if isinstance(bounds, list):
                obj[key] = bounds[int(rng.integers(len(bounds)))]
            else:
                low, high = bounds
                obj[key] = float(np.clip(obj[key] + rng.normal()*sigma*(high-low), low, high))
        return result


def approximate(renderer, library, target, *, experts=5, budget=96, seed=1234, synths=None):
    if experts < 1 or budget < 0:
        raise ValueError('experts must be positive and budget nonnegative')
    target = prepare(target)
    descriptor = describe(target)
    eligible = [name for name,spec in renderer.specs.items() if spec.get('collectionCompatible', False)]
    if synths is not None:
        if set(synths)-set(eligible):
            raise ValueError('Requested synths cannot be loaded through normal collection import')
        eligible = synths
    retrieved = library.retrieve(descriptor, per_synth=4, synths=eligible)
    if not retrieved:
        raise ValueError('No eligible synths in library')
    names = list(dict.fromkeys(row['synth'] for row in retrieved))[:experts]
    if any(r['synth']=='Bfxr' for r in retrieved) and 'Bfxr' not in names:
        names.append('Bfxr')
    started = time.monotonic()
    results = []
    for name in names:
        # Seed separately, so Bfxr gets identical search in baseline/multi runs.
        synth_seed = sum((i+1)*ord(c) for i,c in enumerate(name))
        rng = np.random.default_rng(seed+synth_seed)
        elites = [deepcopy(r) for r in retrieved if r['synth']==name]
        initial = elites[0]['score']
        space = ControlSpace(renderer.specs[name])
        failures, trace = 0, [initial]
        for step in range(budget):
            parent = elites[0] if step % 3 else elites[int(rng.integers(len(elites)))]
            sigma = [.18,.09,.04,.015][min(3,step*4//max(1,budget))]
            params = space.mutate(parent['params'], rng, sigma)
            # An informed first proposal fits the target's actual duration.
            if step == 0 and 'duration' in params:
                params['duration'] = len(target)/44100
            try:
                params, wave = renderer.render(name, params, parent['seed'])
                candidate_descriptor = describe(wave)
                score = float(distances(descriptor, candidate_descriptor[None])[0])
            except (ValueError, RuntimeError):
                failures += 1
                trace.append(elites[0]['score'])
                continue
            row = dict(parent, params=params, score=score)
            # Never discard an incumbent: refinement cannot worsen retrieval.
            elites.append(row)
            elites.sort(key=lambda r:r['score'])
            elites = elites[:4]
            trace.append(elites[0]['score'])
        best = elites[0]
        best.update(initial_score=initial, evaluations=budget, failures=failures, trace=trace)
        # Export audio is an additional deterministic replay, outside search budget.
        params, wave = renderer.render(name, best['params'], best['seed'])
        replay_descriptor = describe(wave)
        replay_score = float(distances(descriptor, replay_descriptor[None])[0])
        if abs(replay_score-best['score']) > 1e-5:
            raise ValueError(f'{name} replay changed its score; stale library or nondeterministic DSP')
        best.update(params=params, wave=wave,
                    components={k:float(v[0]) for k,v in components(descriptor,replay_descriptor[None]).items()})
        results.append(best)
        print(f'  {name}: {initial:.3f} → {best["score"]:.3f} ({budget} evaluations)', flush=True)
    results.sort(key=lambda r:r['score'])
    return {'candidates':results, 'seconds':time.monotonic()-started,
            'search_evaluations':len(names)*budget, 'export_renders':len(names),
            'seed':seed, 'experts_requested':experts, 'budget_per_expert':budget,
            'retrieval_best':retrieved[0]['score']}
