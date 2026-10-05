# Coverage selection implementation plan

**Goal:** Test whether expanded inverse proposals complement the frozen expert.

**Architecture:** Pure fixed-baseline selection policy, immutable candidate archives, actual-DSP evaluation on frozen new controls. Preserve all previous experiments.

**Tech stack:** Python, NumPy, PyTorch, existing JavaScript DSP renderer.

- [x] Archive native coverage results and verify retained renders with `native-coverage-v1-render-audit.py`.
- [x] Add `tools/tests/test_coverage_selection.py`; verify loss of direction, contour coverage, paired support and static register are rejected, unreliable-target fallback works, missing/nonfinite proposals cannot win, and the best allowed candidate wins independently of ordering.
- [x] Run the focused tests with the established external virtualenv; verify missing implementation failure. Implement `tools/neural_invert/coverage_selection.py`, then rerun: eight selection tests plus three coverage tests pass.
- [x] Add `tools/multisynth/evaluations/coverage-selection-v1.py`. Freeze seed-20261027 targets before inference, prove group exclusion, retain every rendered candidate and exact hashes, report retrospective/fresh sets separately and old-eight budget comparison.
- [x] Run the evaluator once to a fresh directory. Inspect outcomes and verify selected files and policy invariants; request bounded code review. Audit complete, numerical gate passes. Real-reference refinement warranted and launched privately; no likeness or replacement promotion.
