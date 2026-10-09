# Standalone bfxrlib

Approved in conversation: ordinary script inclusion, one global `bfxr`, all 23 current synths and their preset generators, portable sound data, lazy audio setup, automatic bounded caching, and reusable mutations around an unchanged original.

## Public interface

`preset(synth, category, seed?)` returns a `.bfxr` compatible object (`synth_type`, engine `version`, `params`, plus `renderSeed`). Category IDs are stable strings derived from existing generator IDs; Footsteppr has `snow`, `grass`, `dirt`, `gravel`, and `wood`. An optional number or string seed reproduces the generated sound. `synths()` and `presets(synth)` return available string IDs.

`play(sound, options?)` and `playMutated(sound, amount=0.05, count=15, options?)` return independent voice handles with idempotent `stop()`. Options are `volume` (default 1), `pitch` in semitones (default 0), and `loop` (default false). Input is either an exported object or its JSON string. Unknown synths/categories and invalid options throw descriptive errors.

`cache(sound)` and `cacheMutations(sound, amount=0.05, count=15)` return Promises and prewarm PCM without creating an AudioContext. Work yields between renders. `stopAll()` stops active voices. `clearCache()` removes cached PCM and mutation pools. `render(sound)` returns an independent mono Float32Array at `sampleRate=44100`, useful for other audio systems and inspecting synthesis without playing.

The first `count` mutated plays build one variation each; later plays randomly reuse that pool. Every variation starts from the original. Numeric controls stay within their schema bounds; waveform/instrument choices, seeds, master volume, transition curves, edited phrases, and Mixr source assignments stay fixed. Mixr mutates the numeric controls inside its saved sources too. Cache keys include normalized parameters and rendering seed, never object identity or filename. A 32 MiB LRU budget covers retained sample data and a separate bounded metadata cache holds mutation definitions.

## Shared synthesis and packaging

All engines expose `render()` without Web Audio; the editor's existing `generate_sound()` wraps that output in RealizedSound. The library bundles the same engine files inside a private closure, with a private Math object for existing synchronous seeded generators. It does not change the host's Math object or create other globals. Footstep terrain patches compile at build time and retain their existing source patches.

Build script `node tools/build-library.js` produces readable and minified JS in `lib/`, with notices embedded in both. No consumer npm dependency, assets, fetches, workers, setup call, or module loader. The HTML example lives alongside those files and works directly from disk. AudioContext is created only when playing and resumed from a user gesture; browser autoplay rules still apply.

## Verification

Tests exercise the shipped readable/minified scripts in isolated contexts without DOM/storage, all current engines, seeded reproducibility, compatibility with exported sounds, cache reuse and eviction, mutation immutability, voice overlap/cleanup, lazy audio setup, and isolation of globals. Browser smoke tests load the example from disk and test genuine Web Audio. Existing editor tests and build must continue to pass.
