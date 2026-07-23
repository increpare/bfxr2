# Inverse Model: audio features → bfxr params

Date: 2026-07-23
Status: approved design, pre-implementation

## Goal

A neural model that predicts bfxr parameter settings from audio, used as a
smarter opening move for the existing wav→bfxr matcher. **v1 success bar:**
model-seeded search beats the current f0-heuristic seeding on the hard
targets in `tools/targets/` (flame, beam-out, mario jumps, …) at equal
budget. One-shot prediction quality (no search) is tracked as the growth
metric over time; it is not gated for v1. Browser shipping is out of scope
(a later distillation/port once the offline quality ceiling is known).

Decisions made during brainstorming:

- **Role:** seeder + refine, not one-shot replacement. A seeder model *is* a
  one-shot model; the gap between raw-prediction score and post-refine score
  measures progress toward one-shot.
- **Architecture order:** build the single-head baseline first (Option 1),
  then the wavetype-conditioned version (Option 2). Multi-hypothesis heads
  (Option 3) only if evaluation shows within-wavetype mode-averaging hurts.
- **Input representation:** perceptual contours alone are insufficient
  (centroid+noisiness cannot distinguish square from saw, cannot see duty
  cycle, flanger combs, or filter resonance). Model input = contours **and**
  blurred log-mel.
- No differentiation through the synth. Training data is generated, so true
  params are known; the synth stays a black box (the "flashcard printer").
  Real targets have no true params — the model projects them onto the
  nearest bfxr-reachable sound, judged by the perceptual metric, never by
  knob distance.

## Layout

New package `tools/invert/`, sibling of `match/`, importing its renderer,
feature extractor, and objective:

```
tools/invert/
  sampler.py    # param sampling for training data
  dataset.py    # generate + shard (features, params) pairs; gen_data CLI
  augment.py    # audio roughing-up (noise/reverb/EQ/level)
  model.py      # encoder + heads (v1 single-head, v2 per-wavetype)
  train.py      # training loop CLI
  predict.py    # checkpoint -> param guesses for a wav
  data/         # feature shards (gitignored)
  runs/         # checkpoints + training logs (gitignored)
```

## Dataset generation

- **Sampling** (`sampler.py`): the proven stage-0 recipe — each param takes
  its default with p=0.5, else uniform in range — plus ~20% fully-uniform
  examples for coverage. Envelope params projected with the same
  cap/projection logic as `optimizer.py` so labels live in the space search
  explores. Square-only params (`squareDuty`, `dutySweep`) pinned to
  defaults for non-square wavetypes, matching the optimizer.
- **Filtering:** reject near-silent renders (peak below threshold) and
  failed renders. Silence is unlearnable and never a good answer.
- **Rendering:** native worker pool (`bfxr_native`), fixed stored seed per
  example.
- **Scale:** 300k examples initially (~minutes to render; feature
  extraction dominates, ~1–2 h once). Stored as float16 shards of
  *features + unit-space params + wavetype + duration*, not raw audio —
  a few GB. Shards are cheap to regenerate when `features.py` changes;
  a dataset version tag ties shards to the feature-extractor revision.
- **Augmentation** (`augment.py`): for ~50% of examples, degrade the audio
  before feature extraction — noise floor, cheap reverb tail, EQ tilt,
  level jitter. Param labels unchanged. Teaches the model to squint past
  dirt that real recordings have and bfxr cannot reproduce.

## Model input

Fixed-size tensor per sound:

- 6 contour tracks from `match/features.py` (env_db, f0_log2, voiced,
  active, centroid_log2, noisiness), and
- the 64-band blurred log-mel scale from `match/objective.py`,

stacked on the channel axis, time axis padded/resampled to 128 frames,
**plus a scalar log-duration input** (time normalization would otherwise
hide exactly what the envelope knobs need). Unvoiced frames use the
existing fill+mask convention.

## Model + training

Small 1-D CNN over time (~1–2M params) → global pooling → heads:

- **v1 baseline:** single head: 30 unit-space knobs (MSE) + 12-way wavetype
  softmax (cross-entropy). Square-only knobs masked out of the loss on
  non-square examples.
- **v2:** same encoder; wavetype classification, then a separate 30-knob
  regression head per wavetype, each trained only on its own examples. At
  inference, the top-3 wavetypes' heads produce three candidate param sets.

Training on M1 (MPS), a few hours. Held-out validation split. Loss is in
unit param space; evaluation is perceptual (see below).

## Integration with the matcher

- `match.py --seed-model <checkpoint>`: the model's top-3 wavetype guesses
  and their knob predictions (plus jittered copies) replace stage 0's
  random screen. Stages 1/2/refine unchanged.
- `match.py --one-shot`: render the raw top prediction, no search — the
  growth-metric mode.
- `predict.py` also works standalone: wav in, ranked `.bfxr` guesses out.

## Evaluation

One eval script producing a per-target table over all 32 sounds in
`tools/targets/`, three columns:

| current pipeline | model-seeded pipeline | one-shot |

Equal budget for the two pipeline columns. v1 passes when model-seeded wins
on the hard targets. Also an in-domain sanity check: held-out *generated*
sounds → knob recovery error + perceptual score of the re-render. In-domain
scores should be near-perfect; if they are not, the model is broken
independently of the real-audio projection question.

## Error handling

Inherited conventions: failed/silent renders filtered at data-gen; NaN-free
features guaranteed by the fill+mask convention; per-target try/except in
batch eval so one bad sound never kills a run; renders deterministic per
stored seed.

## Tests

- sampler determinism + envelope projection matches optimizer's
- dataset shard round-trip (write → read → identical tensors)
- augmentation leaves labels untouched and output finite
- model forward-pass shapes for v1 and v2 heads
- integration smoke test: tiny randomly-initialized checkpoint seeds a
  1-target match run end to end

## Out of scope (recorded)

- Multi-hypothesis heads (Option 3) — only if within-wavetype
  mode-averaging shows up in eval.
- Browser port / distillation — after the offline ceiling is known;
  requires either a JS feature-extractor port or a mel-only model.
- Weight tuning of the perceptual metric — separate track, gated on
  listening verdicts.
