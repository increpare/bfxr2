import numpy as np
import torch

from invert.constants import N_CHANNELS, N_FRAMES
from invert.features_pack import pack_features


def test_pack_features_shape_and_finite():
    # 0.3s of noise
    sr = 44100
    w = (np.random.default_rng(0).standard_normal(int(0.3 * sr)) * 0.2).astype(np.float32)
    feat, log_dur = pack_features(w)
    assert feat.shape == (N_CHANNELS, N_FRAMES)
    assert np.isfinite(feat).all()
    assert np.isfinite(log_dur)


def test_pack_features_determinism():
    w = (np.random.default_rng(1).standard_normal(10000) * 0.15).astype(np.float32)
    a, da = pack_features(w)
    b, db = pack_features(w)
    assert np.allclose(a, b)
    assert da == db
