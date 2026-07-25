# Structure-Aware Match Objective Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `MatchObjective` rank pitch *structure* (note count, interval
direction, discrete-vs-glissando) correctly, so search and future fine-tuning
can no longer win by smearing a multi-note target into a glissando.

**Architecture:** Add a *sound-level* structure summary computed once per
waveform (`match/structure.py`) and a bounded additive penalty term wired into
`MatchObjective`. Existing per-frame contour terms stay untouched. A 14-case
synthetic probe suite (`match/structure_probes.py`) is the daily automatic
gate; real-target eval and a human listen pass are the claim gates.

**Tech Stack:** Python 3.12, numpy, torch/torchaudio, pytest, `uv`. Headless
bfxr renderer via `match.renderer.BfxrRenderer`.

## Why a sound-level term (measured, not assumed)

Scoring the probe suite against the **current** objective and dumping
`score_components` gives the diagnosis:

```
notes_2_up_gliss  (target = two flat notes rising; bad = glissando)
    pitch_movement   good=  0.000 bad=  0.000   delta= +0.000   <-- the term meant to catch this
    timbre           good=  0.634 bad=  0.098   delta= +0.535
    mel              good=  1.121 bad=  0.177   delta= +0.944
```

`pitch_movement` is a per-frame histogram, so a single discrete jump is one
frame out of ~70 and dilutes to nothing. `timbre` + `mel` then decide the
ranking and the glissando wins. Summarizing structure once per sound makes a
jump count as a whole structural fact instead of 1/70th of a contour.

## Baselines measured before writing this plan

Run from `tools/`, probe renders seeded 1234.

| Suite | Current objective | Target after this plan |
| --- | --- | --- |
| Probes, **no handicap** (spec's literal wording) | **14/14** | 14/14 |
| Probes, **mild handicap** (the gate) | **8/14** | **14/14** |
| Probes, **severe handicap** (report-only) | **6/14** | 10/14 |
| `tests/` (notes, rankings, objective, duration_floor) | 30 passed in 1.73s | 30 passed |
| `tests/` full suite (`uv run pytest -q`) | 130 passed, 6 deselected | 148 passed (130 + 2 Task 1 + 8 Task 2 + 8 Task 3) |

The six mild-tier failures and their score deficits — these are what the new
term must overcome, and they are small, so a modest weight suffices:

```
notes_2_up_gliss   -0.197     notes_3_arp_count  -0.557
notes_2_down_gliss -0.315     gliss_up_steps     -0.256
notes_3_arp_gliss  -0.605     gliss_down_steps   -0.086
```

## Global Constraints

- All commands run from `tools/`. Tests: `uv run pytest` (pytest config sets
  `testpaths=tests`, `pythonpath=["."]`, `addopts="-m 'not slow'"`).
- Ad-hoc scripts need `PYTHONPATH=. uv run python ...` — `pythonpath` is a
  pytest-only setting.
- **Never edit `js/`.** Never commit `tools/invert/data/` or `tools/invert/runs/`.
- **No retraining in this plan.** Baseline checkpoint is frozen at
  `/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt`
  (lives only in that worktree; `runs/` is gitignored).
- Probe render seed is `1234` everywhere.
- Structure-family probes use `sustainTime=0.6` (≈0.87 s, ~71 frames).
  At `sustainTime=0.3` (22 frames) the note detector misses the middle note of
  a 3-note arpeggio — measured. Do not shorten them.
- Probe gate tier = **mild** (correct structure, same waveType, ~2 semitones
  off). Severe tier (wrong waveType) is **reported, never gated** — forcing
  structure to beat a whole-waveType error would swamp timbre matching.
- Work on a new branch off `master`: `git switch -c feature/inverse-model-structure-metric`.
  (`feature/inverse-model-next-steps` is already merged into `master`.)

## File Structure

| File | Responsibility |
| --- | --- |
| `tools/match/notes.py` | *(modify)* discrete-note detection — fix boundary-frame fragility |
| `tools/match/structure.py` | *(new)* `StructureSummary`, `summarize`, `pitch_structure_penalty` |
| `tools/match/structure_probes.py` | *(new)* 14 probe definitions + suite runner CLI |
| `tools/match/features.py` | *(modify)* `FeatureWeights` gains `structure_pitch` |
| `tools/match/objective.py` | *(modify)* precompute target structure; add term to both scoring paths |
| `tools/match/match.py` | *(modify)* `--legacy-objective` A/B flag |
| `tools/invert/eval_targets.py` | *(modify)* `--legacy-objective` passthrough |
| `tools/match/length_report.py` | *(new)* length/energy ratio histogram over an eval run |
| `tools/match/listen_compare.py` | *(new)* two-way listen comparison page for Gate B |
| `tools/tests/test_notes.py` | *(modify)* boundary-frame regression test |
| `tools/tests/test_structure.py` | *(new)* unit tests for summary + penalty |
| `tools/tests/test_structure_probes.py` | *(new)* the automatic gate |

---

### Task 1: Make `detect_note_sequence` robust to note-boundary frames

A real bug found while calibrating the probes, and **not in the original
spec**. The pitch tracker emits one transitional frame between notes. When that
frame's step lands just under `JUMP_ST` (1.5 st) it is absorbed into the
preceding segment; flatness is then judged on the raw segment, blows past
`FLAT_ST` (1.2 st), and the whole note is discarded. Measured on a real render:

```
[  0, 26) len=26 spread=1.49st med=360.9Hz DROP   <-- 25 flat frames thrown away
[ 26, 50) len=24 spread=0.00st med=441.0Hz KEEP
[ 50, 71) len=21 spread=0.84st med=538.6Hz KEEP
```

`notes.py` also drives the **existing pitch-jump arp seeding** in
`optimizer.py`, so note counts may be wrong on real targets today. This is a
plausible cause of the `leeneBell` listen note ("two of three notes, wrong
slope") — unverified, but Task 5 will show it.

**Files:**
- Modify: `tools/match/notes.py:82-97`
- Test: `tools/tests/test_notes.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `detect_note_sequence(f0_log2, voiced, *, jump_st=JUMP_ST,
  flat_st=FLAT_ST, min_frames=MIN_NOTE_FRAMES, max_notes=MAX_NOTES) ->
  list[tuple[float, float]]` — signature unchanged, detection more robust.
  Return stays `[(f0_hz, start_frac), ...]` with `start_frac` relative to the
  **full** segment start (unchanged, so arp-seed onsets keep their meaning).

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_notes.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_notes.py::test_boundary_frame_does_not_discard_a_flat_note -v`
Expected: FAIL with `assert 0 == 2` (`detect_note_sequence` returns `[]`).

- [ ] **Step 3: Write minimal implementation**

In `tools/match/notes.py`, inside `detect_note_sequence`, replace:

```python
        chunk = f0[start:end]
        if (chunk.max() - chunk.min()) * 12.0 > flat_st:
            continue  # not flat -> part of a glide, not a note
        hz = float(2.0 ** float(np.median(chunk)))
        notes.append((hz, start / n))
```

with:

```python
        # The tracker emits a transitional frame at each note boundary. When
        # its step lands just under jump_st it is absorbed into this segment,
        # and judging flatness on the raw segment then discards an otherwise
        # flat note (measured: a 25-frame note lost to one 1.47-semitone
        # frame). Judge flatness and pitch on the interior, where the segment
        # is long enough to have one. start_frac stays segment-relative so
        # arp-seed onsets are unchanged.
        lo, hi = (start + 1, end - 1) if end - start >= 4 else (start, end)
        chunk = f0[lo:hi]
        if (chunk.max() - chunk.min()) * 12.0 > flat_st:
            continue  # not flat -> part of a glide, not a note
        hz = float(2.0 ** float(np.median(chunk)))
        notes.append((hz, start / n))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_notes.py -v`
Expected: PASS, including the four pre-existing detector tests
(`test_detects_three_note_rising_arpeggio`, `test_glide_is_not_a_sequence`,
`test_single_flat_note_is_not_a_sequence`, `test_two_note_with_unvoiced_gap`) —
all verified unchanged by this edit.

- [ ] **Step 5: Run the wider suite (this changes arp seeding)**

Run: `uv run pytest -q`
Expected: `130 passed, 6 deselected` — no new failures. (The 30-test figure above
covers only the four files listed there; the whole suite is 130.)

- [ ] **Step 6: Commit**

```bash
git add tools/match/notes.py tools/tests/test_notes.py
git commit -m "fix(notes): don't discard a flat note over one boundary frame"
```

---

### Task 2: Structure probe library + suite runner (expected RED)

Builds the daily gate. The objective is **not** touched in this task, so the
suite must land at the measured baseline of **8/14** on the mild tier and the
gate test must FAIL. That failure is what Task 3 fixes.

**Files:**
- Create: `tools/match/structure_probes.py`
- Create: `tools/tests/test_structure_probes.py`

**Interfaces:**
- Consumes: `match.renderer.BfxrRenderer`, `match.objective.MatchObjective`.
- Produces:
  - `Probe` frozen dataclass with fields `id: str`, `family: str`,
    `target: dict`, `good: dict`, `bad: dict`, `severe: dict`.
  - `PROBES: list[Probe]` — 14 entries.
  - `ProbeResult` frozen dataclass: `id: str`, `family: str`,
    `good: float`, `bad: float`, `severe: float`, `passed: bool`,
    `severe_passed: bool`, `margin: float`.
  - `evaluate(objective_factory=MatchObjective) -> list[ProbeResult]`
  - `STRUCTURE_IDS: tuple[str, ...]` — the six IDs that fail at baseline.
  - `PASS_THRESHOLD: int = 12`

- [ ] **Step 1: Write the probe library**

Create `tools/match/structure_probes.py`:

```python
"""Synthetic ranking probes for pitch-structure failures.

Each probe is a (target, good, bad) triple of bfxr param dicts. The objective
passes a probe when it scores `good` below `bad`. No real product WAVs are
needed, so this is the daily engineering gate.

Handicap tiers. With `good` rendered as a near-copy of `target` the current
objective already scores 14/14 — the probe tests no trade-off and is useless.
The failure that actually happens in search is a *structurally correct but
timbrally imperfect* candidate losing to a *timbrally perfect but structurally
wrong* one. So `good` carries a deliberate handicap:

  gate tier (`good`)     same waveType, ~2 semitones off, envelope wobble
  report tier (`severe`) additionally a different waveType

Only the gate tier is asserted. Requiring structure to beat a whole-waveType
error would need a penalty ~3x larger, which would swamp timbre matching on
real targets.

Structure families use sustainTime=0.6 (~71 frames): at sustainTime=0.3 (22
frames) the note detector misses the middle note of a 3-note arpeggio.

    PYTHONPATH=. uv run python -m match.structure_probes
    PYTHONPATH=. uv run python -m match.structure_probes --describe
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from .objective import MatchObjective
from .renderer import BfxrRenderer

RENDER_SEED = 1234
PASS_THRESHOLD = 12  # of len(PROBES); spec Section 1

_S = dict(sustainTime=0.6, decayTime=0.15)   # target / bad
_G = dict(sustainTime=0.6, decayTime=0.18)   # good: envelope wobble


def _t(**kw) -> dict:
    return {**_S, **kw}


def _g(**kw) -> dict:
    return {**_G, **kw}


@dataclass(frozen=True)
class Probe:
    id: str
    family: str
    target: dict
    good: dict
    bad: dict
    severe: dict


@dataclass(frozen=True)
class ProbeResult:
    id: str
    family: str
    good: float
    bad: float
    severe: float
    passed: bool
    severe_passed: bool
    margin: float


# pitch_jump_amount values, via notes.pitch_jump_param_from_ratio:
#   +0.61  -> ratio 1.50 (+7 st)      -0.2236 -> ratio 0.667 (-7 st)
#   +0.45  -> ratio 1.22 (+3.5 st)    +0.58   -> ratio 1.43 (+6.2 st)
#   -0.21  -> ratio 0.694 (-6.3 st)
# frequency_slide 0.10 sweeps 320->461 Hz (+6.1 st); -0.10 sweeps 884->614 Hz.
PROBES: list[Probe] = [
    Probe("notes_2_up_gliss", "notes_2_up",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_up_flat", "notes_2_up",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.3318),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_down_gliss", "notes_2_down",
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.50, frequency_slide=-0.10),
          _g(waveType=0, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_2_down_flat", "notes_2_down",
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.4519),
          _g(waveType=0, frequency_start=0.53, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("notes_3_arp_gliss", "notes_3_arp",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.33, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.66),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68),
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68)),
    Probe("notes_3_arp_count", "notes_3_arp",
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.33, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.66),
          _g(waveType=2, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68),
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.318, pitch_jump_amount=0.45,
             pitch_jump_onset_percent=0.35, pitch_jump_2_amount=0.45,
             pitch_jump_onset2_percent=0.68)),
    Probe("gliss_up_steps", "gliss_up",
          _t(waveType=2, frequency_start=0.30, frequency_slide=0.10),
          _g(waveType=2, frequency_start=0.318, frequency_slide=0.10),
          _t(waveType=2, frequency_start=0.30, pitch_jump_amount=0.58,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.318, frequency_slide=0.10)),
    Probe("gliss_down_steps", "gliss_up",
          _t(waveType=2, frequency_start=0.50, frequency_slide=-0.10),
          _g(waveType=2, frequency_start=0.53, frequency_slide=-0.10),
          _t(waveType=2, frequency_start=0.50, pitch_jump_amount=-0.21,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.53, frequency_slide=-0.10)),
    Probe("dir_flip_up", "dir_flip",
          _t(waveType=2, frequency_start=0.35, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.368, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.35, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.368, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.55)),
    Probe("dir_flip_down", "dir_flip",
          _t(waveType=2, frequency_start=0.45, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.5),
          _g(waveType=2, frequency_start=0.478, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55),
          _t(waveType=2, frequency_start=0.45, pitch_jump_amount=0.61,
             pitch_jump_onset_percent=0.5),
          _g(waveType=0, frequency_start=0.478, pitch_jump_amount=-0.2236,
             pitch_jump_onset_percent=0.55)),
    Probe("mute_tail_tone", "mute_tail",
          dict(waveType=2, frequency_start=0.35, sustainTime=0.6, decayTime=0.3),
          dict(waveType=2, frequency_start=0.368, sustainTime=0.58, decayTime=0.32),
          dict(waveType=2, frequency_start=0.35, sustainTime=0.08, decayTime=0.05),
          dict(waveType=0, frequency_start=0.368, sustainTime=0.58, decayTime=0.32)),
    Probe("mute_tail_sweep", "mute_tail",
          dict(waveType=2, frequency_start=0.30, frequency_slide=0.06,
               sustainTime=0.6, decayTime=0.3),
          dict(waveType=2, frequency_start=0.318, frequency_slide=0.06,
               sustainTime=0.58, decayTime=0.32),
          dict(waveType=2, frequency_start=0.30, frequency_slide=0.06,
               sustainTime=0.06, decayTime=0.05),
          dict(waveType=0, frequency_start=0.318, frequency_slide=0.06,
               sustainTime=0.58, decayTime=0.32)),
    Probe("noise_onset_mute", "noise_onset",
          dict(waveType=3, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.42, sustainTime=0.32, decayTime=0.28),
          dict(waveType=3, frequency_start=0.45, sustainTime=0.03, decayTime=0.03),
          dict(waveType=3, frequency_start=0.30, sustainTime=0.32, decayTime=0.28)),
    Probe("noise_onset_tone", "noise_onset",
          dict(waveType=3, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.42, sustainTime=0.32, decayTime=0.28),
          dict(waveType=2, frequency_start=0.45, sustainTime=0.3, decayTime=0.3),
          dict(waveType=3, frequency_start=0.30, sustainTime=0.32, decayTime=0.28)),
]

# The six that fail against the pre-structure-term objective. These must pass.
STRUCTURE_IDS = (
    "notes_2_up_gliss",
    "notes_2_down_gliss",
    "notes_3_arp_gliss",
    "notes_3_arp_count",
    "gliss_up_steps",
    "gliss_down_steps",
)


def evaluate(objective_factory=MatchObjective) -> list[ProbeResult]:
    """Render every probe and score good/bad/severe against its target."""
    results: list[ProbeResult] = []
    with BfxrRenderer() as renderer:
        for probe in PROBES:
            waves = []
            for params in (probe.target, probe.good, probe.bad, probe.severe):
                wave = renderer.render(params, seed=RENDER_SEED)
                if wave is None or len(wave) == 0:
                    raise RuntimeError(f"probe {probe.id}: render failed")
                waves.append(wave)
            target, good, bad, severe = waves
            objective = objective_factory(target)
            g = objective.score(good)
            b = objective.score(bad)
            s = objective.score(severe)
            results.append(ProbeResult(
                id=probe.id, family=probe.family,
                good=g, bad=b, severe=s,
                passed=g < b, severe_passed=s < b, margin=b - g,
            ))
    return results


def _describe() -> int:
    """Print the detected structure of each probe wave — use this when
    retuning params, so a probe never silently stops testing what it names."""
    import numpy as np
    import torch

    from .audio import normalize_peak
    from .features import FeatureExtractor, frame_count
    from .notes import detect_note_sequence

    extractor = FeatureExtractor()

    def structure_of(wave) -> str:
        length = max(len(wave), 4096)
        batch = torch.zeros(1, length + 2048)
        batch[0, : len(wave)] = torch.from_numpy(
            normalize_peak(np.asarray(wave, dtype=np.float32)).copy()
        )
        feats = extractor.extract(batch).slice(0, frame_count(length))
        notes = detect_note_sequence(
            feats.f0_log2[0].numpy(), feats.voiced[0].numpy()
        )
        return f"{len(notes)} notes {[round(hz, 1) for hz, _ in notes]}"

    with BfxrRenderer() as renderer:
        for probe in PROBES:
            print(f"{probe.id}:")
            for role in ("target", "good", "bad", "severe"):
                wave = renderer.render(getattr(probe, role), seed=RENDER_SEED)
                print(f"    {role:8s} {structure_of(wave)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="match.structure_probes")
    parser.add_argument("--describe", action="store_true",
                        help="print detected note structure per probe wave")
    args = parser.parse_args(argv)
    if args.describe:
        return _describe()

    results = evaluate()
    print(f"{'id':22s} {'good':>7s} {'bad':>7s} {'margin':>8s} {'severe':>7s}  gate")
    for r in results:
        print(f"{r.id:22s} {r.good:7.3f} {r.bad:7.3f} {r.margin:+8.3f} "
              f"{r.severe:7.3f}  {'PASS' if r.passed else 'FAIL'}"
              f"{'' if r.severe_passed else '  (severe FAIL)'}")
    n_pass = sum(r.passed for r in results)
    n_severe = sum(r.severe_passed for r in results)
    print(f"\ngate (mild): {n_pass}/{len(results)}  "
          f"(threshold {PASS_THRESHOLD})")
    print(f"report (severe): {n_severe}/{len(results)}")
    failed = [r.id for r in results if not r.passed]
    if failed:
        print("failed: " + ", ".join(failed))
    return 0 if n_pass >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write the gate test**

Create `tools/tests/test_structure_probes.py`:

```python
"""The automatic daily gate (spec Section 1 / Gate A step 1).

Failures are reported by probe ID, never averaged into a median distance.
"""
import pytest

from match.structure_probes import PASS_THRESHOLD, PROBES, STRUCTURE_IDS, evaluate


@pytest.fixture(scope="module")
def results():
    return {r.id: r for r in evaluate()}


def test_every_family_has_a_case():
    families = {p.family for p in PROBES}
    assert families == {
        "notes_2_up", "notes_2_down", "notes_3_arp", "gliss_up",
        "dir_flip", "mute_tail", "noise_onset",
    }


def test_suite_pass_rate(results):
    failed = sorted(r.id for r in results.values() if not r.passed)
    n_pass = len(results) - len(failed)
    assert n_pass >= PASS_THRESHOLD, (
        f"{n_pass}/{len(results)} probes pass "
        f"(need {PASS_THRESHOLD}); failed: {failed}"
    )


@pytest.mark.parametrize("probe_id", STRUCTURE_IDS)
def test_structure_probe_passes(results, probe_id):
    """The six cases that fail against the pre-structure-term objective."""
    r = results[probe_id]
    assert r.passed, f"{probe_id}: good={r.good:.3f} not < bad={r.bad:.3f}"
```

- [ ] **Step 3: Run the suite runner and confirm the measured baseline**

Run: `PYTHONPATH=. uv run python -m match.structure_probes`
Expected: exit code 1 in about 2 seconds (measured: 1.7 s wall for all 14
probes including interpreter startup), and exactly this gate line:

```
gate (mild): 8/14  (threshold 12)
report (severe): 6/14
failed: notes_2_up_gliss, notes_2_down_gliss, notes_3_arp_gliss, notes_3_arp_count, gliss_up_steps, gliss_down_steps
```

If the failing set differs, **stop** — the probes are not reproducing the
measured baseline. Run `--describe` and check each target has the structure its
name claims before continuing.

- [ ] **Step 4: Run the gate test to verify it fails**

Run: `uv run pytest tests/test_structure_probes.py -v`
Expected: `test_every_family_has_a_case` PASSES; `test_suite_pass_rate` FAILS
with "8/14 probes pass (need 12)"; the six `test_structure_probe_passes`
params FAIL.

- [ ] **Step 5: Commit**

```bash
git add tools/match/structure_probes.py tools/tests/test_structure_probes.py
git commit -m "test(match): add structure probe suite (8/14 at baseline)"
```

---

### Task 3: Sound-level structure term (RED → GREEN)

**Files:**
- Create: `tools/match/structure.py`
- Create: `tools/tests/test_structure.py`
- Modify: `tools/match/features.py:159-168` (`FeatureWeights`)
- Modify: `tools/match/objective.py` (imports, `__init__`, `score_candidates`, `_score_valid`)

**Interfaces:**
- Consumes: `detect_note_sequence` from Task 1; `Features` from `match/features.py`.
- Produces:
  - `StructureSummary` frozen dataclass: `note_count: int`,
    `first_interval_st: float`, `voiced_frac: float`.
  - `summarize(f: Features) -> StructureSummary` (single-row `Features`, shape `(1, T)`).
  - `pitch_structure_penalty(target: StructureSummary, cand: StructureSummary) -> float`,
    bounded to `[0.0, PENALTY_CAP]`.
  - `FeatureWeights.structure_pitch: float = 1.0`.
  - New `score_components` key: `"structure_pitch"`.

- [ ] **Step 1: Write the failing unit tests**

Create `tools/tests/test_structure.py`:

```python
import math

import torch

from match.features import Features
from match.structure import (
    COUNT_W,
    DIR_W,
    PENALTY_CAP,
    StructureSummary,
    pitch_structure_penalty,
    summarize,
)


def _features(hzs, per=10, voiced=True):
    """Single-row Features with a piecewise-flat pitch track."""
    values = [math.log2(hz) for hz in hzs for _ in range(per)]
    f0 = torch.tensor([values], dtype=torch.float32)
    n = f0.shape[1]
    on = torch.ones(1, n, dtype=torch.bool)
    return Features(
        env_db=torch.zeros(1, n),
        f0_log2=f0,
        voiced=on if voiced else torch.zeros(1, n, dtype=torch.bool),
        active=on,
        centroid_log2=torch.zeros(1, n),
        noisiness=torch.zeros(1, n),
    )


def test_summarize_counts_notes_and_first_interval():
    s = summarize(_features([400, 600, 900]))
    assert s.note_count == 3
    assert s.first_interval_st > 0
    assert abs(s.first_interval_st - 12 * math.log2(600 / 400)) < 0.5


def test_summarize_reports_no_notes_for_a_single_tone():
    assert summarize(_features([440], per=30)).note_count == 0


def test_identical_structure_is_free():
    s = summarize(_features([400, 600]))
    assert pitch_structure_penalty(s, s) == 0.0


def test_two_note_target_penalizes_a_structureless_candidate():
    target = summarize(_features([400, 600]))
    gliss = summarize(_features([440], per=30))
    assert gliss.note_count == 0
    assert pitch_structure_penalty(target, gliss) == PENALTY_CAP


def test_wrong_direction_costs_the_direction_weight():
    target = summarize(_features([400, 600]))
    flipped = summarize(_features([600, 400]))
    assert pitch_structure_penalty(target, flipped) == DIR_W


def test_glide_target_penalizes_invented_jumps():
    glide = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=1.0)
    jumpy = summarize(_features([400, 600]))
    assert pitch_structure_penalty(glide, jumpy) == COUNT_W


def test_unpitched_target_disables_the_term():
    noise = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=0.0)
    jumpy = summarize(_features([400, 600, 900]))
    assert pitch_structure_penalty(noise, jumpy) == 0.0


def test_penalty_is_bounded():
    target = summarize(_features([400, 600, 900]))
    worst = StructureSummary(note_count=0, first_interval_st=0.0, voiced_frac=1.0)
    assert 0.0 <= pitch_structure_penalty(target, worst) <= PENALTY_CAP
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_structure.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'match.structure'`.

- [ ] **Step 3: Write the structure module**

Create `tools/match/structure.py`:

```python
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
```

- [ ] **Step 4: Run unit tests to verify they pass**

Run: `uv run pytest tests/test_structure.py -v`
Expected: 8 passed.

- [ ] **Step 5: Add the weight**

In `tools/match/features.py`, in `FeatureWeights`, add after `mel`:

```python
    mel: float = 0.35
    # sound-level pitch structure (structure.py); 0.0 = pre-2026-07-24 objective
    structure_pitch: float = 1.0
```

- [ ] **Step 6: Wire the term into the objective**

In `tools/match/objective.py`, add after the `.features` import block:

```python
from .structure import pitch_structure_penalty, summarize
```

In `MatchObjective.__init__`, after the `with torch.no_grad():` block ends
(i.e. after `self.target_features = ...`), add at method-body indentation:

```python
        self.target_structure = summarize(self.target_features)
```

In `score_candidates`, after `terms["mel"] = ...`:

```python
            terms["structure_pitch"] = self.weights.structure_pitch * (
                pitch_structure_penalty(
                    self.target_structure, summarize(cache.features[row])
                )
            )
```

In `_score_valid`, after `terms["mel"] = ...`:

```python
            terms["structure_pitch"] = self.weights.structure_pitch * (
                pitch_structure_penalty(
                    self.target_structure, summarize(cand_features)
                )
            )
```

- [ ] **Step 7: Run the gate**

Run: `PYTHONPATH=. uv run python -m match.structure_probes`
Expected: exit code 0, and:

```
gate (mild): 14/14  (threshold 12)
report (severe): 10/14
```

Run: `uv run pytest tests/test_structure_probes.py -v`
Expected: all PASS.

- [ ] **Step 8: Run the full suite for regressions**

Run: `uv run pytest -q`
Expected: no failures. Specifically `tests/test_metric_rankings.py` (12 cases
derived from earlier listening feedback) and `tests/test_objective.py`
must still pass — including `test_identity_is_zero` (a sound has zero structure
penalty against itself) and `test_batch_speed` (measured overhead of the new
term is 1.07 ms on 14 candidates against a 26.7 ms baseline, ~4%, versus a
500 ms assertion).

- [ ] **Step 9: Commit**

```bash
git add tools/match/structure.py tools/match/features.py \
        tools/match/objective.py tools/tests/test_structure.py
git commit -m "feat(match): sound-level pitch-structure term (probes 8/14 -> 14/14)"
```

---

### Task 4: `--legacy-objective` A/B flag

Gate A needs old-vs-new under an identical budget. `structure_pitch=0.0`
reproduces the pre-2026-07-24 objective exactly.

**Files:**
- Modify: `tools/match/match.py:60-63` (parser), `tools/match/match.py:84-88` (construction)
- Modify: `tools/invert/eval_targets.py:60-63` (parser), `:101-126` (`run_mode`), `:135-172` (`eval_one_target`), `:241-265` (`main`)
- Test: `tools/tests/test_structure.py`

**Interfaces:**
- Consumes: `FeatureWeights.structure_pitch` from Task 3.
- Produces: `--legacy-objective` on both `match.match` and `invert.eval_targets`;
  `run_mode(..., legacy_objective: bool = False)` and
  `eval_one_target(..., legacy_objective: bool = False)`.

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_structure.py`:

```python
def test_legacy_weights_disable_the_term():
    """--legacy-objective must reproduce the pre-structure-term objective."""
    import numpy as np

    from match.features import FeatureWeights
    from match.objective import MatchObjective
    from match.renderer import BfxrRenderer

    params_target = dict(waveType=2, frequency_start=0.30,
                         pitch_jump_amount=0.61, pitch_jump_onset_percent=0.5,
                         sustainTime=0.6, decayTime=0.15)
    params_gliss = dict(waveType=2, frequency_start=0.30,
                        frequency_slide=0.10, sustainTime=0.6, decayTime=0.15)
    with BfxrRenderer() as renderer:
        target = renderer.render(params_target, seed=1234)
        gliss = renderer.render(params_gliss, seed=1234)

    new = MatchObjective(target)
    legacy = MatchObjective(target, weights=FeatureWeights(structure_pitch=0.0))
    assert new.score_components(gliss)["structure_pitch"] > 0.0
    assert legacy.score_components(gliss)["structure_pitch"] == 0.0
    assert legacy.score(gliss) < new.score(gliss)
    assert np.isclose(
        legacy.score(gliss),
        new.score(gliss) - new.score_components(gliss)["structure_pitch"],
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_structure.py::test_legacy_weights_disable_the_term -v`
Expected: PASS already (the weight exists from Task 3). If it fails, Task 3's
wiring is wrong — fix before continuing.

- [ ] **Step 3: Add the flag to `match.match`**

In `tools/match/match.py`, change the import on line 18 area to also bring in
the weights:

```python
from .features import FeatureWeights
from .objective import MatchObjective
```

In `build_parser`, after the `--duration-floor` argument:

```python
    p.add_argument("--legacy-objective", action="store_true",
                   help="disable the sound-level pitch-structure term "
                        "(pre-2026-07-24 objective; for A/B comparison)")
```

Replace the `MatchObjective(...)` construction:

```python
    objective = MatchObjective(
        target,
        allow_pitch_shift=args.allow_pitch_shift,
        allow_time_stretch=args.allow_time_stretch,
        weights=(
            FeatureWeights(structure_pitch=0.0) if args.legacy_objective else None
        ),
    )
```

- [ ] **Step 4: Thread it through `invert.eval_targets`**

In `build_parser`, after `--duration-floor`:

```python
    p.add_argument("--legacy-objective", action="store_true",
                   help="run match with the pre-structure-term objective")
```

In `run_mode`, add the keyword parameter after `duration_floor`:

```python
    duration_floor: float = 0.0,
    legacy_objective: bool = False,
```

and after the `--duration-floor` argv block:

```python
    if legacy_objective:
        argv += ["--legacy-objective"]
```

In `eval_one_target`, add the same keyword parameter after `duration_floor`
and pass it in the `run_mode(...)` call:

```python
                    duration_floor=duration_floor,
                    legacy_objective=legacy_objective,
```

In `main`, pass it to `eval_one_target`:

```python
                duration_floor=args.duration_floor,
                legacy_objective=args.legacy_objective,
```

- [ ] **Step 5: Verify the flag reaches the objective**

Run:
```bash
PYTHONPATH=. uv run python -m match.match "targets/chrono_trigger_leeneBell.wav" \
  -o /tmp/ab_new --budget 300 --jobs 4
PYTHONPATH=. uv run python -m match.match "targets/chrono_trigger_leeneBell.wav" \
  -o /tmp/ab_legacy --budget 300 --jobs 4 --legacy-objective
```
Expected: both exit 0 and write `match.wav`; the printed scores differ.

- [ ] **Step 6: Run the suite and commit**

```bash
uv run pytest -q
git add tools/match/match.py tools/invert/eval_targets.py tools/tests/test_structure.py
git commit -m "feat(match): --legacy-objective flag for old-vs-new A/B"
```

---

### Task 5: Gate A — real targets + the length/energy decision

Spec Section 3 Gate A, plus **the measurement that decides whether spec
Section 2a gets built at all**. The mute/energy probes already pass under the
current objective (`mute_tail_tone` +3.71, `noise_onset_mute` +6.73 even at the
severe tier), so 2a has no demonstrated failure yet. This task produces the
evidence.

**Files:**
- Create: `tools/match/length_report.py`
- Create: `docs/superpowers/plans/2026-07-24-gate-a-results.md`

**Interfaces:**
- Consumes: `--legacy-objective` from Task 4; `match.audio.trim_silence`,
  `match.audio.SAMPLE_RATE`.
- Produces: `length_ratios(eval_root: Path, targets_dir: Path, mode: str) ->
  list[tuple[str, float, float]]` returning `(stem, duration_ratio,
  energy_ratio)` per target; a `main(argv)` CLI printing a histogram.

- [ ] **Step 1: Write the length/energy report**

Create `tools/match/length_report.py`:

```python
"""Length / energy ratio histogram over an eval_targets run.

Spec Priority 0 asks whether candidates collapse to a fraction of the target's
duration while still scoring acceptably. This reads each mode's best render
(`<eval_root>/<stem>/<mode>/match.wav`) against its target and reports the
ratio of trimmed durations and of total energy.

    PYTHONPATH=. uv run python -m match.length_report \\
        --eval-root invert/runs/v7_real_ft/eval_new --targets targets/ \\
        --mode one_shot
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE, trim_silence

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}
COLLAPSE_RATIO = 0.5  # spec: flag candidates under 0.5x the target duration


def _safe_stem(stem: str) -> str:
    """Must match invert.eval_targets._safe_stem EXACTLY — that is the function
    that creates the per-target output directory this tool reads back. It only
    strips path separators and KEEPS spaces and parentheses: real dirs are named
    e.g. "Mario 3 - jump (nes)". Mangling every non-alnum character finds zero
    renders and reports an empty table that reads like "no collapses"."""
    return stem.replace("/", "_").replace("\\", "_")


def _read(path: Path) -> np.ndarray:
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(mono) * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono
        ).astype(np.float32)
    return mono


def length_ratios(
    eval_root: Path, targets_dir: Path, mode: str
) -> list[tuple[str, float, float]]:
    rows: list[tuple[str, float, float]] = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        cand_path = eval_root / _safe_stem(target_path.stem) / mode / "match.wav"
        if not cand_path.is_file():
            continue
        target = trim_silence(_read(target_path))
        cand = trim_silence(_read(cand_path))
        if len(target) == 0:
            continue
        dur = len(cand) / len(target)
        t_energy = float(np.sum(target.astype(np.float64) ** 2))
        c_energy = float(np.sum(cand.astype(np.float64) ** 2))
        energy = c_energy / t_energy if t_energy > 0 else 0.0
        rows.append((target_path.stem, dur, energy))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.length_report")
    p.add_argument("--eval-root", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--mode", default="one_shot",
                   choices=("current", "model_seeded", "one_shot"))
    args = p.parse_args(argv)

    rows = length_ratios(args.eval_root, args.targets, args.mode)
    if not rows:
        print("no matched renders found")
        return 1

    print(f"{'target':40s} {'dur x':>8s} {'energy x':>9s}")
    for stem, dur, energy in sorted(rows, key=lambda r: r[1]):
        flag = "  <-- COLLAPSE" if dur < COLLAPSE_RATIO else ""
        print(f"{stem:40s} {dur:8.2f} {energy:9.2f}{flag}")

    durations = np.array([r[1] for r in rows])
    edges = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, np.inf]
    print("\nduration-ratio histogram:")
    for lo, hi in zip(edges[:-1], edges[1:]):
        n = int(((durations >= lo) & (durations < hi)).sum())
        print(f"  [{lo:4.2f}, {hi:4.2f})  {'#' * n} {n}")

    n_collapse = int((durations < COLLAPSE_RATIO).sum())
    print(f"\ncollapsed (<{COLLAPSE_RATIO}x): {n_collapse}/{len(rows)} "
          f"= {n_collapse / len(rows):.0%}   median {np.median(durations):.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run both evals over the 32 product targets**

`tools/invert/runs/` is gitignored and the checkpoint lives only in the
worktree, so point `--ckpt` at it explicitly:

```bash
CKPT=/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt

PYTHONPATH=. uv run python -m invert.eval_targets --targets targets/ \
  --ckpt "$CKPT" --budget 2000 -o invert/runs/gateA_legacy/ --legacy-objective

PYTHONPATH=. uv run python -m invert.eval_targets --targets targets/ \
  --ckpt "$CKPT" --budget 2000 -o invert/runs/gateA_new/
```

Expected: both complete over 32 targets. This is the long step — expect tens of
minutes. Do not commit anything under `invert/runs/`.

- [ ] **Step 3: Produce the histograms**

```bash
for MODE in one_shot model_seeded; do
  for RUN in gateA_legacy gateA_new; do
    echo "=== $RUN / $MODE ==="
    PYTHONPATH=. uv run python -m match.length_report \
      --eval-root invert/runs/$RUN --targets targets/ --mode $MODE
  done
done
```

- [ ] **Step 4: Re-run the probe gate and record Gate A**

Run: `PYTHONPATH=. uv run python -m match.structure_probes`
Expected: `gate (mild): 14/14`.

Create `docs/superpowers/plans/2026-07-24-gate-a-results.md` recording, with
actual numbers pasted in:

1. Probe suite: mild and severe pass counts, plus any failing IDs by name.
2. One-shot and seeded score medians, legacy vs new (**trend only** — the two
   runs use different objectives, so absolute scores are not comparable across
   columns; compare each target's rank-order and listen outcome, not the number).
3. Duration/energy histograms for both runs.
4. Note-detection change from Task 1: does `chrono_trigger_leeneBell` now
   recover three notes? Check with:
   `PYTHONPATH=. uv run python -m match.structure_probes --describe` for the
   probe side, and inspect the leeneBell target's detected sequence directly.

- [ ] **Step 5: Decide on spec Section 2a — energy/duration coverage**

Apply this rule and write the verdict into the Gate A doc:

- **If ≥25% of targets show a duration ratio < 0.5x in either run** → 2a is
  justified. Open it as a separate task before Gate B, implementing the
  time-to-90%-cumulative-energy penalty from spec 2a as a second bounded term
  (`FeatureWeights.structure_energy`), with new probes whose *good* candidate
  carries the mild handicap. Only once that penalty exists may
  `OptimizeSettings.duration_floor` / envelope pinning in `optimizer.py` be
  tightened as a **search prior** (spec 2c) — it is secondary and never a
  substitute for the metric term, so do not tighten it on its own.
- **Otherwise** → record the measurement, mark 2a **not justified by evidence**,
  and proceed to Gate B with the pitch-structure term alone. The existing
  `coverage` term (weight 3.0, already the dominant cost for absence) is
  handling it.

- [ ] **Step 6: Commit**

```bash
git add tools/match/length_report.py docs/superpowers/plans/2026-07-24-gate-a-results.md
git commit -m "feat(match): length/energy report + Gate A results"
```

---

### Task 6: Gate B — human listen comparison page

Spec Section 3 Gate B. **No improvement may be claimed before this passes.**
Metric deltas are footnotes.

**Files:**
- Create: `tools/match/listen_compare.py`

**Interfaces:**
- Consumes: the two eval roots from Task 5; `_wav_data_uri(wave) -> str` and
  `_spectrogram_data_uri(wave) -> str` from `match/report.py` (the same pair
  `metric_bakeoff.py` already uses).
- Produces: `write_compare_page(out: Path, targets_dir: Path, baseline_root: Path,
  candidate_root: Path, modes: tuple[str, ...], only: set[str] | None) -> None`
  and a `main(argv)` CLI.

**Dependency note:** `_spectrogram_data_uri` lazily imports matplotlib, which
comes from the optional `report` extra. It is installed in this environment
(3.11.1) — if it is ever missing, install with `uv sync --extra report`.

- [ ] **Step 1: Write the comparison page generator**

Create `tools/match/listen_compare.py`:

```python
"""Two-way listen comparison page: baseline objective vs candidate objective.

    PYTHONPATH=. uv run python -m match.listen_compare \\
        --targets targets/ \\
        --baseline invert/runs/gateA_legacy \\
        --candidate invert/runs/gateA_new \\
        -o invert/runs/gateB_listen.html --hard-slice

Metric scores are deliberately NOT shown: the point of this page is to decide
with ears, and a visible number anchors the verdict.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE
from .report import _spectrogram_data_uri, _wav_data_uri

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}

# The annotated hard slice from the v7 listen pass.
HARD_SLICE = (
    "Mario 1 - Jump", "Mario 2 - Throw", "Mario 3 - jump (nes)",
    "Mario 3 - jump (snes)", "Mario Break Brick", "mario 2 - jump",
    "mega_man_ii_one-up", "mega_man_iii_cursor", "mega_man_ii_beam-out",
    "chrono_trigger_leeneBell",
)


def _safe_stem(stem: str) -> str:
    """Must match invert.eval_targets._safe_stem EXACTLY (see length_report.py):
    only strip path separators, KEEP spaces and parens. Real eval dirs are named
    e.g. "Mario 3 - jump (nes)"; mangling non-alnum characters silently yields a
    page with every match cell empty."""
    return stem.replace("/", "_").replace("\\", "_")


def _read(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(mono) * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono
        ).astype(np.float32)
    return mono


def _cell(wave: np.ndarray | None) -> str:
    if wave is None or len(wave) == 0:
        return "<td class='miss'>-</td>"
    return (
        "<td>"
        f"<audio controls preload='none' src='{_wav_data_uri(wave)}'></audio>"
        f"<br><img src='{_spectrogram_data_uri(wave)}' alt=''>"
        "</td>"
    )


def write_compare_page(
    out: Path,
    targets_dir: Path,
    baseline_root: Path,
    candidate_root: Path,
    modes: tuple[str, ...] = ("one_shot", "model_seeded"),
    only: set[str] | None = None,
) -> None:
    head = "".join(
        f"<th>baseline {m}</th><th>candidate {m}</th>" for m in modes
    )
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        cells = [f"<td class='name'>{target_path.stem}</td>",
                 _cell(_read(target_path))]
        for mode in modes:
            for root in (baseline_root, candidate_root):
                cells.append(_cell(_read(root / safe / mode / "match.wav")))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Gate B - baseline vs candidate objective</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Gate B - baseline vs candidate objective</h1>"
        "<p>Is the candidate <b>acceptably better on structure failures</b> "
        "(note count, pitch direction, discrete vs glissando) without obvious "
        "new regressions or mutes? Scores are hidden on purpose.</p>"
        f"<table><tr><th>target</th><th>original</th>{head}</tr>"
        + "".join(rows) +
        "</table>"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.listen_compare")
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--hard-slice", action="store_true",
                   help="only the annotated hard targets from the v7 listen pass")
    args = p.parse_args(argv)

    write_compare_page(
        args.out, args.targets, args.baseline, args.candidate,
        only=set(HARD_SLICE) if args.hard_slice else None,
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Build the page**

```bash
PYTHONPATH=. uv run python -m match.listen_compare \
  --targets targets/ \
  --baseline invert/runs/gateA_legacy \
  --candidate invert/runs/gateA_new \
  -o invert/runs/gateB_listen.html --hard-slice
```

Expected: writes the file; every hard-slice row has audio in all four match
columns. If a row shows `-`, the corresponding eval mode failed in Task 5 —
fix that before asking for ears.

- [ ] **Step 3: Hand to the user for the listen verdict**

**Stop here and ask.** Do not claim an improvement from Gate A numbers alone.
Ask specifically: on the hard slice, is the candidate acceptably better on
*structure* (note count, pitch direction, discrete vs glissando), with no
obvious new mutes or regressions?

- [ ] **Step 4: Commit the tool (not the outputs)**

```bash
git add tools/match/listen_compare.py
git commit -m "feat(match): Gate B listen comparison page"
```

- [ ] **Step 5: Record the verdict**

Append the listener's verdict to
`docs/superpowers/plans/2026-07-24-gate-a-results.md` under a "Gate B" heading,
per-target where the listener gave detail.

**If Gate B fails:** adjust `structure.py` weights (`COUNT_W`, `DIR_W`,
`INTERVAL_W`, `PENALTY_CAP`) and re-run Tasks 3 Step 7 → 6 Step 3. **Do not
retrain the inverse model** — that is explicitly out of scope here and belongs
to the follow-up in spec Section 4.

---

## Out of scope (carried from the spec)

- Another 500k–1M synth scale ladder; declaring synth FT a win over v6.
- Product app wiring / shipping checkpoints.
- Synth capability extensions (formants, colored noise).
- Replacing the objective with CLAP/Zimtohrli as the CMA driver.
- Retraining of any kind — including after a Gate B win (spec Section 4 is a
  separate plan).

## Success criteria

| Stage | Success | Verified by |
| --- | --- | --- |
| Engineering | Probe suite mild tier ≥ 12/14, all six `STRUCTURE_IDS` pass, no regression in the 30 existing tests | Task 3 Steps 7–8 |
| Evidence | Duration/energy histograms recorded; 2a decision made on measurement | Task 5 Step 5 |
| Claimed improvement | Gate B listen: clear structure wins on the hard slice, no major new mutes | Task 6 Step 3 |
| Explicit non-goal | Median match distance alone | — |

## Deviations from the spec (approved 2026-07-24)

1. **Probe handicap tiers.** The spec's probes (`good` = "same structure, small
   timbre error") score **14/14 under the current objective** — they test no
   trade-off. Replaced with a mild-handicap gate tier and a severe report tier.
2. **Section 2a is measurement-gated,** not built up front: the mute/energy
   probes already pass, so the term has no demonstrated failure. Task 5 Step 5
   decides on real-target evidence.
3. **Task 1 is new.** A boundary-frame bug in `detect_note_sequence`, found
   while calibrating the probes, discards flat notes and also affects the
   existing arp seeding.
