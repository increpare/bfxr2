# Inverse Model — Structure-Aware Metric & Eval Design

**Date:** 2026-07-24  
**Status:** design approved — awaiting spec review → implementation plan  
**Branch / worktree:** `feature/inverse-model-next-steps` / `.worktrees/inverse-model-next`  
**Baseline checkpoint:** `tools/invert/runs/v7_real_ft/best.pt` (freeze; do not retrain until gates below pass)

## Goal

Stop optimizing against a similarity score that can prefer wrong pitch structure
and mute/crackle misses. Make the **match objective and automatic probes**
fail closed on the failures already heard on product targets, then only claim
an improvement after a **human listen spot-check**.

This is not a product ship. Absolute quality is still far from acceptable
(listen scores ~1–3/5 on a hard slice). Real FT is only the best *relative*
baseline among v6 / synth FT / real FT.

## Why (evidence already collected)

From the v7 listen pass and pairwise table (n=32 product targets):

1. **Metric ≠ ears on synth FT.** Synth FT improved one-shot median (9.56 vs
   v6 10.80) but lost perceptually on one-shots **13–19**. Real FT won one-shots
   vs v6 **20–12** and vs synth **18–14**. Seeded rankings are soft / often tied.
2. **Dominant failure mode is pitch structure**, not “wrong genre”:
   - multi-note / arp → smeared glissando (`mega_man_ii_one-up`, `cursor`,
     `beam-out`)
   - wrong pitch *direction* (Mario jumps going down when the target goes up)
   - wrong *kind* of motion (glissando vs discrete steps; SNES jump)
   - incomplete note sequences (`leeneBell`: two of three notes, wrong slope)
3. **Texture under the radar:** `Mario Break Brick` — crackly/scuttly original,
   recreations near-mute; metric still ranks some FT variants “better.”
4. **Prior diagnosis (next-directions Priority 0):** length/energy collapse can
   still score acceptably because onset matching dominates.

User listen remains **vital** to validate any claimed improvement. It is not
the daily engineering loop.

## Decisions

| Decision | Choice |
| --- | --- |
| Next lever | Harden **judge + probes**, not more synth scale / another real-FT round |
| Baseline | Freeze `v7_real_ft`; compare search/metric changes against it |
| Daily gate | Synthetic structure probes + metric bakeoff (no human required) |
| Claim gate | Human listen spot-check on fixed product slice before calling anything better |
| Scope of metric change | `tools/match/objective.py` (+ small helpers); reuse `match/notes.py` pitch track / note detection where possible |
| Retrain | **Out of first plan** — only after new objective passes auto probes and a listen gate |

---

## Section 1 — Failure taxonomy → probe library

Codify failures as **synthetic ranking cases** (correct candidate must score
better than a crafted distractor). No real product WAVs required for the daily
gate; cases are rendered from known bfxr params.

**Probe families (minimum set):**

| ID | Target structure | Correct candidate | Distractor that must lose |
| --- | --- | --- | --- |
| `notes_2_up` | two flat notes, upward jump | same structure, small timbre error | upward *glissando* (slide, no jumps) matching rough pitch span |
| `notes_2_down` | two flat notes, downward | same | downward glissando |
| `notes_3_arp` | three-note arp (use pitch_jump + pitch_jump_2) | same note count/direction | single glissando or 2-note wrong count |
| `gliss_up` | continuous upward slide | glissando | discrete two-note jump spanning same endpoints |
| `dir_flip` | upward jump | upward | downward jump (same |ratio|) |
| `mute_tail` | tonal + audible sustain | full envelope | onset-matched blip / near-silence after ~50 ms |
| `noise_onset` | noisy/crackly burst (high flatness onset) | noisy onset | near-mute or pure soft tone |

Implementation sketch:

- New module e.g. `tools/match/structure_probes.py` that builds
  `(target_wave, good_wave, bad_wave)` triples via `BfxrRenderer` + fixed seeds.
- Extend or parallel the existing ranking bakeoff pattern in
  `tools/bfxr_native/scripts/metric_bakeoff.py` / `tools/match/metric_bakeoff.py`
  with a **structure suite** that only needs current objective (+ proposed
  penalties), not CLAP/Zimtohrli unless useful as reference.

**Pass criterion (engineering):** every probe family has ≥1 case; suite pass rate
≥ **12/14** (or ≥85% if case count differs) under the candidate objective.
Document failures by ID — do not average them away into a median distance.

## Section 2 — Objective hardening

Edit `MatchObjective` (`tools/match/objective.py`) so search and future FT cannot
“win” by the failure modes above.

**2a. Energy / duration coverage (Priority 0)**

- Compute target and candidate energy envelopes (existing volume contour in
  `match/features.py` is fine).
- Penalize candidates whose **usable energy ends early** relative to the target
  (e.g. time-to-X% cumulative energy, or fraction of target frames with
  candidate energy below a floor while target is still above floor).
- Must make `mute_tail` pass; must not destroy normal short SFX (probe with
  short-but-dense targets).

**2b. Pitch-structure term**

Reuse `match/notes.py` / pitch contour from `match/features.py`:

- Extract discrete-note sequence when voiced; else treat as glissando/unpitched.
- Penalize mismatch on:
  - **note count** (when target has ≥2 discrete notes),
  - **direction of first significant interval** (up vs down),
  - optional: rough **log-pitch span** within a tolerance.
- When target is classified as glissando (no flat notes), penalize candidates
  that introduce strong discrete jumps (`gliss_up` probe).
- Keep this term **bounded** so it cannot overwhelm timbre matching on
  unpitched noise (weight schedule + only apply when target pitch track is
  sufficiently voiced).

**2c. Integration constraints**

- New terms are additive components exposed in `score_components` for debugging.
- Default weights chosen so existing in-domain sanity cases from the prior
  bakeoff do not collapse (re-run structure suite + a small subset of prior
  ranking cases).
- No change to CMA API surface beyond objective scores; `duration_floor` /
  envelope pinning in `optimizer.py` may be tightened as a **search prior**
  once the metric penalty exists (secondary; not a substitute for 2a).

## Section 3 — Eval protocol (two gates)

### Gate A — Automatic (required before asking for ears)

1. Structure probe suite passes threshold (Section 1).
2. Re-eval product targets (`tools/targets/`, n=32) with **search seeded from
   `v7_real_ft`** under old vs new objective (same budget). Report:
   - one-shot + seeded medians (trend only),
   - structure probe scores on *recreated* waves where note detector applies,
   - length/energy ratio histograms (flag <0.5×).
3. Do **not** declare a win from Gate A alone.

### Gate B — Human listen (required to claim improvement)

1. Produce a small comparison page: **baseline real-FT (old objective search)
   vs candidate (new objective search)** — prefer one-shot + seeded columns,
   not six-way model soup unless needed.
2. Fixed listen slice: the hard set already annotated (Mario jumps, Mega Man
   one-up/cursor/beam-out, Break Brick, leeneBell, plus any new mute_tail
   failures). Full n=32 optional if energy allows.
3. Verdict from listener: is the candidate **acceptably better** on structure
   failures without obvious new regressions? Metric deltas are footnotes.

If Gate B fails, fix objective/weights; do not retrain the inverse model yet.

## Section 4 — What happens after a listen win

Only if Gate B says the new objective helps:

1. Optionally light **search-default** switch to the new objective (tools path).
2. Consider a short **real spectral FT** or param FT pass that uses the improved
   spectral/match proxy — separate plan.
3. Still no “ship to product” language until absolute listen quality is in a
   different band than today’s ~1–3/5.

## Out of scope (this design)

- Another 500k–1M synth scale ladder.
- Declaring synth FT a win over v6.
- Product app wiring / shipping checkpoints.
- Synth capability extensions (formants, colored noise, etc.) — real ceiling
  for unreachable timbres; separate track.
- Replacing the objective entirely with CLAP/Zimtohrli as the CMA driver
  (expensive / contour issues); they may remain bakeoff references only.

## Success criteria

| Stage | Success |
| --- | --- |
| Engineering | Structure suite ≥ threshold; `mute_tail` / `dir_flip` / note-vs-gliss cases pass |
| Claimed improvement | Gate B listen: clear structure wins on the hard slice, no major new mutes |
| Explicit non-goal | Median match distance alone |

## References

- Listen pairwise tally: conversation 2026-07-24; canvas `v7-listen-pairwise`
- Qualitative notes: slash/jump/one-up/cursor/beam-out/Break Brick/leeneBell
- `docs/superpowers/plans/2026-07-23-inverse-model-next-directions.md` (Priority 0)
- `docs/superpowers/plans/2026-07-24-inverse-model-data-retrain-results.md`
- Existing: `tools/match/notes.py`, `tools/match/objective.py`, metric bakeoff scripts
