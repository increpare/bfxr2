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

## Human verdict, 2026-10-03

The completed pass is retained in `listening_data/2026-10-03-coverage-v3/`:
six references, 24 candidates, 24 likeness and 24 usefulness ratings. Raw export
bytes and every audition clip are preserved. No qualitative notes were supplied.
The full analysis is `evaluations/coverage-v3-human-review.json`.

| Choice | Mean likeness | Mean usefulness | Likeness vs rerated baseline: win / tie / loss |
| --- | ---: | ---: | --- |
| Automatic | 1.67 | 3.50 | 1 / 1 / 4 |
| Category-guided | 1.83 | 3.17 | 0 / 1 / 5 |
| Different ingredients | 1.83 | 3.33 | 0 / 2 / 4 |
| Previous baseline | 2.67 | 2.67 | — |

Even choosing the highest human likeness score among the three new candidates
for each reference gives 2.50/5, with one win, three ties and two losses against
the rerated baseline. This is an upper bound for these three sampled candidates,
not for the entire library. None of the 18 new sounds reached likeness 4 or 5.
The automatic Transfxr splash for the punch was the sole new likeness win (3
versus 2); semantic category mismatch is not necessarily audible mismatch.

Seven new candidates received usefulness 4. All seven are retained, without
likeness filtering, in `presets/coverage-v3-useful.bcol`: Clonkr blip, Transfxr
splash, Bfxr/Clonkr hit, Rustlr step, Footsteppr/Rustlr step, Jinglr win, and
Swarmr cast. Their IDs, scores and source provenance are in the analysis JSON;
full parameters and exact audio remain in the listening archive. Every exported
preset was replayed and compared sample-for-sample with its rated audio using
the pinned DSP. These are promising individual presets, not proof that all
draws from those recipe families will be useful.

Frozen-metric rescoring of exact audition audio agrees with 18/28 strict
likeness preferences for auditory-v1, 22/28 for the gesture prior, and 23/28 for
the first-batch gesture fit. Among new candidates only, agreement is 6/14, 9/14,
and 10/14 respectively. These correlated comparisons from six development
references do not reverse the previous rejection of gesture-v2 generation:
rescoring a fixed candidate set and optimizing new sounds are different tests.
This also cautions against assuming a single metric is reliably best across
candidate pools. No metric has been promoted or retrained on this batch.

Three repeat likeness judgments differ by one point (coin 3→4, punch 3→2,
door 1→2). Preserve both sessions rather than overwriting either; comparisons
above use the judgments from this same listening pass. All means describe
ordinal ratings, not calibrated perceptual distances.

**Decision:** reject Soundboard-only retrieval and hard category filtering as
standalone fixes for likeness. Keep the seven useful sounds separately. The
next development experiment should refine human-preferred saved gestures with
controlled changes, retain the original candidates, and compare likeness and
usefulness independently. Do not present target-specific human-selected seeds
as an automatic result on unseen references, or infer qualitative failure
labels from filenames when the listener supplied no notes.
