from __future__ import annotations

import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import RENDER_SEED
from match.renderer import BfxrRenderer

from .constants import SILENCE_PEAK, SQUARE_ONLY
from .features_pack import pack_features
from .sampler import sample_unit


def _acceptable(wave) -> bool:
    if wave is None or len(wave) == 0:
        return False
    w = np.asarray(wave)
    if not np.isfinite(w).all():
        return False
    peak = float(np.max(np.abs(w)))
    return np.isfinite(peak) and peak >= SILENCE_PEAK


def param_sensitivity(
    space: ParamSpace,
    renderer: BfxrRenderer,
    *,
    n_probes: int = 200,
    delta: float = 0.05,
    seed: int = 0,
) -> dict[str, float]:
    """Mean ‖Δfeatures‖ / Δunit per parameter, over random operating points.

    A near-zero value means perturbing that knob does not change the rendered
    audio (unidentifiable from sound). Uses the REAL renderer so weights are
    truthful, not surrogate-approximated.
    """
    rng = np.random.default_rng(seed)
    names = list(space.names)
    accum = np.zeros(len(names), dtype=np.float64)
    counts = np.zeros(len(names), dtype=np.int64)
    wave_types = sorted(space.wave_types)

    for _ in range(n_probes):
        wt = int(rng.choice(wave_types))
        base_unit = sample_unit(space, rng, mode="biased")
        base_wave = renderer.render(space.params_dict(base_unit, wt), seed=RENDER_SEED)
        if not _acceptable(base_wave):
            continue
        base_feat, _ = pack_features(base_wave)
        for j, name in enumerate(names):
            if name in SQUARE_ONLY and wt != 0:
                continue  # inaudible off square; measured only on square
            u2 = base_unit.copy()
            step = delta if u2[j] + delta <= 1.0 else -delta
            u2[j] = float(np.clip(u2[j] + step, 0.0, 1.0))
            dstep = abs(u2[j] - base_unit[j])
            if dstep < 1e-9:
                continue
            wave2 = renderer.render(space.params_dict(u2, wt), seed=RENDER_SEED)
            if not _acceptable(wave2):
                continue
            feat2, _ = pack_features(wave2)
            accum[j] += float(np.linalg.norm(base_feat - feat2)) / dstep
            counts[j] += 1

    sens = accum / np.maximum(counts, 1)
    return {name: float(sens[j]) for j, name in enumerate(names)}


def sensitivity_to_weights(
    sens: dict[str, float],
    names: list[str],
    *,
    floor: float = 0.1,
) -> list[float]:
    """Per-param loss weights, mean ~1.0 over active params, clamped [floor, 4.0].

    Uses the median (not the mean) of all raw sensitivities as the scale: the
    mean is dominated by whichever param happens to be most sensitive, which
    would prevent that same param's weight from ever hitting the [floor, 4.0]
    clamp. The median is robust to that outlier and still centers typical
    params near a weight of 1.0.
    """
    vals = np.array([sens[n] for n in names], dtype=np.float64)
    scale = float(np.median(vals))
    if scale <= 0:
        active = vals > 0.0
        scale = float(vals[active].mean()) if active.any() else 1.0
    if scale <= 0:
        scale = 1.0
    w = vals / scale
    w = np.clip(w, floor, 4.0)
    return [float(x) for x in w]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Measure per-param audio sensitivity")
    p.add_argument("--n-probes", type=int, default=200)
    p.add_argument("--delta", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--jobs", type=int, default=None)
    args = p.parse_args(argv)

    space = ParamSpace()
    with BfxrRenderer(jobs=args.jobs) as renderer:
        sens = param_sensitivity(
            space, renderer, n_probes=args.n_probes, delta=args.delta, seed=args.seed
        )
    weights = sensitivity_to_weights(sens, list(space.names))
    out = {
        "sensitivity": sens,
        "weights": {n: weights[i] for i, n in enumerate(space.names)},
        "weights_list": weights,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
