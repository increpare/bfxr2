# Persistent listening evidence

## Retained sessions

| Archive | References judged | Distinct rated candidate identities |
| --- | ---: | ---: |
| `2026-10-03-real-v1/` | 40 | 73 |
| `2026-10-03-tagged-v2/` | 18 | 48 |
| `2026-10-03-coverage-v3/` | 6 | 24 |
| `2026-10-04-big-v4/` | 36 | 103 |

The first two sessions contain 58 reference judgments, **57 exact unique reference
audios** and **120 exact unique reference/candidate audio pairs**. The repeated
horn/Clonkr pair has consistent ratings. Preserve both sessions and group by
audio identity when learning or splitting data; folder-based candidate IDs
alone do not identify repetition across experiments.

The second archive also retains previous-model ratings and their exact clips.
It rejects gesture-v2 as an improvement: on the same 18 references it scored
1.83/5 against the previous model's 2.06/5, with 1 win, 13 ties and 4 losses.
See [the human review](../evaluations/tagged-v2-human-review.json) for the
comparison, frozen-model preference check and named regressions.

The third session retains **both likeness and usefulness** for all 24 candidates,
using schema 2. It contains six already-reviewed references, 18 new candidates,
and six exact previous audio baselines. See
[the coverage review](../evaluations/coverage-v3-human-review.json) for combined
audio-identity counts and same-session comparisons. Automatic matches scored
1.67/5 likeness and 3.50/5 usefulness; previous baselines scored 2.67/5 for both.
Seven new sounds rated usefulness 4 are exported in
`../presets/coverage-v3-useful.bcol`. Their low likeness scores are preserved too.
The same-session reference/candidate mapping is authoritative; repeated ratings
remain separate observations, including three one-point baseline changes.

The fourth session preserves all 103 likeness and 103 usefulness ratings from
big-v4, plus the note about unwanted clicks in `bird/Bird Sounds.WAV`. The learned
selector scored 1.94/5 likeness versus 1.75 for expanded auditory-v1 and 1.69 for
the historical baselines. Its same-pool comparison has 6 wins, 30 ties, 0 losses;
against historical baselines it has 13 wins, 18 ties, 5 losses. Five exact audio
agreements count for both selectors when comparing methods, but remain one
judgment each when training. No displayed candidate scored above 3/5 likeness.
See [the v4 human review](../evaluations/big-v4-human-review.json).

All four sessions retain **100 reference judgments, 75 exact unique reference
audios and 223 unique reference/candidate PCM pairs**. Twelve of the eighteen
replayed historical candidates received a different likeness rating from their
latest earlier rating of the same PCM pair. Preserve both observations and use
within-session comparisons; this is not a reason to overwrite earlier ratings.
The v4 checkpoint was evaluated against these labels before any retraining on
them. Its 27/36 strict pair predictions (16/20 on new exact-reference groups)
beat auditory-v1's 16/36 (8/20), but pairs are correlated and the evaluated
candidates were selected by these same metrics. This supports further study,
not a claim of generally good reproduction.

Schema 2 stores each target's role aliases in a `candidates` array and candidate
labels in `likeness` and `usefulness`. Schema 1 instead uses named roles and a
single `rating` field for likeness. Future consumers must explicitly support
the schema and dimension; never silently substitute usefulness for likeness.

## First session format

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

The first two sessions are one listener's ordinal **likeness-to-reference**
ratings (1–5), not labels of fun or production quality. The third session adds
separate usefulness labels; likeness keeps its original meaning. Preserve
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
