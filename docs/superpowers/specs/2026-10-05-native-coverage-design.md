# Expanded Transfxr native coverage

The paired gesture-loss experiment failed promotion. Training acoustic error is
about .07 while validation is about .59. Current Transfxr data has 12,288 rows but
only 2,048 native/preset-mutation examples; remaining rows emphasize structured
coverage. Retained old Bfxr manifests include a 200,000-example v5 corpus and
300,000-example predecessors. That establishes a corpus-scale gap, not a causal
claim about which old stage produced its good recreations.

Generate 32,768 additional native Transfxr examples using the existing verified
sampler: half native preset outputs, 30% sparse control mutations, 20% broad
mutations, equal cycling over preset generators. Four independent 8,192-row
shards use fixed different seeds starting at 20261020. Reuse shipped DSP and
the frozen coarse descriptor, retaining every source control, seed, PCM/feature
hash and generation failure. Do not change DSP, feature extraction or original
datasets. This expands native diversity, not the number of easy tones.

Merge the completed shards into an isolated derivative of temporal-v3 data.
Preserve all original split memberships, exclude any new control groups matching
original validation or frozen probes from training, and keep identical control
groups together. Preserve original normalization for matched fine-tuning from
the frozen v3 checkpoint. Retain native/structured 50:50 aggregate training mass.
Data normalization population and final merge checks must be explicit before
training; generation by itself does not authorize model promotion.

Compare matched continued training on old versus expanded data, same architecture
and update budget. Select checkpoints by development validation consistently.
Evaluate existing diagnostic targets plus fresh generated holdouts; include
native and structured strata separately. A real-reference human comparison is
still needed to establish improvement. No listening request follows generation.

Other options (new head structure or learned audio loss) are deferred until this
directly motivated coverage test. User authorization covers autonomous execution.

Controlled training recipe, fixed before shard completion: 4,000 AdamW updates
at .0001, weight decay .0001, batch 128 with exactly 64 native and 64 structured
rows sampled with replacement, gradient norm limit 5. Each arm starts from the
same frozen v3 Transfxr flat checkpoint. Separate seeded native/structured random
streams preserve the structured sequence across arms. Validate every 200 steps
on the unchanged original split, with original 50:50 stratum weights. Include
step zero in checkpoint selection; save the lowest original validation acoustic
loss. Report fresh native holdout loss separately, never use it for selection.

New controls use a deterministic hash split (15% validation), grouped globally
across shards. Original training groups stay training; matches to original
validation or frozen probes are reserved, not additional training. The derivative
retains original rows verbatim at its prefix. Freeze 32 new native holdout control
groups before training for a separate equal-budget render check. This holdout is
new control draws, not a held-out preset family or real recording generalization.

Render gate, fixed before training: use four proposals per arm on the previous
32 validation cases, 10 probes, and the new 32 native holdouts. Require at least
5% mean distance improvement on both original validation and fresh native
holdouts over the matched control, with no loss in aggregate static median pitch,
reliable pitch, voiced-span direction or target-active contour coverage; no
increased failures/silence or missing targets. Probe pitch/coverage regressions
veto promotion. Use the same diagnostic definitions as physical-gesture-v2 and
report individual regressions separately. The frozen v3 model remains a third
comparator. This gate permits listening only, not a claim of convincing likeness.
