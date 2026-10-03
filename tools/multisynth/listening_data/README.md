# Persistent listening evidence

`2026-10-03-real-v1/` retains the user's first exported listening session:
40 reference judgments and 73 distinct rated candidates. Seven targets selected
Bfxr itself; the two UI roles share one candidate and one judgment.

- `feedback.json`: the original attachment bytes, unchanged.
- `manifest.json`: validated identities, target source hashes, DSP/feature/library
  provenance, candidate parameters, render seeds, scores, search traces, notes,
  ratings and summary. Audio paths are relative to the archive directory.
- `audio/*.flac`: lossless PCM16 copies of the exact normalized/trimmed reference
  and candidate clips played by the gallery. Every file is decoded and compared
  sample-for-sample on import. Content-addressed files deduplicate identical
  clips; the manifest retains original WAV and decoded PCM hashes.

The archive survives cleanup of ignored run directories and original source
folders. Parameters plus seeds identify a recreation; exact re-rendering also
requires the recorded DSP revision. Archived clips remain authoritative if DSP
changes. Source paths are provenance, not playback dependencies.

## Interpretation and reuse

These are one listener's ordinal **likeness-to-reference** ratings (1–5), not
labels of fun, production quality, or whether a preset is worth keeping. Preserve
them indefinitely as versioned evidence; never rewrite them with a new model's
score or attach them to a changed render. A later opinion is a new session.

Use both low and high ratings. There are 15 selected wins, 21 ties and 4 losses
against Bfxr; only 19 pairs give a strict preference. Deduplicate shared candidate
roles. Do not count ties as wins or treat two candidates from the same reference
as independent held-out examples. The mean is descriptive, not a calibrated
interval measure. There are no 5/5 ratings in this batch.

If used to tune retrieval, a distance, or a selector, this becomes development
data. Split validation by reference/audio family, including copied files under
different tags, before reporting generalization. Use audio hashes and listening
checks to detect overlap; exact hashes alone cannot detect alternate encodings,
crops or related takes. The next tagged manifest marks exact normalized PCM
overlap with this batch, but does not certify all remaining files as independent.

A low selected score does not establish that a different finalist was good.
Diagnose candidate availability separately from selection quality. Do not fit a
large preference model to these 40 references and then evaluate on them.

For future sessions, collect likeness and game-SFX usefulness separately if both
are wanted. Qualitative notes about gesture, weight, texture and event structure
can explain failure modes that a single number cannot. No such notes were
provided in this first batch; do not invent them from filenames.

This archive is local research material containing reference audio from the
user's corpus. Retention here does not change the original sources' licenses.
