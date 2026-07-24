# Inverse Model — spectral-loss experiment results

**Date:** 2026-07-23
**Branch:** `feature/inverse-model-next-steps`
**Plan executed:** `2026-07-23-inverse-model-spectral-loss.md` (all code tasks landed + gated; run/gate tasks executed here)
**Data:** `invert/data/v4` (300k, pad/crop time features, unblurred mel), eval budget 2000.

## TL;DR

Of the three legs of the "alternative approach," **only the spectral loss moved the needle, and only in-domain.**

1. **v4 time-features** (finer hop, pad/crop, `t_abs`, unblurred mel): helped pitch (`frequency_start` R² 0.41→0.47) but **did not** recover the envelope — `sustainTime`/`decayTime` stayed ~0.24, unchanged from v3. The "stretch-up destroyed the timeline" hypothesis was only partly right.
2. **Identifiability weighting + curriculum (Phase 1):** a **wash** — every per-param R² delta is noise-level; `unit_mse` and top-3 unchanged. Reweighting doesn't manufacture information at the ceiling.
3. **Spectral loss via a differentiable surrogate (Phase 2):** the winner **in-domain** — one-shot median improved monotonically with spectral weight (5.46 → 4.56 → 3.66), at the cost of slightly worse parameter R² (as the literature predicts: spectral loss trades *param* accuracy for *sound* accuracy). But it **does not transfer out-of-domain** to real game SFX.

## Runs

| run | config | best epoch | val unit_mse | top-3 |
| --- | --- | --- | --- | --- |
| `v4_baseline` | uniform weights, no curric, no spectral | 7 | 0.0448 | 0.853 |
| `v5_weighted` | identifiability weights + curriculum-5 | 10 | 0.0450 | 0.854 |
| `surrogate` | params→features, 20 epochs | — | recon MSE **0.226** (<0.3 gate; ~77% of feature variance) | — |
| `v6_spectral` | curric-5 + spectral-weight 1.0 | 14 | 0.0463 | 0.850 |
| `v7_spectral3` | curric-5 + spectral-weight 3.0 | — | (spectral term active ~0.18) | — |

## In-domain (bfxr presets, 9 targets)

| model | one-shot median | seeded median | seeded ≤ current |
| --- | --- | --- | --- |
| baseline | 5.46 | 0.94 | 7/9 |
| spectral w1.0 | 4.56 | **0.85** | 7/9 |
| spectral w3.0 | **3.66** | 0.91 | 6/9 |

Per-target one-shot (baseline → w1.0 → w3.0): Jump 5.20→2.43→2.45, Random 5.47→2.41→3.40, Random1 5.46→3.74→4.43, Pickup 9.27→6.44→**2.06**, PowerUp 2.23→2.83→**1.48**, Shoot 9.37→9.97→8.76. A few regress (Hit 4.24→6.55).

**The tradeoff:** w1.0 is the best *seeder* (feeds CMA search; seeded median 0.85, 7/9); w3.0 is the best *one-shot* (raw guess; median 3.66) but a slightly worse seeder. Choose by use: seed-and-refine → w1.0; standalone one-shot → w3.0.

## Out-of-domain (real game SFX, 32 targets)

| model | one-shot median | seeded median | seeded ≤ current |
| --- | --- | --- | --- |
| baseline | 9.72 | 3.30 | 10/32 |
| spectral w1.0 | 10.14 | 3.75 | 9/32 |

Spectral seeds better than baseline on only 16/32 (coin flip), one-shot on 13/32. **No transfer.**

## Interpretation

The spectral loss works exactly as the literature (Masuda & Saito) says — it optimizes for *sound match* rather than exact parameters — and the in-domain monotone improvement is clean evidence the surrogate + combined-loss machinery is wired correctly and does its job. But the surrogate was trained only on bfxr-rendered features, so it knows only the **bfxr manifold**. In-domain targets live on that manifold and benefit; real SFX live *off* it, so the surrogate-based spectral gradient points at "the nearest bfxr-renderable sound the surrogate can imagine," which does not generalize. This is the exact two-regime / domain-shift thesis from the diagnosis: the in-domain surrogate cannot cross the domain gap.

## Recommendation / next step

- **Ship the spectral model as the in-domain seeder now** (w1.0 for seed-and-refine, or w3.0 if standalone one-shot is the priority). It is a strict in-domain improvement over the param-only baseline.
- **For the real-SFX (general-purpose) goal, do the deferred follow-on:** spectral-loss **fine-tuning on unlabeled real audio** (Masuda's semi-supervised result — the best out-of-domain matches there came from adapting on real recordings with spectral loss, which needs no parameter labels). The surrogate-on-synthetic path proven here is the prerequisite machinery; the missing piece is exposing it to real audio during training.
- **Drop** the identifiability-weighting/curriculum leg (wash) and further pursuit of envelope recovery via time-features alone (didn't work). Keep the `--uniform-weights` and weighting code — harmless and useful for ablations.

## Reproduce

```
# from tools/
uv run python -m invert.train --data invert/data/v4 --out invert/runs/v4_baseline --epochs 15 --uniform-weights
uv run python -m invert.surrogate --data invert/data/v4 --out invert/runs/surrogate --epochs 20
uv run python -m invert.train --data invert/data/v4 --out invert/runs/v6_spectral --epochs 15 \
    --curriculum-epochs 5 --surrogate invert/runs/surrogate/surrogate.pt --spectral-weight 1.0
make eval_inverse_model_all RUN=invert/runs/v6_spectral CKPT=invert/runs/v6_spectral/best.pt
```
