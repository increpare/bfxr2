# Temporal mixture inverse and short listening delivery

Architecture review update: follow the controlled experiment order in
`tools/multisynth/TRAINING_ARCHITECTURE.md`. The warm-up and four-mode head below
are separate ablations after the independent one-mode temporal baseline, not
mandatory simultaneous first-stage changes. The old encoder's onset resolution
and measured parameter sensitivity are explicit baselines to recover. Existing
coarse descriptors do not substitute for that resolution; version new inputs
separately if needed. Hardware placement is provisional pending equal-workload
comparison; no desktop training has been launched.

The user explicitly requests working until there is useful feedback to give.
Standing autonomy overrides design approval interruptions. Reuse the isolated
research checkout and preserve frozen galleries, feedback, DSP, features and
all previous checkpoints. The final deliverable is a new six-item quick
listening page, with exact previous winners and one-click choices. Do not stop
at another diagnostic failure: use diagnostics to revise and continue.

Alternatives considered: repair the forward surrogate before any new inverse
training (valuable but delays direct candidate improvement); pure retrieval and
search (baseline support, not the requested learned inverse); train temporal
per-engine multiple-solution inverse experts with actual-DSP selection (chosen).
This stage does not claim that the missing real-audio fine-tuning is solved.

Use all22 engines for cross-synth representation warm-up: a shared temporal
encoder learns masked descriptor completion plus known source-engine recognition.
Only audio descriptors and real source-engine IDs supervise this stage; no
foreign parameter labels.10epochs, same optimizer/batch/seed policy, mask25%
of whole relative/absolute frames, reconstruction on masked features with the
same nine equal groups (peak ignored), plus .1 source classification CE. Balance
aggregate engine contributions. Retain global train-only normalization and this
shared encoder's separate strict-load checkpoint/report. Then initialize each
independent inverse expert from that encoder; fine-tune numeric/categorical
controls on its own synth only. Off-diagonal native-source reconstructions from
all22 engines are evaluated through the actual target synth, not presumed correct.

Train Bfxr, Transfxr and Pluckr independently. Expand the immutable v2 dataset
using the existing structured generator with8192 new examples per trio engine,
seed20261008, retaining every native example and other engines unchanged.
Separate native versus structured supervision receives equal aggregate weight
so a larger tonal set does not eliminate native/mutated sound coverage. Preserve
complete splits; verify fresh benchmark full controls excluded from all rows.

A new standalone temporal module reads existing4083 descriptors as relative
51x48 and absolute51x32 sequences (48 spectrum + envelope/pitch/voicing), plus
duration and normalized RMS. Peak gain is omitted. Two strided temporal Conv1d
layers64/128 channels, kernel5, GELU; flattened relative and absolute embeddings
feed256 hidden features and four mixture candidates, each with numeric sigmoid
controls and categorical logits. Each engine has its own forked encoder, using the shared all-engine train-only
feature mean/std (.025 floor). No surrogate gradients or TEXT transcription.
Numeric/control likelihood energy preserves acoustic-v2 physical pitch mapping,
control priorities and inactive masks per example. There is no generator-ancestry
head or generator loss; random anchors stay fixed. Mixture loss is
-.1*logsumexp(logsoftmax(mode_logits)-energy/.1), with .01 batch aggregate route
KL to uniform. One-mode ablation uses identical encoder/data/recipe. Track mode
responsibilities/collapse.90epochs AdamW .001 cosine to.0001, batch128, seed20261009,
threads1; choose per-engine balanced validation loss. Every row processed.

Checkpoints bind recipe, complete dataset/files/splits/spec, DSP, feature/schema/
model/loss code, normalization and selected epoch/report hashes. Fresh outputs
only. Four ranked/deduplicated numeric+categorical predictions are decoded with
fixed declared random anchors and rendered by actual DSP. Existing loaders and
models are unaffected. APIs model/train/load/predict in new temporal.py.

Compare new mixture and one-mode ablation against v2 on the fixed20 actual
benchmark sources and retain source-engine raw versus unrestricted evidence.
Equal4 raw candidates and actual-render evaluation budgets; no inferred engine
or target tag supplied in end-use. Before further use require raw static pitch
at least7/9 within1semitone and reliable matching motion on at least6/8 moving
cases, and improvement on at least12/20 actual raw comparisons under the same
selection protocol. These are development diagnostics, not human likeness.
If a model misses those checks, adjust the architecture/data or use validated
acoustic initialization and repeat; user requires reaching another feedback set.

Actual-DSP selection/refinement is isolated from learning. Keep the older Bfxr
and previous all-engine candidates available. A new pitch/gesture-aware selector
uses actual rendered diagnostics; apply strong pitch constraints only when two
independent existing pitch measurements agree within3semitones and both have
high voicing. Never force a sole vaguely tonal candidate on noisy material.
Refinement accepts only actual-render score improvements with preserved already
matched pitch/direction. Record all proposals, controls, seeds, losses and WAV/
PCM hashes. No global edits to old selector defaults. Objective development is
reported honestly; model/distance scores do not establish audible quality.

Freeze6 tagged references before seeing new model scores: the five previous
quick items and a tagged item not included in those quick sets. Show new
approximation, exact previous winner, and original Bfxr if distinct; deduplicate
exact identical audio. Use existing cached WebAudio/autoplay/one-click/none/tie
UX, pause after5, no scalar rating burden. Hide algorithm identities until
choice when possible using existing neutral A/B/C. Validate all rendered/audio
boundaries and browser behavior on a separate origin without changing user
localStorage. Preserve results/parameters and serve localhost and LAN. Ask user
for six best/none judgments and exported JSON only when page is ready.
