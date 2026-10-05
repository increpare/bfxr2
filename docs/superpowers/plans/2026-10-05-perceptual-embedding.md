# Perceptual embedding diagnostic plan

**Goal:** Test an independent frozen audio representation against durable human evidence.
**Architecture:** Exact-audio archive -> provenance-connected source families -> frozen encoder cache -> identical grouped comparisons.
**Tech stack:** Python, PyTorch, Transformers 4.57.1, LAION CLAP.

- [x] Archive latest five trials and verify exact-audio review (8 pairs, 7 adequacy labels).
- [x] Inspect primary research and freeze design before computing new representation scores.
- [x] Test family union across differently named transformed references and duplicated PCM; fail on nonfinite/overlength encoder inputs.
- [x] Implement isolated extractor and grouped diagnostic under `tools/multisynth/embedding.py`; cache in ignored runs, retain protocol and report under evaluations.
- [x] Download official immutable weights; verify model loading, deterministic extraction, and input preservation.
- [x] Run all 14 archives. Fit current and augmented features on identical five family folds; keep scales strictly train-only and report per-family/overall outcomes.
- [x] Review code and provenance, document result, and only advance to a new listening pilot if the predeclared screen passes.

No production selector or inverse model changes in this diagnostic. Existing
models and old gallery bytes stay frozen. Autonomous execution is authorized by
the standing user instruction; no additional design-approval interruption.
