# Preset mixing and sound cabinet implementation plan

**Goal:** Make two-generator mixing immediate, add expressive birds, sharpen the physical sound families, and prune weak tabs.

**Architecture:** Mixr stores generator identity alongside its two immutable parameter snapshots. Playback uses snapshots; Regen alone invokes generators. Each acoustic engine retains its saved identity and migrates newly added controls. Retired engines remain importable for existing files but leave navigation and the Mixr catalog.

**Tech stack:** Existing browser JavaScript, PresetSynth, mono Float32 DSP at 44.1 kHz, Node test runner.

- [x] Add failing Mixr tests for stable generator identity, independent regeneration, both-slot regeneration, deterministic saved playback, catalog validation and legacy snapshots.
- [x] Implement generator catalog and Mixr selectors with Regen / Regen Both; develop curated complementary pair recipes including Ghost Chord × Portal Tear.
- [x] Add Birdr and short animal articulations in Crittr; verify deterministic sound and useful short randomization.
- [x] Rework Fractr structure/fragment timing and Boomr gas/aftershock/rubble layers; verify raw finite output and distinct envelopes.
- [x] Add single-breath direction interpolation and independent Pluckr vibrato amount; retain old cycle and string snapshots.
- [x] Move Transfxr Morph below destination; rename no-morph choice. Keep independent noise texture. Order Impactr Object, Surface, Force. Explain Choirr ensemble seed.
- [x] Remove Chattr, Pewpr and Rumblr from default tabs; preserve explicit legacy imports. Integrate new parameter migrations for saved links.
- [x] Render reproducible Mixr and new-synth examples with editable links. Check saved replay, levels and extremes.
- [x] Run full tests and in-memory bundle minification. Inspect and exercise browser controls, capture final UI.

Verification: 395 tests pass. Final JavaScript/CSS bundles parse and minify. Browser checks cover Morph placement, both Mixr regeneration paths via exported snapshots, classic-source dropdowns, Breathr mode visibility, Impactr order and Birdr generators. Rendered 45 reproducible examples plus 32 isolated Mixr ingredients and a six-combination reel. Read-only review found one mode-visibility bug; fixed and covered by a regression test.
