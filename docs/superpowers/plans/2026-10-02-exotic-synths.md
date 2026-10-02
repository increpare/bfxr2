# Exotic synths implementation plan

**Goal:** Add five distinct game-oriented instruments with randomized presets and editable audio examples.

**Architecture:** Five independent DSP/definition pairs reuse SoundDSP and PresetSynth; shared UI registration and Stackr integration remain with the main agent. Parallel workers own disjoint new files. Existing work is preserved in the current checkout.

**Tech stack:** Browser JavaScript, Web Audio PCM, node:test, Uglify and CleanCSS.

- [x] Add Crittr_DSP/Crittr and Signlr_DSP/Signlr plus tests/creatures-signals.test.js. Write failing contracts, implement distinct models, verify every recipe and relevant audible control changes.
- [x] Add Fractr_DSP/Fractr and Riftr_DSP/Riftr plus tests/fractures-rifts.test.js. Verify cascade timing/material spectra and dispersed-field/reverse behaviors independently.
- [x] Add Swarmr_DSP/Swarmr plus tests/swarmr.test.js. Implement independent agents with coherent versus scattered motion, count/panic/pitch/size controls, and eight randomized game recipes.
- [x] Extend index.html and js/index.js to append the five tabs. Add the five source constructors to Stackr.sources; match existing panel sizing in css/index.css. Verify new sounds survive links and copied Stackr layers.
- [x] Write tools/render/exotic_examples.js to generate exact per-category .bcol/WAV files and a short reel under examples/Exotic. Use reproducible recipe selection and validate each PCM and saved-parameter reconstruction. Document concise controls in README.
- [x] Run node --test tests/*test.js, read-only JavaScript/CSS minification, and git diff --check. Exercise each tab and preset generation in browser, inspect layout, verify import/reload, and save a screenshot. Review spec coverage and code, then fix findings.

## Validation

- 163 tests pass, including acoustic controls, presets, locks, persistence and Stackr copies.
- 57 scripts and four stylesheets minify successfully; whitespace checks pass.
- All five tabs exercised in the browser, a Swarmr copy added to Stackr, and the 40-sound collection imported and restored after reload. No browser errors.
- Forty example renders are finite, bounded, audible, edge-faded and reproduce exactly after loading. An 18.59-second reel includes ten complete sounds.
- Independent review found a short ticking-swarm silence case; an arrival pulse and transient envelope fix it, with regression coverage and clean follow-up review.
