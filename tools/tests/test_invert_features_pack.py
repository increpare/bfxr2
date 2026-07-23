import numpy as np

from invert.constants import (
    INVERT_CONTOUR_HOP,
    N_CHANNELS,
    N_FRAMES,
)
from invert.features_pack import pack_features
from match.audio import SAMPLE_RATE
from match.features import ENV_FLOOR_DB


def test_pack_features_shape_and_finite():
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


def test_short_wave_pads_and_has_increasing_t_abs():
    # ~40ms blip — under old pack this was 1 frame stretched to 128.
    sr = SAMPLE_RATE
    n = int(0.04 * sr)
    t = np.arange(n, dtype=np.float32)
    w = (0.3 * np.sin(2 * np.pi * 440 * t / sr)).astype(np.float32)
    feat, _ = pack_features(w)
    t_abs = feat[3]  # channel replaces active
    # Pad region at the end should be ~0 for t_abs
    assert abs(t_abs[-1]) < 1e-6
    # Real region: strictly increasing positive times
    real = t_abs[t_abs > 0]
    assert len(real) >= 4, f"expected multiple native frames, got {len(real)}"
    assert np.all(np.diff(real) > 0)
    # Hop spacing ≈ INVERT_CONTOUR_HOP / SAMPLE_RATE
    dt = float(np.median(np.diff(real)))
    assert abs(dt - INVERT_CONTOUR_HOP / SAMPLE_RATE) < 1e-4
    # Env pad uses floor
    assert feat[0, -1] <= ENV_FLOOR_DB + 1e-3


def test_long_wave_is_cropped_not_stretched():
    # Long enough that native frames > N_FRAMES at hop=128
    sr = SAMPLE_RATE
    n = int(2.0 * sr)
    t = np.arange(n, dtype=np.float32)
    w = (0.2 * np.sin(2 * np.pi * 220 * t / sr)).astype(np.float32)
    feat, _ = pack_features(w)
    t_abs = feat[3]
    # Full buffer should be real time (no trailing zero pad from shortfall)
    assert t_abs[-1] > 0
    # Last frame time ≈ (N_FRAMES-1) * hop / sr  (onset crop)
    expect = (N_FRAMES - 1) * INVERT_CONTOUR_HOP / SAMPLE_RATE
    assert abs(float(t_abs[-1]) - expect) < 1e-3
