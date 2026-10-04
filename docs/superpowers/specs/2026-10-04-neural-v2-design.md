# Neural v2: acoustic control learning

Proceed autonomously under the user's explicit instruction, until a short human
listening check is needed. Work in the existing isolated Codex branch. Preserve
all published galleries, earlier checkpoints and exact feedback.

The diagnosed v1 problem is data/objective mismatch: no stationary Bfxr sine
examples, control MSE diluted among inactive knobs, generator ancestry affecting
the same input's pitch, and unvoiced finalists winning voiced targets. More
epochs alone already overfit. A retrieval-only selector refit would leave the
inverse predictor weak. A full differentiable DSP surrogate is a larger separate
experiment. This bounded iteration instead tests structured acoustic coverage,
direct audio-conditioned controls and an audible-control supervised objective.

## Data

Keep every original example for all 22 active engines. Add 2,048 independently
rendered structured examples each for Bfxr, Transfxr and Pluckr: log-uniform
pitches, varied waveforms/materials, durations/envelopes, stationary motion and
sparse moving/jumping/vibrato gestures where actual DSP supports them. This is
an addition to general generator/mutation examples, not a replacement. Saved
canonical controls, render seeds, raw audio/feature hashes, packed bytes and
source provenance remain bound. Split exact parameter groups globally within
each engine, so duplicates never cross train/validation. No user target is a
synthetic control label. Existing feature representation stays unchanged.

## Model and loss

V1 remains loadable. Metadata selects generator-conditioned v1 or acoustic v2
heads. V2 numeric/category outputs depend on the audio embedding directly.
Generator classification is auxiliary and supplies fixed TEXT/random anchors;
Jinglr's phrase remains generated. Categorical alternatives, rather than two
identical generator-conditioned vectors, supply distinct v2 proposals.

V2 emphasizes pitch and temporal controls, masks Bfxr square-only and inactive
rate/curve controls where explicitly known, and uses known DSP log-frequency
mapping for Bfxr/Transfxr/Pluckr pitch. Record fixed weights and mask policy.
Pluckr coupling remains supervised even with one string; motion speed is active
when either vibrato or tremolo is active, and one-string strum is inactive.
This is an acoustic-priority parameter loss, not a differentiable rendered-audio
loss. Compare structured-data-only legacy loss against the acoustic model and
frozen v1 on the same fresh diagnostics. Broad all-engine reconstruction remains
an acceptance check so tonal specialization cannot be hidden.

## Selection and delivery

Retain original Bfxr as an expert. Use explicit pitch/voicing diagnostic checks
and the saved human preferences to evaluate selector weaknesses before changing
its objective. Candidate quality and selector ranking are reported separately.
Keep MatchObjective unchanged for the paired model ablation. The optional tagged
delivery selector reranks that candidate pool with the fitted preference score,
plus a documented experimental coarse pitch/voicing safeguard: reliable voiced
references discourage unvoiced output and changes of register, while tolerating
three semitones of detuning. This policy addresses an observed development
failure; it is not independently validated psychoacoustics or an audible win.
If reliable voiced candidates within an octave of the target register exist,
rank among those; otherwise keep a best-effort candidate. The first development
preview showed that a soft penalty alone could still select a lower register.
Fit preferences with exact-reference grouped validation; seven new comparisons
are four groups, not seven independent cases. A new scorer is experimental until
it shows a supported improvement; never rewrite old human ratings.

A reproducible CLI loads the chosen checkpoint and renders actual shipped DSP.
Fresh generator/control holdouts for every engine, fresh static/moving pitch
probes and exact replay checks precede delivery. Publish a five-reference quick
listening batch with new candidate, original Bfxr and exact previously preferred
audio, using unchanged low-friction autoplay/choice UI. Only then is more human
input needed. No numerical score constitutes a claim of audible success.
