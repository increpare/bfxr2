# Persistent listening evidence

## Retained sessions

| Archive | References judged | Distinct retained candidate identities |
| --- | ---: | ---: |
| `2026-10-03-real-v1/` | 40 | 73 |
| `2026-10-03-tagged-v2/` | 18 | 48 |
| `2026-10-03-coverage-v3/` | 6 | 24 |
| `2026-10-04-big-v4/` | 36 | 103 |
| `2026-10-04-neural-v1-quick-01/` | 5 | 19 |
| `2026-10-04-neural-v2-quick-01/` | 5 | 20 |
| `2026-10-04-temporal-v3-quick-01/` | 5 | 15 |
| `2026-10-05-pitch-calibration-quick-01/` | 5 | 12 |

The eighth archive retains all five pitch-calibration comparisons, with all 12
options auditioned and seven strict heard-only preferences. Both changed
calibration selections lose: the uncalibrated Bfxr beep wins, and original Bfxr
wins the bell. Original Bfxr also wins battleStart. The earlier Transfxr charm
wins its first direct heard comparison against the later Bfxr partial success.
The Transfxr whistle wins against original Bfxr, but is the unchanged baseline,
so this is not evidence for calibration. No absolute likeness or usefulness
ratings were supplied. The exact-audio matching objective agrees with 2/7 pairs;
the older learned preference scorer agrees with 3/7. See
[the human review](../evaluations/pitch-calibration-quick-01-human-review.json).
Do not promote the passing synthetic pitch gate to a human quality claim.

The seventh archive is a partial temporal-v3 session: five of six references,
four best choices and one rejection, with 15 candidate identities and 19 exact
PCM audios. New Pluckr wins book-close over both heard historical options. New
Bfxr wins charm2 over heard original Bfxr; the earlier Transfxr option was not
recorded as auditioned, so no preference against that earlier winner is inferred.
Earlier Bfxr wins spinout and bird. All heard robot-talk candidates are rejected
again. Egg jump remains unjudged. There are six strict heard-only comparisons
from four reference groups, with no scalar ratings. The separate, verbatim
`qualitative-feedback.json` records book-close as the same general character but
still a bit off, and charm2 as closeish, approaching a recreation. These are
qualified partial matches, not fully convincing successes or evidence that the
entire new pipeline is close. The matching objective agrees with four of six pairs and
disagrees on bird and one spinout pair, supporting regular human review even
when numerical scores improve. See
[the temporal-v3 human review](../evaluations/temporal-v3-quick-01-human-review.json).
Keep the earlier Transfxr charm2 as a listening anchor alongside the new Bfxr:
this partial audition does not justify replacing it as the established baseline.

The sixth archive retains all five v2 quick comparisons, 20 candidate identities
and 24 exact PCM audios. Four best choices yield seven strict comparisons from
four reference PCM groups; computer was rejected. Previous Bfxr wins spinout,
selected Bfxr wins bird/card, and previous Transfxr wins charm2. The user's
separate qualitative assessment says **only charm2 was actually approximated**.
That clip predates v2, so this round demonstrates no new v2 audible success.
Relative choices do not establish absolute closeness. See
[the v2 human review](../evaluations/neural-v2-quick-01-human-review.json).

The fifth archive is a **partial quick-listening session** using schema 3:
four explicit best choices and one “None are close”, with no scalar likeness
or usefulness ratings. All presented options were auditioned. Four reference
groups produce seven strict heard-only comparisons; these are correlated
comparisons, not seven independent reference judgments. It retains all 19
candidate identities (including raw diagnostic clips) and 24 exact PCM audios.

Original Bfxr won `attack/spinout.wav`; previous audio won bird and card;
the neural-selected Transfxr finalist won `die/charm2.wav`. All three displayed
computer finalists were rejected. See
[the partial human review](../evaluations/neural-v1-quick-01-human-review.json).
The user reported that the quick listening flow was much better. This UI
feedback is separate from the sound preference evidence; no absolute sound
quality scores or new model-quality claims are inferred.

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
Schema 3 adds an optional target-local `choice` with protocol/kind, presented,
auditioned and preferred IDs. Preserve it unchanged. Only a heard best choice
versus other heard, distinct audio yields strict training labels. None, ties
and skips remain useful evidence without invented scores or strict labels.

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
