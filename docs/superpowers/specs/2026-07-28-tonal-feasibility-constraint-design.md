# Tonal Feasibility Constraint — Design

**Date:** 2026-07-28
**Status:** Approved in conversation
**Scope:** Opt-in experiment; no shipping-default changes

## 1. Problem

The 2026-07-25 headroom probe established a median-level reachability
ceiling under the current matcher, but the blind ratings exposed a separate
failure: extra search sometimes finds a lower-scoring, perceptually worse
candidate by abandoning tonality.

On the affected tonal targets, the target feature track is 96–100% voiced
while several poorly rated winners are 0% voiced. The objective then charges
the fixed `voiced_mismatch` term but stops charging pitch, pitch-slope, and
pitch-movement terms, because those terms only apply where both sounds are
voiced. This gives the optimizer an escape hatch:

| Target | Existing control rating | Collapsed rating | Objective change |
|---|---:|---:|---:|
| Mario 2 — Throw | 3 | 1.5 | 2.93 → 2.38 |
| Mario 3 — jump (SNES) | 2 | 1 | 3.19 → 2.33 |
| Mega Man II — One-Up | 3 | 1.5 | 2.54 → 2.51 |

Mario 3 — jump (NES) is the clearest universal failure: the target is 96%
voiced, the inspected winners are 0% voiced, and all three blind candidates
received 1/5.

Two instrumentation risks accompany the collapse:

- Writing a candidate as PCM-16 can flip the current pitch detector despite
  changing samples by only about `3e-5`. For two saved candidates, the
  objective changed from 2.38 to 10.35 and from 2.96 to 10.88 after the exact
  round trip used by the listening page.
- The White-noise Throw winner scored 2.61 on its search render seed and
  10.65 on the held-out seed.

The experiment must therefore test a hard tonal-feasibility constraint and
must validate the exact artifact heard by the listener. It must not interpret
an aggregate metric gain as audible success.

## 2. Goal and decision rule

The product goal is not “fewer catastrophes” or a better mean. Every emitted
match must be genuinely good.

The treatment succeeds only when:

1. every treatment result on the ten-target development slice receives 4/5
   or 5/5 on the new human-rating scale; and then
2. after freezing code and settings, every treatment result across all 32
   product targets receives 4/5 or 5/5.

There are no compensating wins, mean thresholds, or metric-based substitutes.
One treatment rating below 4/5 is enough to conclude that this constraint is
insufficient.

## 3. Non-goals

- Do not change the shipping matcher defaults.
- Do not claim that tonal feasibility is sufficient for perceptual quality.
- Do not tune the structure objective, inverse model, synth, or search budget.
- Do not add multi-voice synthesis in this experiment.
- Do not train on product targets, exemplars, or manual recreations.
- Do not convert historical ratings onto the new scale by inference.
- Do not run the 22-target holdout before the treatment passes the known
  ten-target slice and all settings are frozen.

If the treatment fails, the result selects the next research problem; it does
not trigger threshold tuning until a partial aggregate result looks good.

## 4. Experiment boundary

The treatment mirrors the existing `big_seeded` arm:

- learned inverse-model seed enabled;
- RNG seed unchanged;
- 200,000-evaluation budget;
- restarts enabled;
- existing objective weights;
- existing renderer and search stages.

The only search-behavior change is the opt-in tonal-feasibility constraint.
Exact-artifact and held-out-seed checks are validation corrections: they
report whether the candidate being claimed is the one actually heard and
whether its feasibility depends on a render seed.

The initial control is the existing `big_seeded` artifact for each hard-slice
target. The blind page presents control and treatment under randomized labels.
The listener rates both on the new scale, but only the decoded treatment
ratings determine whether the experiment advances.

There are no existing 200,000-evaluation controls for the remaining 22
targets. If the treatment reaches the frozen-holdout stage, run both
unconstrained and constrained `big_seeded` arms there with the same checkpoint,
RNG, budget, and renderer. This costs another arm but preserves the same causal
A/B comparison over the full target set.

## 5. Tonal feasibility

### 5.1 Component boundary

Add an isolated matcher component, provisionally
`tools/match/feasibility.py`, with no dependency on optimizer internals. It
accepts extracted target features once and evaluates candidate features
through a small result object containing:

- whether the constraint applies;
- target voiced fraction;
- candidate preservation fraction;
- feasibility threshold;
- non-negative deficit;
- feasible/infeasible verdict.

The component is usable independently in unit tests, optimizer evaluation,
artifact validation, reports, and exemplar checks.

### 5.2 Target applicability

Define the target tonal mask as frames that are both active and voiced:

```text
target_tonal = target.active AND target.voiced
target_voiced_fraction =
    count(target_tonal) / max(count(target.active), 1)
```

The constraint applies when `target_voiced_fraction >= 0.80`.

This produces a clean split on the current hard slice: nine targets are
96–100% voiced, while Mario Break Brick is 2.4% voiced and remains
unconstrained. The applicability threshold is fixed before the treatment run.

### 5.3 Candidate preservation

Pad or truncate the candidate feature masks to the target timeline. Measure
whether the target's tonal frames remain both active and voiced:

```text
preserved =
    count(target_tonal AND candidate.active AND candidate.voiced)
    / max(count(target_tonal), 1)
```

A candidate is feasible when `preserved >= 0.75`.

This aligned definition prevents two trivial workarounds:

- a very short tonal blip cannot pass merely because all of its own frames
  are voiced;
- an unrelated voiced tail outside the target's tonal interval cannot pass.

The constraint deliberately does not check pitch correctness. It closes the
observed “opt out of pitch” failure; the existing objective still ranks pitch,
envelope, motion, timbre, and detail among feasible candidates.

For a non-tonal target, the result is `applicable=false`, `feasible=true`, and
the existing search behavior is unchanged.

## 6. Feasibility-first optimization

Expose the experiment through an opt-in CLI/settings flag such as
`--preserve-voicing`; its default is off.

The optimizer retains raw objective score and feasibility data separately.
Candidate ordering is lexicographic:

1. every feasible candidate outranks every infeasible candidate;
2. among infeasible candidates, smaller feasibility deficit wins, with raw
   objective as a deterministic tie-breaker;
3. among feasible candidates, the existing raw objective wins.

CMA-ES still requires scalar fitness, but its updates depend on population
rank. For each evaluated population, stably sort candidates by the
lexicographic key above and pass ordinal ranks to CMA-ES. Renderer failures
sort after ordinary infeasible candidates. The archive and final selection use
the lexicographic key directly, not the transient population rank. Raw
objective, feasibility, and CMA fitness remain separate fields. This makes it
impossible for objective magnitude to let an infeasible candidate outrank a
feasible one.

The continuous deficit gives an all-infeasible CMA population a direction
toward feasibility. Once feasibility is crossed, optimization resumes on the
unchanged objective.

If a run never finds a feasible candidate, report
`no_feasible_candidate`. A diagnostic best-infeasible artifact may be retained
under an explicitly diagnostic name, but it must not appear as the treatment
winner or on the claim-gate listening page.

## 7. Exact-artifact and render-seed validation

After search:

1. save the selected `.bfxr`;
2. re-render it with the declared listening seed;
3. write the PCM-16 WAV exactly as the listening page will consume it;
4. reload that WAV;
5. recompute feasibility and objective components on the reloaded samples;
6. render the same `.bfxr` on the held-out seed and recompute feasibility and
   objective components there.

Both the exact listened artifact and the held-out render must be feasible for
the run to be valid. Failure produces an explicit invalid outcome and excludes
the candidate from the blind page.

Reports preserve all three score contexts separately:

- in-memory search winner;
- exact emitted PCM-16 artifact;
- held-out render seed.

No score is silently substituted for another. Objective disagreement is
diagnostic evidence, not the human claim gate.

## 8. Human-rated exemplar corpus

Create a tracked corpus at:

```text
tools/exemplars/human_rated/
  manifest.json
  blind/
  manual/
```

Each unique artifact stores:

- target identity and target path;
- exact `.bfxr`;
- exact listened WAV;
- content hashes;
- renderer/version and render seed;
- provenance and source run;
- one or more rating observations;
- rating scale identifier;
- optional listener note.

Duplicate artifacts are stored once while retaining every observation.

### 8.1 Existing blind positive controls

The current headroom ratings contain four unique exemplary artifacts and nine
rating observations:

- Leene Bell: one identical artifact rated 4/5 in three blind arms;
- Beam-Out: one identical artifact rated 4/5 in three blind arms;
- Cursor: one artifact rated 4/5 in two blind arms;
- Cursor: the distinct `big_unseeded` artifact rated 5/5.

These exact artifacts must remain feasible under the new constraint.

Known collapsed candidates from Throw, NES/SNES Jump, and One-Up become
negative regression fixtures and must be rejected. Negative fixtures remain
separate from the positive-control manifest so “exemplar” continues to mean
human-approved sound.

### 8.2 Manual reachability witnesses

The user may contribute up to five hand-made `.bfxr` recreations. The
recommended diagnostic set is:

- Mario 2 — Throw;
- Mario 3 — jump (NES);
- Mario 3 — jump (SNES);
- Mega Man II — One-Up;
- Mario Break Brick as the non-tonal control.

For each recreation, the user supplies the `.bfxr`, a 0–5 creator
self-rating, and an optional note. The project renders and preserves the exact
reference WAV. The manifest labels this rating
`creator_self_rating`, never `blind`.

A manual recreation rated at least 4/5 is a reachability witness: it shows that
one Bfxr voice can represent the target at acceptable quality. Its feasibility
and objective breakdown are compared with the optimizer's winner. A manual
rating below 4/5 is still useful evidence but does not prove unreachability.

Manual witnesses neither block nor satisfy the blind claim gate.

## 9. Rating scales

Ratings are stored with explicit scale identifiers.

### 9.1 Historical scale

Existing ratings remain on `legacy_1_to_5`. They are preserved exactly as
given. No numeric conversion is inferred, even though the listener stated that
the former 1/5 occupied the role of the new 0/5 failure anchor.

### 9.2 New scale

All manual recreations and all new blind pages use `quality_0_to_5`:

| Rating | Anchor |
|---:|---|
| 5 | Could convincingly replace the original |
| 4 | Clearly the same effect; minor imperfections only |
| 3 | Recognizable, but materially wrong |
| 2 | Shares some traits but is not a usable match |
| 1 | Barely related or badly degenerate |
| 0 | Silent, broken, or unrelated |

The experiment's human pass condition is `quality_0_to_5 >= 4` for every
treatment output. Half-point ratings are allowed, so valid values are
`0, 0.5, 1, …, 5`.

## 10. Blind evaluation protocol

### 10.1 Development/falsification set

Use the ten targets already named by `match.listen_compare.HARD_SLICE`.
Generate a page with:

- the original target;
- existing `big_seeded` control;
- constrained `big_seeded` treatment;
- per-target randomized A/B assignment;
- no arm names or objective scores.

Write the decode key separately and do not inspect or expose it while ratings
are collected. The user rates every candidate on `quality_0_to_5`.

If any decoded treatment rating is below 4/5, stop. Record the negative result
and do not spend the 22-target holdout.

### 10.2 Frozen holdout

If all ten treatment results pass:

1. freeze the commit, thresholds, RNG, model checkpoint, budget, renderer
   version, and page-generation procedure;
2. run unconstrained-control and constrained-treatment `big_seeded` arms on
   the remaining 22 audio targets in `tools/targets/`;
3. generate the same blind control/treatment comparison;
4. collect new-scale ratings;
5. decode only after the complete table is returned.

The final experiment succeeds only if all 32 treatment ratings are at least
4/5.

The 22 targets remain a holdout until the freeze. Rating old candidates from
those targets before the freeze would spend that holdout and is therefore
deferred.

## 11. Reporting and failure handling

Each treatment result records:

- target and arm identifiers;
- target tonal applicability and voiced fraction;
- winner preservation fraction and deficit;
- raw objective components;
- ordinal optimizer fitness only where needed for debugging;
- evaluation count, elapsed time, model checkpoint, RNG, and renderer version;
- emitted-artifact validation;
- held-out-seed validation;
- validity status and explicit failure reason.

Expected explicit failure reasons include:

- `no_feasible_candidate`;
- `render_failed`;
- `emitted_artifact_infeasible`;
- `heldout_render_infeasible`;
- `missing_output`;
- `invalid_exemplar_manifest`.

An invalid or missing treatment cell is a failed target, not an omission from
the denominator.

## 12. Tests

### 12.1 Unit tests

- Tonal applicability below, at, and above 0.80.
- Candidate preservation below, at, and above 0.75.
- Timeline padding/truncation and aligned masking.
- Short voiced blip and out-of-window voiced tail rejection.
- Non-tonal target exemption.
- Feasible-over-infeasible ordering independent of objective score.
- Deficit ordering among infeasible candidates.
- Renderer failures ordered below ordinary infeasible candidates.

### 12.2 Regression tests

- All four unique blind positive controls are feasible.
- Known tonal-collapse fixtures are infeasible.
- Mario Break Brick remains unconstrained.
- Exact PCM-16 round trips retain their own recorded validation result.
- Rating observations retain their original scale identifiers.
- Duplicate observations do not duplicate artifact files.

### 12.3 Integration tests

- A small deterministic constrained search can move from infeasible candidates
  to a feasible winner.
- Default/off mode reproduces existing matcher behavior.
- Opt-in CLI settings reach the optimizer and report.
- A no-feasible run produces an explicit failure and no claim-gate winner.
- `.bfxr` render, emitted WAV reload, held-out render, report, blind page, and
  separate decode key agree on target and artifact identity.

Run the complete existing test suite before committing implementation and
before starting the expensive experiment.

## 13. Execution order

1. Preserve and validate the four unique positive exemplars and their nine
   historical observations.
2. Add negative collapse fixtures.
3. Implement `TonalFeasibility` with unit and regression tests.
4. Integrate opt-in feasibility-first ranking with default behavior unchanged.
5. Add exact-artifact and held-out validation/reporting.
6. Add constrained experiment and blind-page wiring.
7. Run smoke and full test suites.
8. Run the ten-target constrained treatment.
9. Collect the complete new-scale blind table.
10. Stop on any treatment rating below 4/5.
11. Otherwise freeze the experiment and run the untouched 22-target holdout.
12. Collect and decode the final table; require all 32 treatment ratings to be
    at least 4/5.

Only a full human pass justifies a later, separate decision about enabling any
behavior by default. A failed pass becomes evidence for the next capability
or objective design rather than a partial shipping win.
