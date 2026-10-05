# Confidence-conditioned gradient diagnostic plan

> Execute inline using superpowers:executing-plans. Ongoing autonomous research
> authorization covers routine experiment design and execution.

**Goal:** Establish whether unreliable pitch terms explain the observed harmful
local optimization directions before selecting a new training loss.

**Architecture:** One private evaluation script reuses frozen coordinate renders
and the frozen forward checkpoint. An audit verifies new DSP steps and summaries.
No runtime or training behavior changes.

**Tech stack:** Python, NumPy, PyTorch, existing shipped DSP renderer.

- [x] Verify source/model hashes and the three-unreliable/five-reliable split.
- [x] Implement the experiment in `tools/multisynth/evaluations/confidence-gradient-v1.py`.
      Reduce remaining group losses with `sum(groups[k] for k in kept)/len(kept)`;
      preserve the original total and gradient verbatim on reliable targets.
      Use `slope` with actual canonical displacement for rendered secants.
      Assert old autograd gradients reproduce before computing masked gradients.
- [x] Run once into fresh `runs/confidence-gradient-v1`, retaining every outcome.
- [x] Audit exact DSP/audio/loss replay, categories, direction construction,
      reliable-case identity and aggregate results; retain a compact tracked report.
- [x] Document the result, its post-hoc scope and the next justified action;
      run `git diff --check`, inspect changes and commit.
