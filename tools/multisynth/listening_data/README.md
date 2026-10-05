# Persistent listening evidence

## Collection policy

Collect absolute likeness while the reference and the listener's A/B/C choice
are still visible. Do not ask the listener to reconstruct anonymous comparisons
after submitting or refer to hidden synth/model labels as if they were visible.
The user explicitly objected to that follow-up burden on 2026-10-05. Missing
adequacy in prior submissions remains unknown; no request to repeat those trials.

New galleries use `feel-choice-v2` within schema 3. After best/tie, retain the
relative choice and ask very close / roughly similar / least-bad / not sure
before advancing. `adequacy` binds a `level` to exact `candidateIds`: the winner
for best, all presented tied candidates for tie. Null means unanswered; not-sure
is explicit uncertainty. None/skip need no second answer. These are separate
qualitative labels, not inferred numeric scores. A pending answer survives
reload; completed v1 choices remain completed. Published galleries are frozen;
future exports use the updated questionnaire.

The user confirmed on 2026-10-05 that the current buffered HTML interface is
enjoyable and authorized up to **20 useful comparisons** per batch, including
additional questions when helpful. Keep breaks optional and collect each extra
judgment while its sound is still in view; do not pad batches or ask retrospective
questions about hidden synth labels.

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
| `2026-10-05-coverage-selection-quick-01/` | 3 | 6 |
| `2026-10-05-transfxr-transfer-quick-01/` | 6 | 12 |
| `2026-10-05-native-mixture-quick-01/` | 5 | 10 |
| `2026-10-05-specialists-quick-01/` | 5 | 11 |
| `2026-10-05-specialists-tagged-quick-01/` | 5 | 15 |
| `2026-10-05-tagged-coverage-quick-01/` | 5 | 15 |
| `2026-10-05-cue-calibration-quick-01/` | 5 | 10 |
| `2026-10-05-soft-periodicity-quick-01/` | 5 | 15 |
| `2026-10-06-squishr-v1-quick-01/` | 5 | 11 |

The seventeenth archive is a **partial submission**: the first five tagged
references from the ten-trial Squishr specialist comparison. All eleven options
were auditioned. The repeated wooden footstep is a **very-close tie** across the
retained anchor, shared head and new specialist, each with its published search.
The fresh footstep rejects both options. Shared wins hit and clothes, specialist
wins Anubis step, but all three winners are **least-bad**. This does not establish
better tagged transfer or adequacy of either raw inverse prediction.

Three strict heard pairs and eight candidate-scoped labels are retained: three
very-close, two not-close and three least-bad. The soft scorer agrees on all
three strict pairs, preference-neural-v2 on two, legacy on one; ordering bad
options correctly is not evidence of good reproduction. Five reserved native
trials remain unsubmitted. Preserve this partial session when later feedback
arrives, and avoid double-counting unchanged choices from cumulative exports.
See the [Squishr human review](../evaluations/squishr-v1-quick-01-human-review.json).

The sixteenth archive retains five actual-synth comparisons. The new soft-search
Squishr wooden footstep wins and is **very close**. The chosen soft-search
Transfxr block-hit is **similar**, but its export records only that option as
auditioned, so it supplies no strict pairwise comparisons. Brick remains **none
close**. The earlier Transfxr cloth is **least-bad**, and the unchanged earlier
Bfxr laser is **similar**. Preserve both that laser judgment and its earlier
least-bad judgment; this is not a new synthesis improvement.

Six strict heard preference pairs and seven candidate-scoped adequacy labels
are retained: one very-close, two similar, one least-bad and three not-close.
No numeric scores or unheard comparisons are inferred. Frozen legacy and soft
scores each agree on 2/6 pairs; preference-neural-v2 agrees on 4/6. The successful
footstep is useful reachable-synth evidence, **not a global scorer endorsement**.
See the [soft-search human review](../evaluations/soft-periodicity-quick-01-human-review.json).

The fifteenth archive retains five controlled-edit comparisons. All ten options
were auditioned; all five preferred edits are explicitly **very close**. Winners:
footstep lowpass, 125%-duration brick, charm shifted +2 semitones, 125%-duration
cloth, and attenuated laser tail. These are edited originals, **not synth model
successes**. Five strict pairs and five candidate-scoped adequacy labels are
retained; the unchosen options have no inferred adequacy.

Frozen matching agrees on 2/5; preference-neural-v2 and both CLAP representations
each agree on 4/5. Pitch/duration tolerance is local evidence, not a universal
invariance: edit strengths and artifacts differ. The near-identity footstep
confirms a concrete hard-pitch scoring failure. See the
[cue human review](../evaluations/cue-calibration-quick-01-human-review.json).

The fourteenth archive retains the five candidate-coverage comparisons and all
fifteen auditioned options. The new Squishr footstep wins and is **similar**;
the new Transfxr cloth wins but is **least-bad**. Original Bfxr retains block-hit
and laser, both **least-bad**. **None** of the three brick-break options is close.
There are zero very-close judgments, eight strict heard preference pairs, and
seven candidate-scoped qualitative labels. Matching distance agrees on 2/8
pairs; frozen preference-neural-v2 agrees on 6/8. No unchosen adequacy or numeric
rating is inferred except the explicitly rejected three brick options.

Broader retrieval did not find convincing displayed recreations. That is not
proof that the synths cannot produce them. Preserve these failures for ranking
research; do not use least-bad controls as successful inverse-training teachers.
This repeated batch is development evidence. See the
[coverage human review](../evaluations/tagged-coverage-quick-01-human-review.json).

The thirteenth archive retains all five tagged-transfer choices and all fifteen
auditioned options. Older Clonkr wins wooden footstep and is **roughly similar**.
New Footsteppr wins brick-break and cloth, but both are **least-bad**. Original
Bfxr wins block-hit and laser, also **least-bad**. Thus this batch contains zero
very-close winners, one similar winner and four least-bad winners. No adequacy
is assigned to the unchosen options, and no numerical likeness ratings are
invented. Ten heard preference pairs remain useful independently of adequacy.

Matching distance agrees with 6/10 pairs; frozen preference-neural-v2 with 8/10.
The specialist relative wins do not demonstrate successful real-recording
transfer. Merely choosing better among these displayed options cannot solve the
four least-bad cases; diagnose candidate coverage before training on their
pseudo-labels. Exact audio and provenance are retained in the
[tagged human review](../evaluations/specialists-tagged-quick-01-human-review.json).
The five references were preselected and excluded prior exact judged files/PCM;
they were not checked for membership in original Bfxr's real training corpus
and do not constitute family-disjoint or population validation.

The twelfth archive retains five of six specialist comparisons and all eleven
auditioned candidates. New Footsteppr wins the familiar footstep and the Whooshr
wingbeat, both **very close**; new Boomr wins rocket burst, also **very close**.
The older shared Boomr wins the fresh native short burst and is **very close**.
The fresh native footstep is a tie, both **roughly similar**. These produce five
strict heard pairs and six candidate-scoped qualitative labels: four very-close
and two similar. No scalar ratings are inferred. Book-close is unsubmitted and
unknown; no retrospective clarification is requested.

MatchObjective agrees with 3/5 strict pairs and the frozen preference-neural-v2
scorer with 4/5. Lower matching distance wrongly rejects the new footstep winner
and favors the losing new short burst. The new experts have audible strengths,
including a Whooshr-to-Footsteppr transfer, but are not universal replacements.
This deliberately selected synthetic batch establishes no tagged-recording
success or population win rate. See the
[specialist human review](../evaluations/specialists-quick-01-human-review.json).
The questionnaire offers a break after five trials, so future short batches
contain five trials instead of putting the sole tagged reference after a break.

The eleventh archive is a partial submission of five of six native-mixture
comparisons. All ten options are recorded as auditioned. The new mixture wins
Gentle rise, Wide rising sweep and Low-pass filtered bouncing rise, with an
immediate **very-close** label for each winning candidate. Both Footsteppr
recreations are rejected as not close. The older Boomr recreation wins and is
immediately rated **roughly similar**. These yield four strict heard preference
pairs, three positive adequacy labels, one similar label, and two explicit
not-close labels; no scalar ratings are inferred. Warbling sweep was not
submitted and remains unknown. No request to complete or recall that trial.

Both frozen matching scorers favor the new option on all five references:
they agree with 3/4 strict preferences but favor the rejected new Boomr option,
and the large Footsteppr score improvement still fails the absolute listening
test. Native self-inversion progress does not establish other-synth or tagged
real-recording success. See the
[exact-audio human review](../evaluations/native-mixture-quick-01-human-review.json).
Its pitch-guard probe uses the displayed previous option as a hypothetical
baseline, not necessarily the original old-four baseline of the deployed policy.
The gentle and wide rises would be rejected by those strict guards despite
their explicit very-close judgments. The separate
[export-stability audit](../evaluations/native-mixture-export-stability.json)
isolates trimming sensitivity behind the wide sweep's changed direction
diagnostic. The listening audio itself is correct.

The tenth archive retains all six robustness/transfer judgments, all 12 options
recorded as auditioned, and 17 unique lossless reference/candidate PCM files.
The compressed warble is a tie; the transposed warble favors the prediction from
the altered input; the filtered texture favors the frozen clean-input prediction.
Combined Transfxr models win the Bfxr and Boomr source comparisons. Both Pluckr
recreations are rejected as not close. Four best choices yield four strict
heard-only pairs; the tie and rejection remain separate evidence. No scalar
scores or absolute likeness judgments for the winners were supplied.
Do not request retrospective clarification for these winners: the questionnaire
failed to collect it when the sounds were being judged.

On the exact audition PCM, MatchObjective and the frozen preference-neural-v2
scorer each agree with 2/4 preferences, on different pairs. MatchObjective favors
the wrong transposition option and the old Boomr-source recreation. The MP3
numerical regression is not an audible preference loss in this listening test.
Perceptual-v5 is unavailable because its compatibility check fails; do not bypass
that check. See [the transfer human review](../evaluations/transfxr-transfer-quick-01-human-review.json).
For any future preference validation, keep transformed warble references with
their clean warble source family, and filtered texture with its clean source
family. Distinct reference PCM hashes do not make these independent holdouts.

The ninth archive retains three held-out Transfxr self-inversion comparisons.
The expanded expert wins Warbling sweep and Bouncing rise; Short texture is a
tie. All nine reference/candidate audios are retained losslessly. No scalar
ratings were supplied. The subsequent
[qualitative follow-up](2026-10-05-coverage-selection-quick-01/qualitative-feedback.json)
says both Warbling sweep reproductions are **very close**, Short texture is
**less close but similar**, and Bouncing rise reproductions are **all very close**.
This applies to both alternatives, not only the expanded expert's relative wins.
The previous batch's zero-convincing verdict does not apply to these comparisons.
Warbling sweep has an explicit preference but empty playback telemetry: retain
that choice as evidence, without claiming the listener did not hear it. The
existing strict heard-only training policy yields one pair, from Bouncing rise;
the tie remains non-directional evidence. These deliberately selected synthetic
diagnostics do not establish a population win rate or real-recording transfer.
See [the coverage-selection human review](../evaluations/coverage-selection-quick-01-human-review.json).
That original review predates the follow-up; its null adequacy fields describe
what was available then. Preserve it and consult the linked supplementary
evidence for the later absolute likeness assessment. Do not invent 1–5 labels.

The eighth archive retains all five pitch-calibration comparisons, with all 12
options auditioned and seven strict heard-only preferences. Both changed
calibration selections lose: the uncalibrated Bfxr beep wins, and original Bfxr
wins the bell. Original Bfxr also wins battleStart. The earlier Transfxr charm
wins its first direct heard comparison against the later Bfxr partial success.
The Transfxr whistle wins against original Bfxr, but is the unchanged baseline,
so this is not evidence for calibration. No numerical likeness or usefulness
ratings were supplied. In a subsequent direct reply, the user confirmed that
there were **no convincing recreations: zero of five references**. The separate
[qualitative follow-up](2026-10-05-pitch-calibration-quick-01/qualitative-feedback.json)
retains the exact words and winner identities. Relative preferences remain valid;
none of these winners is an established successful recreation. The exact-audio matching objective agrees with 2/7 pairs;
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
