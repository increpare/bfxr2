# Inverse model — v3 diagnosis and next steps

**Date:** 2026-07-23
**Branch:** `feature/inverse-model-next-steps`
**Inputs:** `tools/invert/runs/{v2_flatten,v3,v3_wide,v3_twophase}` (train logs, `gate.md`, `escalation.md`, `eval_bfxr`, `eval_targets`); follow-up feature-pack probes on preset-like renders
**Status:** Wave-1/Wave-2 gate FAIL. This report explains *why* the gate fails, argues it is not a capacity problem, and recommends what to do next.

---

## TL;DR

We've hit an **information ceiling**, not a modeling wall — but the ceiling has **two layers**:

1. **Self-inflicted representation ceiling** — invert reuses matcher features (`stretch_to` + coarse contour hop). For typical bfxr/preset SFX the contour time series barely exists before stretch invents one (median ~9 native frames → 128, ~14×). Envelope knobs cannot be recovered from that no matter how wide the net is.
2. **Task ill-posedness** — many params are weakly audible or inactive in most renders; uniform MSE dilutes the loss toward predicting their means.

Stop scaling the network. Instead: (1) **invert-specific time features** (finer hop, pad/crop, no stretch-up); (2) **identifiability-weighted loss + honest re-gate**; (3) treat the model as a search *seeder*; (4) longer-term, render-in-the-loop via a differentiable surrogate if one-shot must improve. Deprioritize Wave-3 multi-hypothesis heads and any further width experiments.

---

## The one fact that reframes everything

Across all v3-family runs, **train and val `unit_mse` are essentially identical and both plateau**:

| run | train unit_mse | val unit_mse |
| --- | --- | --- |
| `v3` (joint) | 0.0427 | 0.0440 |
| `v3_wide` (width 192 + dilated) | ~0.0427 | 0.0440 |
| `v3_twophase` (5 CE → freeze trunk) | — | 0.0449 |

`v3` train unit_mse falls 0.0480 → 0.0427 over 15 epochs and stops; val tracks it the whole way (0.0460 → 0.0442). There is **no train/val gap**.

This rules out the usual suspects:

- **Not overfitting** — train ≈ val, so we are not memorizing.
- **Not under-capacity** — width 192 + dilations (`v3_wide`) lands on the *same* floor. A capacity-starved model would improve when widened; this one doesn't.
- **Not the CE/knob gradient fight** — two-phase (freeze trunk after CE warmup) also lands on the same regression floor (and costs top-3).
- **Not a label/pairing bug** — the Wave-1 canary confirmed stored features ≈ re-render of labels (corr 0.999 on a 32-row sample).

When a model cannot fit its *own training set* below a floor, on data it has exact labels for, and more capacity doesn't help, the floor is in the **inputs / task**, not the network size.

Oracle-wavetype + model-knobs one-shot stays ~8 (same as full one-shot): **knob regression is the failure mode**, not wavetype classification.

---

## Layer 1: invert ≠ matcher features (representation ceiling)

The invert pack reuses `match/features.py` contours and the matcher's `stretch_to(N_FRAMES)`. That is a **category error**:

- The **matcher** wants duration-invariant shape comparison (stretch is a feature).
- The **inverter** needs absolute timing and a real time axis to recover envelope / jump onset / sweeps.

### Contour hop is far too coarse for bfxr SFX

Contour framing is FRAME/HOP = 2048/512 (~11.6 ms). On 64 preset-generator renders:

| | value |
| --- | --- |
| median duration | ~145 ms |
| median native contour frames | **9** |
| stretch to 128 | **~14×** |
| ≤4 native frames | **~38%** |
| stretched *up* to 128 | **100%** |

A ~38 ms blip → **1** native frame → linear interpolate to 128. Most of the "envelope contour" is fabrication. Sustain vs decay cannot be split from that; attack still partly survives as onset shape in normalized time — matching the R² pattern (`attackTime` ~0.70 vs `sustainTime`/`decayTime` ~0.24–0.27).

Clean probes (isolated knobs, no stretch ambiguity) show the *audio* carries signal the pack discards:

- `mean_f0` ↔ `frequency_start` ≈ **0.90**
- `log_duration` ↔ `sustain+decay` ≈ **0.88**
- individual sustain/decay from time-normalized env alone: weak / mixed

So envelope/pitch underperformance is not "physics says unknowable"; it is "our tensor barely has a timeline."

### Mel helps wavetype/duty, not flanger

The design already noted contours alone cannot see duty / flanger / resonance, so blurred log-mel was added. Probes:

- Square vs saw: healthy mel RMSE — wavetype cue present.
- `squareDuty`: visible (e.g. centroid corr ≈ −0.9).
- **`flangerOffset`: mel-bin mean corr ≈ 0** — blur + averaging wipe comb structure. Collapsed flanger R² is a feature-visibility issue, not only "subtle in the mix."

`active` is nearly constant on these loud short renders (near-useless channel).

### Why capacity / two-phase could not move the floor

More width cannot invent temporal samples that stretch interpolated away. Two-phase lands on the same regression floor for the same reason.

---

## Layer 2: the inverse isn't a function (task ill-posedness)

`params → audio` is deterministic, but `audio → params` is many-to-one. Large regions of parameter space render to identical or perceptually indistinguishable sound.

Final-epoch per-param R² for `v3` splits cleanly into two groups:

**Partially recoverable (audio + decent features can constrain them):**

| param | R² |
| --- | --- |
| attackTime | 0.70 |
| compressionAmount | 0.68 |
| bitCrush | 0.59 |
| hpFilterCutoff | 0.46 |
| frequency_start | 0.41 |
| overtones / repeatSpeed / frequency_slide / min_freq / lpFilterCutoff | 0.36–0.38 |

**Weakly recoverable with *current* features (audio barely constrains them, or features erase them):**

| param | R² | why |
| --- | --- | --- |
| flangerOffset / flangerSweep | ≈ 0.00 | invisible in blurred mean-mel; often subtle |
| lpFilterCutoffSweep / hpFilterCutoffSweep | ≈ 0.00 | sweep of a filter that's often already open/closed |
| pitch_jump_amount / pitch_jump_2_amount | 0.02–0.03 | jump frequently never fires or is inaudible; onset needs time axis |
| squareDuty / dutySweep | negative | square-only; labels pinned for 11/12 wavetypes (metric artifact vs loss mask) |
| vibratoDepth / overtoneFalloff | ~0.22 | weakly audible in short SFX |
| sustainTime / decayTime | ~0.24–0.27 | sum in `log_duration`; split destroyed by stretch |

For the bottom group the Bayes-optimal prediction is often the prior mean, and MSE floors near prior variance. Because training **averages MSE across all 30 params**, dead params dilute gradients away from sharpening readable ones. That contributes to `frequency_start` (0.41) trailing the isolated mean-f0 canary (corr 0.73 ≈ R² ~0.5) — alongside multi-knob pitch ambiguity, stretch, and aug on full shards (full-shard f0↔label corr was already weak).

**Corollary about the gate.** The Wave-1 gate (`frequency_start` R² ≥ 0.8, `sustainTime` ≥ 0.7, …) was **optimistic given current features**. The isolated canary suggests a *probe* ceiling near ~0.5 R² for naive mean-f0 — not a hard audio-theoretic cap forever. With invert-specific time features, higher envelope/pitch R² is a testable hypothesis. `escalation.md`'s "modeling/inductive-bias wall" is half right: it is a wall, but primarily **representation + objective**, not one that per-wavetype heads will break.

`frequency_start` residuals on v3 are **unimodal** around 0 (not ±octave) — weak evidence for pitch mode-averaging as the current bottleneck.

---

## What the model is actually good at: seeding search

One-shot is genuinely bad (in-domain median ~8; oracle wavetype does not save it). But **one-shot was always the growth metric, not the bar** — the design bar was "better matches as a seeder." On that axis the model helps:

- **In-domain (`eval_bfxr`):** Wave-2 model-seeded beats current on 5/9 (Pickup 3.26 → 1.52, Boom 1.15 → 0.60, …). Wave-1 was 7/9 seeded — seeding quality is real but run-dependent; do not overfit narrative to one table.
- **Real SFX (`eval_targets`):** seeded wins 8/32 (Wave-1 was 6/32), including hard `mega_man_ii_beam-out` (3.05 → 2.84) and some Chrono hits.

Out-of-domain game SFX often live outside bfxr's reachable space — no inverse recovers what the synth cannot produce; seed-then-refine is the honest product.

---

## Recommendations (priority order)

### 1. Invert-specific time features — do this first

Highest leverage against the representation ceiling; requires `DATASET_VERSION` bump + regen + new channel stats.

- Finer contour hop (or mel-rate contours) sized for ~50–200 ms SFX.
- **Pad/crop** (or pool) to fixed `N_FRAMES` instead of stretch-*up*; preserve absolute time in frame index / an explicit `t_abs` channel.
- Keep matcher `stretch_to` untouched — invert pack diverges on purpose.
- **Success check before more architecture:** sustain/decay and pitch-trajectory R² rise materially on a clean (`augment_p=0`) or v3-mixture retrain; in-domain one-shot median drops.

### 2. Identifiability-weighted loss + honest re-gate

Cheap; complementary to (1).

- Perturb each param with the renderer; score Δ log-mel (identifiability).
- Weight / drop dead params in unit loss so gradients focus on readable knobs.
- Re-gate on the identifiable set (and on match/seeder metrics). Drop blanket `frequency_start ≥ 0.8` until the representation probe says it's in reach.

### 3. Judge and ship the model as a seeder

Seed-then-refine (CMA-ES from model seed); evaluate on match score. Matches the original design bar.

### 4. Render-in-the-loop for real one-shot gains (a project)

Train a small differentiable surrogate (params → log-mel), then spectrogram loss into the inverse model — "wrong param, right sound." Best fix for remaining ill-posedness **after** inputs actually contain time structure; same coarse/stretched mel would re-impose the representation ceiling.

### Deprioritize

- **Wave-3 multi-hypothesis / per-wavetype heads.** Residual evidence does not currently show pitch multimodality; keep behind an explicit trigger (e.g. bimodal ±octave error histograms after better features).
- **Further width/capacity experiments.** Already falsified by `v3_wide`.

---

## Evidence appendix

- `tools/invert/runs/v3/gate.md`, `escalation.md` — Wave-2 results and prior escalation table.
- `tools/invert/runs/v3/train_log.jsonl` — 15-epoch curve; train unit_mse 0.0480→0.0427, val 0.0460→0.0442, top-3 ~0.84.
- `tools/invert/runs/v3/eval_bfxr/results.md`, `eval_targets/results.md` — seeded 5/9 in-domain, 8/32 real.
- `tools/invert/runs/v2_flatten/gate.md` — Wave-1 gate + input-sanity canary (frequency_start isolated corr 0.73; label pairing corr 0.999).
- Feature-pack probes (2026-07-23): preset native-frame / stretch stats; clean f0 and duration correlations; square/saw and duty mel sensitivity; flanger mel corr ≈ 0; oracle-wavetype one-shot attribution.
