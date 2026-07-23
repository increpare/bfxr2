from __future__ import annotations

import numpy as np


def maybe_augment(
    wave: np.ndarray,
    rng: np.random.Generator,
    *,
    p: float = 0.5,
) -> np.ndarray:
    """Rough up audio ~half the time. Labels must stay unchanged at the call site."""
    x = np.asarray(wave, dtype=np.float32).copy()
    if rng.random() >= p:
        return x

    # level jitter
    x *= float(rng.uniform(0.5, 1.4))

    # additive noise floor
    if rng.random() < 0.8:
        noise_db = float(rng.uniform(-45, -25))
        amp = 10 ** (noise_db / 20.0)
        x = x + rng.standard_normal(len(x)).astype(np.float32) * amp

    # cheap one-tap "reverb" (decaying echo)
    if rng.random() < 0.5 and len(x) > 2000:
        delay = int(rng.integers(800, 2400))
        decay = float(rng.uniform(0.15, 0.45))
        y = x.copy()
        y[delay:] += x[:-delay] * decay
        x = y

    # gentle EQ tilt via 1st-order IIR high/low shelf approximation
    if rng.random() < 0.7:
        tilt = float(rng.uniform(-0.35, 0.35))
        # simple first-difference blend
        dx = np.diff(x, prepend=x[:1])
        x = x + tilt * dx

    peak = float(np.max(np.abs(x))) + 1e-12
    if peak > 0.98:
        x *= 0.98 / peak
    return x.astype(np.float32)
