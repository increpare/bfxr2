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

What *is* realistic for “feels like A” later: **one-shot → cheap refine (&lt;1s through the surrogate) → optional short CMA**. That is still strategy C, with a fast path that can become the default UX.

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
6. **Hard ceiling.** Some targets are outside bfxr’s reachable set (rich Mario / formant-ish timbres). No amount of inverse-model training fixes that without synth extensions.
7. **Wrong lever already tried.** Sound-level `structure_pitch` in the match objective: probes 8/14 → 14/14, ears unchanged on the hard slice (Gate B FAILED). Term now defaults to weight 0.0; `--structure-objective` keeps it for experiments. Do not spend another cycle retuning that term before changing the *model/seed* path.

### What a retrain would *not* learn from Gate A/B

The structure-metric branch changed search/eval tooling (`structure.py`, probes, listen page, note-boundary fix, default-off weight). None of that alters training data, labels, architecture, or loss. A fresh `best.pt` would not see those changes. Retrain only if the **training** side changes again.

---

## Literature and practitioner map

| Idea | Source | Fit for bfxr2 |
| --- | --- | --- |
| Spectral / audio loss + real unlabeled FT | Masuda & Saito (DDSP sound matching; TASLP 2023) | **Already done** (v6 spectral → v7 real FT) |
| Keep joint param + spectral (don’t drop param loss on OOD) | Masuda 2023 | Worth checking if real-FT was spectral-only too aggressively |
| **Inference-time finetune through a synth proxy** | InverSynth II (ISMIR 2023) | **High value, not done** — `SurrogateSynth` already exists |
| Generative / multi-hypothesis params | ISMIR 2025 flow matching; projects like synth-setter | Sample K seeds → score with matcher (pairs with CMA) |
| True differentiable synth | DDSP / Masuda | Bigger project than improving the surrogate |
| Retrieval + nearest presets / CLAP | Synth-galaxy, Syntheon (Vital) | Useful as a seed library later, not a full replacement |
| Synth capability gaps | next-directions “Q8” | Separate track for unreachable timbres |

Also relevant: *Learning to Solve Inverse Problems for Perceptual Sound Matching* (PNP / JTFS) — perceptual features matter more than many architecture knobs when the synth is differentiable; for us the cheap analogue is “score and refine in a better audio feature space,” which we already partly do via the match objective and the surrogate.

---

## Ranked next bets (value / effort)

### 1. Test-time surrogate refine — **do first** (chosen)

After one-shot (and/or before CMA): a few gradient steps on predicted params minimizing spectral distance to the target **through the frozen `SurrogateSynth`**. Same shape as InverSynth II’s inference-time finetuning.

- No new data, no retrain.
- Directly attacks the one-shot gap.
- Clear listen A/B: raw one-shot vs refined one-shot vs current seeded.
- Also builds the “almost-A” fast path under strategy C.

### 2. Multi-hypothesis seeding — follow-up if (1) helps but basins stay wrong

Emit top‑K diverse param / wavetype guesses (dropout, noise, or later a small conditional generative head). Score each with the existing match objective; keep the winner as CMA seed. Directly addresses ill-posedness; matches “search already does the impressive part.”

### 3. Sharper surrogate → short real-FT — only after (1) proves the proxy

Widen/deeper surrogate, multi-scale mel target (the matcher already uses multiple scales), retrain surrogate, then a short real-FT from v7. Costly; only worth it once inference-time refine shows the surrogate gradient is useful on real targets.

### 4. Name the ceiling; optional synth extensions

For targets that aren’t bfxr-reachable, improve the synth (colored noise / formants / etc.) rather than the inverse model. Longer horizon; frames expectations.

### Deprioritize for now

- More structure-metric weight / gate tuning (Gate B null; term ships off).
- Pure 500k→1M scale ladder with the same v5 recipe and no new training idea.
- Treating one-shot median alone as the north star while the product path is seed+search.
- Retraining “because we changed the match objective” (we didn’t change what training sees).

---

## Decision log (2026-07-25)

| Decision | Choice |
| --- | --- |
| Product success mode | **C** — seed+search first; one-shot as bonus / fast path |
| Next implementation bet | **(1) Test-time surrogate refine** |
| Follow-ups | (2) multi-hypothesis seeds if refine helps but basins wrong; (3) surrogate retrain only if (1)’s gradient is useful |
| Structure term | Remains default-off; not the next lever |

---

## Pointers

- Prior directions (length, real-FT, surrogate, synth ceiling): `2026-07-23-inverse-model-next-directions.md`
- Spectral experiment: `2026-07-23-inverse-model-spectral-results.md`
- Data retrain / v7: `2026-07-24-inverse-model-data-retrain-results.md`
- Structure metric Gate A/B (FAILED listen): `2026-07-24-gate-a-results.md`
