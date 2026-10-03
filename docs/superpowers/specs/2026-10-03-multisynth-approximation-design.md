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
