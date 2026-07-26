# Inverse model — next bets after Gate B

**Date:** 2026-07-25  
**Branch:** `feature/inverse-model-structure-metric`  
**Baseline checkpoint:** `invert/runs/v7_real_ft/best.pt` (frozen for the structure-metric work; still the best relative real-SFX baseline)  
**Context:** Follows `2026-07-23-inverse-model-next-directions.md`, the v7 data-retrain results, and Gate A/B on the structure-aware match term (`2026-07-24-gate-a-results.md`).

---

## Product framing

| Option | Meaning |
| --- | --- |
| A | Instant one-shot: drop WAV → usable `.bfxr` with little/no search |
| B | Seed + short search (a few seconds of CMA is OK if the result is good) |
| **C (chosen)** | Optimize **B** first; treat one-shot as a bonus / path toward A |

**A as “one forward pass = current seeded quality” is probably not realistic soon.** Gate B already shows the gap: one-shot ~1.2/5 vs seeded 3–4/5 on the same hard-slice sounds. That gap is the ill-posed inverse plus weak envelope/jump identification — not a missing match-objective term.

What may still produce “feels like A” later is **one-shot → a cheap,
perceptually valid fast path → optional short CMA**. The current
surrogate-gradient refine is not that fast path: its hard-slice listen failed.
This remains strategy C, with seed + short search as the product mode while a
better fast path is only a possible future bonus.

---

## What already works

The task is solvable in the sense that **parts of the stack already work impressively**. The mistake is treating “make the model better” as one undifferentiated problem.

| Regime | Evidence |
| --- | --- |
| In-domain bfxr presets | Spectral model: seeded median ~0.85; one-shot improved monotonically with spectral weight (spectral-results) |
| Seeded search on real SFX | v7 real FT seeded median **2.61**; Gate B listener gave Throw / leeneBell / cursor **3–4/5** |
| Discrete-note structure via search | Pitch-jump arp seeding (not the structure metric) is what found the arps |
| Relative real-audio FT | Real FT beat v6 one-shots **20–12** by ear; beat synth FT **18–14** |

So the pipeline *can* land in the right basin. What’s weak is mostly the **raw one-shot** and anything the synth **cannot** make.

---

## Weaknesses (stratified)

1. **Ill-posed inverse.** Many param vectors produce similar audio. Point regression averages modes. Recent literature (ISMIR 2025 flow matching / Param2Tok; InverSynth II) treats this as multi-modal: sample several parameter hypotheses, score in audio space.
2. **One-shot ≪ seeded.** The model is a mediocre initializer; CMA + arp seeds do most of the impressive work on real targets.
3. **Envelope / jump params still poorly identified.** `sustainTime` / `decayTime` R² ~0.24 even after v4 time-features; `pitch_jump_amount` only ~0.2–0.28 after structured data. Identifiability reweighting was a wash; time-features alone did not fix envelopes.
4. **Surrogate is the spectral gradient.** Recon MSE **0.226** (~77% of feature variance). Spectral training and real-FT both lean on it; a blurry surrogate → a blurry “sound” signal at train and (if we use it) at inference.
5. **Domain gap.** Spectral-on-synth alone did not transfer to real SFX. Real-FT helped relatively; absolute quality is still low. The surrogate remains on the bfxr feature manifold.
6. **Measured reachability ceiling on the real hard slice.** At 100x search
   budget, the seeded held-out objective improved only **3.2%** on real targets
   versus **46.9%** on reachable in-domain controls, and the real/in-domain
   floor ratio grew **1.328 → 2.420**. This does **not** establish that every
   real target is unreachable: Throw and Break Brick showed seeded objective
   reductions, and a larger shipping budget may capture some of that objective
   upside. It does establish that the hard-slice median is now limited
   primarily by bfxr's reachable set, not by the current seed or search budget.
   See the headroom results.
7. **Wrong lever already tried.** Sound-level `structure_pitch` in the match objective: probes 8/14 → 14/14, ears unchanged on the hard slice (Gate B FAILED). Term now defaults to weight 0.0; `--structure-objective` keeps it for experiments. Do not spend another cycle retuning that term instead of pursuing the selected capability track.

### What a retrain would *not* learn from Gate A/B

The structure-metric branch changed search/eval tooling (`structure.py`, probes, listen page, note-boundary fix, default-off weight). None of that alters training data, labels, architecture, or loss. A fresh `best.pt` would not see those changes. Retrain only if the **training** side changes again.

---

## Literature and practitioner map

| Idea | Source | Fit for bfxr2 |
| --- | --- | --- |
| Spectral / audio loss + real unlabeled FT | Masuda & Saito (DDSP sound matching; TASLP 2023) | **Already done** (v6 spectral → v7 real FT) |
| Keep joint param + spectral (don’t drop param loss on OOD) | Masuda 2023 | Worth checking if real-FT was spectral-only too aggressively |
| **Inference-time finetune through a synth proxy** | InverSynth II (ISMIR 2023) | **Done; failed hard-slice listen** with the current `SurrogateSynth`; remains default-off |
| Generative / multi-hypothesis params | ISMIR 2025 flow matching; projects like synth-setter | Historical seed-quality direction; **de-selected by the headroom probe** |
| True differentiable synth | DDSP / Masuda | Bigger project than improving the surrogate |
| Retrieval + nearest presets / CLAP | Synth-galaxy, Syntheon (Vital) | Useful as a seed library later, not a full replacement |
| Synth capability gaps | next-directions “Q8” | **Selected next** after the measured reachability ceiling |

Also relevant: *Learning to Solve Inverse Problems for Perceptual Sound Matching* (PNP / JTFS) — perceptual features matter more than many architecture knobs when the synth is differentiable; for us the cheap analogue is “score and refine in a better audio feature space,” which we already partly do via the match objective and the surrogate.

---

## Ranked bets — historical order and resolution

This was the ranking before the headroom measurement. It is retained as the
decision trail, not as current implementation advice.

### 1. Test-time surrogate refine — **FAILED**

After one-shot (and/or before CMA): a few gradient steps on predicted params minimizing spectral distance to the target **through the frozen `SurrogateSynth`**. Same shape as InverSynth II’s inference-time finetuning.

The implementation and listen gate are complete. Refined one-shots scored
worse by ear (mean 1.32 vs 1.55 raw), including one mute/trash result, and the
match objective was worse on all 10 hard-slice targets. It remains available
for experiments but defaults to `--surrogate-refine-steps 0`.

### 2. Multi-hypothesis seeding — **DE-SELECTED BY HEADROOM**

The historical proposal was to emit top-K diverse parameter / wavetype
hypotheses and score them as CMA seeds. The headroom probe removed its premise:
at the measured 200 000-evaluation endpoint, `big_unseeded` reached a slightly
better objective than `big_seeded` (2.2877 vs 2.3441 median), and at 2 000
evaluations seeded was also slightly worse (2.4226 vs 2.3891). The current
seed therefore did not improve hard-slice median quality at either endpoint;
the probe did not measure or establish a time-to-quality benefit. This
de-selects multi-hypothesis seeding as the next project because it does not
address the pre-registered median reachability result. The finite endpoints do
not rule out a learned seed finding an unobserved basin; reopen only with new
evidence that seed quality is binding.

### 3. Sharper surrogate → short real-FT — **STILL DEPRIORITIZED**

Widen/deeper surrogate, multi-scale mel target (the matcher already uses
multiple scales), retrain surrogate, then a short real-FT from v7. This remains
costly and aimed at seed quality; test-time refine failed and the headroom
endpoint comparisons do not identify current seed quality as the next binding
lever.

### 4. Synth capability / pairs-of-sounds — **SELECTED NEXT**

The reachability premise is now measured rather than speculative. The next
project should expand what the synth can express, including the
pairs-of-sounds direction, before spending another cycle on inverse-model seed
quality. This needs a fresh brainstorm → design → plan; the headroom result
selects the problem, not a particular implementation.

### Deprioritize for now

- More structure-metric weight / gate tuning (Gate B null; term ships off).
- Pure 500k→1M scale ladder with the same v5 recipe and no new training idea.
- Treating one-shot median alone as the north star while the product path is seed+search.
- Retraining “because we changed the match objective” (we didn’t change what training sees).

---

## Decision log (updated 2026-07-26)

| Decision | Choice |
| --- | --- |
| Product success mode | **C** — seed+search first; one-shot as bonus / fast path |
| Bet (1) test-time surrogate refine | **FAILED listen** — refined mean 1.32 vs raw 1.55; mute on `mario 2 - jump`. Default stays `--surrogate-refine-steps 0`. See `2026-07-25-test-time-refine-results.md` |
| Headroom verdict | **REACHABILITY CEILING.** At 100x budget, seeded held-out objective improved **+3.2%** on the real hard slice vs **+46.9%** on reachable in-domain controls; the real/in-domain floor ratio grew **1.328 → 2.420**. |
| Blind-listen result | For this one listener on the ten-target slice, 100x did not show a general audible gain: `baseline_seeded` mean/median **2.80/3.00** vs `big_seeded` **2.35/1.75** (**0/6/4** W/T/L) and `big_unseeded` **2.30/1.50** (**2/3/5**). The sole 5/5 was an isolated `big_unseeded` cursor win. |
| Metric interpretation | **Metric ceiling did not fire:** the listen side was flat/worse, but its objective-improvement precondition (>=10%) was not met. The listen does not reopen objective work. |
| Bet (2) multi-hypothesis seeding | **DE-SELECTED AS THE NEXT PROJECT.** The current seed did not improve hard-slice median quality at either measured endpoint; time-to-quality was not measured. Reopen only with new evidence that seed quality is binding. |
| Next project | **(4) Synth capability / pairs-of-sounds.** Begin with a new brainstorm → design → plan. |
| Candidate free upside | A shipping budget around 10k may capture objective gains on some targets, but requires a separate listen gate. No budget, restart, or default change in this branch. |
| Structure term | Remains default-off; not the next lever |

---

## Pointers

- Prior directions (length, real-FT, surrogate, synth ceiling): `2026-07-23-inverse-model-next-directions.md`
- Spectral experiment: `2026-07-23-inverse-model-spectral-results.md`
- Data retrain / v7: `2026-07-24-inverse-model-data-retrain-results.md`
- Structure metric Gate A/B (FAILED listen): `2026-07-24-gate-a-results.md`
- Headroom verdict (REACHABILITY CEILING): `2026-07-25-headroom-probe-results.md`
- Headroom decision rule / design: `../specs/2026-07-25-headroom-probe-design.md`
- Headroom implementation + run plan: `2026-07-25-headroom-probe.md`
