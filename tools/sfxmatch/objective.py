"""The one fixed matching objective.

Two parts, equally weighted and neither fitted to listening data:

* support-trimmed soft-periodicity (multisynth.soft_periodicity): envelope,
  continuous pitch/periodicity maps and their motion, i.e. gesture;
* a multi-scale log-mel distance, i.e. spectral balance, counted only where
  at least one of the two sounds is audible so silence cannot dilute it.

History: v1 was soft-periodicity alone, chosen because it agreed best with
archived preference pairs. Those pairs compare finalists of earlier searches
that already matched the spectrum, so they never showed what v1 does when it
drives a search itself: it accepted candidates 25 dB too loud across half the
spectrum, and the listener rated them unrelated. Judge an objective by what
its optimum sounds like (the reach probe), not only by pairwise agreement.

Use scores to get into the right neighbourhood and show the listener several
different candidates. Human judgments are a test set (sfxmatch.agreement).
"""
import numpy as np

from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.support_objective import analysis_support
from .mel import BANDS, FLOOR_DB, logmel, trim

VERSION = 2
INFEASIBLE = 1e3
SPECTRAL_WEIGHT = 1.   # a mean 10 dB spectral error costs 1.0, about a third of a typical total
AUDIBLE_DB = 60.       # frames quieter than this below peak in both sounds are ignored
MAX_FRAMES = 1024      # ~12 s


def spectrum(wave):
    return logmel(trim(wave))[:, :MAX_FRAMES]


def spectral_distance(a, b):
    """Mean |dB| difference / 10 between two spectrum() arrays, over audible frames, at four scales."""
    frames = max(a.shape[1], b.shape[1])
    frames += -frames % 8
    pad = lambda db: np.pad(db, ((0, 0), (0, frames-db.shape[1])), constant_values=-FLOOR_DB)
    a, b = pad(a), pad(b)
    total = 0.
    for k in (1, 2, 4, 8):
        pa, pb = (db.reshape(BANDS//k, k, frames//k, k).mean(axis=(1, 3)) for db in (a, b))
        weight = np.clip((np.maximum(pa.max(axis=0), pb.max(axis=0))+AUDIBLE_DB)/AUDIBLE_DB, 0, 1)
        total += float((np.abs(pa-pb).mean(axis=0)*weight).sum()/max(weight.sum(), 1e-9))
    return total/40


class Objective:
    def __init__(self, target):
        self._gesture = SoftPeriodicityObjective(analysis_support(target))
        self._spectrum = spectrum(target)

    def components(self, wave):
        wave = np.asarray(wave, dtype=np.float32)
        return {'gesture': float(self._gesture.score(analysis_support(wave))),
                'spectrum': SPECTRAL_WEIGHT*spectral_distance(self._spectrum, spectrum(wave))}

    def score(self, wave):
        """Lower is closer; silent or invalid audio is infeasible."""
        wave = np.asarray(wave, dtype=np.float32)
        if wave.ndim != 1 or len(wave) < 64 or not np.isfinite(wave).all() or np.max(np.abs(wave)) < 1e-7:
            return INFEASIBLE
        return sum(self.components(wave).values())


class Score:
    """RenderPool task (synth, params, seed) -> (canonical params, score against one target)."""

    def __init__(self, target):
        self.target = np.asarray(target, dtype=np.float32)
        self.objective = None

    def __call__(self, renderer, task):
        if self.objective is None:
            self.objective = Objective(self.target)
        synth, params, seed = task
        canonical, wave = renderer.render(synth, params, seed)
        return canonical, self.objective.score(wave)
