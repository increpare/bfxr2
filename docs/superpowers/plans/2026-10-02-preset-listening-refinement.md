# Transfxr listening refinement plan

**Goal:** Make preset names predict a recognisable audible voice, incorporating the user's audition notes.

**Architecture:** Explicit family profiles curate full states from the saved survey. Runtime sampling enforces those profiles before lock-aware application. Render a separate curated catalogue and keep the unedited discovery corpus available as an archive.

- [x] Add regression checks for short sounds, sustained wobble, soft tonal pips and sand/air separation; observe current failures.
- [x] Add bounded family profiles and sampling support; curate complete exemplar states with survey provenance.
- [x] Render and measure every curated exemplar and fresh variations; enforce audible character checks and fix discovered failures.
- [x] Rebuild catalogue, collections, reel and documentation; preserve the raw survey as an archive.
- [x] Verify regressions, browser playback/imports and source provenance; request a focused review and address findings.

Verification: 228 curated exemplars and 480 seeded fresh variants passed rendered trait checks. All 352 app tests and six Python tests passed; 95 scripts and four stylesheets minified successfully. Browser checks confirmed all 15 family names, six short tap variants, sustained-call playback and exact editor import, fresh dry taps and clean pips, and source-linked archive playback without console errors.

Review fixes: removed the archive's link to the revised reel; fingerprints now cover all nine sampler/renderer dependencies and reject stale records. Archive regeneration uses saved source states without rewriting the corpus. Versioned preset script URLs resolved a browser cache holding the old bank, with matching build support. The original 512 states and analysis remain unchanged. Listening remains the aesthetic test.
