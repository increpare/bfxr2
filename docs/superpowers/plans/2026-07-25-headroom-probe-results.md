# Headroom probe — results and ceiling attribution

**Date:** 2026-07-26
**Spec:** `../specs/2026-07-25-headroom-probe-design.md` (decision rule pre-registered in §4)
**Plan:** `2026-07-25-headroom-probe.md`
**Branch:** `feature/inverse-model-structure-metric`
**Checkpoint:** `v7_real_ft/best.pt` (frozen; no retrain)
**Run:** 2026-07-25 22:32 → 2026-07-26 05:23 CEST, unattended, `tools/invert/runs/headroom/`
**Artifacts:** `results.json` (60 rows), `headroom.html` + `headroom_key.json` (blind listen)

## Verdict — REACHABILITY CEILING

100x budget cuts the objective by **47%** on targets the synth provably can
make, and by **3%** on the real hard slice. The search is not stuck and the
budget is not wasted: this contrast fires the pre-registered reachability
rule. On this slice, increasing budget barely lowered the real-target median
while strongly lowering the reachable-control median. The next project is
**capability (synth extensions / pairs-of-sounds)**, not seeding and not the
objective.

For this one listener on the ten-target slice, 100x did not show a general
audible gain. `baseline_seeded` had the best mean and median; `big_seeded`
never won against it (6 ties, 4 losses). This is descriptive evidence on this
slice, not a claim of statistical significance.

This **de-selects bet (2) multi-hypothesis seeding**, which the handoff named
as the next project, because it does not address the pre-registered median
reachability result. The finite endpoints do not prove that every possible
learned seed would fail to find an unobserved basin; reopen the bet only with
new evidence that seed quality is binding.

## Run health

All 60 rows completed: 10 real targets x 4 arms + 10 in-domain presets x 2 arms.

| Check | Result |
| --- | --- |
| Arm failures | 0 |
| Missing held-out scores | 0 |
| Restart arms flagged `underspent` (<90% of budget) | 0 |
| Median evals, big arms | 221 202 (seeded) / 228 392 (unseeded) against a 200 000 budget + arp's additive 0.5x |

The restart loop did its job: without it a single CMA run converges and stops,
and every big-arm result would have been an early-stopping artifact rather than
evidence of a ceiling. This was the probe's single correctness risk (spec §1a).

## 1. Per-arm medians

| Set | Arm | Budget | Median score | Median held-out | Median evals |
| --- | --- | ---: | ---: | ---: | ---: |
| real | `baseline_seeded` | 2 000 | **2.4226** | 2.4226 | 2 508 |
| real | `big_seeded` | 200 000 + restarts | **2.3441** | 2.3441 | 221 202 |
| real | `baseline_unseeded` | 2 000 | 2.3891 | 2.3891 | 2 502 |
| real | `big_unseeded` | 200 000 + restarts | **2.2877** | 2.2877 | 228 392 |
| in-domain | `baseline_seeded` | 2 000 | **1.8245** | 1.8245 | 2 015 |
| in-domain | `big_seeded` | 200 000 + restarts | **0.9685** | 0.9685 | 200 087 |

100x budget buys:

- **+3.2%** on real targets, seeded
- **+4.2%** on real targets, unseeded
- **+46.9%** on in-domain targets

### The current model seed did not improve endpoint quality

`big_unseeded` (2.2877) is **better** than `big_seeded` (2.3441). The spec
called this "the sharpest arm on the table," and it landed at the measured
200 000-evaluation endpoint. At 2 000 evaluations the seeded arm is also not
ahead (2.4226 vs 2.3891 unseeded). Thus the current model seed did not improve
hard-slice median quality at either measured endpoint. The probe did not
compare matched time-to-quality, so it did not establish a speed benefit. It
also does not rule out a different learned seed finding an unobserved basin.

(One of `big_unseeded`'s ten wins is a render-seed artifact rather than a real
match — see §4. It is not the median, so the comparison stands, but the arm's
true edge is a little smaller than the number suggests.)

### 100x changed nothing at all on 6 of 10 real targets

| target | base_seeded | big_seeded | base_unseeded | big_unseeded | seeded gain |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mario 1 - Jump | 2.569 | 2.569 | 3.496 | 2.468 | +0.0% |
| Mario 2 - Throw | 2.926 | 2.381 | 2.845 | 2.612 | +18.7% |
| Mario 3 - jump (nes) | 4.094 | 4.094 | 4.083 | 3.139 | +0.0% |
| Mario 3 - jump (snes) | 3.188 | 2.962 | 3.199 | 2.335 | +7.1% |
| Mario Break Brick | 1.484 | 0.737 | 1.732 | 0.964 | +50.3% |
| chrono_trigger_leeneBell | 2.237 | 2.237 | 2.237 | 2.237 | +0.0% |
| mario 2 - jump | 1.670 | 1.670 | 1.997 | 1.997 | +0.0% |
| mega_man_ii_beam-out | 1.922 | 1.922 | 1.922 | 1.922 | +0.0% |
| mega_man_ii_one-up | 2.538 | 2.515 | 2.538 | 2.515 | +0.9% |
| mega_man_iii_cursor | 2.308 | 2.308 | 2.240 | 2.240 | +0.0% |

On six targets the 198 000 extra evaluations produced a **bit-identical**
float score — not merely close, equal. On the in-domain control only two of
ten did that:

| preset | base_seeded | big_seeded | gain |
| --- | ---: | ---: | ---: |
| preset_00 | 1.050 | 1.050 | +0.0% |
| preset_01 | 0.063 | 0.019 | +70.4% |
| preset_02 | 2.069 | 0.834 | +59.7% |
| preset_03 | 1.334 | 0.886 | +33.6% |
| preset_04 | 0.633 | 0.133 | +79.0% |
| preset_05 | 3.004 | 0.632 | +79.0% |
| preset_06 | 2.489 | 1.995 | +19.8% |
| preset_07 | 3.991 | 1.964 | +50.8% |
| preset_08 | 1.580 | 1.580 | +0.0% |
| preset_09 | 2.511 | 2.141 | +14.7% |

## 2. Convergence traces — where the curve flattens

Eval count at which `big_seeded` first reaches within 5% of its final score,
measured on the main pipeline only (trace capped at 200 000, since the arp
stage runs afterwards on additional budget and would otherwise place a
spurious "knee" at ~200 000):

| Set | Median knee |
| --- | ---: |
| real | **~6 000 evals** |
| in-domain | **~65 000 evals** |

This is the reachability reading arriving a second time by an independent
route. On reachable targets the search is still meaningfully improving out to
~65 000 evals. On real targets the measured trace is usually within 5% of its
final endpoint by ~6 000. The much earlier real-target knee, paired with the
control behavior, is consistent with the pre-registered reachability reading;
it does not prove that no unobserved basin exists.

Per-target real knees: 1 147 / 1 175 / 1 427 / 1 763 / 2 183 / 9 771 / 11 843 /
18 451 / 26 627 / 74 199.

**Free upside (follow-up, not this branch).** The two targets with >10% seeded
objective reductions have knees at 9 771 (Throw, +18.7%) and 26 627 (Break
Brick, +50.3%). A shipping budget of ~10 000 rather than 2 000 would capture
most of those measured objective reductions at ~5x the current search cost.
Per spec §6 that is a separate change with its own listen gate — the objective
delta alone must not ship it.

## 3. Pre-registered decision rule (spec §4)

Applied to held-out-seed medians, as pre-registered.

| Reading | Rule | Measured | Fired? |
| --- | --- | --- | --- |
| **Search ceiling** | median improves >= 10% at 100x | **+3.2%** seeded, +4.2% unseeded | **NO** |
| **Metric ceiling** | objective improves >= 10% **but** blind listen gains < 0.5/5 | seeded listen mean gain **-0.45/5** (< +0.5), but objective gain only **+3.2%** (< 10%) | **NO** — listening threshold met; objective precondition not met |
| **Reachability ceiling** | real/in-domain floor ratio **does not shrink** as budget goes 2 000 → 200 000 | ratio **1.328 → 2.420**: it nearly doubled | **YES** |

The reachability rule was deliberately written as "does not shrink" rather than
an absolute ratio, because the ~3x gap was expected a priori and an absolute
cut would have fired trivially (spec §4). The measured ratio does not merely
fail to shrink — it grows by 82%, because 100x budget closes most of the
in-domain gap and almost none of the real gap. That is as clean a firing of
this branch as the design allowed for.

The listen meets the metric-ceiling rule's listening-side threshold, but the
full rule does **not** fire because its objective precondition was not met.
The reachability verdict therefore remains, and this listen result does not
reopen objective work.

Absolute ratios, reported as context rather than as a trigger:

| Budget | real median | in-domain median | ratio |
| ---: | ---: | ---: | ---: |
| 2 000 | 2.4226 | 1.8245 | 1.33 |
| 200 000 | 2.3441 | 0.9685 | 2.42 |

## 4. Render-seed overfit check — fired, on the one row where it could

`heldout_score` equals `score` **exactly on 59 of 60 rows**. The exception is
severe:

| target | arm | wave type | search score | held-out score |
| --- | --- | --- | ---: | ---: |
| Mario 2 - Throw | `big_unseeded` | **White** | 2.6120 | **10.6469** |

That candidate is **4x worse** on a fresh render seed. It is not a match; it is
a fit to one RNG realization of white noise, which a 200 000-eval search has
ample capacity to find and a 2 000-eval search does not.

The 59 exact ties are a property of the synth, not evidence of robustness. Of
the twelve wave types, **only waveType 3 (White) renders differently across
render seeds**: the renderer seeds by replacing `Math.random` in the JS realm
(`render/bfxr_context.js`), and every other wave type — Bitnoise included — is
generated by a deterministic LFSR that never calls it. Exactly one arm winner
in the whole matrix was a White-noise sound, and that is exactly the row that
diverged. The check has a 1-in-60 opportunity to fire and took it.

Consequences:

- **Shipping-relevant bug, not just a probe artifact.** With `avg_seeds=1`, any
  search that lands on White noise can return a winner that is right for one
  seed only. The mitigation already exists (`--avg-seeds ~3`) but is not the
  default, and the exposure grows with budget — another reason a budget bump
  needs its own gate.
- The spec §3 worry is **structurally impossible for 11 of 12 wave types** and
  a live risk for the twelfth.
- The exact ties are still a useful cross-check in the other direction: they
  confirm the held-out path rebuilds the search's objective exactly, since a
  mismatched objective would have produced different numbers everywhere.
- Any future run must not report "held-out == search score" as evidence that
  overfitting was ruled out.

The verdict is unaffected: the outlier is not any arm's median, so all
held-out medians equal their search medians and every reading in §3 stands.
It does slightly qualify the `big_unseeded` result — one of that arm's ten
wins is a render-seed artifact rather than a real match.

## 5. Blind listen (spec §4 claim gate)

`invert/runs/headroom/headroom.html` — 10 targets x (original + 3 lettered
arms), labels hidden, key held separately in `headroom_key.json`. Verified free
of label leaks (arm names, budgets, and ordering all absent from the page).

Arms on the page: `baseline_seeded`, `big_seeded`, `big_unseeded`
(`baseline_unseeded` is the control arm and is excluded from listening).

| target | A | B | C | notes |
| --- | ---: | ---: | ---: | --- |
| Mario 1 - Jump | 1 | 3 | 3 | |
| Mario 2 - Throw | 1 | 3 | 1.5 | |
| Mario 3 - jump (nes) | 1 | 1 | 1 | |
| Mario 3 - jump (snes) | 2 | 1 | 1 | |
| Mario Break Brick | 2 | 1.5 | 3 | |
| chrono_trigger_leeneBell | 4 | 4 | 4 | |
| mario 2 - jump | 2 | 2 | 1.5 | |
| mega_man_ii_beam-out | 4 | 4 | 4 | |
| mega_man_ii_one-up | 1.5 | 1.5 | 3 | |
| mega_man_iii_cursor | 4 | 5 | 4 | wow finally got a 5/5! |

Revealed through the separately held key:

| target | `baseline_seeded` | `big_seeded` | `big_unseeded` |
| --- | ---: | ---: | ---: |
| Mario 1 - Jump | 3 | 3 | 1 |
| Mario 2 - Throw | 3 | 1.5 | 1 |
| Mario 3 - jump (nes) | 1 | 1 | 1 |
| Mario 3 - jump (snes) | 2 | 1 | 1 |
| Mario Break Brick | 2 | 1.5 | 3 |
| chrono_trigger_leeneBell | 4 | 4 | 4 |
| mario 2 - jump | 2 | 2 | 1.5 |
| mega_man_ii_beam-out | 4 | 4 | 4 |
| mega_man_ii_one-up | 3 | 1.5 | 1.5 |
| mega_man_iii_cursor | 4 | 4 | **5** |

Deltas and W/T/L are computed per target against the baseline before
aggregation.

| Arm | Mean | Median | Mean paired delta vs baseline | Median paired delta vs baseline | W / T / L vs baseline |
| --- | ---: | ---: | ---: | ---: | ---: |
| `baseline_seeded` | **2.80** | **3.00** | — | — | — |
| `big_seeded` | 2.35 | 1.75 | **-0.45** | 0.00 | **0 / 6 / 4** |
| `big_unseeded` | 2.30 | 1.50 | **-0.50** | -0.25 | **2 / 3 / 5** |

For this one listener on the ten-target slice, 100x did not show a general
audible gain. `big_seeded` never won, tied six times, and lost four; the
baseline had the best mean and median. `big_unseeded` produced the sole 5/5 on
`mega_man_iii_cursor` and won on Mario Break Brick, but those two wins are
isolated rather than a general improvement. The listen is descriptive
evidence, not a statistically powered result. It does not reopen objective
work, while the render-seed caveat in §4 remains in force.

## 6. Harness defects found and fixed during validation

Both found by plan Task 7's pre-launch checks, which is what those checks exist
for.

1. **In-domain control set never rendered** (`19de4b2`). `harvest_preset_params`
   emits records `{"preset", "seed", "params"}`; `make_preset_targets` passed
   the records straight to the renderer, whose worker merges any dict over the
   bfxr defaults — every key unknown, so all 10 presets rendered as the same
   default sound. The all-identical degeneracy guard caught it at runtime, the
   driver warned and continued, and the run produced **zero in-domain rows**.
   Undetected, this would have removed the entire leg of the decision rule that
   ended up carrying the verdict. Every unit test passed throughout, because
   the fakes used the wrong shape too.
2. **Control targets rendered on the held-out seed** (`605eb16`, found in the
   pre-launch review). A well-recovered noisy preset would have reproduced the
   target's own noise realization on the held-out re-score, deflating the
   in-domain floor more for the better-recovering big arm — firing the
   reachability branch for a reason unrelated to reachability. Now rendered on
   `PRESET_TARGET_RENDER_SEED = 31337`.

Also confirmed pre-launch: the shipping path is **bit-identical** to the
pre-branch commit (`5c634d9` vs `605eb16`, same target and seed — identical
evals, identical score, all six output artifacts byte-identical), so
`restarts=False` remains untouched by this work.

## 7. Consequences

| Bet | Status after this probe |
| --- | --- |
| (2) Multi-hypothesis seeding | **De-selected as the next project.** The current seed did not improve hard-slice median quality at the measured 2 000- or 200 000-evaluation endpoints, and the bet does not address the pre-registered median reachability result. Time-to-quality and possible unobserved basins were not measured; reopen only with new evidence that seed quality is binding. |
| (3) Sharper surrogate → real-FT | Still deprioritized; it targets seed quality, which the current endpoint comparisons do not identify as the next binding lever. |
| (4) Synth capability / pairs-of-sounds | **Selected.** The measurement its premise was missing now exists. |
| Shipping budget 2 000 → ~10 000 | Candidate follow-up with its own listen gate; not this branch. |
| `structure_pitch`, test-time refine | Unchanged; both remain default-off. |

Nothing in the shipping path changed in this branch (spec §6): `restarts`
defaults to `False`, budgets are untouched, and the objective is unmodified.
