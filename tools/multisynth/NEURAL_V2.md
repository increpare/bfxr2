# Neural v2: acoustic control learning

This iteration trains real inverse experts for all 22 active individual synths.
The acoustic model learns controls directly from audio; preset ancestry remains
an auxiliary prediction for fixed text/random anchors. The frozen v1 model and
original trained Bfxr model remain available.

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
