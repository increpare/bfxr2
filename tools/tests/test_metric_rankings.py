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


def test_pitch_accuracy_outranks_envelope_detail(renderer):
    """'mario 2 - jump': a 1.5-semitone pitch error is glaring to ears and
    must cost more than a mildly different envelope."""
    target = render(renderer, waveType=0, frequency_start=0.4,
                    sustainTime=0.2, decayTime=0.25)
    right_pitch = render(renderer, waveType=0, frequency_start=0.4,
                         sustainTime=0.22, decayTime=0.27)
    off_pitch = render(renderer, waveType=0, frequency_start=0.418,  # ~ +1.5 st
                       sustainTime=0.2, decayTime=0.25)
    obj = MatchObjective(target)
    assert obj.score(right_pitch) < obj.score(off_pitch)


def test_amplitude_modulation_beats_static():
    """'mario 3 - flame': a jumpy-amplitude target must prefer a candidate
    with amplitude motion over a statically decaying one. Synthetic signals:
    bfxr itself has no tremolo parameter (repeatSpeed alone doesn't touch
    the envelope), but the metric must still hear the difference."""
    sr = 44100
    rng = np.random.default_rng(0)
    t = np.arange(int(0.6 * sr)) / sr

    def band_noise(seed):
        return np.convolve(np.random.default_rng(seed).standard_normal(len(t)),
                           np.ones(8) / 8, mode="same").astype(np.float32)

    def tremolo(hz, phase=0.0):
        return (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * hz * t + phase))).astype(np.float32)

    target = band_noise(0) * tremolo(8)
    modulated = band_noise(1) * tremolo(7, phase=1.0)
    static = band_noise(0) * 0.55
    obj = MatchObjective(target)
    assert obj.score(modulated) < obj.score(static)


def test_discrete_steps_beat_glissando(renderer):
    """'mega_man_ii_beam-out': discrete repeated pitch steps are not a
    glissando, even when start/end pitches agree."""
    target = render(renderer, waveType=2, frequency_start=0.3,
                    pitch_jump_amount=0.3, pitch_jump_repeat_speed=0.7,
                    sustainTime=0.35, decayTime=0.2)
    steppy = render(renderer, waveType=2, frequency_start=0.31,
                    pitch_jump_amount=0.28, pitch_jump_repeat_speed=0.65,
                    sustainTime=0.35, decayTime=0.2)
    gliss = render(renderer, waveType=2, frequency_start=0.3,
                   frequency_slide=0.12, sustainTime=0.35, decayTime=0.2)
    obj = MatchObjective(target)
    assert obj.score(steppy) < obj.score(gliss)


def test_silence_is_never_the_cheapest_error(renderer):
    """Batch round 3: several 'best matches' were silent for most of the
    target. A full-length candidate with clearly wrong pitch must still
    beat a perfect-pitch candidate that only covers a quarter of the
    target — absence has to be the most expensive error, because every
    both-active content term silently excuses it."""
    target = render(renderer, waveType=0, frequency_start=0.4,
                    sustainTime=0.4, decayTime=0.3)
    wrong_pitch_full = render(renderer, waveType=0, frequency_start=0.45,
                              sustainTime=0.4, decayTime=0.3)
    right_pitch_short = render(renderer, waveType=0, frequency_start=0.4,
                               sustainTime=0.1, decayTime=0.1)
    obj = MatchObjective(target)
    assert obj.score(wrong_pitch_full) < obj.score(right_pitch_short)


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
