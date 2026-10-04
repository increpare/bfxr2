# Pitch-input ablation, 2026-10-05

This run is rejected as an upgrade: actual-render distance regressed overall,
and actual Whistle waveforms exposed a further input-estimator defect. The latest human
feedback qualifies book-close and charm2 as partial matches; both remain off.
Historical audio, judgments and the earlier Transfxr charm2 anchor stay intact.

## Scope

The separately versioned descriptor replaces only 160 pitch/voicing coordinates
of the frozen 4,083-dimensional input. Spectra, envelope, duration and gain
coordinates stay byte-identical. Native-rate autocorrelation uses Hann-weighted
DC removal, fourfold band-limited interpolation, window correction, endpoint
neighbours and fractional peaks. Harmonic-rich upper-register regression tests
caught and fixed octave errors that a sine-only sweep missed.

Committed input diagnostics bind the exact descriptor code. Across the archived
55–8,000 Hz pure-tone sweep, worst median error is 0.0134 semitone; across 315
non-aliasing harmonic cases it is 0.0213 semitone. Twenty white-noise cases are
unvoiced. These synthetic checks do not establish human likeness. Rapid low
chirps, finite-window boundary effects, out-of-range subharmonics and interpolation
across unvoiced transitions remain documented limitations.

All 75,776 existing examples from 22 synths are replayed with their original
controls and seeds, requiring exact canonical parameters, audio hash and sample
count. Re-extraction preserves labels, grouped train/validation splits, row order
and all non-pitch feature bytes. All 22 engines remain the train-only normalization
population. This does not train 22 new inverse experts: the controlled comparison
re-trains Bfxr four-mode temporal, Transfxr one-mode flat and Pluckr one-mode
temporal networks, matching the selected v3 architectures, seed and 90-epoch recipe.

The old structured Bfxr/Transfxr draws cover nominal 80–1,600 Hz. The four high
probes are outside that structured range, although native examples supply some
upper-register coverage. Correcting input alone may not resolve this data gap.

## Execution and result

Python is `/Users/stephenlavelle/Documents/bfxr2/tools/.venv/bin/python`, with
`PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/bfxr-mpl`.

```sh
python -m neural_invert.pitch_data \
  --source tools/multisynth/runs/temporal-v3/data \
  --output tools/multisynth/runs/pitch-v4/data --jobs 6
```

The initial three-worker run was intentionally stopped and resumed with six
workers to improve CPU use. Completed Footsteppr output is validated and retained;
uncommitted engine work is regenerated. Worker count is not a feature or sampling
change. No old training data or models are modified.

The full 75,776-row replay completed with all 22 engines and a validated complete
manifest. Validation: 73 descriptor tests, 33 replay/training/loader tests, three
actual-render evaluation tests and 11 listening generator tests passed. All three
90-epoch fits and 24 development probes completed. The listening export was
stopped before delivery after a new actual-waveform pitch failure was confirmed.

## Intended checks

The comparison keeps the numerical objective unchanged and renders four proposals
from each of three experts. It reports source-engine diagnostic selection and
unrestricted routing separately, with all missing/failed slots. Scores are not
human ratings, and the fixed development probes are not independent validation.
The training audit recomputes every held-out row on CPU and checks architecture,
recipe, seed, source data and unchanged normalization coordinates.

Five listening references were fixed before training: bird, charm2, spinout,
book-close and Egg Jump. They include qualified partial successes, regressions
and unjudged coverage; human review is required even when numerical measures agree.
The existing quick cached-WebAudio interface and best/tie/none choices are retained.

The old diagnostic can accept a 5 kHz Transfxr candidate for a 2.5 kHz target
because it halves the candidate frequency. An actual-DSP regression now covers
this case. Reports retain the old metric for comparison and separately count
corrected-tracker passes, agreement between both trackers, disagreement, and
unreliable corrected estimates. Neither tracker is independent human validation.

Matched training commands (same default seed 20261009, batch 128, 90 epochs):

```sh
python -m neural_invert.pitch_temporal --data tools/multisynth/runs/pitch-v4/data --output tools/multisynth/runs/pitch-v4/bfxr-four --engines Bfxr --modes 4 --encoder-kind temporal --device mps
python -m neural_invert.pitch_temporal --data tools/multisynth/runs/pitch-v4/data --output tools/multisynth/runs/pitch-v4/trans-flat --engines Transfxr --modes 1 --encoder-kind flat --device cpu
python -m neural_invert.pitch_temporal --data tools/multisynth/runs/pitch-v4/data --output tools/multisynth/runs/pitch-v4/pluck-one --engines Pluckr --modes 1 --encoder-kind temporal --device mps
```

## Outcome: retain as a failed controlled experiment

All checkpoint audits pass: all 5,529 validation rows were recomputed on CPU,
with maximum loss discrepancy 3.46e-8. Best checkpoint epochs are Bfxr13,
Transfxr23 and Pluckr20. Data identity and training integrity do not establish
sound quality.

On the 20 development probes, unrestricted mean distance worsens from 1.43568
to 1.70542, with only 7/20 improvements. Static median pitch within one semitone
drops from 8/9 to 7/9. The unchanged older diagnostic reports moving direction rising from 7/8 to 8/8, but mean contour
error worsens from 0.871 to 1.212 semitones and excursion error from 1.276 to 1.908.
The defective v4 tracker reports two high-register median passes,
15.74/17.37-semitone spans and 9.5%/8% of active frames within tolerance. These
are compromised estimator outputs, not established physical pitch or instability. Neither establishes
a successful recreation. Both are Bfxr outputs, not high-register Transfxr success.

A coverage diagnostic found very few apparently stable high-pitch native Transfxr
examples. Inspection of structured examples then exposed an input defect:
a strong low fundamental plus a weak distant overtone creates short-lag ripples
inside the initial positive autocorrelation lobe, and v4 can report one of those
as pitch. Actual Bfxr2059 and Transfxr2066 reproduce this with dominant FFT peaks
near167/336Hz but tracked pitch around3573/6859Hz. This also invalidates a naive
interpretation of the coverage counts as true fundamental-frequency coverage.
The passing sine and nearby-harmonic tests were insufficient.

The partial listening run retains completed bird and charm2 outputs and exact
historical anchors, but is deliberately incomplete and unpublished. No new human
labels are requested or inferred. Next experiment is separately versioned v5,
with regressions for actual Whistle waveforms and weak distant partials.

Reproduction and retained evidence:
- `evaluations/pitch-v4-training-audit.py` / `.json`: full data preservation,
  198 actual row spot-replays, exact architecture/recipe and validation checks.
- `evaluations/pitch-v4-comparison.py` / `.json`: 20+4 probes, both routing modes,
  full-contour diagnostics, candidate coverage, file hashes and code bindings.
- `evaluations/pitch-v4-coverage.py` / `.json`: explicitly heuristic realized
  input coverage, including row indices for follow-up.
- `evaluations/pitch-v4-overtone-failure.py` / `.json`: 15 deterministic known
  tones and two exact actual-synth failures.

McLeod and Wyvill's [2005 peak-picking method](https://www.cs.otago.ac.nz/graphics/Geoff/tartini/papers/A_Smarter_Way_to_Find_Pitch.pdf), section5,
excludes the initial positive lobe and retains only the highest peak per later
positive lobe before threshold selection. That motivates a narrowly scoped
peak-selection test; adapting it to window-corrected autocorrelation does not
make our algorithm a full implementation of their normalized difference method.
