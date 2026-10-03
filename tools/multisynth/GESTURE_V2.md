# Second listening iteration: gesture and feel

The first ratings showed poor absolute likeness (mean 2/5). This iteration
changes the representation and candidate search; audible improvement still
requires the next listening pass.

## Model

`gesture.py` transforms the saved auditory-v1 features into nine comparison
components: envelope shape at multiple scales, attack/release timing, pulse
structure, centered spectral movement, pooled timbre, texture, centered pitch
movement, pitch register and duration. Pitch register and duration have small
prior weights, so retuning or modest stretching need not outweigh event shape.
It preserves the original feature extractor and library format: old experiments
remain reproducible. Existing descriptors contain only 32 relative-time frames,
so fast rattles and fine temporal details may still be undersampled.

Controlled tests check that upward gestures resemble modestly retuned or
stretched upward gestures more than downward ones; retuned impacts resemble
impacts more than swells; bursts resemble retuned bursts more than sustained
tones. These tests encode useful hypotheses, not perceptual validation.

## Fitting experiment and decision

The archived feedback contains 73 distinct rated candidates on 40 references,
but only 19 strict selected-vs-Bfxr preferences. We fit nine nonnegative weights
using pairwise logistic loss, shrunk toward the fixed gesture prior. Rating gaps
provide heuristic confidence weights; they are not calibrated distances. Ties
and absolute ratings remain in the archive but are not strict preference labels.

Five-fold validation groups by reference audition PCM; each prediction uses
weights fitted without that reference. This prevents exact-reference leakage,
not related-take leakage. The small sample and restricted old finalists make
these results highly provisional.

| Selector | Correct strict preferences, out of 19 |
| --- | ---: |
| Original auditory-v1 | 15 |
| Fixed gesture prior | 15 |
| Fitted gesture weights, held-out predictions | 14 |
| Fitted weights, evaluated on training pairs | 15 |

**The fitted weights are not promoted.** The listening batch uses the fixed
gesture prior. Both checkpoints are retained under `models/`: `gesture-v2.json`
contains the fitting report and per-reference held-out predictions;
`gesture-v2-prior.json` contains the active weights and decision. This is a new
representation/search experiment, not evidence that weight retraining helped.

## Listening comparison

Use 18 preselected tags from the frozen 36-tag manifest: attack, bell, carbeep,
card, chains, click, collect, door, explode, hit, jump, laser, magic, power_up,
shoot, slime, step and sword. Selection precedes the search and is not filtered
by winner score. One horn reference overlaps the first rated set; it is marked
as development overlap. Other files are not certified independent audio families.

- Previous model: original 3,648-example library, auditory-v1, five experts plus
  Bfxr if needed, 64 mutations per expert.
- New model: 7,296-example library, gesture prior, eight experts plus Bfxr if
  needed, 96 mutations per expert. Previous finalists are replayed and re-scored
  as additional seeds. A promising previous result therefore remains available.
- Bfxr card: the new run's Bfxr expert, using the gesture objective and expanded
  library. It can differ from the old run's Bfxr result; all old finalists are
  saved in the run's `previous/` directory.

This changes library coverage, compute and distance together. It tests whether
the overall iteration helps, not an equal-compute causal ablation. The gallery
shows reference/new/previous/Bfxr, supports independent ratings and notes, and
shares a rating only for identical synth/parameters/seed identities. Numeric
distances are hidden on these comparison cards because old/new values are not
comparable. Exact candidate identities and model provenance accompany feedback.

## Reproduce from tools/

```sh
uv run python -m multisynth.train_gesture \
  multisynth/listening_data/2026-10-03-real-v1 \
  --output multisynth/models/gesture-v2.json
uv run python -m multisynth.cli build \
  -o multisynth/runs/library-v2 --per-preset 32 --jobs 4
uv run python -m multisynth.iterate \
  --targets multisynth/evaluations/tagged-v2-targets.json \
  --library multisynth/runs/library-v2 \
  --previous-library multisynth/runs/library-v1 \
  --model multisynth/models/gesture-v2-prior.json \
  --output multisynth/runs/tagged-v2 --jobs 3
```

The iteration refuses to overwrite an existing output directory, checks frozen
reference file hashes, and validates library/DSP fingerprints. Use a new output
path for another run. The copied `model.json`, manifest, per-target reports and
editable `.bcol` files preserve the exact experiment. Feed the new exported
ratings into `multisynth.listening` for durable archival before further tuning.

## Completed batch and checks

The 18-target batch took **551.3 seconds** with three workers, after building
the expanded library. New matching used **14,362 renders**, including carried
seeds and final exports; the previous-model comparison used **6,695 renders**.
Seventeen selected parameter/seed identities changed. The known horn reference
still retains its old Clonkr winner, an unresolved development failure given
the earlier preference for Bfxr. Nothing here establishes a human likeness gain.

The gallery is `runs/tagged-v2/index.html`. A versioned copy of every result,
parameter snapshot, comparison score and run metadata is retained in
[evaluations/tagged-v2-results.json](evaluations/tagged-v2-results.json).

Verification: **26 focused Python tests and 9 Node tests passed**. All 72 gallery
audio references resolve to valid, finite mono WAVs; six new/previous presets
were re-rendered and matched the audition PCM exactly. Browser testing confirmed
independent 2/4/3 ratings, their JSON export and persistence through reload;
test ratings were cleared afterward. The existing real-v1 listening archive
also passed an idempotent import/PCM verification with the updated importer.

The next ratings can train preferences across new, previous and Bfxr candidates.
The fitter deduplicates shared candidates and keeps every pair from a reference
in the same validation fold.
