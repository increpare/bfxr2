# Actual-render pitch calibration implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Apply TDD and separate spec then quality review. User has delegated routine decisions; continue autonomously.

**Goal:** Test whether an explicit acoustic pitch component improves the existing multisynth inverse without sacrificing already-correct gestures.

**Architecture:** Frozen v3 experts propose timbre/structure. A new module adjusts pitch through known DSP mappings and verifies every step with actual audio. A bounded pitch-eligibility selector is evaluated against the exact original candidate pools before human listening.

**Tech Stack:** Python/NumPy, existing shipped-JS Renderer, frozen v5 diagnostic and MatchObjective, existing cached-WebAudio gallery.

Spec: `docs/superpowers/specs/2026-10-05-pitch-calibration-design.md`.

## Task1: bounded calibration and selection

Create `tools/neural_invert/pitch_calibration.py` and
`tools/tests/test_neural_pitch_calibration.py`. No other neural module changes.
Public API:
- `POLICY`: JSON-serializable exact thresholds/mappings/version.
- `shift_register(synth, params, semitones, spec)`: deep-copy controls, change only
  primary frequency controls using mappings/schema bounds; reject unsupported
  engines/nonfinite offsets. Input remains unchanged.
- `calibrate_candidate(candidate, target_wave, renderer, objective, max_steps=3)`:
  return `{original, accepted, attempts, status}`. Rows contain actual `wave`,
  `params`, `seed`, `synth`, actual `score`, `audioHash`, pitch diagnostics/comparison,
  provenance. Replay original; raise if original cannot produce a valid baseline.
  Record every attempted adjustment (requested/canonical params, seed, audio hash,
  actual score/evidence or error, accepted/rejection reason). Implement all exact
  algorithm/acceptance requirements in the spec, including stationary pitch-head
  initialization on first attempt, then measured residual calibration.
- `select_candidates(originals, accepted, target_wave)`: return baseline,
  expanded-objective selection, pitch-first selection, eligibility records/reason.
  Use the exact eligibility and baseline-preservation rules in the spec.

- [x] Write failing tests first. Start with input immutability and known shifts:
  `shift_register('Transfxr', p, 12, spec)['pitch']['start'] == p['pitch']['start']+1/7`
  when unclamped, and Bfxr `(new_s**2+.001)/(old_s**2+.001) == 2`.
  Real-render tests compare a stable 440Hz target to lower-pitched compatible
  patches in all3 engines and require measured error reduction. Add stationary
  false-motion correction, moving-target motion-control preservation, noisy
  target exact fallback, clipped range, silent/failed/duplicate render handling,
  actual PCM/seed bindings, nonpitch controls unchanged, duration/voicing/span
  rejection, all-active tolerance, and selection that cannot discard original
  fallback or regress reliable baseline pitch. Use actual DSP for acoustic claims.
- [x] Run red tests, implement module, run focused suite with
  `PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/bfxr-mpl /Users/stephenlavelle/Documents/bfxr2/tools/.venv/bin/python -m pytest tools/tests/test_neural_pitch_calibration.py -q`.
- [x] Independent specification review, then code-quality review; fix findings,
  rerun relevant tests, freeze and commit only the two owned files.

## Task2: actual probe and audit

Create `tools/neural_invert/pitch_calibration_eval.py` and
`tools/tests/test_neural_pitch_calibration_evaluation.py`.
CLI accepts `--benchmark` (one frozen v5 comparison results file) and fresh
`--output`. Process only its temporal-v3 arm, preserving target order/IDs.
- [x] Test missing/modified source report/audio/DSP/checkpoint bindings, incomplete
  source, missing originals, safe fresh output, literal actual render persistence,
  all3 output selections and counted render failures. Use temporary fixture
  reports with real tone render identities and fake predictor-free pools.
- [x] Implement report schema with incomplete manifest until alltargets verified;
  original report/hash, model/checkpoint/data/DSP hashes, policy/code hashes,
  all original/accepted/rejected attempts and exact FLOAT WAVs, source-engine
  versus unrestricted outputs where meaningful. Store full v5 diagnostics and
  objective values; report baseline/expanded-objective/pitch-first separately.
  Aggregate all predeclared gates from the spec with explicit pass/fail; the
  combined20+4 gate may be a root analysis script consuming both reports.
- [x] Run focused tests; independent spec then quality reviews; freeze code.
- [x] Execute both24-target development cohorts. Independently replay every new
  accepted/selected output and audit attempted render accounting/code identities.
  Archive compact report and predeclared gate result in evaluations/. No promotion
  or human page on a known failed gate.

## Task3: useful short listening checkpoint, conditional on actual evidence

- [ ] Use `evaluations/pitch-calibration-listening-targets.json`, frozen from input
  profiles before calibration outputs: charm2, battleStart, Select Beep, heavy
  impact bell003, Descending Fall Whistle. Bird/spinout/book/Egg have insufficient
  global pitch confidence for this conservative component; don't rerate unchanged
  sets. Verify cached v3 allRaw/allRefined and original Bfxr controls/seed/PCM
  against archived reports/audit before using as model proposals. Bind source
  artifacts; human choices only choose historical comparison anchors, never
  calibration or automatic selection.
- [ ] For fresh targets, obtain frozen-v3 proposals and same384 guarded trials
  per available engine plus original Bfxr baseline with declared2000 budget
  (record actual evaluations). These define the common pre-calibration pool;
  calibration adds only Task1's bounded pitch trials. Retain uncalibrated winner
  and original Bfxr for comparison, deduplicating exact heard PCM. No claim of
  equal computation versus a raw inverse or learned-model improvement.
- [ ] Create a separately named calibration listening run. Apply frozen Task1
  without extra tuning to these candidate pools, preserve all attempts and exact
  historical heard PCM. Skip redundant unchanged comparison sets; max5 items.
  Keep <=3 distinct options, both relevant charm histories, cached-WebAudio UX.
- [ ] Test provenance/alias/pool/selection/export behavior; spec and quality
  reviews; actual-DSP/PCM audit and isolated-origin browser QA. Publish a LAN-safe
  link and ask best/tie/none plus optional adequacy notes. Retain outcome as a
  human-quality checkpoint, not a claim that the full goal is complete.

### Listening implementation details

Own new `pitch_calibration_gallery.py` and its focused gallery tests only. Reuse
frozen v3 prediction/refinement and existing quick UI. Fresh reference preparation
is `audition_pcm(prepare_target(path))` exactly once, then direct PCM16 persistence;
assert its decoded float32 hash matches the fixed manifest. Never peak-normalize
an already audition-transformed reference a second time. For charm, copy the
archived reference and bind `archivedReferencePcmSha256`; the inherited source
`normalizedPcmSha256` is a different identity.

The original Bfxr checkpoint is
`/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt`,
SHA256 `47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98`.
Keep its optimizer and seed policy fixed; record actual evaluations and running
backend identity. Verify original-backend versus shipped-DSP replay before treating
its controls as a calibration candidate. If backends differ, retain its actual
original PCM in the common baseline/selection pool and heard comparison, explicitly
skip adjustment of that row, and record why; never replace its PCM silently.

Fresh target refinement seed is `20261011 + target_index*1009 + engine_index*71`
(zero-based fixed manifest and Bfxr/Transfxr/Pluckr order). Original Bfxr optimizer
seed omits the engine term. The common pool has up to12 raw +3 refined +1 original
Bfxr candidates. Its calibration budget is at most3 extra renders per actual pool
member, reported separately from384 trials per engine and original-Bfxr fitting.
Task2's36-render total applies to its12-member synthetic benchmark only.

All accepted/rejected pitch attempts and actual original pool PCM are retained.
Use bounded calibration as frozen; choose all new options without human labels.
Human history only supplies exact comparison anchors. Label the new option as
pitch-calibrated, not as a newly trained model. No page unless the predeclared
synthetic gate passes; fixed fresh listening references are a separate human check.

## Execution constraints

Do not edit frozen v3/v4/v5 feature, model, data, evaluation, gallery or synth code.
Do not rerun training or delete prior artifacts. Root owns documentation/reports;
one implementation agent at a time owns its specified files. Each stage completes
review before dependent work. No new user-owned threads, messages or automations.

## Completed synthetic probe

Code frozen at65508e6 after104 calibration/evaluator tests and independent spec
and quality reviews. Both production cohorts completed; independent replay audit
`tools/multisynth/evaluations/pitch-calibration-audit.json` passed every predeclared
gate. High-register eligible4/4, mean objective7.522992→0.651379; ordinary mean
1.435681→1.484319 (+3.39%, within the predeclared10% bound). No prior ordinary
static median/direction pass lost. Moving contour .981062→.903158 semitones;
span1.311111→1.224379. All originals retained; no failed renders. This supports
the bounded hybrid component proceeding to human listening, not a learned-model
or general auditory success claim.

### Selector tradeoff retained for human scrutiny

The passing mean gate does not imply every ordinary choice improved. In
`031-Pluckr-static`, baseline Pluckr objective0.422535 becomes Bfxr3.076493.
Baseline median error was already0.00566 semitone; it failed the target-active
frame fraction (.7045 versus the .75 requirement), while the longer-voiced Bfxr
passes1.0. Baseline voiced31 frames, target44, new47. The selector is therefore
trading envelope/voicing coverage against objective/timbre, rather than fixing a
wrong median pitch in this case. Keep this counterexample, do not silently
change the frozen rule, and retain uncalibrated baselines in human comparisons.
Auditory preference is unresolved; aggregate pass is permission to test, not
promotion of the selector as generally superior.
