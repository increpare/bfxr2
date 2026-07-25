# Gate A Results — Structure-Aware Match Objective

**Date:** 2026-07-25
**Branch:** `feature/inverse-model-structure-metric`
**Plan:** `2026-07-24-inverse-model-structure-metric.md`
**Checkpoint:** `v7_real_ft/best.pt` (frozen — no retraining in this plan)
**Runs:** `invert/runs/gateA_legacy` (old objective) vs `invert/runs/gateA_new`, budget 2000, 32 targets, rng-seed 0

> Gate A cannot declare an improvement. Its job is to clear the bar for asking
> for ears, and to produce the evidence for the Section-2a decision. The verdict
> lives in Gate B.

## 1. Probe suite

| Tier | Before | After |
| --- | --- | --- |
| Mild (the gate, threshold 12/14) | 8/14 | **14/14** |
| Severe (report-only) | 6/14 | 10/14 |

All six originally-failing IDs now pass: `notes_2_up_gliss`, `notes_2_down_gliss`,
`notes_3_arp_gliss`, `notes_3_arp_count`, `gliss_up_steps`, `gliss_down_steps`.
No probe regressed. Full suite: 161 passed, 6 deselected.

## 2. Does the term fire on real audio, or only on synthetic probes?

The probes are synthetic, so the load-bearing question is whether the term is
relevant to the actual corpus. It is: **20 of 32 targets have ≥2 detected notes**,
so a majority of the product slice has discrete pitch structure to get wrong.

Measured `structure_pitch` component on the recreated waves:

| Mode | Term fired | Median penalty | Mean | Max |
| --- | --- | --- | --- | --- |
| `one_shot` (raw model, no search) | 18/32 | 0.732 | 0.925 | 2.000 (cap) |
| `current` (search under new objective) | 17/32 | **0.005** | 0.567 | 2.000 (cap) |

**This contrast is the most important number in Gate A.** The raw model's
recreations sit near the penalty cap on many targets — it is not reproducing note
structure at all. When the search optimizes *against* the new term, the penalty
collapses toward zero on the targets the search can reach:

| Target | one-shot penalty | after search |
| --- | --- | --- |
| `chrono_trigger_leeneBell` | 2.000 (capped) | **0.006** |
| `mega_man_iii_cursor` | 2.000 (capped) | **0.004** |
| `mega_man_ii_one-up` | 2.000 (capped) | **0.033** |
| `mega_man_iii_get-beat` | 2.000 (capped) | **0.023** |
| `chrono_trigger_gateActivate` | 1.000 | **0.020** |

`leeneBell`, `cursor`, `one-up` and `beam-out` are exactly the targets the v7
listen pass flagged for smeared/incomplete note sequences. The metric now
registers their structure and the search can act on it. **Whether that translates
into audibly better sounds is precisely what Gate B has to answer** — a lower
penalty is the term agreeing with itself, not evidence about ears.

Eight targets stay pinned at the 2.000 cap even after search
(`charm1`, `ozzie`, `slash2`, `waterMagic`, `dead`, `hurt`, `bigger-boom`, `yoku`).
Either the structure is genuinely unreachable in bfxr's parameter space, or the
search cannot find it at this budget.

### Caveat: targets near the voicing threshold

The term is gated off below `VOICED_MIN = 0.35`. Four capped targets sit just
above it — `bigger-boom` 0.36, `ozzie` 0.38, `slash2` 0.49, `hurt` 0.50 — so
their note detection rests on a marginally-voiced pitch track and their penalties
are the least trustworthy in the set. Worth a look in Gate B; if those four sound
*worse* under the new objective, the gate threshold is the first suspect.

## 3. Score medians (trend only — NOT comparable across columns)

| Mode | legacy median | new median | wave-type changed |
| --- | --- | --- | --- |
| `current` | 2.451 | 3.321 | 7/32 |
| `model_seeded` | 2.748 | 3.315 | 5/32 |
| `one_shot` | 9.237 | 10.424 | 0/32 |

**The new medians are higher and that is arithmetic, not regression.** The new
objective adds a non-negative term, so every score gains `structure_pitch ≥ 0`
against the same wave. Comparing these two columns is meaningless; they are
recorded only to show the runs completed and how far the search moved.

The useful signal is the right-hand column: the new objective changes the
*selected wave type* on 7 targets in `current` and 5 in `model_seeded` — real
changes in search behaviour, not noise.

`one_shot` is the A/B control and behaves exactly as it must: 0/32 wave types
changed and duration ratios byte-identical between runs, because one-shot takes
the raw model prediction without search. Only its scores move, by the added term.
That the control held is the strongest evidence the A/B harness is wired
correctly.

## 4. Length / energy — the Section 2a decision

Duration-ratio collapse (candidate < 0.5× the target's trimmed duration). All
three modes reported the full **32 rows** in both runs, so no target was silently
skipped.

| Mode | legacy collapsed | new collapsed | legacy median | new median |
| --- | --- | --- | --- | --- |
| `one_shot` | 3/32 = 9% | 3/32 = 9% | 0.87× | 0.87× |
| `model_seeded` | 5/32 = 16% | **4/32 = 12%** | 1.03× | 1.03× |
| `current` | 0/32 = 0% | 0/32 = 0% | 1.01× | 1.05× |

### Decision: Section 2a is NOT justified by the evidence

The plan's rule was: implement the energy/duration coverage penalty if **≥25% of
targets collapse below 0.5× in either run**. The observed maximum is **16%**
(legacy `model_seeded`), and the new objective *reduces* it to 12%. Every other
cell is at or below 9%, and the search-only mode never collapses at all.

So the term is not built. The existing `coverage` term (weight 3.0, already the
dominant cost for absence) is handling duration collapse adequately. Per the
plan, `duration_floor` / envelope pinning in `optimizer.py` is therefore **also
not** tightened — it was explicitly secondary to the metric term and never a
substitute for it.

**What would reopen this:** `model_seeded` still puts 2 targets below 0.25× in
the new run. If Gate B's listener reports mutes or truncated tails, that is the
counter-evidence, and 2a returns as its own spec with the listen finding as its
justification rather than a threshold that was never crossed.

## 5. Note-detector fix (plan Task 1)

`detect_note_sequence` was discarding a flat note whenever a single transitional
frame at a boundary pushed the segment's spread past `FLAT_ST` — measured on a
real render, a 25-frame note lost to one 1.47-semitone frame. Fixed by judging
flatness on the segment interior.

This also feeds the pre-existing pitch-jump arp seeding, so note counts were
wrong there too. `leeneBell` now detects **3 notes** with `voiced_frac` 1.00, and
its post-search structure penalty is 0.006 — consistent with the v7 listen
complaint ("two of three notes, wrong slope") having been partly a detector bug
rather than purely a search failure. Stated as consistent-with, not proven: the
listen test is what would confirm it.

## 6. Counter-finding: the term perturbs the search without guiding it

Found by the final whole-branch review, in the **slow** roundtrip tests that the
default `pytest` run excludes — so every earlier "161 passed" figure in this
document was blind to it.

| Fixture | branch point | this branch | structure penalty |
| --- | --- | --- | --- |
| `bitnoise_glitch` | 1.991 PASS | 4.130 | 2.00 on **both** arms' winners |
| `sine_powerup` | 3.896 (already failing) | 6.013 | 2.00 on **both** arms' winners |
| other 4 fixtures | — | byte-identical | 0.00 |

Verified against `ea802ea` in a throwaway worktree, not estimated.

Two things make this less alarming than it first looks, and one makes it worth
keeping in view.

**The penalty is pinned at the cap for every candidate the search can reach.**
It is therefore not pulling the search toward better structure and overshooting —
it supplies *no gradient at all* on these targets, and merely reshuffles which
candidates survive early screening. The residue (`4.130 − 1.991 = 2.139`, i.e.
the 2.00 cap plus ~0.14) is the search landing in a different, slightly worse
basin.

**Across 32 real targets it is a coin flip, not a bias.** Scoring both arms'
winners under the legacy objective as a neutral referee:

| Mode | new better | new worse | identical | mean Δ |
| --- | --- | --- | --- | --- |
| `current` | 5 | 9 | 18 | +0.049 (new worse) |
| `model_seeded` | 6 | 8 | 18 | −0.033 (new better) |

9-vs-5 is not significant at n=14 (p ≈ 0.21), the two modes disagree on the sign
of the mean, and restricted to the 17 targets where the term fires the new arm is
worse on only 8/17 and 7/17. The two roundtrip fixtures were an unlucky draw.

**Listen verdict on the two fixtures** (2026-07-25): `sine_powerup` is a smooth
rising melodic sweep that *both* arms render as a noisy thing — equally wrong,
no regression. `bitnoise_glitch` under the new objective is "a bit too loud, but
not the end of the world" — a mild, real regression.

**What was done:** the roundtrip assertion now scores the winner on the legacy
scale (`structure_pitch=0.0`), so `SCORE_THRESHOLD = 3.5` keeps the calibrated
meaning it was given on 2026-07-22 as an optimizer+metric health check; the
search still runs under the real objective. `bitnoise_glitch` passes at ≈2.130,
leaving the ~0.14 of search noise visible but under the bar. `sine_powerup` is
`xfail(strict=True)` citing its pre-branch failure. **No constant in
`structure.py` was tuned to make a test pass.**

**What still deserves the listener's attention:** the term fires on targets whose
"notes" are pitch-tracker artifacts. `bitnoise_glitch` is read as a 714→192 Hz
interval — nearly two octaves, on a *bitnoise* preset — at `voiced_frac 0.56`,
comfortably clear of the 0.35 gate. If Gate B finds the eight capped targets
sound worse, raising `VOICED_MIN` or adding an interval-sanity gate is the
follow-up, and it should be driven by that evidence rather than by this test.

## 7. Gate A verdict

Cleared to ask for ears. The probe gate passes, the term demonstrably engages on
a majority of real targets, the A/B control held, and no duration regression
appeared. **No claim of improvement is made here.** Proceed to Gate B.

## Appendix — reproducing

```bash
cd tools
CKPT=.../\.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt
PYTHONPATH=. uv run python -m invert.eval_targets --targets targets/ \
  --ckpt "$CKPT" --budget 2000 -o invert/runs/gateA_legacy/ --legacy-objective
PYTHONPATH=. uv run python -m invert.eval_targets --targets targets/ \
  --ckpt "$CKPT" --budget 2000 -o invert/runs/gateA_new/
PYTHONPATH=. uv run python -m match.length_report \
  --eval-root invert/runs/gateA_new --targets targets/ --mode model_seeded
PYTHONPATH=. uv run python -m match.structure_probes
```
