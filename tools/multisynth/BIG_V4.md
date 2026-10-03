# Large reproduction run: preference-v4

This iteration returns to multi-synth sound reproduction. It retrains from every
retained listening session, expands the candidate bank, performs controlled
parameter search, and compares new audio with earlier baselines. It is not a
preset-curation exercise. The deliverable is `runs/big-v4/index.html`.

## Research and design

The earlier gesture representation compressed timbre to ten time-averaged
bands and spectral movement to a centroid trajectory. That can erase important
differences between two evolving sounds. Preference-v4 keeps all eight original
auditory components and all nine gesture components, then adds three full-band
spectral comparisons pooled over 4, 8 and 16 time bins. Pooling tolerates some
small timing displacement while retaining spectral evolution and event order.
Absolute envelope, duration and pitch information remain available.

This is temporal pooling of a single-window descriptor, **not multi-resolution
STFT**. [DDSP, section 4.2.1](https://arxiv.org/html/2001.04643v1) motivates using
multiple actual FFT resolutions, including log and linear magnitude, but its
synthesis results do not validate a game-SFX similarity metric. A future short
window descriptor could better resolve attacks below the existing 46 ms window.
It requires a versioned feature/cache rebuild and an independent listening test.

Unrestricted time warping was avoided because it can explain away different
event structures. [Müller's DTW material](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C3/C3S2_DTWvariants.html)
describes the purpose of global/local path constraints. No DTW is implemented
in this run. Likewise, neural embeddings are not assumed to be a ready-made
solution: [Tian et al. (2025)](https://arxiv.org/html/2507.07764v1) found that
embedding layer/statistics choices matter in instrument-timbre comparisons and
that transfer from speech-distortion metrics can be weak. Those findings are
not direct evidence about short game effects. A later embedding experiment
should use the same grouped feedback benchmark before displacing this model.

Additional psychoacoustic and environmental-sound research is recorded in
[PERCEPTUAL_RESEARCH.md](PERCEPTUAL_RESEARCH.md). Its proposed attack, modulation
and embedding benchmarks are future experiments, not features claimed for v4.

## Retraining and validation

`preference.py` fits nonnegative weights over 20 components using a pairwise
logistic objective and fixed KL regularization. Component scales are learned
from training rows only. Every exact reference PCM group has equal total loss
weight; repeated sessions and multiple pairs from one reference cannot dominate
by simple row count. Rating gaps are used only for their direction, respecting
the ordinal scale. Usefulness is never substituted for likeness.

All three archives contributed 145 candidate likeness judgments. There are 67
strict within-session preference pairs over 30 exact reference PCM groups;
44 tied comparisons remain archived but do not enter the strict pair loss.
The dataset also contains 24 separate usefulness labels, unused in this fit.
Cross-session judgments are not directly compared, and candidate audio aliases
are deduplicated within a session. Raw feedback and audio checksums are verified.

Five grouped folds, fixed before evaluation:

| Distance | Correct strict pairs | Pair accuracy | Reference-balanced accuracy |
| --- | ---: | ---: | ---: |
| Original auditory-v1 | 50/67 | 74.6% | 77.7% |
| Retrained preference-v4, held out | 49/67 | 73.1% | 74.8% |
| Fixed gesture prior | 45/67 | 67.2% | See training report |

There is **no demonstrated validation win** for the retrained model. It remains
an experimental A/B candidate. The final checkpoint is fitted to all 67 pairs;
its in-sample score is not presented as evidence of generalization. The historical
fitted gesture model was trained on part of the archives, so its reported score
is only a historical comparator. Related takes or differently encoded versions
may still cross exact-PCM groups. None of these saved-finalist comparisons proves
that optimizing a new sound will make it audibly closer.

Checkpoint: `models/preference-v4.json`. Complete folds, held-out predictions,
hyperparameters, labels and archive hashes: `evaluations/preference-v4-training.json`.

## Candidate generation and comparison

The original library contributes 7,296 candidates across 22 synth engines. The
frozen Soundboard snapshot at `db9f5f8a8bf50b951b44a163dd6685222bfae859`
contributes 18,432 candidates: 96 deterministic draws per 192 catalogue entries,
with zero rejected renders/descriptors. The explicitly reference-fitted coin
recipe remains excluded. The separate branch still points to that same revision.
The combined bank contains **25,728 candidates** with distinct DSP provenance.

Both distances rank the full bank without category tags. Each selects eight
starting recipe signatures. Both then receive the same 64-proposal budget per
start, and both choose their final result from the same jointly generated pool.
On a previously rated reference, up to two earlier candidates are included as
human-informed seeds for each objective. Those references are explicitly marked
as development examples; this is not autonomous generalization to an unseen
reference. Repeated baseline judgments use the latest rating of each identical
audio, then choose the highest-rated candidate. Original observations are never
rewritten.

Refinement keeps synth/recipe identity, wave types, explicit event counts,
melody/phrase text, random seeds, transition curve choices and layer alignment.
It changes eligible continuous controls inside bounded regions around each
starting candidate. Nested layer controls are read from the frozen engines.
Balance and small relative offsets can change in layered sounds. Continuous DSP
controls can still alter emergent event behavior; freezing explicit structure
is not a guarantee of perceptual similarity. Each objective retains its best
incumbent, and its refinement trace must never worsen numerically.

All 36 categories in the frozen tagged manifest are included, without filtering
by scores: **18 previously rated references and 18 with no exact archived audio
overlap**. Previously rated originals are replayed from the immutable archive.
For a new reference, the original auditory-v1 matcher and its original library
provide a baseline (five requested experts, plus Bfxr when needed, 64 proposals
per engine). The old baseline has a smaller candidate/search budget; the expanded
original-distance column separates some of that search improvement from the
learned ranking, but the whole comparison is not an equal-compute old/new test.

The page asks for **likeness of gesture, movement, texture and overall feel**.
Usefulness is optional and separate. It shows:

- Retrained match.
- Expanded original model, using the original distance on the new shared pool.
- Previous best, or Original matcher on a new reference.

If choices have identical audition bytes, they share one card. No additional
rating is requested for a duplicate. The existing schema-2 archive format keeps
parameters, source identity, precise audio, candidate roles and feedback.

## Reproduction

Prepare the pinned snapshot as documented in `COVERAGE_V3.md`, then run from the
repository root using the tools Python environment:

```sh
PYTHONPATH=tools python -m multisynth.preference \
  tools/multisynth/listening_data/2026-10-03-real-v1 \
  tools/multisynth/listening_data/2026-10-03-tagged-v2 \
  tools/multisynth/listening_data/2026-10-03-coverage-v3 \
  --output tools/multisynth/models/preference-v4.json \
  --report tools/multisynth/evaluations/preference-v4-training.json
PYTHONPATH=tools python -m multisynth.soundboard \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --output tools/multisynth/runs/soundboard-library-v4 --takes 96 --jobs 4
PYTHONPATH=tools python -m multisynth.big_run \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --library tools/multisynth/runs/library-v2 \
  --baseline-library tools/multisynth/runs/library-v1 \
  --board-library tools/multisynth/runs/soundboard-library-v4 \
  --targets tools/multisynth/evaluations/tagged-v2-targets.json \
  --model tools/multisynth/models/preference-v4.json \
  --archives tools/multisynth/listening_data/2026-10-03-real-v1 tools/multisynth/listening_data/2026-10-03-tagged-v2 tools/multisynth/listening_data/2026-10-03-coverage-v3 \
  --output tools/multisynth/runs/big-v4 --jobs 4 --budget 64 \
  --learned-starts 8 --auditory-starts 8
```

Choose new output paths for a new experiment; do not overwrite rated galleries
or trained checkpoints. Model/descriptor/library hashes and search/metric code
hashes are recorded in the run. The commit containing this run also preserves
imported feature extraction and baseline search dependencies. The metadata field
`refinementRenders` counts proposed refinements only, excluding initial renders,
export replays and the separate original matcher baseline.

## Completed run and verification

The run completed all 36 references in 1,074.45 seconds using four workers.
It produced 103 audition cards: the two new selectors chose identical audio
on five references, which is displayed once. There were 41,472 refinement
proposals; three were rejected during the Bfxr explosion recipe search for
reference 021, with the incumbent retained. Exception reasons were not logged
separately. Library construction had zero rejections.

Independent fresh rendering reproduced every one of the 103 audition clips
exactly at PCM16. Historical baselines matched their archived audio, every
search trace retained a non-worsening incumbent, and the saved model/search/
metric fingerprints matched the executing code. The focused suite passed
56 Python tests and 12 JavaScript tests. Browser checks verified independent
likeness/usefulness ratings, reload persistence, the copy-success notification,
playback, and an exported JSON round-trip into a temporary archive. Test ratings
were cleared; no synthetic feedback was added to the real training archives.

Full parameters, traces and run provenance: `evaluations/big-v4-results.json`.
Replay hashes and verification summary: `evaluations/big-v4-verification.json`.
The listening page is `runs/big-v4/index.html`, experiment
`140d89d3331adb085c93a93a2bd2e72943145c89329088d0ebcf14b3827ee8f2`.
Its perceptual verdict is pending human ratings.
