# Gestures, texture, and synth coverage (v5)

This iteration tests whether short-window event and texture cues improve
multi-synth recreation. It retains v4 as the listening incumbent: the extended
model has **not** improved held-out prediction of the existing preferences.
The goal remains recognizable, evocative game SFX, with usefulness/fun judged
separately from resemblance to a reference.

## What is trained

The learned model is a 30-component nonnegative similarity scorer. Inversion
uses rendered-example retrieval and bounded parameter refinement across all
22 eligible single-synth engines and a pinned Soundboard catalogue. It is not
an all-synth neural parameter predictor. The older neural inverse in
`tools/invert/` remains Bfxr-only; its mixed sampling modes are different ways
of drawing Bfxr parameters, not examples from several synths.

All four immutable human-feedback archives contribute likeness labels. Useful
or fun ratings remain separate. The data contain 248 likeness judgments and
127 usefulness judgments, yielding 103 strict within-session preferences
across 43 exact-reference PCM groups. Ties do not become invented preferences.
Repeated judgments remain preserved with their original session identities.

The 22-engine diagnostic covers numeric single-synth search. Chattr text,
arbitrary Mixr sources and arbitrary Stackr compositions still need separate
inverse representations. Pinned Soundboard recipes/layers are eligible
reconstruction candidates, but this round does not use layered synthetic
targets.

Synthetic inversion targets are evaluated separately. They do not become
human preference labels and cannot dominate the training fit.

## Representation and fixed evaluation

`waveform-structure-v1` preserves the exact 1,475-float auditory-v1 prefix and
adds 815 values: fine relative/absolute envelopes, positive onset motion,
attack/energy timing, gap structure, repetition, subband envelopes, modulation
energy, cross-band correlation, and local texture fluctuations. Comparison is
reference-conditioned: a legitimate impact is not penalized merely for having
a sharp transient. Relative-time cues preserve event order, while pooled
statistics offer some tolerance to noise realization. This is an engineering
hypothesis informed by [the research notes](PERCEPTUAL_RESEARCH.md), not an
implementation or validation of a published psychoacoustic model.

The added families receive 30% of the fixed prior, with 70% on the old prior.
Temperature 4, KL regularization .08, scale floor .01, Adam .03 for 800 steps,
and five reference-grouped folds with seed 1729 were fixed before evaluation.
Feature scaling is fitted within each training fold. The old 20-component
model is independently refitted on the identical folds.

| Model | Correct strict held-out preferences | Reference-balanced accuracy |
| --- | ---: | ---: |
| Original auditory-v1 | 66 / 103 | 67.64% |
| Refitted old feature set | 75 / 103 | 75.16% |
| New event/texture feature set | 72 / 103 | 74.16% |

The full-data v5 fit gets 80/103 correct; that is a training diagnostic, not
held-out evidence. The frozen v4 model overlaps earlier training labels and
its historical score is not a fair held-out comparator. Complete pairs,
identities, folds, scales, weights, source hashes and limitations are saved in
`evaluations/perceptual-v5-training.json`. No results-driven hyperparameter
sweep was performed, and the CLI default is unchanged.

Related takes and differently normalized copies are not grouped together by
exact PCM identity. The sample is small and consists of earlier finalists;
it cannot establish how the objectives behave when optimized over new sounds.

## Listening comparison

The 18 references were frozen before viewing v5 scores: alternating rows,
starting at index 1, from the existing 36-reference tagged manifest. This
includes the bird example with unwanted clicks. All are known development
references, explicitly labelled as such. No filename/tag routes the search.

Both scorers are fitted to all four archives; the old-feature refit is saved
as `models/preference-v5-refit.json`, leaving the frozen v4 model unchanged.
Both the old-feature refit and v5 receive eight distinct recipe starts plus up to two identical
historically preferred seeds per reference, with 64 bounded proposals per
start. Both select from the union of proposals. Recipe identity, phrases,
random texture seeds and categorical controls remain fixed during refinement.
A third card replays the exact previously rated best PCM. Identical audio is
merged, and a row with only unchanged audio is omitted from renewed rating.
The run's proposal count excludes initial and final verification renders.

The new cache replays all 25,728 old library examples with their original
parameters and seeds. Every old descriptor prefix is checked within 1e-5;
changed DSP, feature code, incomplete caches and changed base libraries are
rejected. Thus library coverage is held fixed while comparing objectives.

## Reproduce

Use `PYTHONPATH=tools` and the project's Python environment. Commands run from
the repository root. Generated libraries/audio remain local under `runs/`;
models, experiment reports and retained feedback are versioned.

```sh
python -m multisynth.train_perceptual \
  tools/multisynth/listening_data/2026-10-03-real-v1 \
  tools/multisynth/listening_data/2026-10-03-tagged-v2 \
  tools/multisynth/listening_data/2026-10-03-coverage-v3 \
  tools/multisynth/listening_data/2026-10-04-big-v4 \
  --output tools/multisynth/models/perceptual-v5.json \
  --report tools/multisynth/evaluations/perceptual-v5-training.json

python -m multisynth.preference \
  tools/multisynth/listening_data/2026-10-03-real-v1 \
  tools/multisynth/listening_data/2026-10-03-tagged-v2 \
  tools/multisynth/listening_data/2026-10-03-coverage-v3 \
  tools/multisynth/listening_data/2026-10-04-big-v4 \
  --output tools/multisynth/models/preference-v5-refit.json \
  --report tools/multisynth/evaluations/preference-v5-refit-training.json

python -m multisynth.perceptual_library \
  --library tools/multisynth/runs/library-v2 \
  --output tools/multisynth/runs/perceptual-library-v5 --backend legacy --jobs 2
python -m multisynth.perceptual_library \
  --library tools/multisynth/runs/soundboard-library-v4 \
  --output tools/multisynth/runs/perceptual-board-v5 --backend board --jobs 2 \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8

python -m multisynth.iterate_perceptual \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --library tools/multisynth/runs/perceptual-library-v5 \
  --board-library tools/multisynth/runs/perceptual-board-v5 \
  --legacy-base tools/multisynth/runs/library-v2 \
  --board-base tools/multisynth/runs/soundboard-library-v4 \
  --targets tools/multisynth/evaluations/perceptual-v5-targets.json \
  --model tools/multisynth/models/perceptual-v5.json \
  --v4-model tools/multisynth/models/preference-v5-refit.json \
  --archives tools/multisynth/listening_data/2026-10-03-real-v1 \
    tools/multisynth/listening_data/2026-10-03-tagged-v2 \
    tools/multisynth/listening_data/2026-10-03-coverage-v3 \
    tools/multisynth/listening_data/2026-10-04-big-v4 \
  --output tools/multisynth/runs/perceptual-v5 --jobs 4 --starts 8 --budget 64
```

## Balanced synthetic inversion diagnostic

`multisynth.synthetic_benchmark` generates 88 targets: four per eligible engine.
Normally this is two sampled generators with two fresh parameter draws each;
Footsteppr exposes only one generator and receives four draws from it. Sampling
and rendering seeds use separate deterministic SHA-256 namespaces. Canonical
parameters are excluded against every library row and every Soundboard source
component, ignoring external rendering seed. Exact normalized audition PCM is
excluded against full library renders and earlier accepted targets. Standalone
PCM for each Soundboard component is not additionally rendered/checked.

Every target is searched in three conditions:

1. Known source engine, using that engine's single-synth examples.
2. Unrestricted, using the complete single-synth and Soundboard library.
3. Generator excluded, using only single-synth examples and removing that
   engine's matching generator label. This excludes Soundboard aliases by
   removing Soundboard entirely, but does not exclude every semantically
   equivalent generator under another name. Footsteppr has no source-engine
   generator remaining here, so its condition is cross-engine approximation.

Both objectives use the same proposal pool and up to two distinct recipe
starts each, with 24 proposals per start. Footsteppr's known-engine condition
has just one available generator/start per objective; actual starts and render
counts are recorded. These conditions have different candidate coverage and
are diagnostics, not equal-capacity generalization estimates.

The report includes pre/post retrieval/refinement scores, auditory-v1 distances,
source-engine selection and per-engine breakdowns. Auditory-v1 is a common
comparison metric, but shares features with both optimized scorers; it is not
an independent perceptual ground truth. Correct engine identity is secondary:
a different engine can recreate the same gesture convincingly. Source target
parameters never initialize the search, and no synthetic target or automatic
preference is added to human-model training.

```sh
python -m multisynth.synthetic_benchmark \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --library tools/multisynth/runs/perceptual-library-v5 \
  --board-library tools/multisynth/runs/perceptual-board-v5 \
  --legacy-base tools/multisynth/runs/library-v2 \
  --board-base tools/multisynth/runs/soundboard-library-v4 \
  --model tools/multisynth/models/perceptual-v5.json \
  --v4-model tools/multisynth/models/preference-v5-refit.json \
  --output tools/multisynth/runs/synthetic-v5 \
  --jobs 3 --starts 2 --budget 24 --leave-preset-out --save-audio
```

## Completed tagged run

The gallery is `runs/perceptual-v5/index.html`: 18 references, 52 distinct
candidate clips (34 previously unrated recreations plus 18 historical baselines),
23,040 refinement proposals, 610.96 seconds. There were no
rejected proposals or unchanged-only rows. All 52 clips reproduce byte-for-byte
from their saved parameters and seeds; scores replay within 1e-5. Exact
baseline PCM identities, monotonic traces and experiment identity were checked.

The experiment ID is
`d535274b6236a4207109679f950409e59f19fc1b630b1936e5d19f2c5c69e291`.
Complete parameters and traces are in `evaluations/perceptual-v5-results.json`;
replay checks are in `evaluations/perceptual-v5-verification.json`. Browser tests
confirmed independent ratings, reload persistence, JSON generation and successful
archive import in a temporary test directory. Test ratings were cleared and
never entered training. All 82 focused Python tests and 12 renderer/feedback
JavaScript tests pass. The full page has 70 audio players (18 references plus
52 candidates), starts with no test ratings, and is reachable on the existing
localhost and LAN servers.

## Completed synthetic run

All 88 targets across 22 engines completed in 1,309.23 seconds, with 25,152
refinement proposals and no rejected target draws or refinement proposals.
The full record is `evaluations/synthetic-v5-results.json`.

Mean common auditory-v1 distance before → after refinement (lower is better
under that descriptor, not a percentage of audible likeness):

| Condition | Old features, refitted | Event/texture model |
| --- | ---: | ---: |
| Known source engine | .4520 → .3477 | .4574 → .3524 |
| Unrestricted | .4250 → .3388 | .4198 → .3381 |
| Generator excluded, legacy only | .6402 → .5159 | .6384 → .5130 |

There is no clear overall advantage for the new representation. In unrestricted
search it has lower auditory-v1 distance on 26 targets, higher on 32, and ties
on 30. Knowing the engine does not improve the overall mean, but is helpful
for some targets: unrestricted v5 is lower on 42 and higher on 46. Conditions
also use different starts and search seeds, so that is not an isolated routing
ablation.

Unrestricted old-refit selects the exact source engine on 58/88 targets, and
v5 on 59/88. They select Soundboard on 26 and 28 respectively. Of those layers,
25 and 23 contain the source engine, making direct-or-layer source-engine
presence 83/88 and 82/88. These identities are diagnostic only; they do not
measure recreation quality. A different engine may produce an equivalent cue.

The generator-excluded condition is harder, but removes all Soundboard
candidates as well as the matching generator. Its increase in distance cannot
be attributed solely to generator exclusion or over-specialization. A future
legacy-only unrestricted control would isolate that comparison better.

The highest v5 unrestricted per-engine mean residuals are Glitchr (.942),
Zappr (.631), Footsteppr (.520), Crittr (.502), and Riftr (.490). Treat these as
places to inspect search/representation limitations, not reliable engine
rankings: there are only four targets per engine. One Glitchr randomize_params
target contributes a distance of 1.816. The 18-reference human listening batch
remains the deciding test of practical likeness and game usefulness.

All 1,144 synthetic target/before/after audition files reproduce exactly from
the recorded parameters and seeds. The audit rechecked target exclusions,
all condition scopes, score replay, summary aggregates, start/proposal counts,
monotonic traces and candidate PCM identity consistency. Full checks are saved
in `evaluations/synthetic-v5-verification.json`. No test labels were added to
training and no model was promoted on these synthetic scores.
