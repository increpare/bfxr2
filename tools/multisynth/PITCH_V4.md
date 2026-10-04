# Pitch-input ablation, 2026-10-05

This run tests whether correcting a demonstrated pitch-input failure improves
actual synth recreation. It is not yet a quality result. The latest human
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

## Execution (in progress)

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

Validation so far: 73 descriptor tests, 33 replay/training/loader tests, and three
actual-render evaluation tests passed. Full dataset completion, 90-epoch fits,
24 development probes and the new listening export are still pending.

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
