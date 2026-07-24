import numpy as np

from match.notes import (
    detect_note_sequence,
    pitch_jump_param_from_ratio,
)


def _forward_ratio(p: float) -> float:
    """DSP forward mapping param -> post-jump frequency ratio."""
    internal = 1.0 - 0.9 * p * p if p > 0 else 1.0 + 10.0 * p * p
    return 1.0 / internal


def test_pitch_jump_param_ratio_roundtrip():
    for p in (0.3, 0.45, 0.6, -0.3, -0.45, -0.6):
        r = _forward_ratio(p)
        assert abs(pitch_jump_param_from_ratio(r) - p) < 1e-6


def test_pitch_jump_param_directions():
    assert pitch_jump_param_from_ratio(1.5) > 0    # up
    assert pitch_jump_param_from_ratio(0.5) < 0    # down
    assert pitch_jump_param_from_ratio(1.0) == 0.0


def _track(hzs, per=5):
    f0 = np.concatenate([np.full(per, np.log2(h)) for h in hzs])
    return f0, np.ones(f0.size, dtype=bool)


def test_detects_three_note_rising_arpeggio():
    f0, v = _track([400, 600, 900])
    notes = detect_note_sequence(f0, v)
    assert len(notes) == 3
    hz = [n[0] for n in notes]
    assert abs(hz[0] - 400) < 20 and abs(hz[1] - 600) < 20 and abs(hz[2] - 900) < 30
    # start fractions increase across the sound
    assert notes[0][1] < notes[1][1] < notes[2][1]


def test_glide_is_not_a_sequence():
    f0 = np.linspace(np.log2(400), np.log2(900), 15)
    v = np.ones(f0.size, dtype=bool)
    assert detect_note_sequence(f0, v) == []


def test_single_flat_note_is_not_a_sequence():
    f0, v = _track([440], per=15)
    assert detect_note_sequence(f0, v) == []


def test_unvoiced_track_yields_nothing():
    f0, _ = _track([400, 900])
    assert detect_note_sequence(f0, np.zeros(f0.size, dtype=bool)) == []


def test_two_note_with_unvoiced_gap():
    f0a, va = _track([400], per=5)
    gap_f, gap_v = np.zeros(3), np.zeros(3, dtype=bool)
    f0b, vb = _track([800], per=5)
    f0 = np.concatenate([f0a, gap_f, f0b])
    v = np.concatenate([va, gap_v, vb])
    notes = detect_note_sequence(f0, v)
    assert len(notes) == 2
    assert abs(notes[1][0] / notes[0][0] - 2.0) < 0.1


def test_boundary_frame_does_not_discard_a_flat_note():
    """The pitch tracker emits one transitional frame between notes. When its
    step lands just under JUMP_ST it gets absorbed into the preceding segment,
    and judging flatness on the raw segment then blows past FLAT_ST and
    discards an otherwise-flat note. Measured on a real render: a 25-frame
    flat note lost to a single 1.47-semitone boundary frame."""
    a = np.full(10, np.log2(361.0))
    transitional = np.array([np.log2(361.0 * 2 ** (1.4 / 12))])  # 1.4 st < JUMP_ST
    b = np.full(10, np.log2(441.0))
    f0 = np.concatenate([a, transitional, b])
    v = np.ones(f0.size, dtype=bool)

    notes = detect_note_sequence(f0, v)
    assert len(notes) == 2
    assert abs(notes[0][0] - 361.0) < 5.0
    assert abs(notes[1][0] - 441.0) < 5.0
