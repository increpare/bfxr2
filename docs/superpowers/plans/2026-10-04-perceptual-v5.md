# Perceptual v5 and synthetic coverage implementation plan

> Execute with superpowers:subagent-driven-development. The user has authorized autonomous iteration, including design choices; proceed without an approval pause. Remain in the existing isolated research worktree.

**Goal:** Improve multi-synth recreation using event/texture features, measure recovery of held-out synthesized sounds across every active engine, and deliver new tagged listening comparisons against v4.

**Architecture:** Preserve auditory-v1 and every rated experiment. Add a separately versioned waveform descriptor whose prefix is the old descriptor, plus fine event/envelope and modulation/texture blocks. Fit a small nonnegative preference metric to all four immutable likeness archives, with grouped evaluation and a refitted old-feature ablation. Replay the existing library to build compatible descriptors. Search with both v4 and v5, keeping historical human-rated baselines. Synthetic targets are a separate coverage benchmark, not silently added as human preference labels.

**Tech stack:** NumPy/Torch, deterministic Node renderers, Python archive validation and bounded search, existing schema-2 gallery.

## Design choices

- Expanded random search alone has weak evidence; use the same 25,728 starting examples and investigate missing perceptual structure.
- Large pretrained embeddings add domain/compute uncertainty. Defer them until an explicit lightweight feature ablation is measured.
- Add fine envelope/event structure, short-window onset behavior and subband texture modulation/correlations. Compare sounds, not absolute smoothness; genuine impacts must remain valid.
- Keep fixed hyperparameters rather than repeatedly tuning on the same ratings. All normalizers fit training folds only. Synthetic round-trip success is reported separately from real-reference likeness and does not establish generalization.

## Tasks

- [x] Add `tools/multisynth/perceptual.py` and `tools/tests/test_multisynth_perceptual.py`. API: `describe(wave)` -> finite float32 vector with exact auditory-v1 prefix, `DIM`, `VERSION`, `EXTRA_BLOCKS`, and `extra_components(target, candidates)` -> ordered raw differences. Test gain/onset invariance, invalid/silent rejection, directional event/sweep sensitivity, sensitivity to extra gaps/events, and texture-seed tolerance against differing modulation. Temporal statistics must not erase all event order.
- [x] Add `tools/multisynth/train_perceptual.py` and tests. Reuse validated v4 training-pair identities, compute new components from archived PCM, fit fixed regularized simplex weights. Compare v5 and refitted old features in identical five reference-group folds; report frozen v4 only as a historical comparator on overlapping development data. Persist complete labels/folds/scales/hashes. Model API `PerceptualMetric.load`, `.distances`, `.components` over extended descriptors. Refitting must never overwrite v4 checkpoint.
- [x] Add a deterministic compatible library-cache builder and validation tests. Replay every old row with the recorded DSP/seed; retain row order, record failures explicitly, reject source/feature/library mismatches, save under a fresh path. Do not change pinned renderers or catalogue source. Verify subset exact base-descriptor replay before building all rows.
- [x] Add the v5 run wrapper and a descriptor callback to bounded refinement, with old behavior as default. Equal retrieval-start/proposal budgets for v4/v5, both choose from a shared pool; immutable historical audio provides a third baseline. Frozen references are known development examples, explicitly labelled. Export only distinct audition audio; complete provenance and replay checks.
- [x] Generate a balanced synthetic coverage benchmark across all 22 active engines, using held-out random seeds and explicit separation of sampled targets from the retrieval bank. Include preset-family exclusion for a stricter subset if feasible. Report synth identity recovery as secondary; compare reconstruction descriptors and runtime, disclose that objective scores are not human likeness. Do not train from synthetic preference guesses.
- [x] Run fixed feature ablation and 18 tagged references selected before seeing v5 scores (alternating rows of the frozen 36-reference manifest, ensuring bird feedback is included). If validation does not improve, label v5 experimental and retain v4 as incumbent. Include previous best audio for meaningful human comparison; do not resubmit an unchanged-only row for another rating.
- [x] Obtain spec and code-quality review, verify all saved clips/feedback import, archive reports/models/docs, commit, and expose new gallery on localhost and the existing LAN server.

## Fixed evaluation policy

New feature family receives 30% of the prior, old 20 components 70% using the original fixed v4 prior. KL regularization .08, temperature 4, 800 Adam steps at .03; fold seed1729. Refitted old-feature ablation uses existing v4 training unchanged. No post-result hyperparameter sweep. Global train/test grouping is exact reference PCM; related takes remain a stated limitation. Synthetic benchmark is a separate diagnostic, so it cannot dominate human labels or inflate real-sound evaluation. No default CLI promotion based solely on cross-validation.

## Comparison refinement after fixed validation

The old-feature refit scored75/103 held-out pairs, v5 scored72/103. Preserve both and give them identical full-data training labels for generated-output comparison: save the old-feature refit separately as `preference-v5-refit.json`; never overwrite frozen `preference-v4.json`. The historical best card retains incumbent audio. No hyperparameters change; both search objectives keep equal proposal budgets. This avoids a training-data confound while collecting new evidence about event/texture features.

## Completion evidence

82 Python tests and 12 renderer/feedback JavaScript tests pass. The completed tagged gallery has 18 references, 34 previously unrated recreations and 18 exact historical baselines; all 52 candidates replay exactly. Its rating controls persist independently and its JSON imported successfully into a temporary archive, never training. Both localhost and existing LAN endpoints return HTTP 200.

The separate 88-target/22-engine synthetic run completed all three conditions with 25,152 proposals and exact replay of all 1,144 target/before/after clips. Both experiment code/model hashes are verified. Results remain experimental: grouped v5 validation 72/103 versus old-feature refit 75/103, with unrestricted synthetic auditory means nearly tied. Keep this isolated research branch and worktree for continued feedback; preserve the parallel Claude branch.
