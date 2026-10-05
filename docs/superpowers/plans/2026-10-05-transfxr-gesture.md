# Transfxr gesture supervision implementation plan

Execute inline. Goal: train a controlled pair using physical pitch-gesture loss,
then evaluate actual DSP before any human listening request.

1. Test the eight curve equations at fixed values, static and rising/falling
   trajectories, expected discrete loss versus cancelling averages, and finite
   useful gradients to pitch controls and curve logits.
2. Implement isolated `neural_invert/gesture.py`, leaving strict checkpoint-bound
   temporal/feature modules unchanged. Curve order comes from the synth schema.
   Compute each pitch/vibrato curve pair, its squared octave error, then its
   probability-weighted expectation.
3. Implement `neural_invert/gesture_train.py`. Load frozen v3 Transfxr checkpoint,
   retain original normalization and split weights; copy initial state per arm.
   Train 20 epochs at .0001 using seed 20261019 and batch 128. Save histories,
   fixed final checkpoint, source hashes, initial weights hash and loss recipe.
4. Validate output gradients and checkpoint roundtrip, then run both arms on MPS.
   Reproduce final validation losses from saved weights before promotion.
5. Evaluate actual DSP on frozen 32 validation/10 probe references with equal
   four-proposal budgets and original v3 baseline. Save every candidate FLOAT WAV,
   controls, source/checkpoint hashes, pitch and gesture diagnostics. Apply the
   predeclared gate and retain failure evidence as well as improvements.

Completed: the initial 64-point pair is retained invalid due to vibrato aliasing;
the repaired 256-point pair completed 20 epochs each and both render lists.
Seven focused tests pass. Saved validation losses reproduce exactly on MPS;
the small CPU stepped-curve boundary discrepancy is explicitly diagnosed.
Render audit verifies 504 candidate files and 126 selected replays/rescores.
Neither gate passes: primary distance worsens and probe contour coverage drops.
No human listening request follows. See `tools/multisynth/GESTURE_V2.md`.
