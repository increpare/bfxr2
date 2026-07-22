import time

import numpy as np
import pytest

from match.audio import SAMPLE_RATE, normalize_rms, prepare_target, trim_silence
from match.objective import FAILED_SCORE, MelObjective
from match.renderer import BfxrRenderer


@pytest.fixture(scope="module")
def renderer():
    with BfxrRenderer() as r:
        yield r


def sine(freq: float, seconds: float = 0.5) -> np.ndarray:
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_identity_is_zero():
    x = sine(440)
    obj = MelObjective(x)
    assert obj.score(x) == pytest.approx(0.0, abs=1e-6)


def test_silence_scores_high():
    x = sine(440)
    obj = MelObjective(x)
    silence = np.zeros_like(x)
    assert obj.score(silence) > 1.0
    assert obj.score(None) == FAILED_SCORE


def test_gain_invariance():
    x = sine(440)
    obj = MelObjective(x)
    assert obj.score(0.05 * x) == pytest.approx(0.0, abs=1e-4)


def test_monotone_in_frequency_distance(renderer):
    def render_sin(freq_start):
        return renderer.render(
            {"waveType": 2, "frequency_start": freq_start, "sustainTime": 0.3},
            seed=1,
        )

    target = render_sin(0.3)
    obj = MelObjective(target)
    d = [obj.score(render_sin(f)) for f in (0.3, 0.35, 0.42, 0.55)]
    assert d[0] == pytest.approx(0.0, abs=1e-6)
    assert d[0] < d[1] < d[2] < d[3]


def test_pitch_shift_relaxation():
    target = sine(440)
    shifted = sine(440 * 2 ** (3 / 12))  # +3 semitones
    strict = MelObjective(target).score(shifted)
    relaxed = MelObjective(target, allow_pitch_shift=True).score(shifted)
    assert relaxed < strict * 0.7


def test_time_stretch_relaxation():
    target = sine(440, seconds=0.5)
    longer = sine(440, seconds=0.62)
    strict = MelObjective(target).score(longer)
    relaxed = MelObjective(target, allow_time_stretch=True).score(longer)
    assert relaxed < strict * 0.7


def test_trim_and_prepare(tmp_path):
    import soundfile as sf

    x = sine(440, seconds=0.3)
    padded = np.concatenate([np.zeros(SAMPLE_RATE // 2, dtype=np.float32), x,
                             np.zeros(SAMPLE_RATE // 2, dtype=np.float32)])
    trimmed = trim_silence(padded)
    assert len(x) <= len(trimmed) < len(x) + SAMPLE_RATE // 10

    path = tmp_path / "t.wav"
    sf.write(path, padded, SAMPLE_RATE)
    prepared = prepare_target(path)
    assert abs(np.sqrt(np.mean(prepared**2)) - 0.1) < 1e-3


def test_batch_speed(renderer):
    target = renderer.render({"waveType": 0, "frequency_start": 0.4}, seed=1)
    obj = MelObjective(target)
    waves = [renderer.render({"frequency_start": 0.2 + 0.02 * i}, seed=1)
             for i in range(14)]
    obj.score_batch(waves)  # warmup
    t0 = time.perf_counter()
    scores = obj.score_batch(waves)
    dt = time.perf_counter() - t0
    assert len(scores) == 14
    assert dt < 0.5, f"objective too slow: {dt:.3f}s for 14 candidates"
