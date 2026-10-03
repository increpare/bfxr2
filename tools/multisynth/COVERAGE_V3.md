# Soundboard coverage diagnostic

The third listening batch tests a richer candidate generator, including layered
sounds, after human feedback rejected gesture-v2. It retains auditory-v1 ranking
and uses the Soundboard catalogue from `claude/determined-sagan-khz12h`, frozen at
`db9f5f8a8bf50b951b44a163dd6685222bfae859`. The parallel checkout is not modified.

## Evidence from the other branch

Commits `e4a1b59`, `58f7da1`, and `db9f5f8` apply three rounds of listening
feedback: removing weak or misleading recipes, correcting doors/steps/dashes,
and adjusting weights and alignments for compositions. These are useful human
curation priors for generating coherent game sounds. A focused inspection did
not locate raw numeric rating exports. Commit notes and recipe weights are not
imported as exact-reference likeness labels.

The library uses 12 deterministic draws from each of 192 catalogue entries:
2,304 candidates, zero render/descriptor failures. It samples entries equally;
curated weights remain provenance rather than training labels. The explicitly
reference-fitted Bfxr coin template is excluded. Other recipes may have been
influenced by tagged-reference listening; this is a development diagnostic, not
a held-out evaluation. Every candidate uses the real frozen DSP, including
nested source parameters, rendering seeds, balance and alignment for mixtures.

## Listening batch

Local page: `runs/coverage-v3/index.html`. Six previously reviewed references:
coin, punch, jump, step, door and magic. Each has four candidate cards:

- **Automatic match:** lowest auditory-v1 distance across the entire new library.
  No category tags or old ratings enter this selection.
- **Category-guided diagnostic:** best remaining recipe with the known game verb.
- **Different ingredients:** next different recipe signature within that verb.
- **Best previously rated:** highest-rated candidate from the second archive,
  with ties preferring the original auditory-v1 result. Exact archived PCM is
  replayed without further trimming or normalization.

The automatic match often belongs to a different verb. That is not by itself
an error, but the assisted candidates help test whether better sounds exist
that global ranking misses. There is no new claim of audible improvement yet.
There is no parameter refinement in this batch: it deliberately preserves
the catalogue's generated gestures while testing candidate coverage.

Both **likeness** and **usefulness/fun** get independent optional 1–5 ratings.
The browser saves them by immutable experiment and candidate identity; JSON
export includes both dimensions and notes. The schema-2 importer validates
provenance and retains exact PCM16 audio, full presets, raw feedback, and both
labels. Only likeness is evidence for reference matching. Usefulness must not
be substituted for likeness in future training. The existing gesture fitter
still targets schema-1 archives; a future consumer must explicitly read schema-2
candidate arrays and the intended rating dimension.

`evaluations/coverage-v3-results.json` preserves all 24 choices and replay
parameters. `evaluations/soundboard-db9f5f8-snapshot.json` records hashes of the
102 source/helper JavaScript files. Large library/audio output stays local in
ignored `runs/`. Existing listening archives remain versioned and unchanged.

## Reproduce

Run from the repository root, with the tools Python environment available.
Use a new directory for each library/gallery; both builders reject overwrites.

```sh
mkdir -p tools/multisynth/runs/soundboard-db9f5f8
git archive db9f5f8a8bf50b951b44a163dd6685222bfae859 js tests/helpers tools/render/wav.js index.html css img favicon.ico favicon.png | tar -x -C tools/multisynth/runs/soundboard-db9f5f8
cp tools/multisynth/evaluations/soundboard-db9f5f8-snapshot.json tools/multisynth/runs/soundboard-db9f5f8/snapshot.json
PYTHONPATH=tools python -m multisynth.soundboard \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --output tools/multisynth/runs/soundboard-library-v3 --takes 12 --jobs 4
PYTHONPATH=tools python -m multisynth.coverage \
  --snapshot tools/multisynth/runs/soundboard-db9f5f8 \
  --library tools/multisynth/runs/soundboard-library-v3 \
  --archive tools/multisynth/listening_data/2026-10-03-tagged-v2 \
  --output tools/multisynth/runs/coverage-v3
```

Build timing and absolute snapshot paths are retained in library metadata, so
a rebuild may have a different manifest/experiment identity despite identical
candidate audio. Never attach old ratings to that new identity by rewriting IDs.
Keep the original results and archive feedback against the actual audition run.
The gallery's editor links target the pinned app snapshot so newer DSP changes
cannot silently alter the meaning of a saved preset. The collection contains
18 new Soundboard candidates; old comparison audio stays in the gallery.

Archive the next export through the existing command (schema dispatch is automatic):

```sh
PYTHONPATH=tools python -m multisynth.listening /path/to/feedback.json \
  --report tools/multisynth/runs/coverage-v3 \
  --output tools/multisynth/listening_data/NEW-SESSION
```

## Verification

46 focused Python tests passed, including legacy feedback, schema-2 immutable
archival, source replay, tag-blind automatic selection, and baseline audio
preservation. Seven feedback JavaScript tests passed, including separate
dimensions, aliases, clear/reload/copy behavior and exclusive audio playback.
All 18 new gallery clips were replayed sample-for-sample and their descriptors
checked against the library. All 24 candidate clips are nonempty mono 44.1 kHz
PCM16. The entire prior archive's PCM hashes and raw-feedback checksum verified.
Browser checks confirmed separate candidate/dimension ratings survive reload,
test ratings clear to an empty export, and a generated preset opens in the
pinned Soundboard editor. Listening quality remains for the human pass.
