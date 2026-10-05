# Native coverage v1

The expanded Transfxr model learns useful additional coverage, but **does not pass its replacement/listening gate**. Human status remains zero convincing recreations on the previous five-reference batch. Numerical improvements below are not likeness labels.

The old corpus had only 2,048 native examples among 12,288 rows. Added 32,768 native draws with preset/sparse/broad mutations. Original rows and splits remain byte-exact; new control groups use a stable split. Training native pool grows from 1,730 to 29,557, structured pool stays 8,715. No parameter, audio, or packed-feature identity overlaps between train and holdout. Shared preset families limit generalization claims.

Both arms start at the same frozen v3 checkpoint, train 4,000 updates with equal 64-native/64-structured batches, and select using unchanged original validation including step zero. Control selects step zero; expanded selects step 4,000. Original native validation acoustic error falls 1.05995→0.68846 and fresh native error 1.03064→0.69855. Structured error remains near 0.08. CPU checkpoint replay agrees with saved validation within 5.6e-8.

Actual-DSP evaluation uses four raw proposals per arm:

| Set | Old mean distance | Expanded | Outcome |
|---|---:|---:|---|
| Original validation, 32 | 3.45840 | 3.06184 | Aggregate gate passes; one individual direction loss |
| Development probes, 10 | 2.61385 | 2.19513 | Moving contour coverage regresses .527→.229 |
| New native controls, 32 | 6.04588 | 5.49343 | Direction matches regress 15→14; three individual losses |

The render audit verifies all 888 candidate file/PCM hashes, replays and rescores all 222 selected renders with zero score error, and recomputes summaries/gates from retained pitch diagnostics. It does not independently estimate pitch. Data builder independently replays 64 sampled new rows, not all generated audio.

Five private raw proposals on the rejected real references show one substantial distance reduction for Select Beep, smaller changes elsewhere, and no improvement for charm2 or the heavy bell. No new gallery was published from these raw results.

Retain the model as a possible complementary proposal source. `coverage-selection-v1` is a separate inference experiment with additional held-out controls, old-eight render-budget comparison and fixed-baseline pitch safeguards. It cannot retroactively pass this failed replacement gate.

Artifacts: `runs/native-coverage-v1/{data,models,evaluation,real-proposals}`. Tracked audit scripts/results are `evaluations/native-coverage-v1-{data,training,render}-audit.{py,json}`. Models, exact audio and full reports remain in the retained run directory.

## Equal-budget real-reference refinement

Both Transfxr experts received 384 local trials from their best of four raw proposals, with matching seeds per reference. The expanded expert beats the old expert only on charm2 after search:

| Repeated reference | Old refined | Expanded refined |
|---|---:|---:|
| charm2 | 6.10692 | 4.68659 |
| battleStart | 3.88112 | 4.08909 |
| Select Beep | 1.38322 | 4.75641 |
| heavy bell | 4.40430 | 6.77013 |
| descending whistle | 0.72816 | 1.03945 |

Raw proposal gains therefore do not uniformly transfer through search. charm2 remains worse by distance than its previously heard Bfxr candidate (3.53718). No new real-reference gallery is justified by this result alone. Historical gallery comparisons have different compute budgets and may describe pre-audition float PCM; they do not isolate model quality.

Review caught an interpretation error in the private `real-refined/results.json`: its final selection compares against the refined control candidate, while its embedded POLICY description names the raw old-four baseline. The local refinement guard is also the older, different pitch guard. **That private selected field does not establish the coverage-selection policy's raw-baseline safeguards.** Executed source and report remain unchanged for reproducibility.

The separate `evaluations/native-coverage-v1-real-audit.json` corrects selection by retaining all eight raw proposals and both refined candidates, then comparing each against the fixed raw old-four winner. It verifies all 50 exact candidate DSP replays/rescores with zero error and identifies the original selection's raw-baseline regressions for battleStart and Select Beep. Corrected selections are expanded for charm2/battleStart/Select Beep, old for bell/whistle. These descriptor safeguards still cannot certify human likeness and can reject lower-distance alternatives.
