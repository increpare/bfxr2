"""Staged black-box search over Bfxr's parameter space.

Stage 0: random screen per wave type (biased toward defaults).
Stage 1: short CMA-ES on the top wave types.
Stage 2: full CMA-ES on the winner, until the eval budget runs out.
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

import cma
import numpy as np

from .audio import SAMPLE_RATE
from .bfxr_io import ParamSpace
from .objective import MatchObjective
from .renderer import BfxrRenderer

RENDER_SEED = 1234
ENVELOPE_PARAMS = ("attackTime", "sustainTime", "decayTime")
# envelope stage length in samples is param^2 * 100000 (Bfxr_DSP.js reset())
ENVELOPE_SAMPLES_PER_UNIT = 100000.0
SQUARE_ONLY_PARAMS = ("squareDuty", "dutySweep")
# oscillator period is 100/(fs^2+0.001) supersamples at 8x supersampling,
# so pitch in Hz = 8 * 44100 * (fs^2 + 0.001) / 100 (verified empirically)
SUPERSAMPLED_RATE = 8 * SAMPLE_RATE


def freq_param_from_hz(hz: float) -> float | None:
    fs_sq = hz * 100.0 / SUPERSAMPLED_RATE - 0.001
    if fs_sq <= 0:
        return None
    return float(np.sqrt(fs_sq))


@dataclass(order=True)
class Candidate:
    score: float
    wave_type: int = field(compare=False)
    unit: np.ndarray = field(compare=False)


@dataclass
class OptimizeSettings:
    budget: int = 5000
    time_budget: float | None = None
    popsize: int = 28  # generous for CMA in 30-dim, but it parallelizes across workers and is noise-robust
    screen_size: int = 64
    stage1_iters: int = 25
    stage1_keep: int = 3
    wave_types: list[int] | None = None
    avg_seeds: int = 1
    rng_seed: int = 0
    top_k: int = 3
    verbose: bool = True
    refine_steps: int = 0  # 0 = skip Stage 3
    refine_eps: float = 0.015
    refine_step0: float = 0.05
    seed_units: list[tuple[int, np.ndarray]] | None = None  # (wave_type, unit)
    seed_jitter: float = 0.05
    seed_jitter_copies: int = 8


class StagedOptimizer:
    def __init__(
        self,
        space: ParamSpace,
        renderer: BfxrRenderer,
        objective: MatchObjective,
        settings: OptimizeSettings,
        target: np.ndarray | None = None,
    ):
        self.space = space
        self.renderer = renderer
        self.objective = objective
        self.s = settings
        self.rng = np.random.default_rng(settings.rng_seed)
        self.evals = 0
        self.t0 = time.perf_counter()
        self.archive: list[Candidate] = []
        self.trace: list[tuple[int, float]] = []  # (evals, best score so far)

        self.upper = np.ones(space.dim)
        self._cap_envelope()
        self.freq_idx = space.names.index("frequency_start")
        self.slide_idx = space.names.index("frequency_slide")
        self.pitch_trend = 0
        self.freq_seeds = self._estimate_freq_seeds(target) if target is not None else []

    @staticmethod
    def _dominant_hz(segment: np.ndarray) -> float | None:
        if len(segment) < 256:
            return None
        spec = np.abs(np.fft.rfft(segment * np.hanning(len(segment)))) ** 2
        freqs = np.fft.rfftfreq(len(segment), 1.0 / SAMPLE_RATE)
        band = (freqs >= 60) & (freqs <= 6000)
        if not band.any() or spec[band].max() <= 0:
            return None
        return float(freqs[band][np.argmax(spec[band])])

    def _estimate_freq_seeds(self, wave: np.ndarray) -> list[float]:
        """frequency_start values matching the target's early dominant pitch
        (and octave neighbors) — random screening almost never lands on the
        right pitch by itself in 30 dimensions. Also records the pitch trend
        (rising/falling between the first and last third) so screening can
        seed frequency_slide's sign."""
        third = max(len(wave) // 3, 256)
        f_start = self._dominant_hz(wave[:third])
        f_end = self._dominant_hz(wave[-third:])
        f_whole = self._dominant_hz(wave)

        self.pitch_trend = 0
        if f_start and f_end:
            ratio = f_end / f_start
            if ratio > 1.15:
                self.pitch_trend = 1
            elif ratio < 0.87:
                self.pitch_trend = -1

        seeds = []
        for hz in (f_start, f_whole):
            if hz is None:
                continue
            for mult in (1.0, 0.5, 2.0):
                fs = freq_param_from_hz(hz * mult)
                if fs is not None and 0.02 <= fs <= 1.0:
                    seeds.append(fs)
        return sorted(set(round(s, 4) for s in seeds))

    def _cap_envelope(self) -> None:
        """Cap envelope params so candidates can't be much longer than the
        target — long renders are pure wasted CPU."""
        target_samples = self.objective.target_len
        self.cap_samples = max(1.6 * target_samples, 0.3 * SAMPLE_RATE)
        cap_value = np.sqrt(self.cap_samples / ENVELOPE_SAMPLES_PER_UNIT)
        self.envelope_idx = [self.space.names.index(n) for n in ENVELOPE_PARAMS]
        for i in self.envelope_idx:
            span = self.space.maxs[i] - self.space.mins[i]
            self.upper[i] = np.clip((cap_value - self.space.mins[i]) / span, 0.05, 1.0)

    def _project_envelope(self, params: dict) -> None:
        """Scale attack/sustain/decay down so the summed envelope length
        stays under the cap (the box bound alone still allows 3x)."""
        total = sum(
            params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS
        )
        if total > self.cap_samples:
            scale = float(np.sqrt(self.cap_samples / total))
            for n in ENVELOPE_PARAMS:
                params[n] *= scale

    # ---------- evaluation ----------

    def params_for(self, unit: np.ndarray, wave_type: int) -> dict:
        params = self.space.params_dict(unit, wave_type)
        if wave_type != 0:
            for name in SQUARE_ONLY_PARAMS:  # DSP ignores these off-square
                i = self.space.names.index(name)
                params[name] = float(self.space.defaults[i])
        self._project_envelope(params)
        return params

    def _evaluate(self, units: list[np.ndarray], wave_types: list[int]) -> np.ndarray:
        params = [self.params_for(u, wt) for u, wt in zip(units, wave_types)]
        seeds = range(RENDER_SEED, RENDER_SEED + self.s.avg_seeds)
        all_scores = []
        for seed in seeds:
            waves = self.renderer.render_batch(params, seeds=int(seed))
            all_scores.append(self.objective.score_batch(waves))
        scores = np.mean(all_scores, axis=0)
        self.evals += len(units)
        for u, wt, sc in zip(units, wave_types, scores):
            self.archive.append(Candidate(float(sc), wt, u.copy()))
        best = min(self.archive).score
        self.trace.append((self.evals, best))
        return scores

    def _log(self, msg: str) -> None:
        if self.s.verbose:
            elapsed = time.perf_counter() - self.t0
            print(f"[{elapsed:6.1f}s evals={self.evals:5d}] {msg}", file=sys.stderr)

    def _out_of_budget(self) -> bool:
        if self.evals >= self.s.budget:
            return True
        if self.s.time_budget is not None:
            return time.perf_counter() - self.t0 > self.s.time_budget
        return False

    # ---------- stages ----------

    def _screen_sample(self) -> np.ndarray:
        """Default with p=0.5 per param, else uniform — pure uniform over 30
        dims is mostly mush."""
        unit = self.space.defaults_unit().copy()
        mask = self.rng.random(self.space.dim) > 0.5
        unit[mask] = self.rng.random(int(mask.sum()))
        if self.freq_seeds and self.rng.random() < 0.5:
            seed = self.freq_seeds[self.rng.integers(len(self.freq_seeds))]
            unit[self.freq_idx] = seed + self.rng.normal(0.0, 0.02)
        if self.pitch_trend != 0 and self.rng.random() < 0.5:
            # frequency_slide spans [-0.5, 0.5], so unit 0.5 = no slide
            unit[self.slide_idx] = 0.5 + self.pitch_trend * self.rng.uniform(0.03, 0.4)
        return np.clip(unit, 0.0, self.upper)

    def _stage0(self, wave_types: list[int]) -> dict[int, Candidate]:
        if self.s.seed_units is not None:
            return self._stage0_seeded()
        best: dict[int, Candidate] = {}
        defaults = np.clip(self.space.defaults_unit(), 0.0, self.upper)
        # spend at most half the eval budget screening
        n_screen = min(self.s.screen_size,
                       max(2, self.s.budget // (2 * len(wave_types))))
        for wt in wave_types:
            if best and self._out_of_budget():  # always screen at least one
                break
            units = [defaults] + [self._screen_sample()
                                  for _ in range(n_screen - 1)]
            scores = self._evaluate(units, [wt] * len(units))
            i = int(np.argmin(scores))
            best[wt] = Candidate(float(scores[i]), wt, units[i])
            self._log(f"stage0 waveType={wt} ({self.space.wave_type_names[wt]}): "
                      f"best {scores[i]:.4f}")
        return best

    def _stage0_seeded(self) -> dict[int, Candidate]:
        """Evaluate model seeds (+ Gaussian jitter) instead of f0 screening."""
        best: dict[int, Candidate] = {}
        assert self.s.seed_units is not None
        for wt, unit in self.s.seed_units:
            if best and self._out_of_budget():
                break
            base = np.clip(np.asarray(unit, dtype=np.float64), 0.0, self.upper)
            units = [base]
            for _ in range(self.s.seed_jitter_copies):
                noise = self.rng.normal(0.0, self.s.seed_jitter, size=base.shape)
                units.append(np.clip(base + noise, 0.0, self.upper))
            scores = self._evaluate(units, [wt] * len(units))
            i = int(np.argmin(scores))
            cand = Candidate(float(scores[i]), wt, units[i])
            if wt not in best or cand.score < best[wt].score:
                best[wt] = cand
            self._log(f"stage0 seed waveType={wt} "
                      f"({self.space.wave_type_names[wt]}): best {scores[i]:.4f}")
        return best

    def _run_cma(self, start: Candidate, max_iters: int | None) -> None:
        opts = {
            "bounds": [np.zeros(self.space.dim).tolist(), self.upper.tolist()],
            "popsize": self.s.popsize,
            "seed": self.s.rng_seed + 1,
            "verbose": -9,
            "tolfun": 1e-4,
        }
        x0 = np.clip(start.unit, 1e-6, self.upper - 1e-6)
        es = cma.CMAEvolutionStrategy(x0.tolist(), 0.25, opts)
        iters = 0
        while not es.stop() and not self._out_of_budget():
            if max_iters is not None and iters >= max_iters:
                break
            xs = es.ask()
            units = [np.asarray(x) for x in xs]
            scores = self._evaluate(units, [start.wave_type] * len(units))
            es.tell(xs, scores.tolist())
            iters += 1

    def run(self) -> list[Candidate]:
        wave_types = self.s.wave_types or self.space.wave_types
        best_by_wt = self._stage0(wave_types)

        survivors = sorted(best_by_wt.values())[: self.s.stage1_keep]
        if len(survivors) > 1:
            for cand in survivors:
                if self._out_of_budget():
                    break
                self._run_cma(cand, max_iters=self.s.stage1_iters)
                self._log(f"stage1 waveType={cand.wave_type}: "
                          f"best {min(self.archive).score:.4f}")

        by_wt: dict[int, Candidate] = {}
        for c in self.archive:
            if c.wave_type not in by_wt or c.score < by_wt[c.wave_type].score:
                by_wt[c.wave_type] = c
        winner = min(by_wt.values())
        if not self._out_of_budget():
            self._log(f"stage2 waveType={winner.wave_type} "
                      f"({self.space.wave_type_names[winner.wave_type]})")
            self._run_cma(winner, max_iters=None)

        by_wt = {}
        for c in self.archive:
            if c.wave_type not in by_wt or c.score < by_wt[c.wave_type].score:
                by_wt[c.wave_type] = c
        results = sorted(by_wt.values())[: self.s.top_k]
        if self.s.refine_steps > 0:
            from .refine import RefineSettings, free_mask, make_evaluate, steepest_descent

            polished: list[Candidate] = []
            for cand in results:
                self._log(f"stage3 refine waveType={cand.wave_type} "
                          f"steps={self.s.refine_steps}")
                mask = free_mask(self.space, cand.wave_type)
                u0 = cand.unit.copy()
                if cand.wave_type != 0:
                    for name in SQUARE_ONLY_PARAMS:
                        i = self.space.names.index(name)
                        u0[i] = float(self.space.defaults_unit()[i])
                evaluate = make_evaluate(self, cand.wave_type)
                u1, sc, _ = steepest_descent(
                    u0, cand.wave_type, evaluate, self.upper, mask=mask,
                    settings=RefineSettings(
                        max_steps=self.s.refine_steps,
                        eps=self.s.refine_eps,
                        step0=self.s.refine_step0,
                        verbose=self.s.verbose,
                    ),
                )
                polished.append(Candidate(sc, cand.wave_type, u1))
            results = sorted(polished)[: self.s.top_k]
        self._log(f"done: best {results[0].score:.4f} "
                  f"(waveType={results[0].wave_type}), {self.evals} evals")
        return results
