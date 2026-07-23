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

Stop scaling the network. Instead: (1) **invert-specific time features** (finer hop, pad/crop, no stretch-up); (1b) **sharper / multi-scale spectral detail** once time is honest; (2) **identifiability-weighted loss + honest re-gate**; (3) treat the model as a search *seeder*; (4) longer-term, render-in-the-loop via a differentiable surrogate if one-shot must improve. Deprioritize Wave-3 multi-hypothesis heads and any further width experiments.

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

### Spectral detail: what we feed vs what a human “sees”

Invert does **not** get a raw spectrogram. Input today:

- 6 contours + **one** log-mel scale (64 bands, `n_fft=512`, hop=128 — `FEATURES_MEL_SCALE_IDX=2`)
- Mel is **Gaussian-blurred along frequency** (`MEL_BLUR_SIGMA=2` → ~1 bin σ) — matcher heritage so near-miss tones aren’t distance needles
- Time-stretched to 128 frames

The matcher scores **four** mel scales; invert packs only one. No linear STFT, no multi-scale mel stack, no Fourier-along-time (modulation spectrum) / cepstral map.

That matches matcher philosophy (contours for structure; blurred mel as a soft tiebreaker) but under-serves knobs that live in **fine frequency texture**. Humans often reject a candidate from a glance at a sharp spectrogram; our net never sees that picture.

| Idea | Likely helps | Caveat |
| --- | --- | --- |
| Unblurred / sharper mel or linear STFT | Flanger, harmonics, duty fine structure | Larger input; pitch-shift brittle |
| Multi-scale mel (matcher’s 4 scales) | Short vs long spectral structure | Still useless for envelope if stretch-up remains |
| FFT along time of mel (modulation spectrum) | Vibrato, repeats, jump/repeat cadence | Needs a *real* time axis first |
| Quefrency / harmonic regularity maps | Pitch / harmonic stack | Overlaps f0 contour; extra complexity |

**Order:** fix time framing (finer hop, pad/crop) first; then less-blurred or multi-scale mel as the spectral-detail experiment. Modulation FFT is a follow-on once time is honest — not a substitute for it.

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

## Two regimes: in-domain identification vs general-purpose matching

The perceptual question ("should we perceptually preprocess the wave?") has opposite answers in the two regimes, and the difference is **domain shift**, not taste.

**In-domain (self-inversion): preserve everything, even inaudible signal.** The input was rendered by bfxr, so every systematic cue is real and trustworthy — a flanger comb notch is faint but perfectly informative about `flangerOffset`. Perceptual preprocessing (mel blur, equal-loudness weighting, A-weighting) is designed to *discard differences humans can't hear*, which is exactly what zeroed flanger's mel correlation. For inference you want the opposite: **information preservation** (Rec 1b — un-blur, sharper / multi-scale spectra). Perceptual weighting here throws away the signal you're trying to read.

**General-purpose (real SFX → bfxr): loosen, but not in the model input.** A real game SFX is *off the bfxr manifold* — it was never produced by the synth. Information-preserving features are only trustworthy on-manifold; off-manifold, incidental fine structure (recording artifacts, foreign effects, resampling ringing) mimics bfxr cues that aren't there, so a model trained to key off inaudible detail will **hallucinate** knobs (a flanger from noise). Perceptual features are more manifold-invariant (the audible envelope of a coin sound is shared bfxr↔SNES; the inaudible comb structure is not), so perceptual = regularization against domain shift.

**But put the loosening in scoring, not in the model input.** Cleanest division of labor:

- **Model proposes, using everything** — keep it information-rich, trained on sharp features, maximally sensitive in-domain. It is only a seeder.
- **The perceptual metric disposes, judging only what's audible** — the match objective that scores and CMA-ES-refines is *already* perceptual (multi-scale log-mel). That is the correct home for "ignore inaudible mismatch," and it applies automatically to off-manifold targets. The model over-reaches; refine walks it back to the closest audible match.

This gets general-purpose loosening "for free" without a second model and without blinding the inverter.

**If model *seeds* for real SFX are still bad** (the model over-trusts bfxr-specific fine structure), the fix is **domain-robustness augmentation** — perturb training inputs to mimic real-SFX artifacts so the model learns which cues transfer — *not* perceptually degrading the input. Full resolution in-domain; learned skepticism about non-transferable detail.

**Sequencing:** do not build for the general case yet. Self-inversion is the diagnostic instrument (the only regime with known answers and measurable R²). Nail it with information-preserving features first; then let general-purpose failures show where perceptual scoring or robustness augmentation is actually needed. Premature perceptual loosening would degrade the very signal needed to prove the pipeline works.

### Perceptual preprocessing verdict

| technique | in-domain | general-purpose | notes |
| --- | --- | --- | --- |
| PCEN / adaptive gain control | worth trying | worth trying | transient/onset emphasis + loudness robustness; best candidate, slot under Rec 1b |
| pre-emphasis (HF boost) | helps | neutral | exposes harmonic/flanger fine structure — *preserves more*, not perceptual discard |
| mel blur / equal-loudness / A-weighting | **avoid** | belongs in the *metric*, not the model input | discards predictive signal (killed flanger; A-weighting drops LF pitch energy) |
| gammatone / ERB filterbank | skip | skip | marginal over mel, which is already a perceptual scale |

Net: keep wave-domain prep as-is (mono → resample → trim → normalize); do not add perceptual *feature* weighting to the inverter; hold PCEN as a small experiment after the time-axis fix.

---

## Recommendations (priority order)

### 1. Invert-specific time features — do this first

Highest leverage against the representation ceiling; requires `DATASET_VERSION` bump + regen + new channel stats.

- Finer contour hop (or mel-rate contours) sized for ~50–200 ms SFX.
- **Pad/crop** (or pool) to fixed `N_FRAMES` instead of stretch-*up*; preserve absolute time in frame index / an explicit `t_abs` channel.
- Keep matcher `stretch_to` untouched — invert pack diverges on purpose.
- **Success check before more architecture:** sustain/decay and pitch-trajectory R² rise materially on a clean (`augment_p=0`) or v3-mixture retrain; in-domain one-shot median drops.

### 1b. Spectral detail (after or with time fix)

- Reduce / remove mel frequency blur for invert, and/or pack multi-scale mel (or a sharper STFT) so flanger/resonance/harmonics are visible.
- Optional later: modulation spectrum (FFT along time) once pad/crop gives a real timeline.
- Do not expect sharper spectra alone to fix sustain/decay while stretch-up remains.

### 2. Identifiability-weighted loss + honest re-gate

Cheap; complementary to (1).

- Perturb each param with the renderer; score Δ log-mel (identifiability).
- Weight / drop dead params in unit loss so gradients focus on readable knobs.
- Re-gate on the identifiable set (and on match/seeder metrics). Drop blanket `frequency_start ≥ 0.8` until the representation probe says it's in reach.

### 2b. Grouped representation heads + observability analysis

The decomposition instinct ("detect waveform with one model, envelope with another…") is right, but the axis to split on is the **input representation**, not N independent nets. No single tensor serves every parameter:

| group | evidence in | representation it needs |
| --- | --- | --- |
| wavetype | harmonic/spectral shape | spectrogram; timing irrelevant (already top-3 0.84) |
| envelope (attack/sustain/decay/punch) | amplitude-over-time | RMS contour at real time resolution (Rec 1) |
| pitch (start/slide/accel/vibrato/jumps) | f0-over-time | pitch track at real time resolution (Rec 1) |
| timbre/filter (cutoffs, resonance, duty, flanger, bitcrush) | fine spectral texture | un-blurred / sharp spectra (Rec 1b) |

**Architecture:** one shared front-end → representation branches → grouped heads. *Not* independent from-scratch models (they re-learn the same audio front-end and stay entangled). This is standard multi-task learning — a shared trunk regularizes while heads specialize, usually beating both the monolith and isolated nets. It **subsumes Wave-3**: per-wavetype heads are one group split.

**Handle entanglement with a cascade, not flat parallel heads.** The *evidence* is entangled, not just the params (a filter sweep fakes a short duration; f0 can't be tracked before you know it's tonal vs noise). So detect the confident, easy factors first (wavetype, gross pitch, duration, attack), then **condition the hard heads on them** — estimate flanger/resonance from the *residual* spectrum after the coarse tone is explained (analysis-by-synthesis; residuals expose faint cues the raw mix buries).

**Observability analysis (the "PCA-like" idea, done right).** Finite-difference the renderer to get the Jacobian of audio-features w.r.t. params, then SVD it: large singular values are the param-space *directions* the audio determines; near-zero ones are unrecoverable regardless of model. This is the principled form of Rec 2's sensitivity probe and should drive loss weighting, gating, and the honest gate. **Diagnose in this observability basis; keep predicting in the native param basis** — a rotated output basis destroys conditional activation (mixes `squareDuty` into everything) and per-knob interpretability/renderability.

**Caveat:** grouping de-conflates the loss and matches representations to targets, but does **not create information**. A flanger head still recovers nothing from blurred mel (needs Rec 1b); a genuinely inaudible-in-context param stays lost. This architecture is what lets Rec 1/1b pay off — not a substitute for them.

**Sequencing:** first confirm the Rec 1 time-axis fix lifts envelope R² in the *current single* model (isolates whether the ceiling is representational, one variable at a time). Only then build the grouped trunk — four heads on today's stretched/blurred features would just share one ceiling.

### 3. Judge and ship the model as a seeder

Seed-then-refine (CMA-ES from model seed); evaluate on match score. Matches the original design bar.

### 4. Render-in-the-loop for real one-shot gains (a project)

Train a small differentiable surrogate (params → log-mel), then spectrogram loss into the inverse model — "wrong param, right sound." Best fix for remaining ill-posedness **after** inputs actually contain time structure; same coarse/stretched mel would re-impose the representation ceiling.

### Deprioritize

- **Wave-3 per-wavetype heads as a standalone step.** Not dead — folded into Rec 2b as one group split, and gated behind the Rec 1 time-axis probe. Multi-*hypothesis* (K-way) heads stay behind an explicit trigger (bimodal ±octave error histograms after better features); current `frequency_start` residuals are unimodal, so no trigger yet.
- **Further width/capacity experiments.** Already falsified by `v3_wide`.

---

## Evidence appendix

- `tools/invert/runs/v3/gate.md`, `escalation.md` — Wave-2 results and prior escalation table.
- `tools/invert/runs/v3/train_log.jsonl` — 15-epoch curve; train unit_mse 0.0480→0.0427, val 0.0460→0.0442, top-3 ~0.84.
- `tools/invert/runs/v3/eval_bfxr/results.md`, `eval_targets/results.md` — seeded 5/9 in-domain, 8/32 real.
- `tools/invert/runs/v2_flatten/gate.md` — Wave-1 gate + input-sanity canary (frequency_start isolated corr 0.73; label pairing corr 0.999).
- Feature-pack probes (2026-07-23): preset native-frame / stretch stats; clean f0 and duration correlations; square/saw and duty mel sensitivity; flanger mel corr ≈ 0; oracle-wavetype one-shot attribution; invert mel = single blurred scale (not raw STFT).
