# Interface synths implementation plan

**Goal:** Five game-interface synth tabs, each with eight randomized categories, plus forty editable examples.

**Architecture:** Separate DSP/definition pairs extend PresetSynth; root owns shared registration, Tickr and examples. Two workers own disjoint engine pairs and focused tests. Preserve current uncommitted work.

**Tech stack:** Browser JavaScript, Web Audio PCM, node:test, UglifyJS and CleanCSS.

- [x] Implement Tappr/Rustlr in js/audio and js/synths, with tests/interface-contact.test.js. Start with failing deterministic/duration/audibility contracts; validate down/up contact and friction envelope controls acoustically.
- [x] Implement Notifr/Holor in js/audio and js/synths, with tests/interface-digital.test.js. Validate urgency/interval timing and spectral gesture controls, all recipes, locks, safe extremes and exact saved replay.
- [x] Implement Tickr in js/audio/Tickr_DSP.js and js/synths/Tickr.js with tests/tickr.test.js. Test accelerating event timing, event count, progress pitch, completion mix, extremes, locks and eight randomized recipes before implementation.
- [x] Extend index.html, js/index.js, Stackr.sources and css/index.css. Extend tests/exotic-integration.test.js to cover the five new constructors, serialization, registration order and old collections. Keep the former fifteen indexes stable.
- [x] Add tools/render/interface_examples.js and examples/Interface. Generate exact per-category WAVs and Interface.bcol plus a short complete-gesture reel; assert finite, bounded, audible, faded and restored bit-identical audio. Update README.
- [x] Run npm test, JavaScript/CSS minification and git diff --check. Test all five tabs, preset generation, layering and reload in the browser. Save a screenshot. Obtain independent review, fix findings and record validation.

## Validation

- Full suite: 192 tests pass. All 67 scripts and four stylesheets minify, and whitespace checks pass.
- Forty examples render finite, bounded, audible audio with zero-valued endpoints and exact saved replay. The reel plays fifteen complete gestures in 15.39 seconds.
- All five tabs exercised in-browser; repeated Focus generation varies; a Tickr sound copies into Stackr; the saved Holor Data Reveal example loads through a share URL and survives reload. No browser errors.
- Twenty tabs fit in two rows. Preview saved at /private/tmp/bfxr-interface-synths.jpg.
- Independent code/spec review found no actionable issues. An additional 450-render sweep covered mixed extremes and short durations without invalid or silent output.
