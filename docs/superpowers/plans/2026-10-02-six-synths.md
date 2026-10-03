# Six synth tabs implementation plan

**Goal:** Ship all six approved sound makers with randomized category buttons and editable examples.

**Architecture:** Shared PresetSynth and SoundDSP utilities; independent DSP/definition pairs; special editors for Jinglr and Stackr. The main agent owns common-file integration. Domain implementers own only their assigned new instrument files and tests.

**Tech stack:** Browser JavaScript, Web Audio PCM, node:test, existing Uglify/CleanCSS build.

- [x] Write and verify shared preset/seed/render contract tests, then implement helpers.
- [x] Implement and test Clonkr and Squishr, each with eight or more randomized categories.
- [x] Implement and test Machinr and Weathr, including repeat-safe ambient buffers.
- [x] Implement and test Jinglr engine, presets and editable phrase data.
- [x] Implement Stackr engine, embedded-source layer data, random categories and timeline editor.
- [x] Add Jinglr phrase editor and integrate all six tabs, source includes, previews, wrapping tab bar and instrument labels.
- [x] Generate editable example collections and WAV showcase, document controls and run all tests/minification.
- [x] Browser verification, specification review, code review, and fixes.

Jinglr refinement: replaced the note grid with explicit six-digit melody/instrument codes and eight randomized instrument families. Instrument changes preserve melodies; generated and mutated melodies reconstruct from their visible seed. Added sixteen seed-reproducible voices and an audition reel.

Final verification: 121 tests passed, JavaScript/CSS minification passed, all six tabs exercised in browser, exact example collection imported, layer timing survived reload, and family buttons rerolled voices without changing the melody. Independent reviews completed and findings fixed.
