"""A bounded diagnostic of frozen surrogate gradients, not a trained inverse."""
import numpy as np

POLICY = dict(cases=32, minimumImprovements=24, primaryRadius=.005,
              primaryDirection=1, maximumPitchRegressions=0,
              meaning='Local actual-DSP gradient prerequisite; not human likeness')


def local_step(unit, gradient, radius, direction=1):
    unit, gradient = np.asarray(unit, dtype=np.float64), np.asarray(gradient, dtype=np.float64)
    if (unit.ndim != 1 or unit.size == 0 or gradient.shape != unit.shape
            or not np.isfinite(unit).all() or not np.isfinite(gradient).all()
            or np.any((unit < 0) | (unit > 1))
            or not np.isfinite(radius) or not 0 < radius <= 1 or direction not in (-1, 1)):
        raise ValueError('Invalid bounded gradient step')
    norm = float(np.max(np.abs(gradient)))
    return np.clip(unit-direction*radius*gradient/norm, 0, 1) if norm else unit.copy()


def primary_gate(summary):
    checks = dict(complete=summary['cases'] == POLICY['cases'],
                  improvements=summary['improvements'] >= POLICY['minimumImprovements'],
                  meanDecreased=summary['meanAfter'] < summary['meanBefore'])
    for key in ('additionalSilence', 'reliablePitchLosses', 'staticPitchLosses', 'movingDirectionLosses'):
        checks[key] = summary[key] == 0
    return dict(passed=bool(all(checks.values())), checks=checks, policy=POLICY)
