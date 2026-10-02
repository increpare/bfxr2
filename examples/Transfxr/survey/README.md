# Transfxr sound survey

[Open the listening catalogue](index.html). It includes all 512 sounds, family filters, central and boundary examples, six-exemplar comparisons, a tour of the centers, and links to edit exact sounds in Transfxr. [Families.bcol](Families.bcol) imports the shipped exemplars. [families_showcase.wav](families_showcase.wav) plays one center from each family in the table order; [showcase.json](showcase.json) records timestamps.

The 16 buttons in Transfxr use 344 complete sound exemplars. Repeated clicks change timbre, timing and trajectory as well as pitch. A compatible partner must share the oscillator and every curve shape; small correlated variations move both endpoints together. Dry exemplars stay dry. Locks protect entire transition rows and scalar controls.

| Family | Survey sounds | Shipped exemplars | Character |
| --- | ---: | ---: | --- |
| Bright Whistles | 36 | 24 | Clear high voices: whistles, chirps and thin ringing tones. |
| Grainy Taps | 37 | 24 | Quick textured attacks: part note, part rough little rustle. |
| Rocket Zips | 22 | 20 | Fast pitch climbs spanning several octaves. |
| Wavering Calls | 46 | 24 | Round, sustained electronic calls with changing pitch and tone. |
| Fuzzy Chirps | 16 | 14 | Brief bright fragments with a noisy or grainy coating. |
| Bass Plucks | 26 | 24 | Low rounded notes with a quick onset and a soft tail. |
| Soft Pips | 47 | 24 | Small rounded notes with a short, gentle envelope. |
| Sand Sprays | 32 | 24 | Bright, breathy bursts with little stable pitch. |
| Air Currents | 24 | 22 | Longer moving washes of filtered air and resonant noise. |
| Submarine Calls | 48 | 24 | Deep sustained tones with a subdued upper edge. |
| Descending Sweeps | 54 | 24 | Electronic tails that slide down in pitch or darken through a falling filter. |
| Rising Bloops | 37 | 24 | Rounded upward sweeps, from small burbles to rising calls. |
| Rubber Clicks | 34 | 24 | Short low pips, bouncy ticks and cushioned little clicks. |
| Falling Thumps | 20 | 18 | Low falling notes and resonant groans with a quick attack. |
| Reverse Bloops | 20 | 18 | Soft notes that swell towards their ending. |
| Static Flecks | 13 | 12 | Very short airy flicks and fragments of static. |

## Method and limits

The deterministic seed 20261002 supplies 512 proposals: 75% explore broad parameter combinations and 25% vary neighborhoods of the original eight recipes. Every proposal passes through the editor's parameter validation before rendering at 44.1 kHz. The survey rejects nonfinite/clipped outputs and RMS below 0.004; all 512 normalized proposals were accepted.

NumPy extracts 25 audio features in four equally weighted groups: envelope/time, spectral timbre, timbre motion and dominant-tone motion. Features use robust scaling and clipping. The tone estimate follows a strong spectral peak and may reflect filter resonance, not the oscillator fundamental; noisier frames are marked unvoiced.

K-means++ compares 8, 10, 12, 14 and 16 groups with 12 seeded restarts each. Selection chooses the finest result with at least 12 members per group and average silhouette within 0.04 of the best eligible score. This run selects 16 groups (silhouette 0.152); ten groups have the highest score. Clusters overlap. Names were authored from aggregate profiles and representative spectrograms, without claiming a human listening review. The catalogue exposes every member so the names can be judged and revised by ear.

Each bank starts with the nearest real example to its center, then uses farthest-first coverage inside the closest 92% of members, capped at 24. Exemplars with RMS below 0.009 are excluded from runtime generation to leave an audibility margin. Excluded candidates remain in the full catalogue. The build checks exact center IDs before assigning labels, preventing names from silently attaching to different clusters.

The separate seed 20261003 produced 512 audible, unclipped fresh samples (minimum RMS 0.0116, maximum peak 0.429). 90.0% were closest to their intended family; 95.9% were within 20% of the nearest-family distance. These are feature-space checks, not listening scores. Per-family results are in [validation.json](validation.json).

## Reproduce

Run from the repository root with Node.js and Python 3 plus NumPy. Plotting additionally requires Matplotlib. The application itself needs none of the Python dependencies.

```sh
node tools/preset_survey/render_corpus.js examples/Transfxr/survey
python3 tools/preset_survey/analyze.py examples/Transfxr/survey
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
node tools/preset_survey/validate_families.js /private/tmp/transfxr-family-validation 32
python3 tools/preset_survey/validate_families.py examples/Transfxr/survey /private/tmp/transfxr-family-validation
python3 tools/preset_survey/build_bank.py examples/Transfxr/survey
python3 tools/preset_survey/plot_representatives.py examples/Transfxr/survey
python3 -m unittest discover -s tools/preset_survey -p 'test_*.py'
npm test
```

WAVs and the listening reel are generated locally and ignored by Git. A fresh checkout must run the renderer and bank builder before catalogue playback; the synth buttons work immediately from the shipped JavaScript bank. Serve the repository root with the normal development server to use the catalogue's editor links. Seeded parameter sampling and clustering are reproducible; use the same NumPy version to avoid differences from numeric tie-breaking. If the center-ID check changes, inspect the new clustering and update its labels before building.
