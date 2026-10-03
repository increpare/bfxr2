# Gesture matching iteration implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for isolated implementation and review. User has authorized autonomous design and execution.

**Goal:** Deliver an improved candidate model and a fresh tagged rating gallery with honest evidence about training and comparison limits.

**Architecture:** Keep auditory-v1 reproducible. Derive compact multi-scale gesture descriptors from its cached frame features, fit nonnegative regularized distance weights using archived ordinal ratings, and evaluate by reference-grouped cross-validation. Use an injected scoring interface for library retrieval and search. Produce tagged recreations, with old-model and Bfxr comparisons and persistent exportable ratings.

**Tech stack:** Existing Python/NumPy/Torch sound tooling, Node DSP bridge, standalone HTML/JS feedback.

## 1. Gesture model and learning
- [x] Add tests for gain invariance, rising/falling motion, impact/swell and repeated/sustained events; controlled detuning/stretching should not erase event identity.
- [x] Implement `gesture.py`: compressed envelope shape at several scales, onset/pulse structure, centered spectral/pitch movement, coarse timbre and texture, weak duration. Keep exact descriptor/weight versioning.
- [x] Implement `train_gesture.py`: read immutable archive audio and labels, fit regularized nonnegative weights to strict within-reference preferences. Retain absolute grades and ties as evidence; rating gaps are heuristic confidence weights, not calibrated perceptual distances. Report reference-grouped CV against fixed prior and auditory-v1; never describe resubstitution as validation. Save fitted weights plus training provenance and per-pair predictions.

## 2. Search integration
- [x] Add optional scorer injection to library retrieval and search; default remains auditory-v1. Verify old tests unchanged and new scoring replay/incumbent preservation.
- [x] Use the same saved library initially to isolate scoring changes; broaden candidate coverage across synths before expensive optimization. Record compute budgets and initial/final scores.

## 3. Listening comparison and feedback
- [x] Extend gallery/export/import to support optional previous-model candidate, preserving all existing experiment IDs and shared-candidate behavior for v1.
- [x] Add tests for independent previous-model ratings and archive retention. New gallery compares reference, new model, previous model, and Bfxr; hide incomparable metric numbers from the main listening cards.

## 4. Generate and verify deliverable
- [x] Freeze a manageable tagged subset from the existing 36-tag manifest; include varied gestures. Record overlap with training references rather than claim unseen generalization.
- [x] Run old and new matching, preserve seed/budget/provenance, export all candidate parameters and editable presets. Keep original real-v1 gallery untouched.
- [x] Run Python/Node focused tests; inspect actual gallery and audio paths, feedback persistence/export, and independent review. Save result notes, model checkpoint and compact reproducible selection/provenance in git, with large scratch renders in runs/.
- [x] Commit verified changes and provide the new listening URL. Describe measured evidence and remaining uncertainty without promising audible improvement before ratings.
