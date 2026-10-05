# Rendered finite-difference implementation plan

**Goal:** Separate forward-surrogate gradient error from local objective failure.

**Architecture:** Fixed eight-case diagnostic, existing exact DSP and normalized feature loss, immutable retained perturbations. No new training or deployed inference behavior.

**Tech stack:** Python, NumPy, PyTorch, existing renderer.

- [x] Test a scalar finite-difference slope helper against a quadratic and clipped-boundary displacement; reject zero/nonfinite displacements.
- [x] Implement the helper in `tools/neural_invert/rendered_gradient.py` and verify focused tests: five pass after observed missing-module failure.
- [x] Implement `tools/multisynth/evaluations/rendered-gradient-v1.py`; bind retained report/checkpoint/source hashes, freeze eight cases before renders, retain every finite-difference and step WAV, keep discrete controls and RNG unchanged, and write complete=false until terminal success.
- [x] Run once to a fresh directory. Recompute summaries and inspect whether actual descent works, plus pitch regressions and reversed-direction evidence. Audit verifies 264 candidate files/losses and all 24 final DSP replays. Bounded review finds no important issue. Mixed directions and no mean MatchObjective gain from rendered descent; no training promotion.
