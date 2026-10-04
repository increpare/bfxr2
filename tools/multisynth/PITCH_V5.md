# Pitch-v5: major periodic peaks, 2026-10-05

In progress. This is a controlled follow-up to the rejected v4 input experiment,
not a claim of improved human likeness. The v4 full dataset, three trained models,
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

## Controlled follow-up

The planned replay keeps the same 75,776 rows, 22-engine normalization population,
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
```

The v5 data/training adaptation passed 40 fixture tests, including both directions
of v4/v5 dataset, resume and checkpoint rejection. Independent spec review ran
six focused compatibility tests; quality review confirmed the controlled version
changes and unchanged frozen dependencies. Full replay is in progress. The v5
training/listening audit scripts are prepared but have not yet run on production
artifacts; no production v5 checkpoint or listening page is claimed complete.

The three-arm evaluator and five-target gallery passed independent specification
and quality reviews. The final focused suite passed 21 tests; 35 combined v4/v5
evaluation/gallery tests also passed. Diagnostics retain full relative-time
contours and missing voicing, with direction explicitly limited to the observed
voiced span. Historical PCM and both charm2 anchors remain exact. These checks
verify the experiment tooling, not the quality of a trained v5 model.
