# Quick listening judgments

The user is exhausted by repeated playback controls and eight scalar ratings
per reference. Proceed under their existing autonomous authorization. The design
prioritizes one explicit judgment, short sessions and predictable playback.

## Chosen approach

Present one reference at a time with at most three distinct primary clips:
automatic expert choice, original Bfxr and previous best. Raw neural predictions
remain in an optional detailed view. Deduplicate exact audio, shuffle A/B/C
deterministically within each reference, and hide method names in quick mode.

Pairwise tournaments require repeated judgments; four-way scalar ratings require
both repeated judgments and calibration. A three-way best-of-set question captures
up to two ordinal preferences with one decision without asking for numeric scores.
The question is “Which captures the reference's feel best?” A/B/C choices,
“None are close”, “About equal” and “Skip” each save and advance once. No quality
or usefulness scores are fabricated. Five decisions pause for a break.

After a single Start gesture, play the full reference and options sequentially,
with short gaps. Never advance merely because playback finished. Voting advances
to the next reference and starts its sequence when autoplay is enabled. Stop,
replay, reference/option buttons, previous/undo and keyboard shortcuts remain
available. Progress resumes at the first unjudged reference; existing scalar
ratings survive and fully rated primary sets count as already judged.

## Playback

Fetch and decode the current and next reference/options ahead of time. Use one
AudioContext with cached AudioBuffers and a new BufferSource for every replay.
Every play starts at offset zero. Stop cancels pending sequence timers and old
asynchronous playback requests; only one source sounds at once. Explicit loading,
playing and unavailable states replace native audio controls in quick mode.
Keep the original players in optional details, and stop both systems on view
changes. Handle autoplay rejection, unavailable Web Audio and decode failures
without silently recording a judgment. Use the same gain for all clips.

## Feedback and compatibility

Keep experiment/candidate identities, old storage keys, ratings and audio unchanged.
Store choices alongside ratings. Ratings-only export remains schema 2; exports
containing choices use schema 3. Each target's optional `choice` contains:

```json
{"protocol":"feel-choice-v1","kind":"best","presentedCandidateIds":["a","b","c"],"auditionedCandidateIds":["a","b","c"],"preferredCandidateIds":["b"]}
```

Kinds are `best`, `tie`, `none`, `skip`; only best has one preferred ID.
IDs must belong to the immutable target. Auditioned IDs are a subset of the
presented IDs and require an ended clip or a substantial listened fraction.
Retain all choice fields and exact audio in immutable archives. Strict preference
training uses best against other auditioned options only when the winner was
also auditioned. Ties/rejections/skips remain distinct, with no invented ratings.
Explicit heard choice pairs supersede conflicting scalar-derived pairs in that
session. Older schema-1/2 archives continue working.

## Verification

Test restart-at-zero and stale-request cancellation with a controlled AudioContext,
choice deduplication/order, feedback compatibility and schema-3 archival/training.
Browser-check start, sequence, replay, one-click advance, undo, break/resume,
keyboard actions and JSON. Regenerate only the current gallery HTML from frozen
results without changing experiment identity, metadata, WAVs or prior feedback.
Use a separate-origin smoke page so no test decision touches the user's state.
