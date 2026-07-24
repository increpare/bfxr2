import numpy as np

from invert.augment import maybe_augment, _retro_degrade
from invert.constants import ACCEPT_PEAK


def _tone(n=8000, hz=440, sr=44100):
    t = np.arange(n) / sr
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_augment_can_noop():
    rng = np.random.default_rng(0)
    x = np.random.default_rng(1).standard_normal(8000).astype(np.float32) * 0.2
    y = maybe_augment(x, rng=rng, p=0.0)
    assert np.allclose(x, y)


def test_augment_finite_and_same_length():
    rng = np.random.default_rng(2)
    x = np.random.default_rng(3).standard_normal(12000).astype(np.float32) * 0.3
    y = maybe_augment(x, rng=rng, p=1.0)
    assert y.shape == x.shape
    assert np.isfinite(y).all()


def test_augment_does_not_mutate_input():
    rng = np.random.default_rng(4)
    x = np.ones(4000, dtype=np.float32) * 0.1
    x_copy = x.copy()
    _ = maybe_augment(x, rng=rng, p=1.0)
    assert np.allclose(x, x_copy)


def test_retro_degrade_stays_finite_and_same_length():
    x = _tone()
    y = _retro_degrade(x, np.random.default_rng(0))
    assert y.shape == x.shape and y.dtype == np.float32
    assert np.isfinite(y).all()


def test_retro_degrade_is_seed_deterministic():
    x = _tone()
    a = _retro_degrade(x, np.random.default_rng(3))
    b = _retro_degrade(x, np.random.default_rng(3))
    assert np.array_equal(a, b)


def test_augment_never_silences_an_audible_input():
    x = _tone()
    for s in range(30):
        y = maybe_augment(x, rng=np.random.default_rng(s), p=1.0)
        assert float(np.max(np.abs(y))) >= ACCEPT_PEAK
