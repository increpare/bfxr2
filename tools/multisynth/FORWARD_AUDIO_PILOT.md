# Forward-audio pilot after neural v2's listening rejection

The user's current assessment rejects v2 as an audible improvement. Only charm2
was actually close, and its winning audio was the previous Transfxr clip. The
older Bfxr model remains the standard to beat; inverse-control regression alone
has not reproduced its complete audio-training loop.

The recovered old real-audio manifest contains 5,186 existing reference paths:
4,669 train and 517 holdout, including 445 tagged sounds. These path memberships
are provenance, not proof of audio-family separation. The new v2 experts have
no equivalent unlabeled real-audio fine-tuning stage.

## Prediction prerequisite

Three independent models learn controls to the frozen 4,083-feature descriptor,
with two 256-wide GELU hidden layers, AdamW and 40 epochs on MPS. Each engine has
3,482 training and 614 validation rows. Normalization uses training rows only;
nine descriptor groups get equal weight and peak gain is excluded. Random render
anchors are unobserved, and this is not waveform synthesis.

| Engine | Best epoch | Validation / training-mean baseline |
| --- | ---: | ---: |
| Bfxr | 39 | 0.520 |
| Transfxr | 40 | 0.264 |
| Pluckr | 39 | 0.376 |

All three pass the predeclared prediction gate: total loss at most .8 of the
training-mean baseline and envelope/pitch/voicing groups at most their baselines.
CPU replay independently verifies every validation row, all reported group
losses, exact train-only normalization, complete epoch counts and selected epochs.
See the [training audit](evaluations/forward-audio-pilot-v1-training-audit.json).

The checkpoints and adjacent strict-load reports are in the ignored run path
`runs/forward-audio-pilot-v1/model/<engine>/`. No existing model, DSP source,
feature extractor or listening gallery changes. Fifty-one forward/existing
inverse tests passed before full training; both spec and quality reviews approved.

## Actual-DSP prerequisite

Next, a frozen 20-case source-engine probe uses three native sounds, nine tones
and eight moving sounds from the completed paired benchmark. It starts at v2's
known-source raw controls, optimizes only continuous controls through the frozen
surrogate, and keeps categories and randomness fixed. Selection of the best
state uses surrogate loss only. Exact actual-DSP before/after audio must then
improve at least 15/20 actual feature losses and their mean, without losing
previously reliable pitch. This gate is still not perceptual validation. Before executing the probe,
supplemental safeguards are declared: retain any static pitch previously within
one semitone and retain any previously correct moving-pitch direction. Report
these separately; their failure also prevents promotion.

No new listening round or checkpoint promotion is justified by prediction error
alone. The purpose is to establish a trustworthy prerequisite for audio-loss
inverse training and subsequent real-reference fine-tuning.

## Actual outcome: rejected

All 20 surrogate losses improved, but actual descriptor loss improved on only
9/20 cases. Mean actual loss rose from .287 to .654; two cases lost reliable
pitch. Bfxr improved 0/8 actual losses. Transfxr improved 7/8 descriptor losses,
but that did not preserve its pitch or motion. Pluckr improved 2/4.

All six static cases previously within one semitone regressed outside that band.
Seven of eight previously matching movement directions no longer matched. Both
the original actual gate and the separate predeclared pitch safeguards failed.
This pilot is **not eligible for inverse fine-tuning or promotion** under its
predeclared policy. No new listening session is justified by this result.

The [actual audit](evaluations/forward-audio-pilot-v1-actual-audit.json) independently
replays all 60 target/before/after FLOAT WAVs through shipped DSP, checks frozen
source/knownRaw bindings, recomputes losses and MatchObjective, and verifies pitch
and checkpoint bindings. The full controls, loss traces, spectra/envelope/pitch
evidence and actual audio remain in `runs/forward-audio-pilot-v1/probe/`.

A concrete example: Transfxr's 137 Hz static case moved from .079 to 4.266
semitones of actual pitch error while its total actual descriptor loss decreased.
Its pitch endpoints diverged and its vibrato controls moved from about .016/.010
to .859/1.0. This exposes two distinct issues: surrogate gradients can exploit
prediction errors, and even our actual grouped descriptor score can trade pitch
or gesture for other terms. Prediction accuracy alone does not validate either
its gradients or a perceptual objective.

This is a failed **unconstrained control-gradient pilot**, not proof that every
small-step surrogate-assisted inverse fine-tuning method must fail. No such new
inverse model was trained in this stage. The older Bfxr checkpoint is intact.

Before the next training stage, measure local gradient agreement with real DSP
and calibrate pitch/gesture constraints explicitly. Retain synthetic supervision
and useful control-domain priors when testing real-audio loss; evaluate temporal
encoders and multiple valid control solutions separately. Increasing engine
count or merely reducing surrogate loss is not an acceptance criterion.

## Local gradient follow-up, 2026-10-05

A fresh balanced 32-case Transfxr development set excluded both forward and
inverse training controls. One normalized gradient step of .005 of each control
range improved actual descriptor loss on 23/32 cases (mean .315813 → .277200),
but failed the predeclared 24/32 threshold and lost one previously matching
voiced-span direction. The latter flattened a weak descent from -.615 to -.270
semitones against a -9.377-semitone target, crossing the tracker's deadband.
It did not turn a faithful descent into a rise. No inverse audio training is
authorized by this result. Other radii and reversed directions remain diagnostic.

The [local summary](evaluations/local-gradient-v1-summary.json) retains all six
radius/direction arms. Independent review verified 256 target/before/step WAV
hashes, exact summary calculations, and no source-control training overlaps.
It also prompted stronger preflight source/split checks and dependency hashes;
the raw result and its original evaluator snapshot are unchanged. Pitch safeguard
coverage is limited: five initially accurate static cases and fifteen initially
matching movement directions. This is development evidence, not human likeness.
