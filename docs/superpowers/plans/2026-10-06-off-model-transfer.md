# Off-model transfer evaluation

**Goal:** Evaluate audible transfer on eight unjudged tagged recordings, keeping native inversion separate from the acceptance criterion.

**Design:** Freeze filenames and exact audition PCM before inference. Reuse all existing checkpoints without retraining: shared22, Transfxr mixture, Boomr/Footsteppr/Squishr specialists, and original Bfxr. Human-approved native examples remain diagnostics, not evidence of recording transfer. No native examples in this listening batch. The user's standing autonomous authorization covers execution.

**Alternatives considered:** More synthetic training repeats a successful native task without addressing transfer. Testing only Squishr across arbitrary sounds artificially restricts representational coverage. Use the full pool and two frozen scorers to expose selection uncertainty, retaining original Bfxr as an independent candidate.

**Scope:** Eight tag strata (footstep, clothes, hit, chains, door, bell, laser, collect), one seeded eligible file per stratum, duration .025–1.8 seconds. Exclude every previous feedback reference by file and normalized audition PCM. Source families may overlap earlier development; no family-disjoint or externally certified out-of-distribution claim. External file provenance does not prove its original creation method. Tags are sampling strata, never model inputs.

## Execution

- [ ] Preserve cumulative ten-trial feedback with all audio; compare earlier five for exact equality and verify training-pair deduplication.
- [ ] Freeze manifest, checkpoint/metric/code hashes and eight reference WAVs before inference; bind source DSP revision at runtime.
- [ ] Render shared22 two/head, temporal Transfxr four, three specialists four/head. Retain all raw candidates and failures. For each of soft-periodicity and preference-neural-v2, refine the top two distinct engines using that scorer with128 attempts/start. Preserve original Bfxr's legacy objective and2000 budget. This is a combined-system diagnostic, not equal-compute model ablation.
- [ ] Score all outputs with soft, preference and legacy independently. Replay saved raw/refined candidates through actual DSP. Export soft winner, preference winner and original Bfxr, deduplicating exact PCM. If scorer winners coincide, retain original and add highest-ranked distinct preference alternative. Never drop a reference for poor scores.
- [ ] Verify eight trials with two or three distinct options each; hash every served audio file. Keep immediate adequacy and optional break. Browser QA must not generate votes or audition telemetry.
- [ ] Record human result interpretation, native-vs-transfer distinction and cumulative feedback policy. Deliver one fresh page, no claim of quality until judged.

**Implementation:** New `tools/multisynth/evaluations/off-model-transfer-v1.py` provides freeze/run/gallery stages; existing renderer, predictors, objective, feedback exporter and archival importer remain unchanged. Tracked manifests and audit receipts bind local ignored waveforms and frozen models. Verification uses fail-fast assertions for source PCM, identity, budgets, replay, per-file hashes and exact exported scores, plus existing quick-feedback/selection tests. An interrupted incomplete target must be inspected; only hash-bound completed target results can resume.
