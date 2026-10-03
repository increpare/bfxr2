# Six more Bfxr sound makers

Build the six tabs the user approved: Clonkr (material impacts/scrapes/rattles), Machinr (mechanisms starting/running/stopping), Weathr (seamless environmental textures), Jinglr (short musical gestures with a phrase editor), Squishr (liquids and soft bodies), and Stackr (layered events with a small timeline). Preserve and coexist with the independent Chattr voice work.

Every tab has named randomized category buttons, Randomize and Mutate. Each category click varies multiple relevant controls within a recognizable character; locks preserve parameters during generation. Provide at least six categories per tab and editable .bcol examples plus rendered WAVs. Keep all synthesis local, deterministic for stored parameters, finite and bounded at 44.1 kHz. Reuse existing save, link, collection and WAV tools.

Use a shared PresetSynth subclass solely for parameter validation, random category recipes and PCM realization. SoundDSP provides seeded randomness and safe finishing. Each instrument owns its own DSP and definition files. No existing synthesis behavior changes. Root owns shared integration files; engine implementers only edit their assigned new files.

Clonkr exposes material, size, hollowness, hardness, damping and action. Machinr exposes mechanism, speed, load, roughness and start/stop timing. Weathr exposes source, density, turbulence, brightness and loop duration; its preview loops and exported PCM has a clean repeat boundary. Jinglr has key/scale, contour, count, rhythm/timbre and an editable short note grid. Squishr has viscosity, pressure, wetness, stretch and bubbles. Stackr stores copies of source parameters and edits each layer's source, start, level and pitch; imported/exported stacks remain self-contained. Presets assemble sounds from the other instruments.

Verification: meaningful engine tests for control effects, deterministic renders, bounded output, randomized category variation and locks. Integration tests cover save/link/import and loop/sequence/stack behavior. Browser exercise all tabs, visual editors, categorized buttons, playback and reload. Compile/minify all included code. Review final work and preserve unrelated user changes.

## Jinglr refinement agreed during implementation

Replace the explicit note grid with two repeatable seed fields. Melody seed composes the notes; instrument seed encodes its family in the first digit and its timbral variation in the remaining five. Instrument-family buttons always generate another voice in that family without replacing the melody. Expand to eight acoustically distinct families. Keep stored phrase data for exact existing collections and Stackr snapshots, but remove note-by-note UI. Melody lock holds its musical controls, while instrument lock holds family and voice seed. Keep the usual category generators for complete cues.

## Compact Jinglr revision

Remove the title, duration, descriptive paragraphs and melody/instrument lock buttons. Show one ten-digit Seed field (five melody digits, five instrument-character digits), a Reseed melody button, and eight instrument buttons under a small Reseed instrument header. Family remains selected separately. Each reseed action changes only its own part. Keep exact saved phrases on import and keep seed halves reproducible for newly composed sounds.
