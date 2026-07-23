# Invert Time Features (v4 pack) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the inverse model a real time axis: finer contour hop, pad/crop instead of stretch-up, absolute-time channel, less mel blur — as `DATASET_VERSION=v4`.

**Architecture:** Invert-local packing in `invert/features_pack.py` diverges from matcher `stretch_to`. Contours extracted at hop=128 (aligned with mel). Sequences pad (silence/floor) or crop to `N_FRAMES=128`. Replace useless `active` channel with `t_abs` (seconds). Mel blur reduced for invert only. Matcher code untouched.

**Tech Stack:** PyTorch, existing `invert` + `match` packages, native renderer for regen.

**Related:** `docs/superpowers/plans/2026-07-23-inverse-model-v3-diagnosis.md`

---

### Task 1: Pad/crop + t_abs + finer hop in `pack_features`

**Files:**
- Modify: `tools/invert/features_pack.py`, `tools/invert/constants.py`
- Test: `tools/tests/test_invert_features_pack.py`

**Behavior:**
- Contour extract with FRAME=1024, HOP=128 (invert-local; do not change matcher globals).
- No `stretch_to`. If T < N_FRAMES: right-pad env with ENV_FLOOR_DB, f0/centroid/noisiness/voiced/t_abs with 0; mel pad with log-floor. If T > N_FRAMES: take first N_FRAMES (onset-preserving crop).
- Channel layout (still 6 contours + 64 mel): `env_db, f0_log2, voiced, t_abs, centroid_log2, noisiness` — **`t_abs` replaces `active`**.
- `t_abs[i] = i * HOP / SAMPLE_RATE` for real frames; 0 on pad.
- Invert mel: **unblurred** (diagnosis preferred sharper mel; stronger than σ=0.25). Matcher unchanged.
- `DATASET_VERSION = "v4"`.
- Placeholder CHANNEL_MEAN/STD length still N_CHANNELS; Task 2 re-estimates.

- [x] Tests: short wave → many pad frames + increasing t_abs on real region; long wave → no stretch (native-ish timing); shape (70, 128); determinism.
- [ ] Implement; `uv run pytest tests/test_invert_features_pack.py -q`
- [ ] Commit: `Invert v4 pack: pad/crop, hop=128, t_abs, unblurred mel`

### Task 2: Re-estimate channel stats + smoke dataset

**Files:**
- Modify: `tools/invert/constants.py` (CHANNEL_MEAN/STD)
- Optional script inline in commit message / one-shot Python

- [ ] Generate ~256 clean examples (or smoke shards), compute per-channel mean/std over non-pad-dominated frames (or all frames — document choice).
- [ ] Write stats into constants.
- [ ] `uv run python -m invert.dataset --out /tmp/inv_v4_smoke --n 64 --shard-size 32 --seed 1`
- [ ] Commit: `v4: refresh CHANNEL_MEAN/STD for new pack`

### Task 3: Identifiability canary (no full train yet)

- [ ] On clean isolated envelope/pitch renders through **v4** pack: corr(mean f0, frequency_start), corr(log_duration, sus+dec), and corr(voiced_frac or env width, sustain) — expect material lift vs stretch-era probes.
- [ ] Document numbers in `tools/invert/runs/v4_canary.md` (or stderr + commit note).

### Task 4: Regen v4 data + train + gate

- [ ] `make rebuild_inverse_model DATA=invert/data/v4 RUN=invert/runs/v4 EPOCHS=15 N=300000` (or train after gen).
- [ ] Compare sustain/decay/freq R² and in-domain one-shot vs `v3`.
- [ ] Write `tools/invert/runs/v4/gate.md`.

**Success bar (soft):** sustainTime and decayTime R² clearly above v3 (~0.24); frequency_start up; one-shot median down. Not required to hit old Wave-1 numeric gate.

---

## Out of scope (this plan)

- Multi-scale mel stack / modulation FFT (diagnosis 1b — follow-up)
- Identifiability-weighted loss (diagnosis §2)
- Matcher feature changes
- Wave-3 heads
