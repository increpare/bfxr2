# Transfxr physical pitch-gesture supervision

Local surrogate gradients failed their primary gate. One example predicts a
triangle with nearly stationary pitch for a target falling nine semitones. The
current acoustic loss directly supervises pitch endpoints but gives transition
categories a small generic classification term. Endpoint accuracy cannot ensure
the right trajectory.

Test a differentiable control-domain trajectory derived from Transfxr_DSP's own
eight curve functions. Relative-time pitch is `7 * pitch(t)` octaves above 40 Hz,
plus `0.16 * vibrato(t) * sin(16*pi*duration*t)`. This approximates commanded
oscillator frequency: it omits the DSP's 2 ms smoothing, filtering, echoes and
waveform-dependent pitch perception. It is not an audio or psychoacoustic loss.

For all 8 pitch curves crossed with all 8 vibrato curves, compute mean squared
octave error against the labelled control trajectory at 256 relative-time points.
Average those 64 errors using predicted categorical probabilities. Use expected
error of each actual discrete alternative, not error of an averaged trajectory
that could hide contradictory motion. Ground-truth controls form supervision
only; inference still has to predict every control from sound.

Initialize two identical copies of frozen v3's Transfxr flat expert. Fine-tune
both on the existing 12,288-row data/splits with identical minibatches, 20 epochs,
AdamW lr .0001, native/structured 50:50 weights. Control uses the frozen acoustic
energy; treatment adds the expected trajectory error with weight 1. Retain the
fixed final epoch for the primary comparison, avoiding different checkpoint
selection criteria between arms. Keep original models and datasets unchanged.

Evaluate equal four-proposal budgets without search on the same 32 Transfxr
onset-validation references and 10 previous development probes. Compare with
frozen v3 as well as the fine-tuned control. Require >=5% mean objective reduction
versus the control, no missing/silence increase, and no reduction in passing static
median pitch or moving direction/contour coverage. Probe pitch regressions veto
promotion. These reused cases are development evidence only. A passing result
allows a new small human listening comparison, never a quality claim.

Before evaluation, contour coverage is fixed as follows: use every target with
reliable pitch and a nonzero voiced-span direction; for each candidate count the
target-active frames with aligned candidate pitch within one semitone, divided
by all target-active frames. Missing/unvoiced frames contribute zero. Average
these fractions equally over all eligible targets. Require no decrease against
the paired control, alongside no decrease in static median pass count, reliable
pitch count, or moving-direction count. Missing targets prevent passing.

Pre-evaluation repair: the first completed pair used 64 samples, which aliases
8 Hz vibrato at duration 3.9375 seconds. Preserve that pair as invalid under
`runs/gesture-v1` with its original source; rerun both arms with 256 samples under
`runs/gesture-v2`. No render evaluation or candidate selection used the invalid
pair. A regression test compares this case with its analytic mean-square value.

Alternatives considered: more unconstrained surrogate optimization is rejected
by the local test; categorical-conditioned numeric heads could improve joint
proposals but do not directly address missing trajectory supervision. Test this
small loss change first. User has authorized autonomous experiment decisions.
