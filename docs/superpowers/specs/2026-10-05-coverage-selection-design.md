# Coverage candidate selection

The expanded Transfxr expert improves reconstruction distances but fails its replacement gate. Retain the frozen expert, and evaluate a new selection policy; do not reinterpret the failed experiment as a pass.

Alternatives considered: replace the expert (known gesture regressions); add more loss penalties (previous physical-gesture trial failed); preserve baseline candidates while selecting complementary proposals (chosen, testable without more training).

Select the lowest finite actual-DSP distance among four old and four expanded proposals, provided it preserves the old four-proposal winner's reliable pitch evidence. For reliable targets, preserve candidate reliability, static median within one semitone when previously matched, moving direction when previously matched, active-frame one-semitone coverage, reliable contour-pair count, and mean paired contour error. Compare every candidate against the same baseline, not sequential winners. Unreliable targets use distance only. These descriptor measurements become experimental selection inputs, not independent ground truth.

Retrospective checks use all 74 previously evaluated controls, explicitly development evidence. Freeze another 32 distinct native validation control groups using seed 20261027, excluding training and the previous 32. On those new targets compare old-four, old-eight, unguarded four-plus-four, and guarded four-plus-four. An old-eight policy also retains old-four as fallback. Count actual proposals and failures. Eight proposals cost more than four; old-eight is the budget comparison. No additional training occurs.

Advance only if fresh mean distance improves at least 5% versus old-four, improves versus old-eight, and no individual preserved pitch criterion regresses. These safeguards are partly true by construction and must not be called independent validation. Report how often expanded candidates are selected and how much opportunity the safeguard rejects. Neither synthetic success nor reuse of descriptor metrics proves human likeness.

Autonomous design/execution is authorized by the user's ongoing goal. No new listening page until exact tagged-reference renders offer a meaningful comparison.
