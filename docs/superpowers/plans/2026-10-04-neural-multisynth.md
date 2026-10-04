# Learned multisynth inversion implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for the
> independent implementation and review stages. User authorization is autonomous.

**Goal:** Train and evaluate actual audio-to-control experts for all active numeric
synths, preserving the original Bfxr expert and preparing Mixr composition.

**Architecture:** Shared whole-sound audio encoder with separate instrument heads;
generator and discrete classification plus global continuous control prediction.
Render predictions and refine/select through the established auditory matcher.

**Tech stack:** PyTorch, NumPy, persistent Node DSP workers, soundfile, existing
matcher and immutable listening gallery exports.

## Task 1 — Data, schemas, model, training and inference

Create `tools/neural_invert/{__init__,schema,features,data,model,train,predict}.py`
and `tools/tests/test_neural_invert.py`. Write and run failing behavioural tests
for categorical roundtrip, variable per-engine controls, waveform sensitivity
after 0.4 seconds, separate expert heads, split duplicate exclusion, checkpoint
validation and predictions entering full numeric ranges. Implement those APIs,
run the tests, then run a small real-render/train/load/predict smoke experiment.

Data command: `python -m neural_invert.data --output PATH --per-synth 2048 --jobs 4`.
Training command: `python -m neural_invert.train --data PATH --output PATH --epochs 30`.
Predict exposes `load_model(path)` and `predict(model, metadata, wave, renderer,
per_synth=2)`, returning canonical `{synth, params, seed, provenance}` candidates
for every trained engine; generated non-numeric structure is identified.
Keep heavy model/data artifacts under ignored multisynth runs directories.

## Task 2 — Preserve the original expert and evaluate reconstruction

Create `tools/neural_invert/evaluate.py` and meaningful tests. Load the preserved
`v7_real_ft/best.pt` through existing invert APIs and optimize using the existing
StagedOptimizer. Record checkpoint hash and flags. Generate fresh balanced
synthetic targets and tagged development comparisons. Evaluate all neural experts
with raw predictions, top-candidate refinement, and original Bfxr, recording actual
budgets and renderer failures. Do not import the new gallery into training.

## Task 3 — Execute training and evaluation

- [ ] Generate balanced data with DSP and feature provenance.
- [ ] Train the model, save validation history and best checkpoint.
- [ ] Run independent synthetic reconstruction checks and tonal pitch probes.
- [ ] Produce a tagged listening batch with neural, original Bfxr and previous
      best audio, preserving independent ratings through export_coverage.
- [ ] Review implementation for spec compliance and then correctness.
- [ ] Verify result reproduction, gallery audio and JSON export.
- [ ] Save reports, commands and limitations; commit verified code and reports.

## Task 4 — Continue toward composition

Use measured reconstruction failures to choose the next training change. Mixr
pairing depends on competent individual inverses; arbitrary mixture inversion
requires its own labelled two-source dataset and validation. Do not silently
substitute preset curation for this work.
