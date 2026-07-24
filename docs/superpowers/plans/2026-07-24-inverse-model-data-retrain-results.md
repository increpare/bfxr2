# Inverse-model data-retrain results (scope 3)

**Date:** 2026-07-24  
**Branch:** `feature/inverse-model-next-steps`  
**Synth winner:** `invert/runs/v7_finetune_200k/best.pt`  
**Final (real-audio) checkpoint:** `invert/runs/v7_real_ft/best.pt`

## What ran

1. **v5 canary data** — 200k examples, MIX with `structured 0.25`, `augment_p 0.4`, retro + cull.
2. **Scratch** — 22 epochs, curriculum-5, spectral-weight 1.0 → `v7_scratch_200k`.
3. **Synth finetune** — from v6, lr 1e-4, 5 epochs, curriculum off → `v7_finetune_200k`.
4. **Real spectral finetune** — from synth finetune, 5186-file capped manifest (`targets_non_bfxr_big`, product `targets/` excluded), 5 epochs, lr 1e-4 → `v7_real_ft`.

Scale ladder (500k→1M) **not run** — canary already beat v6 on primary gates.

## Product eval (`tools/targets/`, n=32, budget 2000)

Lower is better.

| model | one-shot median | seeded median |
| --- | ---: | ---: |
| v6_spectral | 10.797 | 3.151 |
| v7_scratch_200k | 10.437 | 2.723 |
| v7_finetune_200k (synth) | 9.561 | 2.906 |
| **v7_real_ft** | **8.980** | **2.610** |

Primary gate (one-shot) improves at each stage. Seeded also best at real-ft.

## In-domain sanity (synth val)

| run | best val unit_mse | notes |
| --- | ---: | --- |
| v6 (prior) | ~0.046 | — |
| v7_scratch_200k | 0.0358 | pitch_jump_amount R² ~0.28 |
| v7_finetune_200k | 0.0340 | pitch_jump_amount R² ~0.20 |

No catastrophic in-domain regression vs v6.

## Real-ft training

Holdout spectral: 0.356 → 0.315 over 5 epochs (monotonic).

## Decision

**Best relative baseline (not product-ready):** `invert/runs/v7_real_ft/best.pt`  
Beats v6 and synth-only canary on product medians; listen pairwise also prefers real FT
one-shots vs v6 (20–12) and vs synth FT (18–14). Absolute quality is still far from
acceptable (~1–3/5 on a hard slice). Synth FT is a metric mirage on one-shots (ears
13–19 vs v6).

**Next:** structure-aware metric + auto probes before more training — see
`docs/superpowers/specs/2026-07-24-inverse-model-structure-metric-design.md`.
