# Inverse Model — Test-Time Surrogate Refine Design

**Date:** 2026-07-25  
**Status:** design approved — implementation plan next  
**Branch:** `feature/inverse-model-structure-metric`  
**Strategy context:** `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md` (product mode C; bet 1)  
**Baseline checkpoint:** `tools/invert/runs/v7_real_ft/best.pt` (frozen — no inverse-model retrain in this plan)  
**Surrogate:** existing `tools/invert/runs/surrogate/surrogate.pt` (or path recorded in the v7 real-FT run config); frozen during refine

## Goal

Sharpen the inverse model’s predicted parameters **at inference** by gradient
descent through the frozen `SurrogateSynth`, so that one-shot and CMA seeds
move closer (in packed-feature space) to the target before any render/search.

This is the InverSynth II–style inference-time finetune applied to our existing
proxy. It does **not** retrain the inverse model or the surrogate.

Product framing (from next-bets): optimize **seed + search** first; treat a
better one-shot / sub-second refine as the path toward a nicer “instant” UX.

## Why

1. One-shot on the hard slice is ~1.2/5; seeded search often reaches 3–4/5 on
   the same targets. The model is a weak initializer relative to CMA + arp seeds.
2. We already train with spectral loss *through* `SurrogateSynth` and have
   real-FT machinery that uses the same proxy — but we never optimize the
   **predicted unit** at test time.
3. Gate B showed that changing the match objective’s structure term did not
   move ears. The next lever is the **seed**, not another judge tweak.
4. Literature (InverSynth II, ISMIR 2023) reports clear gains from a few
   proxy-gradient steps at inference, with no labeled retrain.

## Decisions

| Decision | Choice |
| --- | --- |
| Lever | Test-time refine of predicted `unit` through frozen surrogate |
| Inverse model / surrogate | **Frozen**; only the param vector (and optimizer state on it) updates |
| Wavetype | **Fixed** to the model’s chosen class (hard one-hot); soft wavetype deferred |
| Scope of first plan | Refine every unit `predict_wave` already returns (1 if one-shot, else top‑3). Not a new multi-hypothesis sampler |
| CLI | `--surrogate-refine-steps N` (default **0** = off); `--surrogate-refine-lr`; `--surrogate` required when steps > 0. **Not** `--refine-steps` — that flag already means Stage 3 FD steepest descent in `match.py` / `OptimizeSettings` |
| Default on | **Off** until listen gate passes; then consider a small non-zero default |
| Claim gate | Human listen on the hard slice: refined one-shot vs raw one-shot; seeded as ceiling |
| Retrain | **Out of scope** |
| Structure term | Unchanged (stays default weight 0.0) |
| Multi-hypothesis K / surrogate retrain | Out of scope (next-bets 2 and 3) |

## Section 1 — Algorithm

Inputs: target waveform; inverse-model checkpoint; surrogate checkpoint;
`refine_steps` (≥1 to run); learning rate.

1. Pack and normalize target features `x` and `log_duration` exactly as
   `invert.predict` / training (`pack_features` → `normalize_channels` with
   checkpoint channel stats).
2. Run the inverse model once → top wavetype `wt` and unit vector `u0`
   (same pinning of square-only params as `predict_wave`).
3. Create `u` as a leaf tensor `requires_grad=True`, initialized from `u0`,
   shape `(1, N_PARAMS)`. Build hard one-hot for `wt`.
4. For `t = 1 .. refine_steps`:
   - `pred = surrogate(u, onehot, log_duration)`
   - `loss = MSE(pred, x)`
   - Adam step on `u` only; clamp `u` to `[0, 1]` after each step
5. Detach → numpy; re-apply square-only pin for `wt`; return refined unit
   (and unchanged `wt`).

**Non-goals for v1:** optimizing soft wavetype probs; multi-scale losses beyond
the surrogate’s feature MSE; rendering inside the refine loop.

## Section 2 — Integration

**New module:** `tools/invert/refine.py`

- `refine_unit(unit, wave_type, target_features_norm, log_duration, surrogate, *, steps, lr, device) -> np.ndarray`
- Thin wrapper that loads surrogate if given a path.

**Call site:** `tools/match/match.py` after `predict_wave`, when
`--surrogate-refine-steps > 0` and `--seed-model` is set:

- **One-shot:** refine the single top guess, then render as today.
- **Seeded CMA:** refine every seed `predict_wave` returned (typically top‑3).
  Cheap at 50–100 Adam steps; preserves existing top‑K diversity. Not a new
  multi-hypothesis generator.

**Flags (match CLI + passthrough from `invert.eval_targets` for batch A/B):**

| Flag | Default | Notes |
| --- | --- | --- |
| `--surrogate-refine-steps` | `0` | Off (name avoids clashing with Stage 3 `--refine-steps`) |
| `--surrogate-refine-lr` | `1e-2` | Adam on unit |
| `--surrogate` | required if steps > 0 | Path to `surrogate.pt` |

Report JSON should record `surrogate_refine_steps`, `surrogate_refine_lr`, and
surrogate path when used.

## Section 3 — Tests

Unit-level (no full CMA):

1. **Smoke:** `surrogate_refine_steps=0` path unchanged (no surrogate load).
2. **Loss drops:** build target features as `surrogate(unit_true)` (same
   frozen net); start from a perturbed unit; after N steps, MSE to those
   features is strictly below the initial MSE.
3. **Bounds:** refined unit stays in `[0, 1]`; non-square wavetype still has
   square-only dims pinned to defaults after refine.
4. **Wavetype fixed:** wave_type id is an input and is not changed by refine.

No claim that match-objective score always drops — the surrogate feature space
is not identical to `MatchObjective`.

## Section 4 — Eval / claim gate

**Engineering check (automated):** test suite above + a small script or
`eval_targets` mode that writes refined one-shots for the hard slice
(reuse `listen_compare` HARD_SLICE).

**Claim gate (human):** listen page with columns at least:

- original
- raw one-shot (`--surrogate-refine-steps 0`)
- refined one-shot (`--surrogate-refine-steps` = candidate, e.g. 50 or 100)
- current `model_seeded` (ceiling reference)

**Success:** refined one-shot is acceptably better than raw by ear on the hard
slice, without obvious new mutes/trash. Seeded may still win; that is OK under
product mode C.

**Failure:** no audible one-shot gain, or systematic trash → leave default
`--surrogate-refine-steps 0`, document in a results note, proceed to next-bets
(2) rather than retuning lr forever.

## Section 5 — Out of scope

- Retraining inverse model or surrogate
- Soft wavetype optimization during refine
- Generative / multi-hypothesis sampling beyond existing `top_k`
- Match objective / `structure_pitch` changes
- Synth capability extensions
- Declaring product-ready one-shot quality

## Success criteria

| Stage | Success | Verified by |
| --- | --- | --- |
| Engineering | Refine lowers surrogate MSE on a controlled in-domain case; bounds + wavetype invariants hold | Section 3 tests |
| Evidence | Hard-slice refined vs raw one-shot artifacts written | Section 4 script |
| Claimed improvement | Listener: refined better than raw one-shot; no major new failures | Section 4 listen |
| Explicit non-goal | Matching seeded quality in one forward pass | — |
