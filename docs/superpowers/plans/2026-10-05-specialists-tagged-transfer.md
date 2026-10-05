# Specialist transfer to tagged recordings

**Goal:** Test whether the newly human-supported Boomr/Footsteppr experts add useful recreations on real tagged game sounds while retaining the older system.

**Authorization:** The user explicitly requested autonomous iteration until a listening quality check is needed. Implement inline in the existing isolated experiment worktree; no further design approval is required.

**Architecture:** Frozen trained models generate actual synth controls. Render every proposal, retain older experts and the original neural-seeded Bfxr optimizer, and refine specialist controls with the existing bounded search. Score the exact audition PCM throughout. No retraining, metric fitting, source-label routing, source-audio playback masquerading as synthesis, or global model promotion.

**Alternatives considered:** More native training would defer the requested transfer evidence. Refitting a selector on five new comparisons risks chasing a tiny correlated batch. A small fresh tagged evaluation directly tests the next uncertainty and also produces new preference evidence.

## Frozen protocol

- Five tagged references: one each from footstep, explode, hit, clothes, laser. Use seeded shuffled file order, exclude previously judged file hashes and exact reference PCM, allow 0.025–1.8 seconds, reject silence, and never crop a long source. These categories deliberately test three impact/noise domains, rustling texture and a tonal gesture. They are not a random sample of all SFX.
- Freeze paths, original hashes, prepared reference PCM hashes and selection rejections before inference. Never use names/categories to route experts. All five are retained for listening, regardless of score.
- Old candidate pool: two predictions per engine from the shared acoustic-v2 model, four from the frozen Transfxr mixture, plus the original Bfxr neural checkpoint with 2,000 optimizer evaluations. Refine the best two distinct old synth engines with 128 proposals each. This is a focused current-system baseline, not every historical checkpoint.
- New candidate pool: four raw proposals each from new Boomr/Footsteppr experts. Refine the best raw proposal from each with 128 mutations. Old and new search each receive two starts and the same per-start budget. Seeds and randomness controls remain fixed.
- Retain raw and refined audio and scores. Use one peak normalization and PCM16 quantization per synth output, score that exact audio. Do not apply output pitch shifts or time stretching.
- Select matching-distance minima for the baseline pool and new-specialist pool. Display these alongside original Bfxr when distinct. If original Bfxr duplicates the baseline, use the strongest distinct raw specialist when available; otherwise two options. Never fabricate a difference or conceal a failed candidate. Show at most three options with shuffled identities and immediate candidate-scoped adequacy.
- Report raw/refined gains and chosen engines as numerical diagnostics only. Existing preference-neural-v2 scores are frozen secondary diagnostics, not a newly calibrated selector.
- Original Bfxr has a larger render budget than individual experts. Expanded coverage uses more total compute. Do not claim an equal-total-compute architecture comparison or generalization to unseen source families; only exclude exact previously judged audio.

## Execution and verification

- [x] Import all five submitted judgments immutably and recompute exact-audio scorer agreement in `evaluations/specialists-quick-01-human-review.py`.
- [ ] Create `evaluations/specialists-tagged-v1.py` using the existing data/model/render/search/export APIs. Freeze targets in `runs/specialists-tagged-v1/targets.json` before calling any model.
- [ ] Generate both pools and original Bfxr for each source. Store every raw candidate and finalist with parameters, seed, checkpoint hash, DSP hash and exact raw/audition PCM hashes. Persist complete per-source result files; never overwrite finished runs.
- [ ] Verify original Bfxr and multisynth finalists by actual deterministic DSP replay, exact PCM equality, recomputed objective scores, target source hashes, distinct audition options and no overlap with prior exact reference audio.
- [ ] Publish five short comparisons using the existing questionnaire. Verify HTTP payload hashes for HTML/results/every WAV and read the loaded browser page without creating judgments.
- [ ] Update durable listening-evidence documentation and experiment report, run the applicable feedback checks and `git diff --check`, and commit the experiment. Request the five-trial quality check; retain all old models.
