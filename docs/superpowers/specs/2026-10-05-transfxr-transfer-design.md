# Transfxr robustness and transfer diagnostic

User asks whether Transfxr inversion generalizes to degraded/transposed/filtered
sounds and other sources. Existing native self-inversion does not answer this.
Run the frozen old and expanded checkpoints without training on these targets.

Eight Transfxr base sounds: three human-reviewed anchors plus the first five
other controls in the already frozen coverage-selection fresh list. Report the
anchors separately; remaining controls were previously numerically evaluated.
Apply clean, MP3 32/96 kbps, 8-bit PCM quantization, low-pass 1800 Hz, high-pass
350 Hz, and +/-5-semitone rate transposition with compensating atempo. The last
operation approximately preserves duration but introduces processing artifacts;
report measured pitch and exact method. Each altered sound is the target, not
its clean ancestor. Hold source normalization fixed across its perturbations.

Also draw one fresh native sound from each other active collection-compatible
synth using fixed seed 20261031 + inventory index*104729. Report failed draws;
no selection by Transfxr match score. Include the five previously rejected real
recordings as a separate repeated-development group. Do not pool engine quality
claims from one example each. These are checks of inversion, not engine capacity.

Each target gets eight old proposals and four expanded proposals, comparing old
four, old eight, expanded four, and existing guarded four-plus-four selection.
Retain clean selected reproductions as a frozen baseline when evaluating each
altered target. Record actual DSP distance, reliable pitch/contour diagnostics,
all proposals/failures and candidate identity changes. Equal budget comparison
is old eight versus ensemble eight. No new perceptual-success threshold.

Freeze every target before inference, retain exact FLOAT target/candidate PCM,
replay selected outputs, verify transformation files and hashes, and report
per-group/per-transformation outcomes. Recompute summaries and compare output
pitch to transformed targets. No automatic model promotion; a short listening
batch can follow if evidence provides useful comparisons. Existing gallery and
human ratings remain unchanged. Autonomous design/execution authorized.
