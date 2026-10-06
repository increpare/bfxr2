# Native Stackr event fitting implementation plan

**Goal:** Test whether fitting ordered events separately helps the external movement/rhythm failures, while retaining two similar controls.

**Architecture:** Preserve all existing models, workers and published galleries. Add a separate native Stackr bridge with exact replay, plus a deterministic waveform-only event splitter. Existing shared and Transfxr inverse models propose native controls for each event. Compare a scheduled Stackr result, an ablation with the same components starting together, and the exact previous human winner. This is a capability/initialization pilot, not new neural training or a promotion.

**Tech stack:** Python/NumPy/PyTorch, Node VM running shipped Stackr DSP, existing quick listening exporter.

## Decisions and alternatives

The six latest trials split 2/2/2 among legacy/preference/original, with zero very-close. Merely switching objectives is insufficient. Retraining another whole-sound control regressor does not add independent event scheduling. Stackr already supports that scheduling; test the representation before producing a new synthetic sequence dataset. The prior Mixr inverse trained simultaneous sources only. Use legacy objective for event fitting and whole-sequence selection, keeping the learned metric as diagnostics. No new metric tuning on these four references.

## Frozen experiment policy

Use legacy-transfer rows 1,3,4,6 (book flip and coin movement failures; attack and bell similar controls), all repeated external development references. Preserve every row irrespective of numeric outcome. These references overlap historical Bfxr training. Original Bfxr is only carried forward when the user chose it, not rerun as a fresh competitor. The other prior winners also retain exact PCM.

Detect at most two interior boundaries, minimum60ms spacing, from short-window spectral/envelope change, no filename input. Tests cover separate pulses, changed pitch, steady tone, gain invariance, invalid inputs, short sounds. Save boundaries and pre-inference protocol; no outcome-based boundary editing. Infer each segment with the same existing shared22 and Transfxr-mixture checkpoints. Exclude Footsteppr, which lacks the native Stackr host. Rank actual native source renders under MatchObjective, refine the best source with128 numeric/categorical mutation attempts, then assemble1–3 layers at observed starts. Stackr owns timing, pitch, gain and saturation; no sampled target, post-render waveform shifting or stretching.

Refine only timeline start/gain/pitch controls for128 attempts. One seed per target. Retain initial scheduled candidate if search does not improve. Ablation sets all starts to zero in the final fitted patch, retaining identical sources/pitch/gain. Deduplicate exact PCM, retaining aliases rather than substituting a different sample. No equal-budget superiority claim against earlier searches.

## Execution checklist

- [ ] Archive latest feedback and reproduce strict pairs and scores against exact PCM.
- [ ] Write failing tests for native timeline rendering/replay and segmentation.
- [ ] Implement separate timeline bridge and splitter; run tests. Preserve old source hashes.
- [ ] Freeze script, code, input/checkpoint hashes, boundaries and budgets before inference.
- [ ] Execute all four references with actual DSP, save native controls and results.
- [ ] Publish unchanged quick-choice/adequacy/mismatch UI with transparent experiment description.
- [ ] Verify native replay, exact previous audio, page/audio HTTP hashes, and browser loading.
- [ ] Save evidence and report human-quality uncertainty; request these four judgments.

If all timing candidates deduplicate to simultaneous controls, still retain them and report that this splitter did not test sequence timing. If rendering fails, preserve the failure and repair infrastructure before a new protocol; never silently replace targets.
