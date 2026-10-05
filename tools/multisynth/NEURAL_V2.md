# Neural v2: acoustic control learning

This iteration trains real inverse experts for all 22 active individual synths.
The acoustic model learns controls directly from audio; preset ancestry remains
an auxiliary prediction for fixed text/random anchors. The frozen v1 model and
original trained Bfxr model remain available.

## Human outcome: not an audible improvement

The subsequent five-reference listening round rejected this iteration as a
successful approximation. The user reported only `die/charm2.wav` as actually
close; its winning clip is the retained **previous Transfxr**, not the new Pluckr
output. Bird/card Bfxr wins are relative choices, not adequate likeness labels.
Computer was rejected and spinout preferred the previous Bfxr audio. Preserve
v2's numerical gains as diagnostics; do not promote its checkpoint or experimental
pitch gate as the replacement for the older Bfxr pipeline.

The [exact feedback archive](listening_data/2026-10-04-neural-v2-quick-01/README.md)
and [human audit](evaluations/neural-v2-quick-01-human-review.json) retain both
choices and the qualitative rejection. A bounded forward-audio pilot now tests
a missing training prerequisite before further listening demands. That pilot's
forward prediction passed, but its actual-DSP gradients failed: 9/20 losses
improved, average error increased, and accurate pitch/gesture regressed. See
[the measured pilot outcome](FORWARD_AUDIO_PILOT.md). No new inverse checkpoint
was trained through that rejected surrogate.

## Training

The 51,200 examples retain every one of v1's 45,056 native/mutated examples.
Another 2,048 independently rendered examples each for Bfxr, Transfxr and Pluckr
cover physical log-uniform pitch, envelopes and supported motion. Exact control
groups do not cross training/validation. No reference sound is a synthetic label.

Two 30-epoch MPS runs use the same frozen dataset and seed 20261005:

| Model | Best epoch | Training seconds | Checkpoint |
| --- | ---: | ---: | --- |
| Structured data, legacy heads/loss | 23 | 217 | `runs/neural-v2/data-only-model/best.pt` |
| Direct acoustic heads, acoustic loss | 27 | 275 | `runs/neural-v2/acoustic-model/best.pt` |

Losses from different objectives are not comparable. The new loss expresses
known Bfxr/Transfxr/Pluckr pitch errors in octaves, gives temporal/pitch controls
higher priority, and masks explicitly inactive controls. It is supervised
parameter loss, not a differentiable audio renderer or perceptual audio loss.
Shared encoder size and feature extraction remain unchanged. Old v1 checkpoints
load with their original architecture.

The older original Bfxr checkpoint is a different, more developed pipeline:
a temporal convolutional encoder, synthetic knob training with forward-surrogate
feature loss, then five epochs of unlabeled real-audio spectral finetuning. Its
retained `v7_real_ft/run.sh` and checkpoint metadata bind that last stage. V2
does not yet replicate this complete training loop across synths. The recovered
real-audio manifest contains 5,186 paths (4,669 train and 517 holdout), including
445 tagged sounds. All paths currently exist. Four quick-round references are
old real-training paths and bird is an old holdout path; this repeated round is
development evidence, not a held-out generalization test. See the
[original training audit](evaluations/original-bfxr-real-training-audit.json). The measured
raw pitch improvement is a starting-point repair, not a replacement claim for
that Bfxr pipeline; the original checkpoint stays in the candidate pool.

Both checkpoints bind the immutable training manifest `2701d790…` in
`runs/neural-v2/data`. A later provenance-certified derivative
`runs/neural-v2/data-certified-v2` binds Python/worker dependencies and contains
byte-identical NPZ arrays, canonical rows and splits. The
[certification report](evaluations/neural-v2-data-certification.json) preserves
exact generation source snapshots, complete hashes, grouping checks and 24
actual DSP replays. The final recovery-only writer revision does not change
sampling, labels or these frozen datasets. New generations require fresh paths
when generation code changes.

## Diagnostics

[Fresh raw static probes](evaluations/neural-v2-raw-static.json) use the same
nine actual DSP reference tones at 137, 311 and 673 Hz as the paired benchmark.
They test the known source-engine head, before search or original-Bfxr fallback:

| Model | Within one semitone | Missing/unreliable | Median absolute error |
| --- | ---: | ---: | ---: |
| Frozen v1 | 2/9 | 1 | 6.38 semitones |
| Structured data only | 2/9 | 1 | 1.62 semitones |
| Acoustic v2 | 6/9 | 0 | 0.90 semitones |

These simple tones demonstrate improved raw pitch prediction. They do not
establish overall likeness. The paired fresh benchmark also covers every active
engine and eight moving pitch gestures, with identical references, budgets and
seeds for all three models. It excludes all training and validation control
vectors from both training datasets, shares one original-Bfxr search per target,
and preserves every actual source, raw and refined candidate. FLOAT WAVs and
control replays bind its diagnostic scores to exact rendered samples.

The [completed paired benchmark](evaluations/neural-v2-paired-summary.json)
rendered 39 fresh references and all three arms in 3,904 seconds, with no failed
predictions and no missing engine coverage. Its unchanged MatchObjective selector
chooses between refined neural experts and the shared original Bfxr baseline:

| Model | Mean distance, 22 native cases | Mean distance, 9 tones | Mean distance, 8 gestures | Mean gesture contour error |
| --- | ---: | ---: | ---: | ---: |
| Frozen v1 | 2.103 | 0.638 | 0.929 | 0.86 semitones |
| Structured data only | 2.124 | 0.496 | 1.266 | 1.26 semitones |
| Acoustic v2 | 2.030 | 0.461 | 0.585 | 0.44 semitones |

V2's selected result has lower distance on 25/39 cases, ties two and is worse on
12. Within the 22 native cases that is 13 lower, one tie and eight regressions.
Every model reaches within one semitone on all nine final static results after
search: the raw-head pitch result above is a predictor improvement, not a newly
solved final static-pitch test. V1 and v2 preserve measured movement direction
on 7/8 cases each; all eight final contours are reliable. Known-source raw
gesture contour error falls from 7.03 to 1.54 semitones.

These distances are not perceptual ratings. One native example per synth is
limited coverage, and this benchmark does not validate the experimental
human-preference/pitch selector used by the listening delivery. Original Bfxr
uses its separate 2,000-requested-evaluation search; its actual counts are
recorded and may be larger. All three neural arms use identical budgets/seeds.

## Human feedback and selection

All five retained archives contribute 110 strict preferences across 45 exact
reference PCM groups, including seven newest heard-only choice comparisons.
No numerical rating is invented for a choice, tie, skip or none-close response.
The [preference refit](evaluations/neural-v2-preference-refit.json) agrees with
79/110 held-out comparisons (72%; 76% with equal weight per reference), versus
63/110 (57%) for the existing search objective on those archived finalists.
This is grouped retrospective ranking evidence, not prospective sound quality.

The paired model benchmark leaves MatchObjective unchanged. An optional delivery
selector reranks the raw/refined/original candidate pool using the refit, with
an experimental coarse pitch/voicing safeguard. Reliable voiced targets
penalize lost voicing and large changes of register, while three semitones of
detuning remain unpenalized. Its fixed policy is recorded in every selected
candidate. When reliable voiced candidates within an octave exist, rank among
them; otherwise keep a best-effort result. A soft penalty alone still chose a
different register in the initial development preview. These choices are
experimental and are recorded in the complete pool ranking. The policy
was motivated by a development failure and needs listening
validation; the refit's held-out numbers do not validate this added safeguard.

The frozen source rows retain their original `previouslyRatedReference` and
`normalizedPcmSha256` annotations from the v1 target manifest. Current audition
identities are the exported `referenceAudioSha256` and actual archive PCM hashes.
The [delivery audit](evaluations/neural-v2-delivery-audit.json) distinguishes
those identities and verifies all five historical references/comparison clips.

Quick-choice winners replay exact archived PCM in subsequent comparisons.
A later scalar session returns selection to the previous scalar policy: latest
score per exact audio, then strongest distinct historical candidate. The five
familiar development references are fixed before inspecting v2 results.

## Approximate a sound

From the repository root, use the existing tools environment:

```sh
PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /Users/stephenlavelle/Documents/bfxr2/tools/.venv/bin/python -m neural_invert.run path/to/sfx.wav \
  --model tools/multisynth/runs/neural-v2/acoustic-model/best.pt \
  --bfxr-checkpoint /Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt \
  --selector-model tools/multisynth/models/preference-neural-v2.json \
  --output tools/multisynth/runs/my-new-sound
```

`selected.wav` is the automatic approximation; `result.json` retains synth,
editable controls, seed, model/DSP hashes, search provenance, and alternatives.
The required original Bfxr checkpoint is the existing
`invert/runs/v7_real_ft/best.pt` model from the inverse-model worktree. Omit
`--selector-model` for the unchanged MatchObjective selector. Output must be a
fresh directory. The command renders shipped DSP, normalizes listening copies
to peak 0.5 and PCM16, and separately records search scores and recomputed scores,
pitch diagnostics and hashes of exported audition WAVs.

Composition through Mixr/Stackr, arbitrary text/phrase transcription and fixed
random-anchor inference remain separate work. A single fresh native example per
engine is a coverage check, not evidence for its entire sound distribution.

## Dedicated Squishr experiment, 2026-10-05

The sixteenth listening archive supplies a new positive: the soft-search Squishr
wooden footstep is explicitly **very close**. The scorer itself agrees on only
2/6 strict heard preferences, so it remains experimental. The successful controls
and exact audio are a transfer anchor; neither is used as a training teacher.

The isolated checkpoint at `runs/squishr-v1/model/best.pt` uses the existing
acoustic-head architecture and loss with a dedicated encoder. It is a combined
data/capacity experiment, not an architecture-only ablation. The new dataset has
8,192 fresh DSP renders: **6,964 fitting / 1,196 validation / 32 native test**.
The original generator draws include the built-in randomizer; additional sparse
and broad mutations use the existing sampler. There are 4,129 original draws,
2,421 sparse and 1,642 broad. There were no rejected draws.
Sixty CPU epochs took about 24 seconds after about 20 minutes of generation;
epoch 26 has the lowest validation loss. Checkpoint SHA256:
`232e19d4425cc9210ae6c348bbe3983d2b19f623cc8265564bf8de737c4a2c18`.

Native tests exclude exact encoded controls, ignoring randomness, from both
fitting and checkpoint selection, and exclude the shared model's old controls.
Preset families still overlap. The approved footstep plus four unjudged tagged
files were frozen before fitting; these are transfer tests for the synthetic-only
expert, not independent population validation or an all-synth benchmark.

Both Squishr heads produce four categorical alternatives from one numeric
prediction. Both inverse heads receive the same reference PCM; actual DSP renders
their predicted controls. Raw proposals and equal 128-attempt refinement are
retained separately. Both arms use
the experimental soft score, with legacy distance reported independently. Ten
listening references were fixed before results: all five tagged sources and the
first five seeded native tests. The exact approved footstep stays in its trial.

Bindings and procedures: [protocol](evaluations/squishr-v1-protocol.json),
[test manifest](evaluations/squishr-v1-targets.json),
[training receipt](evaluations/squishr-v1-training-receipt.json).

All 37 references finished with no failed raw proposals and 9,472 total mutation
attempts. Each saved raw/refined waveform replays through actual DSP. Native
distance improves, while tagged transfer remains mixed:

| Reference group | Stage | Shared mean soft distance | Specialist mean | Specialist lower |
| --- | --- | ---: | ---: | ---: |
| 32 native tests | Raw | 2.8994 | 2.6315 | 25/32 |
| 32 native tests | Refined | 1.6510 | 1.5490 | 22/32 |
| 4 new tagged | Raw | 4.0206 | 3.7980 | 1/4 |
| 4 new tagged | Refined | 2.6303 | 2.5852 | 2/4 |
| Repeated footstep | Refined | 2.4765 | 2.5077 | 0/1 |

The tagged average hides regressions: only one new tagged raw prediction wins.
Legacy distance on the four new tagged refined outputs rises from 7.6675 to
9.9342, despite the small soft-distance decrease. These disagreeing metrics do
not establish audible improvement. Native normalized numeric-control MAE falls
from .08493 to .05778; both heads identify all 32 native textures at rank zero.
Control-derived nominal base-frequency error falls from .2353 to .1376 octaves,
but that is not measured audio pitch error or a human closeness score.

The [ten-trial listening page](runs/squishr-v1-listening/index.html) has 21 options,
with immediate adequacy and the exact prior approved footstep. Its first five
references are tagged sources, and the last five are reserved native controls.
All 31 audio files plus HTML/report were verified over HTTP. Human quality
judgments are now required. No other synth expert or CLI default was replaced.

Human update, 2026-10-06: the first five tagged trials were submitted; the five
reserved native trials remain unjudged. The repeated footstep ties all three
options as very-close. The fresh footstep rejects both; hit and clothes prefer
shared, and Anubis step prefers specialist, all least-bad. Thus none of the four
fresh tagged references has a convincing displayed recreation. The three strict
preferences agree with soft distance, but that does not imply absolute likeness.
Keep defaults unchanged and obtain the already-published native judgments before
choosing between native-inversion and transfer-focused follow-up experiments.
See the [partial human review](evaluations/squishr-v1-quick-01-human-review.json).

See [render evaluation](evaluations/squishr-v1-evaluation.json),
[control diagnostics](evaluations/squishr-v1-control-diagnostics.json),
[listening audit](evaluations/squishr-v1-listening-audit.json), and
[HTTP audit](evaluations/squishr-v1-http-audit.json).
