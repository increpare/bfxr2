# Immediate likeness implementation plan

Use executing-plans inline under user authorization; no additional approval gate.

- [x] Add failing validation/roundtrip tests for v2 adequacy, pending choices,
      exact candidate scope, no invented scalar labels, and legacy v1 acceptance.
- [x] Extend Python and JS choice validators; expose a needsAdequacy helper and
      preserve pending v2 choices through export/storage while keeping them pending.
- [x] Add the immediate question, same-reference replay, keys 1/2/3/S, change
      choice, reload/resume and undo handling before automatic advancement.
- [x] Verify tests and exercise an isolated fixture in the browser, including
      saved JSON, reload and old-choice compatibility. Do not create user ratings.
- [x] Document and commit. Already submitted sessions require no extra answers.

Verification: 26 feedback JavaScript tests and 61 Python quick/coverage
feedback tests pass. Isolated browser fixture verified same-reference question,
pending reload, answer/advance, undo back to pending, and exact-ID JSON export.
Review caught and verified fixes for undo after reload and failed-audio recovery.
Browser test choices use internal synthetic fixtures, not human evidence.
