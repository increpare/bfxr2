# Fit native event controls in the complete sound

The learned-events feedback rejects all five new timing fits. All prior clips
win; three remain least-bad and two similar. Native timing F1 did not establish
external quality. Keep this negative outcome and exact audio permanently.

Code inspection identifies a specific restriction: each event's synth controls
are optimized against a crop once, then remain frozen. Only start/gain/pitch
are subsequently adjusted. Real native source tails overlap in Stackr. A good
isolated crop fit need not produce a good aggregate waveform.

## Fixed experiment

Use the four external development references with more than one heuristic
event from the completed learned-events run: book flip, metal footstep, attack and coin.
Initialize both new arms from that exact heuristic scheduled native patch.
Do not select among learned and heuristic patches using the new ratings.

Both arms receive 2048 mutation attempts, seed20261106+1009*trialIndex,
scored against the complete reference with original MatchObjective after the
same single audition normalization. The timing-only arm adjusts start, gain
and pitch. The joint arm uses source-control mutation on 75% of steps and
those timeline controls on the remainder. Source mutator uses existing full
numeric/categorical controls, excluding random seed and volume. Preserve engine,
layer count, native seed, and first start0. Other starts remain within40ms of
initial actual starts; gains .01–1 and pitch -12–12. Four decreasing scales
1,.5,.25,.1 apply equally by budget quarter. Source mutation sigma .12*scale;
time perturbation25ms*scale, gain .2*scale, pitch2semitones*scale.

Only accept improvements in the whole sound score; keep a full monotonic trace,
accepted source/timeline counts and exact final uncached native replay. This
is a restricted search-space ablation, not a training run, equal wall-clock
comparison or evidence of generalization. No synth-control weights change.
The references are repeated and historically overlap original Bfxr training.

Retain the exact latest human winner as a third option, deduplicate exact PCM,
and publish all four references regardless of scores. If an entire option set
was already heard, omit it with an explicit receipt. Use the existing buffered
quick comparison UI and immediate adequacy/mismatch questions. No score change
will be described as an audible improvement before listening.

## Verification

Before experiment freeze, test that source controls can change without mutating
input patches, locked arms preserve them, the objective receives the assembled
waveform, and accepted candidates preserve valid native render controls. Then
freeze source/plan/renderer/input hashes. Re-render initial and final patches
uncached, reproduce scores and all identity/dedup mappings. Serve every asset and
inspect browser loading before requesting feedback. Archive the current30th
feedback session and publish its human verdict first.
