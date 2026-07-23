import numpy as np

from invert.augment import maybe_augment


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
