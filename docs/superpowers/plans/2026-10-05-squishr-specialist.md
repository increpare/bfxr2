# Squishr inverse specialist

**Goal:** Test whether a broader dedicated inverse expert predicts useful Squishr
controls, following one explicit very-close real-footstep search result.
**Architecture:** Reuse the existing independent acoustic-head training recipe
with8192 freshly rendered native/sparse/broad Squishr draws, hidden256,60epochs,
batch128,AdamW .001,CPU1thread. This changes data/capacity, not an architecture
ablation. Keep the shared22 model and successful search controls available.
No human reference or judged winner is a training example. No new loss invariance
is inferred from the controlled edits.

Reserve32 seeded distinct native control groups from validation into a test view
before fitting; all exact encoded controls ignore random seeds for split audit.
Checkpoint selection uses validation control loss only. Evaluate actual renders
on all32, old shared Squishr vs new specialist, four categorical proposals each.
Use the opt-in smooth objective for both at inference, also report legacy scores.
Raw proposals and equal128-mutation refinement are separate. Native test preset
families still overlap training; do not call this family generalization.

Freeze five tagged references before model output inspection: the approved wooden
footstep anchor and four unjudged tagged footstep/hit/step/clothes sources by
stable path ordering and exact PCM exclusion. These are transfer tests for the
new synthetic-only expert, not untouched tests for every older baseline/model.
The slime tag has only one already-judged file, so step replaces the initially
proposed squish stratum before any model output inspection.
Original Bfxr/prior multi-synth winners stay available where already archived;
newly chosen sources compare old/new Squishr to identify the expert's contribution.

- Generate8192 native training candidates with existing audited sampler.
- Freeze native and tagged evaluation manifests before fitting.
- Train isolated expert; bind full dataset/code/checkpoint hashes.
- Evaluate/replay raw and equal-budget refined controls on fixed sources.
- Produce up to10 useful listening trials: five fixed tagged plus five seeded
  native tests selected before scores. Include agreement cases; no quality claim
  from distances. Each choice retains immediate candidate-scoped adequacy.
- Archive latest human evidence including incomplete audition telemetry, preserve
  all earlier judgments and reject global scorer promotion from one positive.
