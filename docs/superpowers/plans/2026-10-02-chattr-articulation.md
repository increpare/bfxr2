# Chattr articulation implementation plan

**Goal:** A continuous path from playful chatter to recognizable synthetic English, approved by the user with “Have at!”.

**Architecture:** CMUdict supplies stressed English phonemes with a deterministic spelling fallback. A local Klatt-style formant engine renders continuous resonances, voiced excitation, consonant noise, stop closures and vowel glides. Articulation changes acoustic detail without changing the underlying pronunciation. No speech service or system voice.

**Files:** `ChattrLexicon.js` contains generated compact pronunciation data; `ChattrFormants.js` contains the attributed vendor engine and English sound bank; `Chattr_Pronunciation.js` converts text; `Chattr_DSP.js` schedules and renders. `Chattr.js`, `SpeechEditor.js`, `SaveLoad.js` and script includes integrate controls and compatibility. Third-party notices and a regeneration tool record provenance.

Execute inline in this checkout, retaining concurrent synth and portrait work.

- [x] Add pronunciation regressions in `tests/chattr.test.js`: homophones, ship/sheep, silent letters, stress, deterministic fallback, stable phonemes across articulation, legacy positional links. Run `node --test tests/chattr.test.js` and confirm the missing behavior fails.
- [x] Vendor the MIT formant engine and BSD pronunciation dictionary with pinned revisions and licenses. Implement English words, numbers, punctuation and fallback. Verify pronunciation fixtures.
- [x] Replace per-letter oscillators with phoneme events, stop closures/bursts, diphthong transitions, stress and sentence melody. Blend acoustic targets toward simplified chatter using articulation; keep voice color separate. Verify finite deterministic bounded PCM, distinctions and all voice controls.
- [x] Add Articulation and a Clear Speaker reference recipe. Update text help and legacy link migration. Keep existing portrait event fields and all exports. Verify old/new save and share round trips.
- [x] Run the whole test suite, minify/parse included JavaScript and CSS, inspect and operate Chattr in the browser. Render comparison WAVs, review code, fix findings, update README and record the limits of verification.

## Verification

- `npm test`: 123 tests pass, including 26 Chattr integration/DSP tests and 11 pronunciation tests.
- All 47 included scripts minify and parse; all four stylesheets minify. MIT/BSD notices remain in the single-file JavaScript bundle. `git diff --check` passes.
- Browser: Clear Speaker reaches articulation 1; dragging and arrow keys change articulation; typing, playback, immediate stop and reload persistence verified; no browser console errors. The compact editor leaves every voice control visible.
- Independent spec and code reviews completed. Fixed newly added controls being locked after old saves, missing lock keys after collection imports, and excessive number-expansion duration. Regressions failed before each fix and pass afterward.
- `node tools/render/chattr_examples.js` produced four WAVs, matching editable voice files, and `examples/Chattr/listen.html`. These share the same text; three vary only articulation. PCM is finite and bounded.
- Screenshot: `/private/tmp/chattr-speech-preview.jpg`. No subjective listening/transcription assessment was available; intelligibility remains a listening judgment.
- Existing and concurrent synth/portrait work is retained; no commits, deployment, or generated `bin` replacement.
