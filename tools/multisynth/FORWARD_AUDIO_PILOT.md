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

## Rendered-direction diagnostic and research follow-up

Before enlarging the surrogate or using its gradients for real-audio fine-tuning,
`rendered-gradient-v1` compares its retained directions with finite differences
through the actual synth. Eight fixed development cases use +/- .001 continuous
control perturbations and the same frozen grouped-descriptor loss/normalization.
This tests a bottleneck: inaccurate surrogate derivatives versus unhelpful local
directions in the objective itself. Finite differences are scale-dependent,
especially around descriptor pitch, voicing and trimming discontinuities.

Relevant primary research, checked 2026-10-05:

- [Sobolev Training for Neural Networks](https://arxiv.org/abs/1706.04859)
  trains on function values and derivatives; it also considers stochastic
  projections to avoid fitting full Jacobians. Our inference: nearby DSP render
  pairs could supervise local directions rather than merely output values. This
  paper does not establish that our finite-difference audio descriptors are good
  perceptual targets, or that this will work for our synths.
- [Multi-Scale Spectral Loss Revisited](https://www.audiolabs-erlangen.de/content/05_fau/assistant/00_schwaer/01_publications/2023_SchwaerM_MultiScaleSpecLoss_IEEE-SPL.pdf)
  analyzes how spectral-loss configuration affects pitch optimization; useful
  forward synthesis does not imply informative frequency gradients. Our
  inference: check the actual objective's directions before blaming only the
  learned approximation.
- [Evaluating Sound Similarity Metrics for Differentiable, Iterative Sound-Matching](https://arxiv.org/abs/2506.22628)
  reports synth-dependent loss performance and only moderate consistency among
  its parameter, spectrogram and listening measures. Our implication is to retain
  per-engine diagnostics and human checks, including agreement cases; do not
  assume one numerical score transfers universally across engines.
- [Synthesizer Sound Matching with Differentiable DSP](https://zenodo.org/records/5624609)
  combines parameter pretraining with spectral fine-tuning on real sounds. This
  supports investigating that missing stage in our new experts, while our failed
  surrogate checks remain evidence against enabling it with the current model.

The PNP/JTFS approach already discussed in `NEURAL_V2_RESEARCH.md` remains
relevant, but is not newly implemented here. None of these papers certifies
human likeness for the current game-SFX system.

The rendered-direction diagnostic completed. At normalized radius .005,
actual finite-difference and retained surrogate directions both improve
descriptor loss on 6/8 cases. Mean descriptor loss is .297966 before, .269078
after the rendered direction, and .266309 after the surrogate direction.
Mean MatchObjective changes 3.00123→3.01053 for rendered descent (slightly
worse), versus 2.96064 for surrogate descent. No reported reliability,
previously accurate static median or moving-direction pass is lost in these
eight cases; coverage is only two static and three moving reliable targets.

All three pitch-unreliable native references have negative directional cosine
agreement between the two methods. Two also worsen descriptor loss after
rendered descent. For case 00151, the .001 rendered step's relative-pitch group
error increases by about .692 despite the target's unreliable pitch diagnostic.
This motivates investigating confidence-aware or smoother audio losses, but is
a post-hoc hypothesis. It does not prove that removing pitch terms is correct,
that secants are exact gradients, or that larger-data forward training would fail.

The audit verifies 264 retained candidate file/PCM hashes, recomputes every
candidate descriptor loss, and replays/rescores all 24 final steps with zero
error. Secant renders are verified from retained PCM, not all independently
replayed; pitch diagnostics are reused. See
`evaluations/rendered-gradient-v1-audit.json`. Five focused tests and bounded
independent review pass. No inverse-audio training or listening promotion follows.

## Conditional pitch-loss diagnostic

`confidence-gradient-v1` tests the post-hoc hypothesis above on the same eight
development cases. It removes relative pitch, absolute pitch and combined
voicing only for the three targets whose frozen pitch diagnostic is unreliable,
then averages the remaining six groups. Both actual-render secants and frozen
surrogate autograd use this loss. All five reliable-target cases retain their
previous exact steps. Categories, seeds, normalization and proposal budgets stay
fixed; no inverse is retrained in this diagnostic.

For the three affected cases, before-step mean MatchObjective is 4.77988. At
radius .005, conditional rendered directions reduce it to 3.58321 (all three
improve), versus 4.89845 under the original rendered directions. However, at
.001 the conditional rendered mean worsens to 4.91767, and even at .005 the
conditional descriptor loss itself slightly worsens, .206879→.207198. This is
a scale-specific result, not evidence of consistently useful descent.

The conditional surrogate direction at .005 lowers actual conditional descriptor
loss on all three cases (.206879→.199141), but mean MatchObjective worsens to
7.78758. Case 00151 rises from 7.82159 to 18.16005, while the other two improve.
Derivative cosine agreement turns positive for two cases (.9045 and .5450),
but remains negative on 00151 (-.3355). Reverse .005 steps are retained as well;
neither method's reversed conditional direction improves MatchObjective on any
of the three cases.

The results support further investigation of objective discontinuities and
local derivative error; they do not justify adopting this binary reliability
mask or enabling surrogate-audio fine-tuning. A useful next test would freeze
additional cases and compare finite-difference scale stability before training
derivative targets. Human adequacy feedback on coverage-selection remains a
separate question; none of these objective changes establishes audible likeness.

Audit: all 74 before/original/new candidate WAV references and descriptor scores
verified; 26 exact DSP replays (eight before states and all 18 new steps), with
zero MatchObjective error. Thirty reliable-case steps are unchanged. The audit
recomputes gradients, direction construction, pitch diagnostics on new renders,
and summaries. Independent review found no important implementation issue and
emphasized the scale-dependent and post-hoc scope. Retained evidence:
`evaluations/confidence-gradient-v1-audit.json`.
