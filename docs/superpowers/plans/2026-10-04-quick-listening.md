# Quick listening implementation plan

> Use superpowers:subagent-driven-development for the independent feedback
> implementation and subsequent spec/correctness reviews. Existing autonomous
> authorization covers routine design and implementation choices.

**Goal:** One click per reference with cached, restartable playback and reusable
ordinal feedback, preserving existing ratings and experiment identities.

**Architecture:** Pure quick-choice helpers, a cached Web Audio player, a small
single-reference controller, and a schema-3 feedback archive/learner boundary.
**Tech stack:** Standalone JavaScript, Web Audio, Python/soundfile, Node tests.

- [x] Add failing JS tests for primary audio deduplication, deterministic order,
  schema-3 export without fake ratings, restart/cancellation and listened evidence.
  Files: `tests/multisynth-quick-listening.test.js`,
  `tools/multisynth/{quick_choice,quick_audio,quick_listening}.js`.
  Run `node --test tests/multisynth-quick-listening.test.js` before implementation.
  Player contract: `preload(url)`, `play(url)`, `stop()`, `onEnded`;
  a replay always calls `source.start(0,0)` and invalidates prior request tokens.
- [x] Implement choice helpers and schema-2-compatible feedback controller updates
  in `coverage_feedback.js`. A state with choices must export schema 3 and keep
  scalar fields null unless explicitly rated; no choices keeps schema 2.
- [x] Delegate schema-3 validation, archival and strict preference training to one
  implementer. Files: `quick_feedback.py`, archival portion of
  `coverage_feedback.py`, `listening.py`, `preference.py`, `big_run.py`, tests.
  Invalid choice IDs/kinds must fail before creating an archive directory.
  One heard winner versus two heard alternatives must yield two sign labels,
  while none/tie/skip and unheard alternatives yield no strict labels.
- [x] Add quick-view markup/CSS through `export_coverage`, embed the scripts, and
  connect the controller. Defaults: reference/A/B/C sequence, 350 ms gap,
  autoplay enabled after Start, pause every five new judgments. Keys: R reference,
  A/B/C replay, 1/2/3 choose, 0 none, T tie, S skip, space sequence/stop, left previous.
- [x] Review schema implementation against the spec, then review correctness.
  Run `node --test tests/multisynth-coverage-feedback.test.js tests/multisynth-quick-listening.test.js`
  and focused Python archive/preference/listening tests in the existing tools venv.
- [x] Regenerate the current `neural-v1-listening/index.html` from unchanged
  `results.json` and prove experiment ID, JSON/WAV hashes and storage key unchanged.
  Test browser interactions on a separate-origin smoke clone; inspect current
  page with existing state untouched. Check localhost/LAN accessibility.
- [x] Save verification/docs and commit the reviewed change in this worktree.

Verification: 17 focused JavaScript tests and 60 focused Python tests passed.
Spec and code-quality reviews completed; cancellation, stale error handling,
manual ended status, save warnings and missing-audio Skip have regression tests.
Separate-origin browser checks passed; the user gallery was reloaded with its
state preserved. Eight localhost/LAN HTML/audio checks passed. Frozen experiment
and all 74 WAV/JSON files remain unchanged. Keeping the existing Codex branch
and worktree for continued model work under the user’s autonomous instruction.
