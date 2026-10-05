# Fine onset inverse experiment

User authorizes autonomous experiment choices and execution. Work inline.

1. Test feature invariants before implementing onset extraction: gain invariance,
   no time stretching, finite silence, fixed-time short-event separation.
2. Build immutable derived onset arrays from exact existing source rows; validate
   source file and DSP hashes, preserve split membership and waveform hashes.
3. Implement matched control/treatment model and train with existing acoustic
   loss and split-balanced weights. Keep original modules unchanged. Record
   data/feature/code bindings and checkpoint selection. Test onset masking,
   output shapes, finite gradients and a tiny end-to-end training/load roundtrip.
4. Train the two paired arms for Bfxr/Transfxr. Save complete histories and selected
   checkpoints. Verify held-out validation loss by loading saved weights.
5. Compare real DSP renders on fixed validation rows and existing probes with
   equal four-proposal budgets. Write outcomes even if the experiment fails.
6. If the predeclared gate passes, prepare a short new listening batch with exact
   earlier baselines. Otherwise investigate measured failure and keep working.

## Execution checkpoint

- Fine-onset feature invariants, onset masking, finite gradients, best-epoch
  save/reload, exact DSP replay and missing-output/pitch gate checks pass.
- Focused plus unchanged temporal-model suite: 45 tests passed. A subsequent
  focused run after removing an unused import: 6 tests passed.
- Frozen lists: `evaluations/onset-v1-targets.json` (64 validation examples) and
  `evaluations/onset-v1-probe-targets.json` (20 existing development probes,
  with exact controls excluded from every original train/validation row).
- Serial data replay was deliberately interrupted for throughput, confirmed
  terminal, and retained incomplete with its matching source snapshot. Its
  partial arrays are never used for training.
- Replacement `runs/onset-v1/data-parallel` replays four independent chunks at
  once, preserving exact row positions and hashes. All 12,288 Bfxr rows passed
  exact PCM checks; Transfxr replay is in progress at this checkpoint.
- One-shot runner `runs/onset-v1/run.py` waits for the verified live data process,
  then trains 90 epochs per arm per engine on MPS, then evaluates both frozen
  lists. It fails explicitly on a dead data job or any training/evaluation error;
  it never automatically restarts an existing run. `job.json` and training logs
  are live status, not evidence of completion or audible improvement.
- Actual renders, checkpoint validation replay and human quality review remain
  outstanding. Do not claim the hypothesis is supported until results exist.
