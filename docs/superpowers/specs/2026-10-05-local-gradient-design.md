# Local forward-gradient diagnostic

The previous unconstrained surrogate optimizer failed actual-DSP checks, including
pitch and motion. Transfxr's 7/8 descriptor improvements did not preserve pitch.
Do not use that result to permit inverse audio fine-tuning.

Test whether small local steps are useful before changing the forward model or
training through it. Alternatives are retraining a larger surrogate (costly before
knowing the gradient defect) or numerical DSP derivatives (accurate locally but
expensive per training example). This bounded diagnostic distinguishes these.

Use 32 freshly frozen Transfxr validation references, 16 native and 16 structured,
starting from the onset control arm's selected four-proposal raw candidate. These cases are new to
the forward-gradient probe, but are development data used for inverse checkpoint
selection. Assert reference controls are absent from both training splits.
The frozen forward checkpoint and categorical controls/randomness stay fixed.

Differentiate the existing grouped normalized descriptor loss at the starting
controls. Normalize the negative gradient to maximum absolute component one.
Render steps of .001, .005 and .02 of each control's schema range in both
directions, clamping to [0,1]. No actual audio participates in step selection.
The .005 descent step is the sole primary treatment; other radii and reversed
steps diagnose scale and sign, and cannot rescue a failed primary result.

Prerequisite: 24/32 primary actual descriptor improvements, lower mean actual
descriptor loss and no increased silent outputs, loss of reliable target pitch,
loss of previously <=1-semitone static pitch, or loss of previously correct
moving-pitch direction. Also report MatchObjective, pitch contour error and all
reversed-step comparisons. Passing only permits consideration of a bounded
training experiment; it is not a human likeness claim or listening promotion.

Store exact controls, gradients, actual FLOAT WAVs, hashes, checkpoint and code
bindings and per-case results. Fail on source/PCM mismatch. No galleries change.
User authorization to work autonomously covers this routine experiment choice.

Preflight correction, before any gradient/render results: the original onset-v1
list overlapped the older forward training split on 16/32 cases. Its first run
aborted before creating output. Replacement targets use seed 20261018, exclude
both training control hashes, and are frozen in `local-gradient-v1-targets.json`.
