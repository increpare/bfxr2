# Native mixture implementation plan

Use executing-plans inline in this isolated worktree under standing autonomy.

- [x] Test `expand_expert` for exact head-zero/encoder preservation, seeded
      distinct heads, unchanged donor and finite gradients through mixture loss.
      Test validation statistics with hand-computed energies and row weights.
- [x] Add `tools/neural_invert/coverage_mixture.py`: initialization, validation,
      matched training, strict checkpoint loader, CLI. Preserve frozen modules.
      Reuse verified expanded dataset and sampler; bind data/checkpoint/code hashes.
- [x] Run 4,000 updates per arm in a fresh native-mixture-v1 run. Inspect
      learning curves and head utilization before interpreting the outcome.
- [x] Add experiment evaluator for retained transfer targets and 32 additional
      validation control groups. Freeze list before inference; exclude previously
      evaluated controls. Save four exact proposals per arm and descriptor checks.
- [x] Audit selected DSP replay and score, summarize real/native/altered scopes
      separately. Prepare a new six-item gallery only if candidates justify it.
- [x] Verify new questionnaire and audio delivery without entering human ratings;
      commit tooling/reports, retain immutable run files and request quality check.

Evidence: 47 focused tests pass. Audit verifies 1,586 saved audio files, 366
selected DSP replays/rescores with zero error, exact ordered target membership,
prior transfer PCM/candidate bindings and CPU validation within 4.3e-8.
HTTP confirms HTML/results/all 18 audition WAV hashes. Browser shows 0/6 with
ready A/B and playback controls; no assistant playback or judgments were entered.
Review fixes: missing comparator summaries now report paired counts, audit binds
the frozen target list, and listener text does not reveal expected outcomes.
Experiment complete; model quality remains awaiting the six listening judgments.
