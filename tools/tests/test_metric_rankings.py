"""Ranking tests derived from listening feedback (2026-07-22): for each
failure mode observed on real targets, assert the metric orders an
obviously-right-genre candidate above an obviously-wrong one. If the metric
can't pass these, no optimizer on top of it can work.
"""
import numpy as np
import pytest

from match.objective import MatchObjective
from match.renderer import BfxrRenderer

SEED = 1234


@pytest.fixture(scope="module")
def renderer():
    with BfxrRenderer() as r:
        yield r


def render(renderer, **params):
    wave = renderer.render(params, seed=SEED)
    assert wave is not None
    return wave


def test_rising_beats_falling_sweep(renderer):
    """'Mario 1 - Jump': rising tonal sweep matched to a falling one."""
    target = render(renderer, waveType=4, frequency_start=0.3,
                    frequency_slide=0.3, sustainTime=0.25, decayTime=0.2)
    rising = render(renderer, waveType=4, frequency_start=0.27,
                    frequency_slide=0.22, sustainTime=0.28, decayTime=0.18)
    falling = render(renderer, waveType=4, frequency_start=0.3,
                     frequency_slide=-0.3, sustainTime=0.25, decayTime=0.2)
    obj = MatchObjective(target)
    assert obj.score(rising) < obj.score(falling)


def test_noise_beats_tone_for_noise_target(renderer):
    """'chrono_trigger_attack/fall': noise targets matched with tonal waves."""
    target = render(renderer, waveType=3, frequency_start=0.3,
                    sustainTime=0.15, decayTime=0.3)
    noise = render(renderer, waveType=3, frequency_start=0.4,
                   sustainTime=0.18, decayTime=0.25)
    tone = render(renderer, waveType=2, frequency_start=0.3,
                  sustainTime=0.15, decayTime=0.3)
    obj = MatchObjective(target)
    assert obj.score(noise) < obj.score(tone)


def test_tone_beats_noise_for_tonal_target(renderer):
    """Converse of the above — voicedness must cut both ways."""
    target = render(renderer, waveType=2, frequency_start=0.35,
                    sustainTime=0.2, decayTime=0.25)
    tone = render(renderer, waveType=4, frequency_start=0.33,
                  sustainTime=0.22, decayTime=0.22)
    noise = render(renderer, waveType=3, frequency_start=0.35,
                   sustainTime=0.2, decayTime=0.25)
    obj = MatchObjective(target)
    assert obj.score(tone) < obj.score(noise)


def test_descending_noise_beats_flat_noise(renderer):
    """'chrono_trigger_fall': noisy descending target — the pitch contour of
    noise (its spectral centroid trajectory) must count."""
    target = render(renderer, waveType=3, frequency_start=0.5,
                    frequency_slide=-0.25, sustainTime=0.3, decayTime=0.3)
    descending = render(renderer, waveType=3, frequency_start=0.45,
                        frequency_slide=-0.2, sustainTime=0.32, decayTime=0.28)
    flat = render(renderer, waveType=3, frequency_start=0.5,
                  sustainTime=0.3, decayTime=0.3)
    obj = MatchObjective(target)
    assert obj.score(descending) < obj.score(flat)


def test_full_length_beats_truncated(renderer):
    """'chrono_trigger_ozzie': matches that die into silence halfway must
    lose to matches that last the target's duration."""
    target = render(renderer, waveType=0, frequency_start=0.4,
                    sustainTime=0.4, decayTime=0.3)
    full = render(renderer, waveType=0, frequency_start=0.45,
                  sustainTime=0.38, decayTime=0.32)
    truncated = render(renderer, waveType=0, frequency_start=0.4,
                       sustainTime=0.15, decayTime=0.1)
    obj = MatchObjective(target)
    assert obj.score(full) < obj.score(truncated)


def test_pitch_jump_beats_flat(renderer):
    """'chrono_trigger_attack': two-pitch (low then high) structure must be
    rewarded over a single flat pitch."""
    target = render(renderer, waveType=0, frequency_start=0.3,
                    pitch_jump_amount=0.5, pitch_jump_onset_percent=0.4,
                    sustainTime=0.25, decayTime=0.2)
    jumpy = render(renderer, waveType=0, frequency_start=0.29,
                   pitch_jump_amount=0.45, pitch_jump_onset_percent=0.45,
                   sustainTime=0.25, decayTime=0.2)
    flat = render(renderer, waveType=0, frequency_start=0.3,
                  sustainTime=0.25, decayTime=0.2)
    obj = MatchObjective(target)
    assert obj.score(jumpy) < obj.score(flat)


def test_matching_pitch_beats_wrong_octave(renderer):
    """'Mario 3 - jump (nes)': right trend but wrong pitch level."""
    target = render(renderer, waveType=2, frequency_start=0.4,
                    sustainTime=0.2, decayTime=0.2)
    close = render(renderer, waveType=2, frequency_start=0.42,
                   sustainTime=0.2, decayTime=0.2)
    octave_off = render(renderer, waveType=2, frequency_start=0.58,
                        sustainTime=0.2, decayTime=0.2)
    obj = MatchObjective(target)
    assert obj.score(close) < obj.score(octave_off)
