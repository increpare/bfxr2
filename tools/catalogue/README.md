# Local UCS catalogue

Organises a collection of sound-effect libraries without moving, renaming or
modifying the source recordings. The first implementation inventories original
files, preserves publisher descriptions, proposes UCS categories, checks exact
duplicates, and provides a local listening/review browser.

This is a **provisional catalogue**, not a finished training dataset. Labels remain
provisional until reviewed. Multi-effect tracks have separate description rows
but still play the full recording; their event boundaries have not been cut.

## Run

From `tools`, using Python 3.12 or later, with `ffmpeg` and `ffprobe` on PATH:

```powershell
$env:BFXR_SFX_ROOT = 'D:\Sound_Effects_Dumps'
python -m catalogue taxonomy
python -m catalogue scan
python -m catalogue dedupe
python catalogue/adapters/described.py --root $env:BFXR_SFX_ROOT --ucs "$env:BFXR_SFX_ROOT/_catalogue/ucs.json" --output "$env:BFXR_SFX_ROOT/_catalogue/labelling/described.jsonl"
python catalogue/adapters/games.py --root $env:BFXR_SFX_ROOT --ucs "$env:BFXR_SFX_ROOT/_catalogue/ucs.json" --output "$env:BFXR_SFX_ROOT/_catalogue/labelling/games.jsonl"
python catalogue/adapters/structured.py --root $env:BFXR_SFX_ROOT --ucs "$env:BFXR_SFX_ROOT/_catalogue/ucs.json" --output "$env:BFXR_SFX_ROOT/_catalogue/labelling/structured.jsonl"
python catalogue/adapters/additions.py --root $env:BFXR_SFX_ROOT --ucs "$env:BFXR_SFX_ROOT/_catalogue/ucs.json" --output "$env:BFXR_SFX_ROOT/_catalogue/labelling/additions.jsonl"
python -m catalogue import
python -m catalogue build
python -m catalogue serve --port 8766
```

Open `http://127.0.0.1:8766`. The server binds only to the loopback address.
Category counts reflect the current search, library and other filters. The
active filters are listed above the results; `Clear other filters` keeps the
selected category and removes the other restrictions. Clicking the whole-catalogue
unclassified count shows all unclassified entries, including duplicate copies.
Page controls appear above and below the results, with a page-number selector.
The core uses the standard library. The structured adapter also needs `pypdf`
to read Universal's track guide. The original UCS spreadsheet is read directly
without editing it or requiring a spreadsheet package.

Run writing stages sequentially, after downloads or external folder changes
have settled. Adapters write separate files, so their analysis can be done
independently. Rescan after adding or renaming source files, then regenerate
the affected adapter output and import/build again. A scan skips unchanged
files and retries pending files; decoded hashes are cached.

On the Windows machine used for the first pass, `python` resolves to an
unavailable Windows Store alias. A working bundled interpreter is available at
`C:\Users\Anwender\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.
Invoke that absolute path with PowerShell's `&` when needed. No package or
system configuration changes are required for the current machine.

## Outputs and their meaning

Everything derived is kept in `<root>/_catalogue/`:

- `catalogue.sqlite`: source inventory, publisher descriptions, taxonomy.
- `catalogue.csv`: export of description entries with file references and labels.
- `ucs.json`: the 753 subcategories from the supplied UCS v8.2.1 workbook.
- `labelling/*.jsonl`: rerunnable metadata classification results with reasons.
- `summary.json`, `coverage.json`: counts and proposed UCS coverage.
- `sample-variants.json`: identical decoded sample values stored at different
  playback rates, retained as related versions rather than exact duplicates.
- `import-errors.json`: metadata rows that could not be joined to playable audio.
- `overrides.jsonl`: append-only manual review decisions; **back this file up**.
- `automated-proposals.jsonl`: reversible proposals for otherwise unlabelled
  entries, from exact labelled copies or a local audio model. These never replace
  metadata labels or manual decisions and are invalidated when source bytes change.
- `previews/`: full-recording PCM playback copies created on demand. No
  normalisation, trimming or replacement of original recordings.
- `work/`: adapter audits and extraction exceptions.

The CSV and browser use one row per description, not necessarily one row per
recording. Universal has 1,074 index descriptions across 484 recordings. A
category count does not establish the number of isolated examples available.

Confidence describes the strength of the **metadata interpretation**. It is not
a calibrated probability and does not mean the audio was listened to. A broad
category without a leaf is intentional. Console/game names are provenance, not
sound labels. Opaque filenames can receive separately marked audio model
suggestions; low similarity and ambiguous alternatives require particular care.

The metadata adapters apply explicit phrase/family mappings and retain the
evidence behind their decisions. They do not call external models or upload
audio. Mappings were checked for misleading words and source
context, but have not received a comprehensive listening audit.

Automated proposals are kept outside the adapter files, with source hashes,
method, model evidence and alternatives. The browser has separate classification
filters for audio suggestions and labels inherited from identical recordings.
An audio model similarity score is not a probability or a human listening review.
Model-labelled entries have `audio_verified=false`, `training_eligible=false`
and `review_needed=true`. A non-empty category does not make an entry ready for
training. Metadata labels also still require listening and segmentation checks.

Explicit FF and Nintendo DS wavebank exports have a separate asset-kind grouping,
`DESIGNED / SOURCE`. This identifies raw sample elements without asserting that
they are musical or naming the sound event. The browser shows their unresolved
sound labels separately; `unresolved_sound_roles` includes unclassified rows,
source elements and context-only groups. Better exact-copy evidence or an accepted acoustic proposal
may refine that asset-only grouping while preserving its bank provenance.

Confirmed rendered console-game effects can use UCS `GAMES / VIDEO` as a
source-context grouping when their exact event remains unknown. These have
`classification_status="context only"`, remain in the unresolved-event count,
and never serve as semantic donors for duplicate labelling. This grouping is
not evidence that a sound is a jump, an explosion, a voice, or synthesised.
Accepted audio proposals and later manual reviews can refine it.

An explicitly tentative audio guess uses `decision_strength=tentative` and is
displayed as `tentative proposal`. Its evidence retains competing interpretations
and conflicts. These guesses give ambiguous recordings a proposed archive home,
but remain in the unresolved sound-role count alongside source-context groups
and raw source elements. They are not verified training labels.

`exact-excerpt` proposals identify a decoded sample sequence contained within a
labelled recording. They are separate from full-recording duplicate matches and
audio-model predictions; playback-rate differences and excerpt boundaries remain
in their evidence. Their inherited category still needs listening review.

`_catalogue/acoustic-traits.jsonl` stores measured waveform character separately
from UCS. The browser can filter very brief clips, strong tonal components,
broadband noise and changing dominant frequency. Traits are attached only to
matching source paths and byte hashes, do not assign a source category, and do
not establish synthesis. The raw measurements and thresholds remain in each
record's evidence. These traits cover the unresolved subset analysed so far;
absence of a trait is not evidence that the opposite characteristic is present.

After importing updated metadata, rebuild the proposal layer with:

```powershell
python -m catalogue.enrichment --root $env:BFXR_SFX_ROOT --audio-proposals "$env:BFXR_SFX_ROOT/_catalogue/work/acoustic-accepted-proposals.jsonl"
python -m catalogue build --root $env:BFXR_SFX_ROOT
```

Omitting `--audio-proposals` rebuilds only exact-copy proposals. Passing an old
prediction file is safe: source hashes and current metadata are checked, and
manual decisions always win. Raw diagnostic predictions without explicit
`accepted=true` are ignored; an unvalidated model run must not fill the archive
with arbitrary labels. Originals and their descriptions remain unchanged.

Exact byte hashes and decoded PCM hashes identify duplicates while retaining
all original paths. Decoded comparisons preserve sample rate and channel count;
they do not equate lossy encodings, resampled versions, alternate edits, or
perceptually similar recordings. All duplicates remain available with the
browser's `Show duplicate files` filter. No originals are deleted.

The `sample_family` column groups identical decoded sample values with matching
channel counts regardless of playback rate. Many Wayzata WAV/AIFF versions have
the same sample values but slightly different rates. Keep these related versions
together in future train/test splits. This grouping does not detect every edit,
lossy copy or near-duplicate.

Manual label changes are read from the override log whenever the browser loads.
Run `build` again to refresh exported CSV/JSON after making reviews. Review IDs
currently include the original source path, so externally renaming a recording
does not automatically move its reviews to the new path. The old evidence and
review log remain preserved for an explicit migration. Numbered publisher-guide
entries survive wording corrections; unnumbered rewritten descriptions may need
the same migration. Preserve the manifest and log when moving the archive.

## Remaining work

- Verify labels by listening and review uncertain source descriptions.
- Segment multi-effect tracks, preserving gestures and natural tails.
- Extend acoustic measurements beyond the unresolved subset and inspect spectrograms.
- Select varied exemplars and freeze independent evaluation sets.
- Handle Craig Smith archives and spoken identifiers, the 6000sfx installer,
  and unsupported legacy resources. These are inventoried, not silently lost.
- Check near-duplicates beyond exact decoded audio.

No scope pruning is imposed in this pass: speech, music and ambience remain
catalogued with their content type rather than being discarded.

## Verification

```powershell
python -m unittest catalogue.test_core catalogue.test_enrichment catalogue.test_server -v
node --test catalogue/test_browser.cjs
```

Core tests use temporary fixtures. Browser tests launch a temporary loopback
server with generated audio, check playback byte ranges and review persistence,
and verify the original audio bytes stay unchanged. They never create a review
decision on a real library recording.
