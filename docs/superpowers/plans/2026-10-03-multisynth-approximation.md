# Multi-synth approximation implementation plan

> Execute autonomously with the subagent-driven-development and verification skills. Reuse this isolated worktree. Do not alter the parallel checkout.

**Goal:** Deliver a working multi-synth inverse retrieval model, perceptual optimization and an evaluated listening collection.
**Architecture:** Shared deterministic renderer → sampled preset library → audio retrieval → per-synth refinement → automatic selector → editable exports.
**Tech stack:** Existing JavaScript DSP, Node VM/worker, Python/numpy/torch/soundfile.

- [x] Renderer adapter: add tools/render/multisynth_context.js and multisynth_worker.js, plus tests/multisynth-render.test.js. Expose inventory with normalized parameter metadata, recipes and source hash. NDJSON commands inventory/sample/render return JSON; render returns base64 little-endian float32 and canonical applied params. Verify deterministic noise, distinct seeds, errors, all supported synths and replay.
- [x] Model and perceptual representation: add tools/multisynth/{renderer,features,library}.py and tests/test_multisynth.py. Test identity, gain invariance, pitch/sweep and transient ranking, silence rejection, serialization/retrieval. Store versioned compact descriptors and parameters, not the target corpus.
- [x] Experts and selector: add tools/multisynth/search.py. Retrieve per-synth seeds; mutate normalized controls and categorical choices; optimize the best several synths and Bfxr using identical budgets; retain each incumbent. Test bounds, deterministic search, budget accounting and monotonic best score.
- [x] CLI/export/evaluation: add tools/multisynth/{cli,report}.py. Commands build, match, benchmark; recursive deterministic source-balanced target selection, target hashes, JSON, WAV and app-compatible .bcol. Test export and reload. Build a useful library and benchmark diverse real targets, reporting measured results and limits.
- [x] Review and verification: independently review correctness and scientific claims; run relevant Node/Python suites; save results and reproducible commands in tools/multisynth/README.md. Keep generated data under ignored tools/multisynth/runs/. Commit the finished side project on codex/multisynth-approximation.

## Outcome

Completed first baseline and 40-target evaluation. Added independent legacy-metric and held-out noise-seed audits. Results and limitations: `tools/multisynth/RESULTS.md`. The implementation remains in this isolated branch. The inherited Mixr catalog test fails identically at the pristine starting revision; browser synth code was not changed.
