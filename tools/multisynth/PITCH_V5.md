# Pitch-v5: major periodic peaks, 2026-10-05

Completed and not promoted. This controlled follow-up fixes the demonstrated
input defect but regresses overall as an inverse model. The v4 full dataset, three trained models,
24-probe results and two partial listening outputs are retained. That batch was
not published or presented for rating after an actual-waveform defect was found.

## Input change

V4's earliest strong autocorrelation peak could be a small ripple inside the
initial positive lobe. With a strong 100 Hz sine plus a weak 2 kHz partial, it
reported roughly 2.3 kHz. Actual Bfxr and Transfxr Whistle examples reproduced the
failure. Excluding only the initial lobe still left near-period ripple errors.
V5 discards that first lobe and keeps the strongest interpolated peak per later
positive lobe before applying the same strength threshold. All other feature
columns are copied byte-for-byte from the frozen descriptor.

This adapts peak selection from [McLeod and Wyvill, 2005, section 5](https://www.cs.otago.ac.nz/graphics/Geoff/tartini/papers/A_Smarter_Way_to_Find_Pitch.pdf).
Our window-corrected autocorrelation is not their full normalized difference
method. Physical periodicity is only one cue to perceived pitch and sound identity;
the spectral evidence stays intact, and human ears remain necessary even when
metrics agree.

Both independent descriptor reviews passed. The 73 frozen v4 tests and 145 v5
tests pass. The new tests include weak distant partials, exact archived actual
synth renders, low/high frequencies, missing fundamentals, noise, gain, motion,
short sounds, padding and capped long-sound schedules. A separate 276-render
actual-synth sweep found no v4-passing cases that failed the stated v5 diagnostic;
13 whistle cases improved. Existing noisy/inharmonic/rapid-decay limitations
remain. The approximate 55–8,000 Hz range is not an out-of-band classifier, and
rapid motion and interpolated voicing transitions are still imperfect.

Descriptor computation is roughly 24–33% slower than v4 in these local checks.
Broader synthetic diagnostics and actual waveform sweeps are saved with code,
DSP, audio and control identities under `evaluations/pitch-v5-*`.

## Actual model outcome

All 864 candidate renders across 24 probes and three arms were saved and audited;
there are no missing candidates or selections. On the 20 ordinary development
probes, unrestricted mean distance worsens from v3's 1.435681 to 1.864569, with
only 5/20 improvements. V5-diagnostic voiced-span direction agreement falls from
6/8 to 3/8; moving contour error rises from 0.981 to 1.427 semitones and span
error from 1.311 to 4.500. Source-engine distance also regresses, 1.747741 to
2.369570. These are one-seed development results, not generalization estimates.

On four high-pitch probes, distance improves 4/4 (unrestricted mean 7.522992 to
6.422091), but only one selected median is within a semitone. That candidate
matches only 55.3% of target-active frames within a semitone. Three targets have
no reliably estimated close-median candidate anywhere in the twelve-proposal
pool. The input correction alone has not solved high-register inversion.

Independent results review confirmed the figures and hash bindings. The frozen
v3 experts remain the working baseline. No v5 listening gallery was generated or
presented for rating. A separate bounded actual-render calibration component on
the frozen v3 experts subsequently passed its predeclared 24-probe gate; see
[evidence](evaluations/pitch-calibration-audit.json). High-register eligibility
reached 4/4 and mean distance fell 7.523→0.651; ordinary mean distance rose 3.39%,
with no previously passing pitch/direction cases lost. One pluck substitution
substantially worsens distance despite satisfying pitch coverage, so human
listening must assess that tradeoff. This is hybrid inference, not a v5 training
win. The prepared v5 gallery code remains tooling, not listening evidence.

## Controlled follow-up

The completed replay keeps the same 75,776 rows, 22-engine normalization population,
labels, splits and source DSP. Train the same Bfxr four-mode temporal, Transfxr
one-mode flat and Pluckr one-mode temporal networks for 90 epochs with the same
seed and recipe. Preserve v3/v4/v5 artifacts separately. Compare actual renders
on the same 20+4 development probes, with full-contour and candidate-pool checks
in addition to median pitch and aggregate distance. These are development probes,
not independent generalization evidence.

Only request another short listening session after reviewing actual tagged outputs.
Retain the latest human winners, both separately heard charm2 anchors, exact
historical PCM and the liked cached-WebAudio best/tie/none interface. A relative
winner does not imply that a recreation is convincing.

## Commands and execution

Runtime: `/Users/stephenlavelle/Documents/bfxr2/tools/.venv/bin/python`, with
`PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/bfxr-mpl`.

```sh
python -m neural_invert.pitch_v5_data --source tools/multisynth/runs/temporal-v3/data --output tools/multisynth/runs/pitch-v5/data --jobs 8
python -m neural_invert.pitch_v5_temporal --data tools/multisynth/runs/pitch-v5/data --output tools/multisynth/runs/pitch-v5/bfxr-four --engines Bfxr --modes 4 --encoder-kind temporal --device mps
python -m neural_invert.pitch_v5_temporal --data tools/multisynth/runs/pitch-v5/data --output tools/multisynth/runs/pitch-v5/trans-flat --engines Transfxr --modes 1 --encoder-kind flat --device cpu
python -m neural_invert.pitch_v5_temporal --data tools/multisynth/runs/pitch-v5/data --output tools/multisynth/runs/pitch-v5/pluck-one --engines Pluckr --modes 1 --encoder-kind temporal --device mps
```

The training commands require a completed dataset and fresh output directories.
Defaults are 90 epochs, batch size 128, seed 20261009 and one CPU thread. The two
MPS jobs run sequentially; Transfxr CPU training can overlap. The `experts/`
assembly binds the three selected checkpoint/report hashes before any benchmark.
The production training audit verifies unchanged rows/columns/splits and recomputes
losses over all 5,529 selected-model validation rows on CPU.

The v5 data/training adaptation passed 40 fixture tests, including both directions
of v4/v5 dataset, resume and checkpoint rejection. Independent spec review ran
six focused compatibility tests; quality review confirmed the controlled version
changes and unchanged frozen dependencies. Full replay and all three 90-epoch
training runs are complete. The production training audit passed: unchanged
nonpitch columns/labels/splits across all rows, 198 exact actual-DSP/feature
replays, matched architectures/recipes/seeds and all 5,529 validation rows
recomputed on CPU. Maximum reported/recomputed loss difference was 1.08e-8.
The production listening audit has not yet run; no listening page is complete.

Dataset manifest SHA-256:
`94c84af68ce3d851954d097060d7df3b57bc40b8e0b2d4b365c23d710c0b8f9a`.

| Expert | Best epoch | Validation control loss |
| --- | ---: | ---: |
| Bfxr, four-mode temporal | 15 | 0.405219 |
| Transfxr, one-mode flat | 15 | 0.579234 |
| Pluckr, one-mode temporal | 12 | 0.251310 |

These losses are not perceptual quality scores. Checkpoint identities and full
validation evidence are retained in `evaluations/pitch-v5-training-audit.json`.
The corrected coverage heuristic finds very few stable upper-register examples;
the intended structured nominal pitch range remains capped around 1.6 kHz for
Bfxr/Transfxr and 880 Hz for Pluckr. Descriptor coverage counts are estimates,
not independently established fundamentals. Expanding the training distribution
would be a separate experiment.

The three-arm evaluator and five-target gallery passed independent specification
and quality reviews. The final focused suite passed 21 tests; 35 combined v4/v5
evaluation/gallery tests also passed. Diagnostics retain full relative-time
contours and missing voicing, with direction explicitly limited to the observed
voiced span. Historical PCM and both charm2 anchors remain exact. These checks
verify the experiment tooling, not the quality of a trained v5 model.
