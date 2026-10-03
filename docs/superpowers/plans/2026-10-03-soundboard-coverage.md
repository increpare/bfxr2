# Soundboard candidate coverage implementation plan

> Use superpowers:subagent-driven-development for isolated implementation and review. The user authorizes autonomous iteration and reading claude/determined-sagan-khz12h; never mutate that checkout.

**Goal:** Test whether the human-refined Soundboard catalogue and compositions contain better recreations, and deliver a small diagnostic rating batch.

**Architecture:** Freeze commit db9f5f8a8bf50b951b44a163dd6685222bfae859 in an ignored local snapshot. A separate seeded bridge renders its real Soundboard engine. Build balanced examples across all catalogue entries (exclude target-fitted reference templates), encode auditory-v1, search globally, and compare against tag-assisted retrieval and the best previously rated candidate on six already-reviewed references. Keep likeness and standalone usefulness separate. This is development/candidate coverage, not an unseen benchmark.

**Technology:** Existing Node VM DSP contexts, Python/Numpy/Torch descriptors, self-contained HTML/JS ratings.

## Tasks
- [x] Snapshot and audit branch changes/provenance. Identify whether numeric raw ratings are actually available; do not invent them from weighted catalogue entries.
- [x] Add seeded Soundboard renderer supporting catalogue inventory, forced entry sampling and exact snapshot replay. Test composite and single-source replay and source identity. Use pinned code exclusively.
- [x] Build a source-fingerprinted candidate library with balanced catalogue entries and exclude reference-fitted templates. Rank across every verb using the original metric; tags never enter automatic selection.
- [x] Prepare six development references (coin, punch, jump, step, door, magic). Include automatic global winner, tag-assisted alternative, best previous rated audio, and one structurally diverse alternative where useful. No new target-fidelity claims from Soundboard quality ratings.
- [x] Provide arbitrary-role diagnostic cards with separate likeness/usefulness ratings and copyable persistent JSON. Preserve old schemas, galleries and listening archives unchanged. Add importer support for durable schema-2 feedback with audio/parameter/provenance verification.
- [x] Validate renderer/feedback/library invariants and actual browser saving/export; verify all gallery WAVs and sampled exact replays. Save results, checkpoints and source-branch findings; commit and present new listening page.

## Research decision

Do not fit another compressed gesture metric after v2's failed human test. Keep old metric as the automatic ranking baseline. Tag-assisted choices are explicitly assisted probes, not evidence that an automatic selector learned categories. Candidate usefulness can improve without target likeness; collect separate labels to distinguish these outcomes. Numeric ratings on the other branch are unavailable until located; applied commit notes and recipe weights only provide indirect curation evidence.
