# Mixr external-reference composition probe

**Goal:** Test whether two simultaneous synth voices improve four previously judged external sounds, using the shipped Mixr DSP and reopenable controls.

**Design:** Add an isolated composition bridge; keep the existing single-synth renderer and source hash unchanged. Load the shipped synth classes, Stackr and Mixr. Canonicalize source snapshots through Mixr and render with its native source-seed semantics. Cache source PCM only as an optimization, proving cached mixtures equal `Mixr.generate_sound()` on reopening. Footsteppr is excluded from this first bridge because its separate PureData host is not loaded; document that scope.

**Alternative hypotheses:** More training examples did not produce clear external improvements. Existing metric-selected single voices may lack simultaneous components; two-source Mixr is a bounded expressive-coverage test. A similar single-voice control and exact earlier audio distinguish composition from seed/backend re-rendering. This is deterministic candidate search, not a newly trained Mixr neural network.

**Targets fixed before inference:** Existing hit/pat, door-close and laser (all three displayed options rejected), plus cloth4 (similar Rustlr control). Select reference PCM from the complete archived session. Keep its human-preferred candidate, or prior soft winner where all were rejected. No quality-based removal after the probe.

**Search:** Re-render all saved raw/refined single-source controls through the composition bridge, including original Bfxr parameters. Deduplicate PCM; seeds are explicitly converted to Mixr's normalized source seed and recorded. Select a pool of up to12 sources by alternating soft and frozen-preference ranks, with at most2 per synth. Test every unordered pair at balances .2,.35,.5,.65,.8 with fixed Mixr masterVolume .5 and seed .5. Rank all mixtures with both frozen scorers; listen to the soft winner in this pilot. Include the soft-selected single-source Mixr control and exact earlier candidate. This does not establish that rejected or omitted mixtures are bad.

**Files:** `tools/render/composition_context.js`, `composition_worker.js`, `tools/multisynth/composition.py`; worker tests in `tests/composition-context.test.js`; experiment script and immutable protocol/audits under `tools/multisynth/evaluations/mixr-transfer-v1*`; run artifacts ignored under `runs/mixr-transfer-v1*`.

**Validation:** First test deterministic cached/full-render equality, source order/balance, source RNG independence, saved-patch roundtrip, invalid/nested source rejection and source-hash inclusion. Then verify all source/control/PCM hashes and actual Mixr replay on selected mixtures; reference and earlier candidate must match archived PCM exactly. Check actual displayed option count after deduplication, no fabricated telemetry, and every HTTP asset. Existing quick-feedback tests remain required.

**Execution:** Archive complete feedback and verify cumulative deduplication; implement/test bridge; freeze four references and code hashes; generate/rank mixtures; export four comparisons with immediate adequacy; record limits and ask for human feedback only after the page works. User's standing autonomous authorization covers this experiment; no source synth or model default changes.
