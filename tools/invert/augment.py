from __future__ import annotations

import numpy as np

from .constants import ACCEPT_PEAK


def _retro_degrade(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Console-sample degradation: sample-rate crush (with aliasing), bit-depth
    crush, mu-law companding, occasional hard clip."""
    y = np.asarray(x, dtype=np.float32).copy()
    n = len(y)
    if n == 0:
        return y

    if rng.random() < 0.8:
        factor = int(rng.integers(3, 8))
        ds = y[::factor]
        y = np.repeat(ds, factor)[:n].astype(np.float32)
        if len(y) < n:
            pad = np.full(n - len(y), y[-1] if len(y) else 0.0, dtype=np.float32)
            y = np.concatenate([y, pad])

    if rng.random() < 0.7:
        bits = int(rng.integers(4, 9))
        step = 2.0 / (2 ** bits)
        y = (np.round(y / step) * step).astype(np.float32)

    if rng.random() < 0.5:
        mu = float(rng.choice([15.0, 31.0, 63.0, 255.0]))
        comp = np.sign(y) * np.log1p(mu * np.abs(y)) / np.log1p(mu)
        comp = np.round(comp * 32) / 32
        y = (np.sign(comp) * (1.0 / mu) * ((1.0 + mu) ** np.abs(comp) - 1.0)).astype(np.float32)

    if rng.random() < 0.3:
        t = float(rng.uniform(0.3, 0.8))
        y = np.clip(y, -t, t).astype(np.float32)

    return y


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

    # console-sample degradation (retro chain)
    pre_peak = float(np.max(np.abs(x))) if len(x) else 0.0
    before_retro = x
    if rng.random() < 0.6:
        x = _retro_degrade(x, rng)

    # bound: never silence an audible input
    post_peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if pre_peak >= ACCEPT_PEAK and post_peak < ACCEPT_PEAK:
        x = before_retro

    peak = float(np.max(np.abs(x))) + 1e-12
    if peak > 0.98:
        x *= 0.98 / peak
    return x.astype(np.float32)
