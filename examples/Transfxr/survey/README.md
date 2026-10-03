# Transfxr listening refinement

[Audition the revised bank](index.html), [download its editable collection](Families.bcol), or play [the family reel](families_showcase.wav). The reel follows the table order; [showcase.json](showcase.json) gives timestamps. [The original survey archive](archive.html) preserves all 512 discovery sounds and the earlier exploratory labels.

The user's listening review found that short sound labels admitted long tails, some wavering calls had no wobble, soft pips were rough, sand included pitched outliers, sand/air overlapped, and direction-only groups had no common voice. The revised bank has 15 species and 228 exemplars. Bass Plucks and Rubber Clicks keep their successful surveyed character. Submarine Calls becomes Mournful Calls; Static Flecks becomes Radio Spits. Descending Sweeps and Rising Bloops become concrete Arcade Zaps and Bubble Pops, Falling Thumps is retired, and Reverse Bloops becomes a tightly defined Bubble Swells voice.

| Family | Exemplars | Character |
| --- | ---: | --- |
| Bright Whistles | 24 | Clear, bright electronic whistles with a clean ringing voice. |
| Grainy Taps | 12 | Dry, low gritty taps. A single quick attack, with no long tail. |
| Rocket Zips | 12 | A short hollow arcade whistle that rockets upwards and cuts off. |
| Wavering Calls | 12 | A rounded voice with an audible, steady quiver throughout the call. |
| Fuzzy Chirps | 12 | Tiny bright buzzes with a pitched chirp inside a fuzzy edge. |
| Bass Plucks | 24 | Low rounded notes with a quick onset and a soft tail. |
| Soft Pips | 12 | Gentle, clean sine pips with a cushioned onset and almost no pitch motion. |
| Sand Sprays | 12 | A short bright powdery spray: all grain, with no pitched note. |
| Air Currents | 12 | A longer, dark breath of air that eases in and out smoothly. |
| Mournful Calls | 24 | Low, woozy electronic calls with a plaintive, fading voice. |
| Arcade Zaps | 12 | A sharp sawtooth zap with a quick diving pitch and a bright sting. |
| Bubble Pops | 12 | Round little water-note pops: a sine voice that curls up and back. |
| Rubber Clicks | 24 | Short rubbery ticks and cushioned clicks, kept close to the original voice. |
| Bubble Swells | 12 | A rounded sine bloop that swells to a small peak, then stops. |
| Radio Spits | 12 | Brief fragments of filtered radio grit, dry and rough around the edges. |

## How this pass works

Family profiles are explicit in `tools/preset_survey/family_profiles.json`, authored by `create_profiles.py`. They select central full states from the measured survey and monotonically remap selected controls into the intended voice, retaining their joint ordering. Fixed oscillator/curve choices and bounded intervals preserve the family character. Successful original banks keep their states. Every C-number records its original T-number in [curated.json](curated.json); editorial projections are recorded per family. Exact curated PCM and editable params are rendered from the current synth.

Runtime generation chooses whole curated states, blends compatible trajectories and nudges controls, then enforces each family's limits. Constraints apply before SynthBase respects user locks. A deliberately locked control may therefore change the resulting voice. Dry short species keep zero echo. The first six catalogue examples are typical members of the revised bank, while all exemplars remain inspectable.

All 228 exemplars and 480 fresh seeded variations passed finite/audible/unclipped and family-trait checks. Checks measure whole rendered durations, spectral separation for sand/air and soft pips, and actual eight-Hz pitch motion for wavering calls. Minimum fresh RMS is 0.0164; maximum peak is 0.388. [Per-family results](curated-validation.json) are tied by SHA-256 to the bank, sampler, renderer and parameter validation sources. Rebuilding rejects stale measurements. These verify traits, not aesthetic quality; this revision incorporates the user's listening notes without claiming another human ear review.

## Reproduce

Use Node.js and Python 3 with NumPy, from the repository root. The saved discovery corpus and analysis are inputs to this editorial pass; they remain unmodified.

```sh
python3 tools/preset_survey/create_profiles.py
node tools/preset_survey/curate_families.js examples/Transfxr/survey
node tools/preset_survey/validate_families.js /private/tmp/transfxr-listening-validation 32
python3 tools/preset_survey/measure_curated.py examples/Transfxr/survey /private/tmp/transfxr-listening-validation
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
node --test tests/preset-character.test.js tests/preset-family.test.js tests/preset-survey.test.js
python3 -m unittest discover -s tools/preset_survey -p 'test_*.py'
```

Curated WAVs and the reel are generated locally and ignored by Git; a fresh checkout runs the commands above before catalogue playback. The runtime JavaScript bank works immediately. To restore archive audio from its saved original states with the current renderer, run `node tools/preset_survey/render_saved_corpus.js examples/Transfxr/survey`. This leaves `corpus.json` and `analysis.json` unchanged. Serve the repository root to use editor links.
