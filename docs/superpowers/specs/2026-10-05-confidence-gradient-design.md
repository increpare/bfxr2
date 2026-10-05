# Confidence-conditioned local loss diagnostic

Hypothesis: pitch/voicing descriptor terms can dominate local directions even
when the target pitch estimate is unreliable. Test this on the eight retained
rendered-gradient-v1 development cases; do not claim independent validation.

For the three pitch-unreliable targets, omit relativePitch, absolutePitch and
combinedVoicing from the equal-group loss and average the remaining six groups.
Use target-only reliability, frozen before any candidate updates. Recompute
actual finite differences from the retained +/- .001 coordinate renders and
autograd directions from the unchanged forward model. Apply each direction at
.001 and .005, plus reversed .005; keep categories and randomness fixed. For the
five reliable targets retain the previous loss/directions and exact steps.

Compare original full loss, masked loss and MatchObjective at identical step
budgets. Independently replay every new final render, recompute its descriptors
and score, and bind reports to source/model/code hashes. Verify unchanged
reliable-target controls and PCM. Record negative controls and every outcome;
no selecting a favorable step or changing thresholds after seeing results.

Alternatives: enlarge the forward model (confounds derivative approximation and
objective); replace all pitch supervision (risks tonal accuracy); perform this
small conditional ablation first (chosen). No production loss, training model,
published gallery or human evidence changes. A numerical improvement would
justify a fresh-case test, not model promotion. User authorizes autonomous work.
