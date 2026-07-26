"""Sound-level pitch structure: note count, interval direction, discrete-vs-glide.

The per-frame contour terms in features.py cannot rank a structural error that
lives in a single frame. A two-note jump differs from a glissando by ONE frame
of large delta out of ~70, so `pitch_movement` -- the term meant to separate
discrete from continuous -- measures 0.000 for BOTH a correct two-note
candidate and a glissando against a two-note target (measured on the probe
suite). `timbre` and `mel` then decide the ranking and the smeared glissando
wins. That is the metric half of the "multi-note -> glissando" failure heard
on product targets.

So summarize each sound's pitch structure ONCE, at the sound level: a single
discrete jump then counts as a whole structural fact instead of 1/70th of a
contour. The penalty is bounded by PENALTY_CAP and switches off entirely on
unpitched targets, so it cannot overwhelm timbre matching on noise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .features import Features
from .notes import detect_note_sequence

# Below this voiced fraction of active frames the target is not really pitched
# and note detection is tracker noise -- switch the whole term off.
VOICED_MIN = 0.35

COUNT_W = 0.75          # per missing/extra note, saturating at 2 notes
DIR_W = 1.0             # first interval goes the wrong way, or no sequence at all
INTERVAL_W = 0.5        # right direction, wrong size
INTERVAL_TOL_ST = 6.0   # semitones of first-interval error scoring the full INTERVAL_W
PENALTY_CAP = 2.0       # bounded so structure cannot swamp timbre


@dataclass(frozen=True)
class StructureSummary:
    note_count: int           # 0 for a glide, a single note, or unpitched
    first_interval_st: float  # signed semitones note0 -> note1; 0.0 if note_count < 2
    voiced_frac: float        # voiced fraction of active frames


def summarize(f: Features) -> StructureSummary:
    """Summarize one sound's pitch structure. `f` is a single-row Features."""
    f0 = f.f0_log2[0].numpy()
    voiced = f.voiced[0].numpy().astype(bool)
    active = f.active[0].numpy().astype(bool)

    n_active = int(active.sum())
    voiced_frac = float(voiced.sum()) / n_active if n_active else 0.0

    notes = detect_note_sequence(f0, voiced)
    first = (
        math.log2(notes[1][0] / notes[0][0]) * 12.0 if len(notes) >= 2 else 0.0
    )
    return StructureSummary(
        note_count=len(notes),
        first_interval_st=first,
        voiced_frac=voiced_frac,
    )


def pitch_structure_penalty(
    target: StructureSummary, cand: StructureSummary
) -> float:
    """Bounded [0, PENALTY_CAP] penalty for getting the target's pitch
    structure wrong. Always 0.0 when the target is not clearly pitched."""
    if target.voiced_frac < VOICED_MIN:
        return 0.0

    if target.note_count >= 2:
        penalty = COUNT_W * min(abs(target.note_count - cand.note_count), 2)
        if cand.note_count >= 2:
            # Cross-module invariant (notes.py:detect_note_sequence): it
            # returns [] unless the first interval is at least JUMP_ST
            # (1.5 st), so any summary with note_count >= 2 has
            # |first_interval_st| >= 1.5 here -- never exactly 0.0. An exact
            # 0.0 would read as "descending" below, but that case is
            # unreachable.
            if (target.first_interval_st > 0.0) != (cand.first_interval_st > 0.0):
                penalty += DIR_W       # wrong direction
            else:
                penalty += INTERVAL_W * min(
                    abs(target.first_interval_st - cand.first_interval_st)
                    / INTERVAL_TOL_ST,
                    1.0,
                )
        else:
            penalty += DIR_W           # no discrete sequence at all
    else:
        # Target glides or holds one note: a candidate must not invent jumps.
        penalty = COUNT_W * min(max(cand.note_count - 1, 0), 2)

    return min(penalty, PENALTY_CAP)
