# Headroom Probe — which ceiling caps the hard slice?

**Date:** 2026-07-25
**Status:** design approved — implementation plan next
**Branch:** `feature/inverse-model-structure-metric`
**Baseline checkpoint:** `invert/runs/v7_real_ft/best.pt` (frozen — no retrain in this plan)
**Strategy context:** `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md`
**Supersedes as next bet:** next-bets (2) multi-hypothesis seeding — see "Why this instead of bet (2)"

## Goal

Measure how much headroom the *existing* pipeline has on the hard slice, and
attribute the remaining gap to one of three ceilings:

| Ceiling | Meaning | Implied next project |
| --- | --- | --- |
| **Search** | CMA has not converged; more budget lowers `MatchObjective` | seeding / search bets (incl. bet 2) |
| **Metric** | more budget lowers `MatchObjective` but ears do not improve | objective work — the judge is wrong |
| **Reachability** | real-target floor sits far above the in-domain floor and budget does not move it | capability — pairs-of-sounds / synth extensions |

Every seeding bet is capped by the search-headroom number, and nobody has
measured it. This probe is cheap (one overnight run) and its result selects the
next multi-week project.

## Why this instead of bet (2)

The handoff proposes next-bets (2) multi-hypothesis seeding, starting cheap by
"scoring all top-k renders, dropout, or noise". **That cheap version already
ships.** `StagedOptimizer._stage0_seeded` (`match/optimizer.py:325`) takes the
top-3 wavetype hypotheses from `predict_wave`, expands each to 9 units via
Gaussian jitter (`seed_jitter=0.05`, `seed_jitter_copies=8`), scores all of them
with the real `MatchObjective`, keeps the best per wavetype, and gives 3
survivors their own CMA runs.

What remains of bet (2) is *diverse modes* rather than a jitter ball around one
point — which needs a conditional generative head, i.e. a retrain. That would be
the fourth consecutive bet on the "better seed / better judge" axis after two
that failed the ear gate (Gate B structure metric; test-time surrogate refine).

Three signals argue for measuring before spending:

1. In the refine listen table, raw one-shot **beat** the full seeded search on
   3/10 hard targets (Mario 1 Jump 3 vs 2; Mario 3 nes 1 vs 0; Mario 3 snes
   2.5 vs 2). Where more search makes things worse by ear, seed quality is not
   the binding constraint.
2. The project's best diagnostic — "render ground-truth params and score, to
   tell an objective failure from a search failure" — has no real-SFX analogue.
   This probe builds one.
3. Weakness #6 in next-bets (synth reachability ceiling) has no owner and no
   measurement, yet it is the premise of the user's own unbuilt pairs-of-sounds
   idea.

## Decisions

| Decision | Choice |
| --- | --- |
| Probe scope | All three ceilings (search / metric / reachability) in one pass |
| Big budget | **200 000** evals (100x the 2 000 baseline), run unattended overnight |
| Restarts | **Required.** Without them the big arms are uninterpretable (see Section 1) |
| Restarts default | `False` — shipping path unchanged regardless of outcome |
| Baseline budget | **2 000**, matching `gateA_legacy`, so existing ear scores cross-check |
| Render-seed confound | Every arm's final candidate re-scored on a **held-out render seed**; both reported |
| Decision thresholds | **Pre-registered** below, applied to held-out-seed medians |
| Claim gate | Blind listen, hard slice, labels hidden and arms shuffled |
| Retrain | Out of scope |
| Shipping defaults | Not changed in this branch, even on a favourable result |

## Section 1 — Harness

### 1a. Restart loop (`match/optimizer.py`)

`_run_cma` exits on `es.stop()` (`tolfun=1e-4`). At budget 2 000 the pipeline is
budget-limited — `gateA_legacy` reports show 2 000–3 004 evals consumed against
a 2 000 budget. At 200 000 a single CMA run will **converge and stop**, leaving
most of the budget unspent, and `run()` would simply end.

A flat result at 100x would then be an artifact of early stopping, not evidence
of a ceiling. This is the single correctness risk that decides whether the whole
experiment means anything.

New settings:

| Field | Default | Notes |
| --- | --- | --- |
| `restarts` | `False` | Off = shipping path bit-identical |
| `restart_popsize_factor` | `2.0` | IPOP-style growth per restart |

Behaviour when `restarts=True`: after stage 2, while budget remains, relaunch
CMA alternating between (a) a perturbed archive-best, keeping that candidate's
wavetype, and (b) a fresh random unit on a wavetype drawn round-robin from the
stage-1 survivors, doubling `popsize` each restart and retaining the shared
archive. Arp and stage-3 handling are unchanged.

### 1b. Probe driver (`match/headroom.py`)

Runs the arm matrix, writes `results.json` and a **best-score-vs-evals trace**
per run.

The trace matters more than the endpoint. A curve still descending at 200 k
means "more search always helps". A curve flat from ~15 k means the current
2 000 default is leaving quality on the table and the knee tells us where.

### 1c. Listen page

Reuse `match/listen_compare.py`. No new page module.

## Section 2 — Arm matrix

Hard slice (10 targets, `match.listen_compare.HARD_SLICE`), all four arms:

| Arm | Seed | Budget | Answers |
| --- | --- | ---: | --- |
| `baseline_seeded` | model | 2 000 | today's shipping quality |
| `big_seeded` | model | 200 000 + restarts | search headroom |
| `baseline_unseeded` | f0 screening | 2 000 | control |
| `big_unseeded` | f0 screening | 200 000 + restarts | does the model seed matter *at convergence*? |

**In-domain control** — 10 bfxr presets from the existing `eval_bfxr` set,
`baseline_seeded` and `big_seeded` only. This is the known-reachable floor that
the real-target floor is measured against.

`big_unseeded` is the sharpest arm on the table: if a converged search *without*
the model matches a converged search *with* it, the inverse model earns its keep
as a time-saver rather than a quality lever, which recolours bet (2)
considerably.

Cost: ~3.5 ms/eval, so 200 k ≈ 12 min/target; the arp stage adds +50% of budget,
so big arms consume ~300 k and run ~18 min. Full matrix ≈ 6 h unattended.

## Section 3 — Run order and confounds

**Validate the harness at small scale first**, then launch the matrix:

1. Bit-identical regression: `restarts=False` at budget 2 000 reproduces current
   output exactly.
2. Sanity: a 200-eval restart arm must not score *worse* than a 200-eval plain
   arm on the same target.

A restart-loop bug found after the overnight run costs the whole night.

**Render-seed overfitting.** `avg_seeds=1`, so candidates are scored against a
single fixed render RNG seed. A 200 k-eval CMA has ample capacity to overfit
that seed's noise. Every arm's final candidate is therefore re-scored on a
**held-out render seed**, and both numbers are reported. If a big-budget
objective win evaporates on a fresh seed, the finding is "we overfit the render
seed" — not "search has headroom" — and that is itself a shipping-relevant bug.

## Section 4 — Pre-registered decision rule

Applied to **held-out-seed medians**. Written into the results doc whatever it
says, including "inconclusive" when readings conflict.

| Reading | Rule | Next project |
| --- | --- | --- |
| Search ceiling | median `MatchObjective` improves **>= 10%** at 100x vs baseline | seeding / search — bet (2) proper |
| Metric ceiling | objective improves >= 10% **but** blind listen mean gains **< 0.5/5** | objective work |
| Reachability ceiling | real-target/in-domain floor **ratio does not shrink** as budget goes 2 000 -> 200 000 | capability — pairs-of-sounds |

On the reachability rule: prior runs put the real-SFX seeded median near 2.61
and the in-domain median near 0.85 (different configs — treat as an expectation,
not a measurement; this probe measures both properly). If that ~3x gap holds, an
absolute "2x" cut would fire trivially, which is why it is not the trigger. The
robust signal
is whether the **ratio shrinks with budget**; the absolute ratio is reported at
both budgets as context, not as the trigger.

Blind listen supplies the ear column: 10 targets x (original + 3 candidates),
shuffled, labels hidden, per the branch's claims discipline.

## Section 5 — Artifacts

| Path | Content |
| --- | --- |
| `match/optimizer.py` | restart loop (default off) |
| `match/headroom.py` | probe driver |
| `invert/runs/headroom/results.json` | per-arm scores, both render seeds, traces |
| `invert/runs/headroom/headroom.html` | blind listen page |
| `docs/superpowers/plans/2026-07-25-headroom-probe-results.md` | verdict against Section 4 |

`invert/runs/` is gitignored; the results doc carries the numbers.

## Section 6 — Out of scope

- Retraining the inverse model or surrogate
- Implementing pairs-of-sounds / segment-and-match
- Any `MatchObjective` change, including re-enabling `structure_pitch`
- Changing shipping budget defaults in this branch (a knee worth shipping is a
  follow-up with its own listen gate)
- Enabling `restarts` by default, whatever the outcome
- Multi-hypothesis / generative seeding (gated on this probe's verdict)

## Success criteria

| Stage | Success | Verified by |
| --- | --- | --- |
| Harness | `restarts=False` bit-identical; restart arm never worse at equal budget | Section 3 checks |
| Evidence | Four arms x 10 targets + in-domain control, with traces and held-out-seed scores | `results.json` |
| Attribution | Verdict names one ceiling (or "inconclusive") per Section 4 | results doc |
| Free upside | Convergence knee identified, so a shipping budget change can be proposed | trace plot |
| Explicit non-goal | Improving hard-slice quality in this plan | — |
