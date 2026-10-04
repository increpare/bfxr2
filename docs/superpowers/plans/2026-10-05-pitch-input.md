# Corrected pitch input implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Isolate and measure the effect of repairing pitch input on three actual-synth inverse experts.

**Architecture:** Separately versioned pitch descriptor, bound re-extraction of the frozen dataset, and new trainer/loader using unchanged temporal-v3 networks and loss. Evaluation retains real DSP outputs and historical human baselines.

**Tech Stack:** Python, NumPy, PyTorch, existing native multisynth Renderer, pytest, WebAudio gallery.

## Task 1: Pitch descriptor

Files: create `tools/neural_invert/pitch_features.py`, `tools/tests/test_neural_pitch_features.py`.

- [x] Write failing tests: parameterize sine frequencies 65,110,220,440,880,1500,2000,2200,2500,3200,4000,6000,7500; require interior median error below 0.5 semitone and adequate voiced coverage. Test white noise rejection, harmonic fundamental, opposite glides, zero audio, invalid arrays, gain invariance and exact untouched feature channels.
- [x] Run `PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 /Users/stephenlavelle/Documents/bfxr2/tools/.venv/bin/python -m pytest tools/tests/test_neural_pitch_features.py -q`; confirm absence of new module fails.
- [x] Implement `describe(wave)` returning float32 4083 values. Begin with `result = frozen.describe(wave)`; assign only slices `3888:3984` and `4016:4080`. Export VERSION, DIM, CONFIG, FEATURE_HASH, FEATURE_CODE_HASH and bound FROZEN_FEATURE_CODE_HASH. Expose a small `pitch_track(wave, positions)` helper for diagnostic tests. Reject invalid input before processing. Preserve silence behavior.
- [x] Run focused tests and archive clean-tone/noise/glide diagnostics; measure representative extraction time. Spec review, then quality review; fix findings before freezing the code for data generation.

## Task 2: Frozen-data re-extraction and strict training

Files: create `tools/neural_invert/pitch_data.py`, `tools/neural_invert/pitch_temporal.py`, `tools/tests/test_neural_pitch_training.py`.

- [x] Test that altered original audio identity, feature columns, labels/splits, code hashes and resumed configuration are rejected; train a tiny fixture and verify loader rejects incomplete reports, modified normalization and checkpoint mismatch. Keep tests focused on provenance and train/inference agreement.
- [x] Implement `reextract(source, output, jobs=3)` with per-engine atomic output, original manifest/file verification, exact DSP replay, unchanged labels/splits, new row feature identities, all-engine normalization and no retained audio cache. CLI: `python -m neural_invert.pitch_data --source tools/multisynth/runs/temporal-v3/data --output tools/multisynth/runs/pitch-v4/data --jobs 3`.
- [x] Implement new training/loading/inference entry points matching temporal.py signatures while using the new features. Import immutable TemporalExpert, acoustic_energy, mixture_loss and proposal helpers; do not monkeypatch or edit old modules. Bind imported code and feature dependencies; validate source and output datasets plus complete training reports. Reuse 90 epochs, batch128, seed20261009, AdamW0.001/cosine/clip5, native/structured weights and train-only all-engine normalization.
- [x] Run focused tests, spec review, then quality review. Generate full data, independently verify all labels/splits and untouched columns, then freeze modules and run three matched training jobs (Bfxr4-temporal, Transfxr1-flat, Pluckr1-temporal). Save exact commands and results.

## Task 3: Actual render comparison and listening checkpoint

Files: create `tools/neural_invert/pitch_eval.py`, a versioned listening generator if needed, and `tools/multisynth/evaluations/pitch-v4-*.json` plus reproducible scripts. Create `tools/multisynth/PITCH_V4.md`.

- [x] Load all checkpoints through strict loaders; independently recompute held-out control loss. Compare 20 known development and four high-pitch probes with four proposals per each of three engines. Preserve controls, seeds, failed attempts, actual audio hashes and both source-engine/unrestricted summaries.
- [x] Audit gains/regressions before choosing real targets; if no material progress, diagnose further autonomously rather than demand another tiring human batch.
- [ ] Produce approximately five comparisons when useful, retaining exact old audition PCM and a fresh feedback experiment identity. Include human partial-success anchors and failures/consensus; avoid inferring that unauditioned charm2 alternatives were defeated.
- [ ] Verify page assets and feedback identity, candidate DSP replay, exact historical PCM, and regular autoplay/restart behavior without touching user ratings. Review final results independently, update experiment notes/plan and commit only relevant files (leave .DS_Store alone). Deliver usable listening link and a concise feedback request.

Outcome: v4 is not promoted. Full 20+4 probes regress overall; actual Whistle
waveforms expose an initial-lobe overtone tracking defect. Gallery stopped before
delivery, completed outputs retained. Continue with 2026-10-05-pitch-initial-lobe.md
before requesting further listening.
