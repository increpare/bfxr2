# Test-time surrogate refine — listen verdict

**Date:** 2026-07-25  
**Plan:** `2026-07-25-inverse-model-test-time-refine.md`  
**Checkpoint:** `v7_real_ft/best.pt` + `surrogate/surrogate.pt`  
**Candidate:** `--surrogate-refine-steps 100`, `--surrogate-refine-lr 1e-2`  
**Page:** `tools/invert/runs/tt_refine_listen.html`  
**Seeded column:** reused `gateA_legacy` model_seeded (ceiling reference)

## Scores (0–5, listener)

| target | raw one-shot | refined one-shot | model seeded |
| --- | ---: | ---: | ---: |
| Mario 1 - Jump | 3 | 1.5 | 2 |
| Mario 2 - Throw | 1 | 1 | 3 |
| Mario 3 - jump (nes) | 1 | 1 | 0 |
| Mario 3 - jump (snes) | 2.5 | 1.5 | 2 |
| Mario Break Brick | 1 | 1.2 | 2 |
| chrono_trigger_leeneBell | 1.5 | 2.5 | 4 |
| mario 2 - jump | 1.5 | **0** | 2 |
| mega_man_ii_beam-out | 1.5 | 2 | 4 |
| mega_man_ii_one-up | 1.5 | 1 | 4 |
| mega_man_iii_cursor | 1 | 1.5 | 4 |
| **mean** | **1.55** | **1.32** | **2.70** |

Refined > raw on 4/10, worse on 4/10 (including a mute at 0), tied on 2/10.

## MatchObjective (footnote)

All ten refined one-shots scored **worse** on the match metric than raw
(Δ about +1.4 to +9.8). Surrogate feature MSE and ears both failed to prefer
the refined arm.

## Verdict: FAILED

Listener: refined is **not** acceptably better than raw; new trash/mute on
`mario 2 - jump`. Per the plan: leave default `--surrogate-refine-steps 0`.
Do not retune lr/steps hoping for a listen win.

The code (`invert/refine.py`, CLI flags, listen page) stays in tree for
experiments; shipping path unchanged.

## Consequences / next

From `2026-07-25-inverse-model-next-bets.md`:

1. ~~Test-time surrogate refine~~ — tried; failed listen gate.
2. **Multi-hypothesis seeding** — next bet if still optimizing seed+search.
3. Sharper surrogate → short real-FT — only if a future proxy proves useful
   at inference; this run argues the current surrogate gradient hurts
   one-shots on the hard slice.
