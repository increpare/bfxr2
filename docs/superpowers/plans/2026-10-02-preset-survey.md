# Audio-derived preset families plan

**Goal:** Replace limited recipe variation with varied, named families drawn from a measured sound survey.

**Architecture:** A Node renderer creates a seeded corpus; Python/NumPy extracts audio features and selects stable clusters; a compact generated bank and shared family sampler provide runtime presets. A local HTML catalogue provides audition, coverage and import.

- [x] Build/test deterministic sampling, render 512 accepted Transfxr sounds and record rejection statistics.
- [x] Extract temporal/spectral/pitch features, compare cluster counts using silhouette and group size, inspect representatives, assign names.
- [x] Store representative and diverse exemplars for each family; generate a searchable listening catalogue of every accepted sound.
- [x] Integrate locked-aware joint exemplar sampling and test that repeated clicks change more than pitch.
- [x] Validate generated family audio against the measured family region; run regressions and browser checks, deliver catalogue and evidence.

Result: 16 named families, 344 joint exemplars. All 512 fresh variations were audible and unclipped; 90.04% were closest to their assigned center and 95.90% within 20% of nearest-center distance. Full app tests passed (126); Python feature/selection tests passed (4). Combined 47-script JavaScript/CSS minification succeeded. Browser checks confirmed catalogue audio decoding, search/filtering, tour playback, exact import links and repeated preset filter variation without console errors.

Review repaired two issues before delivery: raw survey envelopes now pass through editor validation before rendering, and variation preserves zero echo on dry short exemplars. Names are based on measured profiles and inspected spectrograms; the catalogue exposes all sounds for user listening judgment.
