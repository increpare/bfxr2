"""Discrete-note detection + pitch-jump seeding.

Bfxr can render a short arpeggio in a *single* sound via two pitch jumps
(``pitch_jump_amount`` at ``pitch_jump_onset_percent``, then
``pitch_jump_2_amount`` at ``pitch_jump_onset2_percent``). But that region of
the parameter space is a needle: random screening rarely lands a coherent
arpeggio, and CMA can't climb toward discrete jumps from a smooth start (a
small jump amount does nothing until its onset and magnitude align). So a
target that is really "three flat notes" gets matched by a glide or by noise.

This module detects a discrete flat-note sequence in the target's pitch track
and converts it into concrete pitch-jump seed candidates the staged search can
evaluate and then refine — the same idea as the existing frequency seeds, but
for several correlated params that must be set together.

DSP semantics (Bfxr_DSP.js): at a jump, frequency_period *= internal, where
  param p > 0:  internal = 1 - 0.9*p^2   (period shrinks -> pitch UP)
  param p < 0:  internal = 1 + 10*p^2    (period grows   -> pitch DOWN)
so the post-jump frequency ratio is 1/internal. Verified empirically.
"""
from __future__ import annotations

import numpy as np

# Detection thresholds (semitones unless noted).
JUMP_ST = 1.5        # |Δf0| between adjacent frames above this = a note boundary
FLAT_ST = 1.2        # a note segment's f0 spread must stay under this to count
MIN_NOTE_FRAMES = 2  # shorter runs are tracker glitches, not notes
MAX_NOTES = 3        # bfxr does start + 2 jumps


def pitch_jump_param_from_ratio(ratio: float) -> float:
    """Inverse of the DSP mapping: the ``pitch_jump_amount`` param that jumps
    the pitch by ``ratio`` (>1 up, <1 down). Clamped to the param's [-1, 1]."""
    if not np.isfinite(ratio) or ratio <= 0:
        return 0.0
    if ratio > 1.0:
        p = float(np.sqrt(max(1.0 - 1.0 / ratio, 0.0) / 0.9))
    elif ratio < 1.0:
        p = -float(np.sqrt(max(1.0 / ratio - 1.0, 0.0) / 10.0))
    else:
        return 0.0
    return float(np.clip(p, -1.0, 1.0))


def detect_note_sequence(
    f0_log2: np.ndarray,
    voiced: np.ndarray,
    *,
    jump_st: float = JUMP_ST,
    flat_st: float = FLAT_ST,
    min_frames: int = MIN_NOTE_FRAMES,
    max_notes: int = MAX_NOTES,
) -> list[tuple[float, float]]:
    """Find a discrete flat-note sequence in a pitch track.

    Returns ``[(f0_hz, start_frac), ...]`` (up to ``max_notes``) when the track
    is genuinely two-or-more flat notes with real jumps between them; returns
    ``[]`` for a single note, a continuous glide, or an unvoiced/noisy track
    (so seeding is purely additive and never fires on non-arpeggios).
    """
    f0 = np.asarray(f0_log2, dtype=np.float64).reshape(-1)
    v = np.asarray(voiced).reshape(-1).astype(bool)
    n = f0.size
    if n < min_frames * 2 or v.sum() < min_frames * 2:
        return []

    # split into contiguous voiced blocks, then split each block at jumps
    segments: list[tuple[int, int]] = []  # (start, end) exclusive
    i = 0
    while i < n:
        if not v[i]:
            i += 1
            continue
        j = i
        seg_start = i
        while j + 1 < n and v[j + 1] and abs(f0[j + 1] - f0[j]) * 12.0 <= jump_st:
            j += 1
        segments.append((seg_start, j + 1))
        i = j + 1

    notes: list[tuple[float, float]] = []
    for start, end in segments:
        if end - start < min_frames:
            continue
        # The tracker emits a transitional frame at each note boundary. When
        # its step lands just under jump_st it is absorbed into this segment,
        # and judging flatness on the raw segment then discards an otherwise
        # flat note (measured: a 25-frame note lost to one 1.47-semitone
        # frame). Judge flatness and pitch on the interior, where the segment
        # is long enough to have one. start_frac stays segment-relative so
        # arp-seed onsets are unchanged. Only trim when segment >= 4 frames to
        # ensure a 2-frame interior; a 1-frame interior has zero spread and
        # makes flatness vacuous, inventing spurious notes on noisy tracks.
        lo, hi = (start + 1, end - 1) if end - start >= 4 else (start, end)
        chunk = f0[lo:hi]
        if (chunk.max() - chunk.min()) * 12.0 > flat_st:
            continue  # not flat -> part of a glide, not a note
        hz = float(2.0 ** float(np.median(chunk)))
        notes.append((hz, start / n))

    if len(notes) < 2:
        return []
    # require a real jump between the first kept notes (else it's one note)
    if abs(np.log2(notes[1][0] / notes[0][0])) * 12.0 < jump_st:
        return []
    return notes[:max_notes]


def build_arp_seed_units(
    space,
    notes: list[tuple[float, float]],
    upper: np.ndarray,
    target_len: int,
) -> list[np.ndarray]:
    """Turn a detected note sequence into pitch-jump seed unit vectors for the
    staged search (tonal candidates the search can refine). Empty list when
    there is no sequence.

    The envelope is sized to ``target_len`` samples: onset_percent is relative
    to the envelope length, so a mismatched envelope both over-runs the target
    and lands the jumps at the wrong absolute times."""
    from .optimizer import ENVELOPE_SAMPLES_PER_UNIT, freq_param_from_hz

    if len(notes) < 2:
        return []
    fs_param = freq_param_from_hz(notes[0][0])
    if fs_param is None:
        return []

    names = space.names
    mins, maxs = np.asarray(space.mins), np.asarray(space.maxs)

    def to_unit(name: str, value: float) -> float:
        i = names.index(name)
        span = maxs[i] - mins[i]
        return float(np.clip((value - mins[i]) / span, 0.0, 1.0)) if span else 0.0

    base = space.defaults_unit().copy()
    base[names.index("frequency_start")] = to_unit("frequency_start", fs_param)
    base[names.index("frequency_slide")] = to_unit("frequency_slide", 0.0)

    r1 = notes[1][0] / notes[0][0]
    base[names.index("pitch_jump_amount")] = to_unit(
        "pitch_jump_amount", pitch_jump_param_from_ratio(r1))
    base[names.index("pitch_jump_onset_percent")] = to_unit(
        "pitch_jump_onset_percent", notes[1][1])
    if len(notes) >= 3:
        r2 = notes[2][0] / notes[1][0]
        base[names.index("pitch_jump_2_amount")] = to_unit(
            "pitch_jump_2_amount", pitch_jump_param_from_ratio(r2))
        base[names.index("pitch_jump_onset2_percent")] = to_unit(
            "pitch_jump_onset2_percent", notes[2][1])

    # size the envelope to the target: split target_len between sustain and
    # decay so the whole arpeggio is audible and the onset fractions map to the
    # right absolute times. env stage length (samples) = param^2 * PER_UNIT.
    def env_param(frac: float) -> float:
        samples = max(frac * target_len, 1.0)
        return float(np.sqrt(samples / ENVELOPE_SAMPLES_PER_UNIT))

    # two variants: flat/sustained (equal-loudness notes) and a decaying one
    seeds = []
    for sustain_frac, decay_frac in ((0.9, 0.2), (0.4, 0.7)):
        u = base.copy()
        u[names.index("attackTime")] = 0.0
        u[names.index("sustainTime")] = to_unit("sustainTime", env_param(sustain_frac))
        u[names.index("decayTime")] = to_unit("decayTime", env_param(decay_frac))
        seeds.append(np.clip(u, 0.0, upper))
    return seeds
