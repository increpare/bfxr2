# Fifteen-minute tab deluge

**Goal:** Twelve additional game sound makers with eight randomized categories each, integrated into the current cabinet. Work window starts 16:46 UTC and ends around 17:01 UTC on October 2, 2026.

**Design:** Extend the established PresetSynth/SoundDSP model. Separate engines represent explosions, weapons, electricity, moving air, bouncing contacts, rolling surfaces, breath, choirs, plucked strings, digital breakups, body rhythms and structural rumble. No additional explanatory UI. Preserve existing twenty tab positions; append twelve names, keep wrapping navigation. Existing saves and Stackr source copies remain compatible.

**Implementation:** Three workers own disjoint groups and tests; root owns Glitchr/Pulser/Rumblr, shared integration, examples and review. Each synth gets masterVolume, a stored seed, bounded explicit duration and useful audible controls. Presets change several controls. Float32Array audio is 44.1 kHz mono, finite, bounded, deterministic, edge-faded and muted at zero. Counts stay integral. No unrelated edits or commits.

- [x] Boomr/Pewpr/Zappr: shockwave/noise/debris, staged weapon pulse, arc/crackle engines and eight game categories each.
- [x] Whooshr/Bouncr/Rollr: moving filtered airflow, decaying bounce schedule, rolling contacts and speed surface variation.
- [x] Breathr/Choirr/Pluckr: airflow/exertion, detuned vowel ensemble, feedback strings.
- [x] Glitchr/Pulser/Rumblr: chunked digital corruption, double chamber pulses, low resonant pressure fields.
- [x] Append twelve script/tab registrations and Stackr sources; standard 390px panels; expand persistence tests.
- [x] Generate 96 seeded example sounds, editable collection and short reel. Verify all stored parameters replay exactly.
- [x] Run focused/full tests and minification, review new engines, inspect browser layout/generation/reload, save preview and record results.

**Results:** Twelve engines and 96 random preset categories integrated; 32 tabs total. Full test suite: 246 passed, zero failures. All 91 scripts and four stylesheets minified successfully. Example collection: 96 deterministic sounds with finite, bounded audio and exact replay; showcase reel: 20.45 seconds. Cross-review found and fixed a high-note Pluckr delay instability, with a raw-buffer regression test. Browser check confirmed all 32 tabs, Pluckr preset generation and persistence after reload, and no console errors. Screenshot: `/private/tmp/bfxr-tab-deluge.jpg`.
