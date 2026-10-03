# Multi-synth reproduction v4 implementation plan

> Execute with superpowers:subagent-driven-development. User explicitly requests autonomous retraining, research and a large meaningful listening run; no design approval pause. Work only in this isolated research worktree.

**Goal:** Train on all retained likeness judgments and generate new multi-synth reproductions across 36 tagged categories, with strong historical baselines and clear rating questions.

**Architecture:** A small regularized pairwise distance combines original auditory and gestural differences with coarse timing-tolerant comparisons. Load both feedback schemas, exclude usefulness labels from likeness learning, and group validation by exact reference PCM across sessions. Search original synths and a larger frozen Soundboard catalogue together; refine continuous parameters within each candidate's recipe and preserve incumbents. Export schema-2 listening feedback with honest overlap/provenance.

**Tech stack:** Existing NumPy/Torch descriptors, deterministic Node DSP workers, Python search, standalone HTML/JS, immutable JSON/FLAC feedback archives.

## Tasks
- [x] Research primary sources on perceptual audio similarity/inverse synthesis; inspect current preset branch and identify practical changes without assuming semantic embeddings match short SFX.
- [x] Add `multisynth/preference.py` and tests: schema-1/schema-2 likeness-only observations, checksum validation, cross-session PCM grouping, same-session strict pairs, pairwise monotone learned weights, regularization, frozen-baseline comparison, grouped cross-validation and full-data checkpoint with complete training provenance. API `PreferenceMetric.load(path)`, `.distances(target, descriptors)`, `.components(...)` compatible with existing search; CLI training all archives.
- [x] Expand frozen Soundboard library to 96 samples per 192 usable entries (18,432 examples), retaining exclusion of reference-fitted templates. Combine with 7,296 original-synth examples, preserving separate DSP identities.
- [x] Add `multisynth/big_run.py` and tests: deterministic per-target search over both backends; retain several starting recipes per engine, bounded continuous mutation including nested Soundboard sources, recipe/phrase structure preserved. Learned and original auditory ranking provide alternatives from a common generated pool. Incumbent preservation and replay checks required.
- [x] Run all 36 frozen tagged targets. Produce learned selection, expanded original-distance alternative where different, and strongest previously human-rated audio (or original matcher on newly reviewed targets). Keep human-selected seed refinement explicitly labelled; do not call it unseen generalization. No filtering references by result scores.
- [x] Generalize coverage gallery intro through optional metadata without changing old output identities; clear primary request to rate resemblance (gesture/feel), usefulness optional. Three candidates per reference; explicit disclosure when selectors agree. Preserve earlier galleries and ratings.
- [x] Independently review statistics, grouping and search; run focused regression tests and exact audio replay; verify browser feedback save/copy and playable assets. Save report/model/results and commit. Present a listening webpage, not a preset pack.

## Evaluation decisions

Use fixed regularization rather than tuning repeatedly on a six-reference batch. Compare full held-out predictions to auditory-v1 and fixed gesture on identical pairs, with grouped folds and per-reference weighting. Report selection bias and limited sample size; do not equate cross-validation with proven audible improvement. Known references are development; new references are disjoint by exact audio but may have related takes. If the learned distance does not beat the strongest fixed baseline, retain it as an experimental A/B candidate and say so. The user judges novel generated outputs.

Useful/fun labels stay archived and visible as a separate optional dimension; no preset curation diversion. The experiment ends with new audio for feedback, not just a plan or analysis.

The held-out result (learned 49/67 versus original 50/67) triggered the predeclared fallback: keep the learner experimental and compare it to the stronger fixed original distance on the enlarged common candidate pool. Both receive eight retrieval starts and 64 proposals/start.
