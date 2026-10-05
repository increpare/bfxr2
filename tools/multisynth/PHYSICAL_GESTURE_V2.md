# Physical pitch-gesture supervision: not promoted

Two Transfxr experts started from the same frozen v3 flat checkpoint, using
identical examples, normalization, minibatches and 20 additional epochs. One
retained acoustic parameter supervision; the other added expected pitch-trajectory
error across discrete pitch/vibrato curve alternatives. The trajectory uses the
synth's frequency and transition equations, omitting smoothing, filtering, echo
and waveform-dependent perception. It is a control-domain loss, not an audible
likeness metric.

The final epoch was predeclared for both arms. Actual DSP comparison used four
raw candidates per arm and source-engine target, without search:

| Set | Control mean distance | Gesture mean distance | Frozen v3 |
| --- | ---: | ---: | ---: |
| 32 development validation targets | 3.43694 | 3.64417 | 3.45840 |
| 10 existing development probes | 2.31853 | 2.48962 | 2.61385 |

The treatment worsened primary mean distance by 6.03%. Static median pitch,
reliable pitch and voiced-span direction pass counts were unchanged against its
matched control. Moving contour coverage improved .3947→.4099 on validation but
regressed .3428→.2996 on probes. It failed promotion; no listening gallery follows.
These reused targets are development evidence, not independent generalization.

The [render audit](evaluations/gesture-v2-render-audit.json) verified all 504
candidate WAVs and independently replayed/rescored 126 selected candidates with
zero score discrepancy. It recomputed summaries from retained pitch diagnostics,
not from independently estimated pitch. It also exposes per-case regressions;
none lost a previously passing static median or voiced-span direction here.

The [training audit](evaluations/gesture-v2-training-audit.json) loaded final
weights and exactly reproduced both full validation losses on the training GPU.
CPU gesture losses differ by at most 1.43e-5: CPU and MPS quadrature round one
discontinuous Steps sample on opposite sides of a boundary. This small known
device difference is reported, not hidden by loosening the replay tolerance.
Actual inference and render evaluation run on CPU consistently for all arms.

An earlier completed pair with 64 trajectory samples is retained under
`runs/gesture-v1` with its original source, and was never evaluated or promoted.
Review caught vibrato aliasing at a valid long duration. The repaired run uses
256 samples, with a regression test against the analytic mean-square vibrato
value. Strict loading also verifies inherited base-model and dataset bindings.

Models, histories, full controls and FLOAT candidate WAVs remain under
`runs/gesture-v2`. Continued fine-tuning still shows a large training/validation
gap (acoustic error about .07 versus .59). Expanding native sound coverage is
the next test; lowering this training loss further is not evidence of progress.
