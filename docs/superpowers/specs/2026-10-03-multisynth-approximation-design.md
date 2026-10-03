# Multi-synth sound approximation

Build an offline inverse model for game SFX using the existing browser synths without modifying the app or the parallel determined-sagan branch. The user explicitly requests autonomous research, so design and implementation choices proceed without interactive approval gates.

## Approach

A nonparametric inverse model (audio descriptor → nearest rendered preset parameters) routes a target to several synth-specific experts. Each expert optimizes valid controls against rendered audio, and a common perceptual selector ranks the results. This supplies an interpretable baseline and useful editable recreations immediately. A unified neural predictor would need a large heterogeneous dataset before proving useful; one neural model per synth multiplies training complexity. Both can later seed this search if evidence warrants it.

## Components

- A deterministic production headless adapter discovers available numeric synths, exposes parameter bounds and categorical values, samples existing recipes, and renders their actual DSP. Include Bfxr, Transfxr and the specialized synths. Report unsupported structured/text instruments rather than pretending to search them.
- A versioned library stores sampled parameters, source fingerprints, compact perceptual descriptors and render seeds. Sampling spans recipes and duration scales, preserving coherent preset distributions.
- Retrieval retains candidates from each synth, including a Bfxr baseline. Local black-box optimization can adjust continuous, categorical and transition endpoints within the synth schema. Keep the original seed when optimization cannot improve it.
- A loudness-normalized, onset-aligned perceptual objective compares duration, amplitude evolution, auditory-band energy and pitch/timbre contours. Reject silent or nonfinite renders. Do not claim this is a human preference model.
- A reproducible benchmark selects diverse files from the large local collection, records paths/hashes/settings, and exports an HTML A/B gallery, ranked JSON and editable .bcol collections. Source audio and generated data remain local and ignored. Names do not inform model predictions.

## Success criteria

Renderer determinism and app-loadable round trips; tested metric orderings on controlled sounds; retrieval and optimization with a strict evaluation budget; automatic cross-synth selection; fixed-library Bfxr comparison and per-target results on held-out real game sounds. Publish honest limitations, timings and examples. A low score is not a certificate of perceptual quality. Leave subjective judgment available through playback and alternatives.

## Human correction and next model requirements — 2026-10-03

The first human pass rated 30/40 selections 1–2 out of 5. Metric gains did not
establish satisfactory likeness. Preserve that feedback and the exact audition
clips in `tools/multisynth/listening_data/`; unlike scratch runs this evidence
must survive cleanup. Focus current research on `targets_non_bfxr_big/tags`.

The user's explicit requirement is that similarity depends on **large-scale
gestural qualities and feel as much as curve matching**. A useful recreation
preserves the kind of event and its expressive movement; exact quantities may
differ. Game-SFX usefulness and fun matter, but the collected ratings assess
likeness only. Do not reinterpret them as a fun score.

Next-model hypotheses and acceptance checks:

1. Represent event structure at several scales: impulsive vs sustained attack,
   build-up/release, single vs repeated events, accelerating/decelerating rhythm,
   coarse pitch motion, roughness, resonance and decay character. Permit local
   timing variation while preserving event order and gesture direction.
2. Test controlled positive/negative pairs. A modest pitch shift or time stretch
   of a rising charge should usually stay closer than a falling or static sound;
   an impact with different tuning should usually beat a slow swell with similar
   average spectrum. A rattle should retain its repeated-event character.
   These are test hypotheses requiring listening, not universal invariances:
   timing, pitch intervals and event count can define the sound's identity.
3. Avoid collapse into broad semantic classes: two tagged 'hit' sounds can have
   different weight, material and gesture. Tags balance evaluation and may aid
   diagnostics; a category label alone is not evidence of audible similarity.
4. Diagnose candidate coverage before selector fitting. Compare diverse synth
   finalists on a small tagged development set: if none evoke the target, improve
   retrieval/search representations instead of only reweighting winner scores.
5. Use retained judgments as durable regression evidence. Tune only on declared
   development references; reserve separate audio families for subsequent blind
   listening. Compare both likeness and separately collected usefulness, retain
   Bfxr, and report ties/failures. Synthetic ordering checks alone do not validate
   human closeness.

The existing auditory-v1 model remains a reproducible baseline. No gesture-aware
model improvement is claimed until implemented and tested against listening.
