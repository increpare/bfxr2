# Learned event timing pilot

**Goal:** Train and evaluate a small native-sequence timing model before using it to split external sounds for synthesis.

**Architecture:** A separate fully convolutional onset predictor operates on a fixed 24-band log spectrum plus amplitude at256 frames (5.8ms hop). It predicts only interior event starts; the first source starts at zero. Existing inverse synth-control experts remain frozen. Training labels come from actual Stackr schedules, never human-selected approximations.

**Motivation:** Stackr coin won as similar against both prior audio and the simultaneous ablation. The other three earlier clips won. That single local improvement motivates a timing pilot, not replacing every whole-sound model. The prior bell's new very-close label describes unchanged PCM.

## Frozen policy

Source bank: eight engines Bfxr, Transfxr, Boomr, Pluckr, Rustlr, Crittr, Clonkr, Squishr from certified synthetic data. Canonicalize actual Stackr source controls with fixed seed.5. Retain short non-silent60–400ms sources with first8%-peak sample before15ms. Canonical source-control hash determines50/25/25 train/validation/test; exclude duplicate exact source PCM across splits. Target16/8/8 components per engine. Insufficient coverage is a reported data failure, not silently reduced coverage.

Generate1536/384/384 actual native Stackr sequences, balanced1/2/3 layers. Components never cross splits; source/preset families can overlap. Sources start at0 and then uniform80–300ms increments, have gains.2–.9 and native Stackr pitch shifts±6semitones. First layer starts at zero; interior starts are exact known control labels. No real recordings or feedback patches enter this dataset. Audio is peak-normalized for analysis only. Feature horizon is1.486s and oversized sources are rejected; no time resizing.

Model:25-to32 projection and four32-channel temporal convolutions, kernel3, dilation1/2/4/8, GELU, final1-channel output. Fixed seed20261104; AdamWlr.001,weight decay.0001,40epochs,batch64,gradient norm5. Training-only positive weight10, soft Gaussian onset targets of one frame standard deviation. Validation BCE chooses the checkpoint. No test-based checkpoint, threshold or architecture adjustment.

Decode sigmoid peaks>=.5, within60ms of neither edge, greedily retain at most2 peaks separated by60ms. Evaluate interior-onset precision/recall/F1 within25ms and exact count accuracy. Compare to frozen waveform splitter on the same component-disjoint test set. Also evaluate4-bit quantization and1500Hz low-pass inputs without retraining; schedule labels stay fixed, these are timing diagnostics, not human similarity assumptions.

Gate for external use: native onset F1>=.75 and at least.10 above the old splitter, native count accuracy>=.75, and each degraded-set F1 no lower than the old splitter. If it fails, retain checkpoint/evidence but do not feed it into the listening pipeline or call the model improved.

## Work checklist

1. Archive and audit the four submitted judgments, with exact PCM and contextual labels.
2. Test feature timing/gain behavior, label/decoder rules, finite gradients and serialization before implementation.
3. Generate frozen native data with source controls and PCM hashes checked across splits; save hashes before training.
4. Train the fixed40epoch model, reload/reproduce validation, evaluate untouched native/degraded test rows once.
5. Independently verify split isolation, metric summaries, gate and checkpoint identity. Document the result honestly.
6. If the gate passes, compare learned and heuristic boundaries on external inputs with exact earlier anchors; otherwise keep the current splitter and use any further listening to assess existing Stackr transfer, not the failed model.

## Pre-training bank correction

Riftr did not supply the required short, promptly audible validation/test components. The failed bank, original script and plan are retained in `runs/event-timing-v1-bank-rejected-01`, with a tracked receipt. No sequence generation or training occurred. Replace Riftr with the percussive Tappr engine before freezing the successful bank; all quantities, split rules, duration/latency requirements, training recipe and gates remain unchanged.

The attempted Tappr substitution stopped before processing: Tappr is outside the certified22-engine dataset. After checking the available metadata, the final eighth engine is Squishr (398 short parent candidates). The second preflight receipt retains this correction; no model training or test inspection preceded it.
