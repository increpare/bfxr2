# Listener metric implementation plan

**Goal:** Retain latest feedback and test whether human-calibrated ranking improves source/tag-held-out preference prediction.
**Architecture:** A separately versioned21-component distance combines frozen auditory/gesture features and soft-periodicity. All original inverse models and scorers remain unchanged.
**Tech stack:** Python/NumPy/Torch, existing immutable PCM archives and Mixr/native renderers.

- [ ] Validate and archive pair-inverse-v1 feedback, replay current scorer outputs, retain12strict pairs and candidate-scoped adequacy; document zero trained wins.
- [ ] Write failing tests for source/tag group union, native exclusion, train-only scales, lower-distance preference sign, strict metric save/load policies. Implement tools/multisynth/listener_metric.py and tools/tests/test_listener_metric.py.
- [ ] Freeze archives, script/dependency hashes and fixed recipe; extract exact candidate component vectors and soft scores once per reference/candidate PCM. Preserve provenance and all exclusions. Five connected-group folds; no test normalization.
- [ ] Fit/evaluate fixed recipe, save complete fold predictions and conditional full-data experimental model. Apply predeclared gate without tuning on outcomes.
- [ ] If supported, prepare eight new tagged external comparisons using existing native inverse proposals and equal-budget actual-DSP fitting under old/new scorers. Keep original Bfxr where supported, exact render replay, immutable protocol, immediate adequacy, HTTP hashes. If gate fails, inspect held-out errors before deciding the next experiment.
- [ ] Update evidence, limitations and docs, verify applicable tests and native/audio bindings, commit own files only.

Use existing research worktree. No production synth edits or replacement of baseline checkpoints. Changes to frozen experiment code require a distinct run/version, never rewriting historical provenance.
