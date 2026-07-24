# Inverse-Model Retrain via Data-Generator Improvements — Design

**Date:** 2026-07-24
**Status:** design approved, pending spec review → implementation plan
**Branch context:** `feature/inverse-model-next-steps` (worktree `.worktrees/inverse-model-next`)

## Goal

Retrain the inverse model (`tools/invert/`) to be **more robust on real / general SFX**
and to **reliably represent discrete-note structure**, by improving *only the synthetic
training-data generator* — no architecture change, no real-audio labels.

## Why (diagnosis, from prior work)

The current model is trained on ~300k renders of *random bfxr params* only. Three
consequences, all observed this session:

1. **OOD wall** — it has never seen anything but bfxr's own output, so real
   SNES/NES/recorded SFX are off-manifold; its one-shot guesses there are weak
   ("same genre at best").
2. **Discrete notes smear to glissando** — coherent arpeggios (via pitch-jumps)
   are rare under near-uniform param sampling, so the model rarely learns them.
   (Search-side arp seeding fixed the *seeded* column; the raw model is still weak.)
3. **Degenerate pairs pollute training** — the generator culls dead renders but not
   near-silent or pathologically short ("click") ones.

Everything here targets the **model itself** (the one-shot / seed quality), which
search-side work cannot improve.

## Current data-generation state (verified)

- `sampler.sample_unit` modes: `biased` / `uniform` / `kknob`.
- `dataset.MIX`: `biased .35 / uniform .15 / kknob .30 / preset .20`
  (preset = params harvested from bfxr's own preset templates via `presets.py`).
- `augment.maybe_augment` (p=0.25): level jitter, additive noise floor, one-tap
  reverb, EQ tilt. **No** sample-rate / bit-depth degradation.
- `dataset._is_acceptable_wave`: rejects `None` / empty / non-finite / `peak <
  SILENCE_PEAK` (1e-3), and resamples until acceptable. **No** min-duration check;
  threshold is sub-perceptual.
- Loss (v6): param loss + differentiable-surrogate spectral term + identifiability
  weighting.
- `train.py`: **no** checkpoint-init/resume flag.
- `constants.DATASET_VERSION = "v4"`, ~300k examples in `invert/data/v4`.

## Decisions (from brainstorming)

- **Priority:** general / real-SFX robustness — lean into retro-degradation
  augmentation, accept a small in-domain precision cost (measured, not assumed).
- **Training:** train **both** a from-scratch model and a finetune-of-v6, pick the
  winner on the held-out real-SFX eval.
- **Structured mix slice:** ~25% of the training mix.
- **Scope:** synthetic data-generator only. Real-audio "distill-the-search" is a
  separate future sub-project (see Out of Scope).

---

## Section 1 — Structured sampler mode (`sampler.py`)

Add `mode="structured"` to `sample_unit`, plus a `_structured_unit(space, rng)` helper
that builds *coherent* sounds the random modes almost never produce:

- **Arpeggios (primary):** base `frequency_start` in a musical range; 1–2 pitch jumps
  with ratios drawn from ~±2 octaves (both directions), mapped to `pitch_jump_amount`
  / `pitch_jump_2_amount` via the verified DSP inverse
  (`notes.pitch_jump_param_from_ratio`); `pitch_jump_onset_percent` /
  `..._onset2_percent` spread across the sound; **envelope explicitly sized so every
  note is audible** (short attack, sustain+decay spanning the notes). Tonal-leaning
  wavetype.
- **Variants** (rolled in with independent probabilities): `pitch_jump_repeat_speed`
  / `repeatSpeed` (repeating motifs), `vibratoDepth`/`vibratoSpeed`,
  `lpFilterCutoffSweep` / `hpFilterCutoff` (filter-sweep flavor).

All structured units pass through the existing `finalize_example` (envelope cap,
square-only pinning, params round-trip) so labels stay in the search-reachable space.

## Section 2 — Retro-degradation augmentation (`augment.py`)

Keep the existing roughening. Add a **retro chain** (real targets are downsampled
console samples), applied as a weighted sub-choice inside `maybe_augment`:

- **Sample-rate crush:** decimate to ~6–16 kHz then back to 44.1 k, sometimes without
  a proper anti-alias filter so aliasing leaks through (authentic).
- **Bit-depth crush:** quantize to ~4–8 bits.
- **Companding:** µ-law-style quantization (DPCM-ish grit).
- Occasional hard clip / drive.

Labels stay the **clean** params → the model learns to recover the underlying sound
through degradation (denoiser framing). Raise default `augment_p` 0.25 → **0.4**.

Note on the rate: augmentation here is **baked** into shards (features are computed
from the augmented wave), so an augmented example is *permanently* corrupted — unlike
on-the-fly augmentation, where the model re-sees each example clean and differently-
corrupted every epoch and near-100% rates are normal. Baked → keep clean data the
majority (0.4 = 60% clean / 40% roughed); the retro chain is strong, so a moderate
rate suffices, and the effective heavy-degradation rate is lower still (retro stage
has its own 0.6 sub-probability). *Future option (not in scope):* a hybrid — bake the
wave-level retro chain moderately, add cheap on-the-fly feature-space noise/masking at
train time for per-epoch diversity (full on-the-fly retro is impractical: shards store
features, not the ~40 GB of raw waves it would need).

## Section 3 — Degenerate-culling (`dataset.py`, `augment.py`)

Tighten `_is_acceptable_wave` (the resample gate) and bound augmentation:

- **Minimum audible duration:** require ≥ ~20–25 ms of content above an audibility
  floor (rejects pathological "click" renders). Legitimately short SFX (a ~50 ms
  coin/blip) still pass — the bar is *pathologically* short.
- **Perceptual acceptance peak:** raise the accept threshold to ~0.02 (what we
  established is audible), so near-mute renders are resampled away rather than baked
  in as amplified-noise pairs.
- **Bounded augmentation:** guard `maybe_augment` so the retro chain cannot push an
  accepted sound back below audibility (augmentation is baked into shards, so a
  silenced aug is a bad pair).

These matter most for the structured/arp examples, whose collapsed-envelope failures
are exactly the degenerate case.

## Section 4 — Training & eval protocol

- **Regenerate dataset** with the above as `DATASET_VERSION = "v5"` (`invert/data/v5`),
  **~750k examples** (up from v4's 300k). One dataset feeds both arms.
  - *Why more:* v3's plateau was an ill-posedness *ceiling* (train≈val, capacity-
    invariant), so more of the *same* distribution wouldn't have helped. But we're
    now adding retro augmentation (large effective diversity — many corruptions per
    param set) and structured coverage (a big arp param space), which *do* benefit
    from denser sampling. Generation is cheap; training is the cost.
  - *Keep training compute bounded:* scale epochs **down** roughly in proportion so
    total examples-seen stays similar to v4's run — more unique data at fewer passes
    reduces memorization/over-repetition. (~750k is a deliberate 2.5×, not 10×;
    returns diminish past a point.) ~13 GB on disk, gitignored.
- New `dataset.MIX`: `biased .20 / uniform .10 / kknob .25 / preset .20 /
  structured .25`.
- **Two training arms**, loss config held identical to v6 (param loss + surrogate
  spectral term + identifiability weighting) so the *data* change is isolated:
  - **A) from-scratch** — random init, full run.
  - **B) finetune** — init from `invert/runs/v6_spectral/best.pt` via a new
    `train.py --init-weights <ckpt>` flag, continue on v5.
- **Decision = held-out real-SFX eval**, with guardrails:
  1. **Real-SFX (primary):** `invert.eval_targets` on `tools/targets/` (32 sounds),
     seeded-search median + spot-listening on the discrete-note cases. Valid as an
     OOD measure (training is 100% synthetic); treat as *dev* set, not pristine
     holdout, since we've tuned against it.
  2. **In-domain sanity:** a fresh synthetic held-out set to quantify any in-domain
     cost (small dip acceptable; we measure it).
  3. **Arp one-shot probe:** re-check the controlled arpeggio + Throw/cursor/
     leeneBell, confirming the model's *raw one-shot* now predicts discrete notes
     (the real test that the net improved, not just the search).
- **Baseline = v6.** Winner = best real-SFX median without catastrophic in-domain
  regression. If neither arm beats v6, keep v6 and report the negative result.

## File / interface changes

- `sampler.py`: add `mode="structured"` + `_structured_unit()` helper.
- `dataset.py`: new `MIX`; thread `structured` through mode selection + resample;
  default `augment_p` → 0.4; tighten `_is_acceptable_wave` (min duration + peak).
- `augment.py`: retro-chain helpers (samplerate crush, bitcrush, companding, clip);
  bound so output stays audible.
- `constants.py`: `DATASET_VERSION` → `"v5"` (+ any new audibility constants).
- `train.py`: add `--init-weights <ckpt>` (load `state_dict` before training).
- **Gitignored, never committed:** `invert/data/**`, `invert/runs/**`.

## Testing

- **Structured sampler:** produces coherent arp params (jumps in range, onsets
  ordered), envelope audible, labels in search-reachable range; variants toggle.
- **Retro-aug helpers:** finite output, sane level, seed-deterministic; bounded
  (never silences an audible input).
- **Culling:** `_is_acceptable_wave` rejects a synthetic click and a near-mute wave,
  accepts a normal and a legitimately-short one.
- Full suite stays green.

## Success criteria

- Real-SFX seeded-search median improves vs v6 (primary), OR a clear, reported
  negative result.
- Arp one-shot probe: the raw model predicts discrete-note structure noticeably
  better than v6 (measurable + audible).
- In-domain cost quantified and within tolerance (not catastrophic).

## Out of scope (future sub-projects)

- **Real-audio "distill-the-search":** run the CMA matcher on many real sounds, use
  its matched params as pseudo-labels, train the net to imitate the search.
- **Semi-supervised surrogate finetune** on unlabeled real audio.
- **Architecture** changes: multi-hypothesis output, grouped heads, uncertainty.
- **Perceptual-only loss** (predict → surrogate-render → spectral loss) beyond the
  current surrogate term.
