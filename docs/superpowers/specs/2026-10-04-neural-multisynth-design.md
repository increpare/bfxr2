# Learned multisynth inversion

The user approved autonomous implementation of experts for the synths followed
by automatic selection. This replaces the retrieval-only direction as the main
development path. Preserve all listening archives and earlier experiments.

## Architecture

Train an audio encoder and instrument-specific parameter heads on audio rendered
by the actual shipped DSP. Each expert predicts a generator/category and numeric
controls, with explicit discrete-control classification. A generator supplies
non-numeric structure only; numeric predictions cover their declared global
ranges rather than a small preset neighbourhood. Pitch, octave and categorical
choices must be learnable. Non-numeric editable scores remain a declared scope
limit for the initial experiment. Existing Bfxr v7 real-finetuned inference and
its original optimizer remain a separately evaluated expert.

All active numeric individual synths participate. One shared encoder with separate
heads is preferred over separately training 22 complete encoders because it
shares acoustic evidence while allowing differing parameter schemas. Render and
score proposals from each expert, then refine the strongest candidates using the
established contour-based matcher. Always retain the original Bfxr result as a
candidate and a separately labelled baseline. Never equate a lower model score
with better human likeness.

Mixr contains two other synths and their complete saved controls. It is a
composition layer rather than an easier inverse problem. The initial system
learns its individual sources; its candidates can later be paired through Mixr.
Do not claim arbitrary two-source separation has been trained.

## Data and validation

Generate balanced fresh data across engines and generators, mixing original
generator draws, sparse global control changes, and broader changes. Retain
canonical rendered controls, engine identity, generator identity, all randomness,
DSP hashes and packed feature hashes. Do not use user-rated target audio for
supervised synthetic parameter labels. Support resumable per-engine data files.

Features retain whole-sound temporal and pitch information beyond the earlier
inverse pack's approximately 0.37-second prefix. Normalize inputs using training
statistics. Exclude exact canonical parameter duplicates across train/validation
and record splits. Evaluate fresh render seeds and parameter draws separately
from training validation. Generator-family generalization remains a separate
test; do not imply random parameter holdout proves it.

Report known-engine reconstruction, automatic engine selection, raw predictions,
refinement, and the original Bfxr expert. Use actual rendered audio, pitch checks
on reliable tonal probes, and tagged reference comparisons with independent
ratings and copyable JSON. Training loss alone is insufficient evidence.

## Deliverable

Provide reproducible dataset/training/inference commands, a trained first model,
held-out reconstruction results, and a listening page with explicit original
Bfxr comparisons. Describe limitations and measured failures candidly. The first
model is a working foundation for further training rather than a claim that the
long-term quality goal is achieved.
