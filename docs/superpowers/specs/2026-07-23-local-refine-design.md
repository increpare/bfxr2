# Local refine (steepest descent) — design

## Goal

Add a reusable **local polish** stage that improves an already-good Bfxr match by finite-difference steepest descent on continuous parameters, holding discrete and irrelevant parameters fixed. First demo: polish the bakeoff `current` winner for `mega_man_ii_hurt`.

## Context

- Search space today: all RANGE params in a unit cube (`ParamSpace`); only `waveType` is categorical.
- Matcher today: Stage 0 random screen → Stage 1/2 CMA-ES (`StagedOptimizer`). No local refine.
- Scoring: `MatchObjective` (contour + light mel); lower is better.
- Rendering: native `BfxrRenderer` (fast enough for ~12k evals).

## Non-goals

- Replacing CMA / library bakeoff.
- Differentiating through the DSP (black-box FD only).
- Optimizing `waveType` or inventing new metrics.

## Algorithm

**Coordinate steepest descent** on the unit vector `u ∈ [0,1]^d` (axis-aligned local search):

1. Start from a seed `(u0, wave_type)` (from `.bfxr` or CMA best).
2. Each step: score `u ± eps e_i` for every **free** dim; take the single best improving neighbor (or stop improving).
3. Default **200** steps; early-stop if no improvement for N consecutive steps (e.g. 20).

**Why not combined FD gradients?** The MatchObjective landscape is highly discontinuous — central differences look huge, but multi-dim gradient steps fall off cliffs. Picking the best single-axis ±eps move uses the same probe budget and actually descends.

Defaults: `eps = 0.015`, `max_steps = 200`. Tunable via CLI/settings. Score each probe alone (not one joint batch) so padding in `MatchObjective` cannot contaminate neighbors.

## Frozen parameters

| Kind | What | Behavior |
|------|------|----------|
| Discrete | `waveType` | Fixed for the whole refine |
| Irrelevant (non-square) | `squareDuty`, `dutySweep` | Frozen at ParamSpace defaults (DSP ignores them off-square) |
| Locked | `masterVolume` | Already outside the cube; stay `0.5` |

All other RANGE dims are free, subject to existing envelope upper bounds / projection used by `StagedOptimizer.params_for`.

## Integration

1. **Library:** `tools/match/refine.py`
   - `free_mask(space, wave_type) -> bool[d]`
   - `steepest_descent(unit, wave_type, renderer, objective, space, *, upper, settings) -> (unit, score, history)`
2. **Optimizer hook:** optional Stage 3 in `StagedOptimizer.run()` when `refine_steps > 0`.
3. **CLI:** `python -m match.refine --target WAV --seed BFXR -o OUT_DIR [--steps 200]`
   - Writes `refined.bfxr`, `refined.wav`, `before.wav`, `compare.html` (target / before / after).
4. **Demo:** seed = `metric_compare/mega_man_ii_hurt/current_match.bfxr`, target = `targets/mega_man_ii_hurt.wav`.

## Scoring / rendering contract

- Reuse `StagedOptimizer.params_for` (or equivalent) so envelope cap + square defaults stay consistent.
- Fixed render seed (`RENDER_SEED`) unless caller overrides.
- Objective constructed once per target; no library-cache path required.

## Success criteria

- Standalone refine on hurt: score strictly improves vs seed (or early-stops cleanly if stuck).
- A/B HTML lets a human compare target / before / after.
- `--refine-steps 200` on main match path runs Stage 3 without breaking existing defaults (`refine_steps=0`).
- Unit test: free_mask freezes square-only off-square; FD step with a tiny mock/stub or smoke on 1–2 dims if cheap enough.

## Out of scope for v1

- SPSA / coordinate descent variants (keep as later fallback).
- Multi-start from several bakeoff metrics.
- Disk-caching of refine trajectories.
