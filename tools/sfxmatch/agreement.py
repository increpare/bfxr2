"""How often does each objective agree with the listener? A test, not a fit.

    uv run python -m sfxmatch.agreement
"""
from collections import defaultdict

import numpy as np

from . import objective
from .pairs import load_pairs


def _fixed(reference):
    return objective.Objective(reference).score


def _gesture(reference):
    scorer = objective.Objective(reference)
    return lambda wave: scorer.components(wave)['gesture']


def _spectrum(reference):
    scorer = objective.Objective(reference)
    return lambda wave: scorer.components(wave)['spectrum']


def _auditory(reference):
    from multisynth import features
    target = features.describe(reference)
    return lambda wave: float(features.distances(target, features.describe(wave)[None])[0])


def _preference(reference):
    from pathlib import Path
    from multisynth import features
    from multisynth.preference import PreferenceMetric
    metric = PreferenceMetric.load(Path(__file__).resolve().parents[1]/'multisynth/models/preference-neural-v2.json')
    target = features.describe(reference)
    return lambda wave: float(metric.distances(target, features.describe(wave)[None])[0])


def _legacy(reference):
    from multisynth.support_objective import SupportObjective
    scorer = SupportObjective(reference)
    return lambda wave: float(scorer.score(wave))


OBJECTIVES = {'sfxmatch fixed (gesture + spectrum)': _fixed,
              '  gesture part alone (v1, soft-periodicity)': _gesture,
              '  spectrum part alone': _spectrum, 'auditory-v1': _auditory,
              'preference-neural-v2 (fitted on early labels)': _preference,
              'legacy contour (support-trimmed)': _legacy}


def evaluate(pairs, objectives=OBJECTIVES):
    by_reference = defaultdict(list)
    for pair in pairs:
        by_reference[(pair['session'], pair['referenceId'])].append(pair)
    table = {}
    for label, build in objectives.items():
        correct, balanced, late = [], [], []
        for (session, _), group in by_reference.items():
            score = build(group[0]['reference'])
            hits = [score(p['better']) < score(p['worse']) for p in group]
            correct += hits
            balanced.append(np.mean(hits))
            if session >= '2026-10-05':
                late += hits
        table[label] = {'pairs': len(correct), 'agree': float(np.mean(correct)),
                        'referenceBalanced': float(np.mean(balanced)),
                        'since10-05': float(np.mean(late)), 'since10-05Pairs': len(late)}
    return table


def main():
    pairs = load_pairs()
    print(f'{len(pairs)} strict pairs, {len({(p["session"], p["referenceId"]) for p in pairs})} judged references')
    for label, row in evaluate(pairs).items():
        print(f'{label:52s} {row["agree"]*100:5.1f}%  reference-balanced {row["referenceBalanced"]*100:5.1f}%'
              f'  later sessions {row["since10-05"]*100:5.1f}% (n={row["since10-05Pairs"]})')


if __name__ == '__main__':
    main()
