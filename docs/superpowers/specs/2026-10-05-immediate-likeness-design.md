# Collect likeness while the comparison is still visible

The user should not have to recall anonymous comparisons after submitting. After
choosing A/B/C, keep the same reference and playback buttons visible and ask how
close that selected option is: very close, roughly similar, only least-bad, or
not sure. For a tie, ask about all displayed tied options. None and Skip advance
without an extra question. No request to rerate earlier submissions.

Use feel-choice-v2 within schema 3, with an explicit adequacy object containing
level and assessed candidate IDs. Null means the immediate question is pending;
not-sure is an explicit non-assessment that allows advancing. Save relative
choice before asking, so closing/reloading preserves it and resumes its question.
Old v1 choices remain completed and valid. Preserve all published experiments,
archived JSON, exact audio and stored ratings. New exports use the new flow.

Alternative one-click quality buttons on each option would multiply controls and
clutter playback. A brief second step has one clear question and keeps labels
A/B/C and the reference name in view. Bind adequacy to exact IDs, not hidden synth
labels. Undo/edit and keyboard support must work across this step; prevent an
accidental held number key from answering it. No scalar score inferred.
