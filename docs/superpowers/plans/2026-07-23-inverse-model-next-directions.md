# Inverse model — where to go next

**Date:** 2026-07-23
**Branch:** `feature/inverse-model-next-steps`
**Context:** Follows `2026-07-23-inverse-model-spectral-results.md`. The spectral-loss model (`v6_spectral`, w1.0) recreates bfxr's own presets well (seeded median ~0.85) but is only genre-level on real SFX (seeded median ~3.75). This report lays out what to do next, split by the two goals — **(A) make in-domain reconstruction better** and **(B) make general/real-SFX reconstruction better** — and calls out the **length** defect as the highest-impact, most fixable issue.

Listening pages: `invert/runs/v6_spectral/recreations.html` (in-domain) and `recreations_real.html` (real SFX).

---

## Priority 0 — Fix the length collapse (cheapest, most visible)

The most jarring failures are reconstructions that are a *fraction of the target's length*. Measured recreation-length / target-length ratios:

| set | one-shot median | seeded median | seeded < 0.5× | seeded ~0× |
| --- | --- | --- | --- | --- |
| in-domain (n=9) | 1.57× | 1.03× | 2/9 | — |
| real SFX (n=32) | 0.86× | 0.99× | **6/32** | several (0.00–0.04×) |

Worst real-SFX cases (seeded): `iceMagic` 2.02s→0.00×, `mega_man_ii_dead` 1.72s→0.01×, `wily-fortress-appear` 3.25s→0.01×, `gateActivate` 0.74s→0.01×, `charm1` 1.26s→0.22×.

**Two independent roots:**

1. **The 1.5s training cap** (`TRAIN_CAP_SECONDS = 1.5`). 6/32 real targets exceed it; the model never saw sounds that long and cannot represent them. All the worst >1.5s targets are in this bucket.
2. **Envelope collapse.** Sub-cap targets (`gateActivate` 0.74s, `charm1` 1.26s) still collapse to near-silence, consistent with the weak envelope R² (`sustainTime`/`decayTime` ≈ 0.24). Off-manifold, the model's envelope prediction degenerates.
3. **The metric tolerates it.** A search that returns a 0.00× "sound" and still scores acceptably means the match objective is not penalizing missing duration/energy — it rewards matching the onset and ignoring the tail.

**Fixes (do in this order):**

- **Condition on the known target duration.** At match time we already compute the target's length; use it. Pin the seed's envelope (`attackTime`/`sustainTime`/`decayTime`) so the rendered length ≈ target length, and add a hard duration prior to the search so candidates can't drift to a blip. This is a targeted change in `match/optimizer.py` / the seed path — cheap, high impact, needs no retraining.
- **Add an energy-coverage / duration penalty to the metric** (`match/objective.py`): penalize candidates whose energy envelope ends well before the target's. Stops the search from abandoning length.
- **Raise or window the cap** for long targets: either bump `TRAIN_CAP_SECONDS` (regenerate data) or, cheaper, match long targets in overlapping ≤1.5s windows and concatenate. Bumping the cap also means retraining, so scope it against how many real targets are actually >1.5s.

---

## Goal A — Make in-domain reconstruction better

The mechanism works; the ceiling is set by (a) the surrogate's fidelity and (b) how hard we push the spectral objective.

- **Improve the surrogate.** Its reconstruction MSE is 0.226 (captures ~77% of feature variance) — mediocre, and it *is* the spectral gradient. A sharper surrogate → a truer "right sound" signal. Try: wider/deeper decoder, longer training, and a **multi-scale spectral target** (match the matcher's 4 mel scales, not the single scale the surrogate currently learns).
- **Push / anneal the spectral weight.** One-shot improved monotonically (5.46→4.56→3.66 at w1.0→w3.0). Try w5–8 and a schedule that ramps spectral weight up over training. Accept that param R² drops — sound is what matters here.
- **Close the loop end-to-end.** The spectral loss currently uses *ground-truth* wavetype for the surrogate's onehot. Switch to the model's own softmax so classification is also trained by the spectral signal (the machinery already routes through `select_unit_pred`; this is a small change).
- **Test-time refinement (cheap one-shot win).** At inference, run a few gradient steps on the predicted params *through the frozen surrogate* to minimize spectral distance to the target, before (or instead of) the full CMA search. This sharpens the raw one-shot for near-free and is exactly what the differentiable surrogate enables.

---

## Goal B — Make general (real-SFX) reconstruction better

This is the "same genre → closer" problem, and it has one clear lever plus one hard ceiling.

- **The lever: spectral-loss fine-tuning on real audio** (Masuda & Saito's semi-supervised result — the deferred follow-on). Because the spectral loss needs no parameter labels, we can fine-tune the Phase-2 model directly on a corpus of real SFX (freesound, game-audio packs, the existing `targets/`), loss = spectral only, low LR, from the `v6_spectral` checkpoint. This is the single highest-value action for the user's actual goal; the surrogate + spectral machinery built here is its prerequisite. Split the real corpus into train/holdout so gains are measured on unseen sounds. NB: this also needs a surrogate that generalizes — consider training the surrogate itself partly on real audio, or accept it stays bfxr-manifold and rely on fine-tuning to adapt the *inverse* model.
- **Domain-robustness augmentation.** Perturb training inputs to mimic real-SFX artifacts (recording noise, EQ, reverb tails, resampling) so the model stops trusting bfxr-specific fine structure that doesn't transfer — the "distort inputs to make taggers robust" idea, now targeted at the specific transfer failure.
- **Better OOD search, since the model barely helps there.** More budget than 2000, multi-hypothesis seeds (start CMA from several distinct basins), and the metric/duration fixes from Priority 0 — these help the search that is doing most of the OOD work.
- **The hard ceiling (name it, don't fight it).** Many real timbres are simply outside bfxr's reachable space — the melodic/tonal targets (`leeneBell`, `iceMagic`, Mario jumps) sit at the bottom of the sorted list because the synth can't produce them, not because the model failed. Closing that gap needs **new synth capabilities** (band-pass / colored noise, a simple formant filter, tremolo — the original roadmap's "Q8"). That is a different project (and dovetails with the original preset-mining sub-project), but it is the real limit on general reconstruction and should frame expectations: the inverse model can only ever find the closest *reachable* sound.

---

## Recommended shortlist (by value / effort)

1. **Length fixes (Priority 0)** — duration conditioning + metric energy-coverage penalty. Cheap, no retraining, kills the most visible failures. Do first.
2. **Spectral-loss fine-tune on real audio** — the general-reconstruction lever. Medium effort; the machinery exists.
3. **Better surrogate + test-time refinement** — the in-domain "make it better" bundle. Cheap-to-medium.
4. **Synth extensions for unreachable timbres** — longer horizon; the true ceiling on real-SFX matching, and shared with the preset-mining sub-project.

Items 1 and 3 need no new data or labels and could land immediately; item 2 needs a real-audio corpus; item 4 is a separate track.
