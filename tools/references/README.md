# Reference sound measurement

Tooling for measuring a folder of tagged reference sounds and comparing them with the
Soundboard catalogue. The audio itself is never committed: the collection used so far is a
private mix of licensed library recordings and game captures, so only derived numbers live in
the repository (`docs/research/tagged-reference-measurements.md`,
`docs/research/references-vs-catalogue.md`).

## Layout expected

```
<root>/<tag>/<file>.wav      mono, 16-bit, 44.1 kHz
```

Convert a mixed folder of wav/ogg with ffmpeg (close stdin, or ffmpeg eats the file list):

```sh
find tagged -type f \( -iname '*.wav' -o -iname '*.ogg' \) | while IFS= read -r f; do
  tag=$(basename "$(dirname "$f")"); mkdir -p "tagged_wav/$tag"
  ffmpeg -nostdin -loglevel error -y -i "$f" -ac 1 -ar 44100 -sample_fmt s16 "tagged_wav/$tag/$(basename "${f%.*}").wav" </dev/null
done
```

## Measure and compare

```sh
uv venv .venv && uv pip install --python .venv numpy
.venv/bin/python tools/references/measure_tagged.py tagged_wav out/
node tools/render/verb_inventory.js --takes 4 --json out/catalogue_inventory.json
.venv/bin/python tools/references/compare_catalogue.py out/tags.json out/files.json out/catalogue_inventory.json out/compare.md
```

`measure_tagged.py` reuses `tools/preset_survey/analyze.py` for features (active duration,
attack, spectral centroid, flatness, pitch and pitch slope, voiced fraction). Tags map to board
verbs in `TAG_TO_VERB`; tags with no board verb are still measured. `compare_catalogue.py`
prints, per verb, the references' duration spread and tonality next to the catalogue's measured
spread and the vocabulary's class, with a one-line reading.

## Fitting Bfxr to a reference

The wav-to-Bfxr matcher in `tools/match` turns a reference into a `.bfxr` parameter set:

```sh
cd tools && uv sync && make -C bfxr_native
uv run python -m match.match path/to/reference.wav -o out/name --budget 4000
```

Check the match by measuring `out/name/match.wav` with the same features before trusting it;
a low score can still miss the pitch motion.
