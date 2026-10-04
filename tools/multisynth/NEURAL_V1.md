# Learned multisynth inversion, first run

This iteration trains actual audio-to-control predictors for all 22 active
individual numeric engines. Earlier multisynth iterations retrieved presets and
refitted similarity weights; they did not expand the original Bfxr inverse
network. The original real-finetuned Bfxr checkpoint and StagedOptimizer now
participate as a separate expert and remain visible in the listening comparison.

## Model and data

The shared encoder consumes whole-sound log-frequency spectra, amplitude,
fundamental-pitch and voicing contours on relative and absolute timelines, plus
duration. It has 4,083 input features and separate generator-conditioned control
heads: global-range numeric predictions and classification for discrete choices,
including transition curves. There are 2,024,702 learned parameters. Generator
anchors supply only TEXT and randomness; every learned control is overwritten.

Each engine contributes 2,048 independent rendered examples: 50% native
generator draws, 30% sparse mutations and 20% broader mutations. Canonical DSP
controls provide the labels. Exact saved-control groups cannot cross training
and validation: 1,741 training and 307 validation rows per engine. These are
parameter holdouts inside known generator families, not held-out families.
All 45,056 labels were checked against their codecs and 66 sampled examples
replayed exactly in raw audio and descriptors. Persisted shard bytes, feature
code and DSP sources are bound by hashes before training.

Training used MPS, AdamW and 50 epochs. The best validation checkpoint was epoch
12 (combined loss 0.785808); later training overfit. This first loss is supervised
numeric MSE plus generator and categorical cross entropy. Unlike the old Bfxr
pipeline, the new experts do not yet have differentiable forward-renderer audio
loss or adaptation on real recordings. Gain is excluded from normalized neural
inputs so audition normalization does not create a gain-domain mismatch.

## Selection and comparisons

Every trained engine supplies up to two generator-conditioned predictions. The
actual DSP renders all proposals; the existing absolute-pitch MatchObjective
scores them. Four distinct engines receive 128 global-control refinement steps
each, and automatic selection compares those with the restored Bfxr expert.
The old expert's nominal budget is 2,000, with its original additional arpeggio
stage sometimes taking the actual count higher. Reports retain actual counts;
this is not an equal-compute comparison.

The tagged listening page compares raw neural prediction, automatic expert
choice, original Bfxr and exact previously preferred audio on 12 fixed tagged
development references. It separates likeness from useful/fun ratings and keeps
the existing JSON export and archival protocol. Targets and previous ratings are
not synthetic parameter labels. Previous best uses historical ratings only to
choose its comparison card; inference receives neither the filename nor tag.

Independent synthetic reconstruction uses two fresh generator draws per engine,
excluding every training/validation numeric and categorical control combination
(and phrase). Eight separately calibrated stationary tones test absolute pitch.
These diagnostics are distinct from human likeness and gesture judgments.

On the 12 tagged references, the selector chose refined neural experts ten
times and the original Bfxr expert twice. Mean MatchObjective scores were 4.911
for raw neural predictions, 2.575 for the automatic choice and 3.328 for original
Bfxr. The wider selection pool makes score improvement possible by construction;
these numbers are not listening wins. Two highly voiced references,
`attack/spinout.wav` and `laser/laserRetro_000.ogg`, received unvoiced automatic
winners. This exposes a selector failure even while stationary-tone pitch checks
improve. Their cards remain in the page; they were not filtered out.

The 44 fresh synthetic cases completed without candidate render failures. The
best raw expert recovered the source engine in 28/44 cases; another engine can
still be a valid recreation. Mean scores were 3.595 for the raw source-engine
head, 2.767 for the best raw expert, 1.477 after neural refinement, 1.469 for
automatic selection and 3.073 for original Bfxr. Automatic selection used a
refined learned expert 41 times and original Bfxr three times. All methods
produced results on all 44 cases. This small known-family holdout checks the
pipeline; it is not broad generalization or perceptual validation.

The completed stationary-tone check covers Bfxr and Transfxr at 220, 440 and
880 Hz, plus Pluckr at 220 and 440 Hz. All reference pitches calibrate within
0.1 semitones of their nominal frequency. Missing/unreliable pitch estimates
count as failures, rather than disappearing from the denominator.

| Method | Within one semitone | Median absolute error | Unreliable estimates |
|---|---:|---:|---:|
| Raw head for the source synth | 2/8 | 3.42 semitones | 0 |
| Best raw neural expert | 5/8 | 0.74 semitones | 0 |
| Refined neural / automatic choice | 8/8 | 0.08 semitones | 0 |
| Original Bfxr expert | 4/8 | 0.59 semitones | 1 |

The maximum selected pitch error is 0.32 semitones. The original Bfxr result's
median covers seven reliable estimates, while the success count includes all
eight cases. This small stationary diagnostic supports pitch recovery after
search; it neither establishes raw inverse accuracy nor covers moving pitches,
rhythms, multi-source sounds or human likeness. The first report exporter hit a
NumPy-count serialization error after rendering all probes; the repaired run
uses isolated processes and retains every probe report. Its pitch errors match
the first run's logged values.

## Reproduce

Run from the repository root with the existing tools Python environment and
`PYTHONPATH=tools`, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`.

```sh
python -m neural_invert.data --output tools/multisynth/runs/neural-v1/data --per-synth 2048 --jobs 4
python -m neural_invert.train --data tools/multisynth/runs/neural-v1/data --output tools/multisynth/runs/neural-v1/model --epochs 50 --device mps --threads 4
python -m neural_invert.experiment synthetic --model tools/multisynth/runs/neural-v1/model/best.pt --data tools/multisynth/runs/neural-v1/data --bfxr-checkpoint /Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt --output tools/multisynth/runs/NEW-SYNTHETIC --per-synth 2 --jobs 4 --starts 4 --budget 128 --bfxr-budget 2000
python -m neural_invert.tonal --model tools/multisynth/runs/neural-v1/model/best.pt --bfxr-checkpoint /Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt --output tools/multisynth/runs/NEW-TONAL --budget 128 --bfxr-budget 2000 --jobs 4
python -m neural_invert.experiment tagged --model tools/multisynth/runs/neural-v1/model/best.pt --bfxr-checkpoint /Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt --output tools/multisynth/runs/NEW-LISTENING --targets tools/multisynth/evaluations/neural-v1-targets.json --archives tools/multisynth/listening_data/2026-10-03-real-v1 tools/multisynth/listening_data/2026-10-03-tagged-v2 tools/multisynth/listening_data/2026-10-03-coverage-v3 tools/multisynth/listening_data/2026-10-04-big-v4 --jobs 4 --starts 4 --budget 128 --bfxr-budget 2000
pytest tools/tests/test_neural_invert.py tools/tests/test_neural_evaluation.py
```

Use fresh evaluation directories; listening identities are immutable after
publication. Model/data/audio artifacts stay under ignored `runs/`; verified
reports and retained human feedback are versioned. The original checkpoint is
preserved at the absolute path above, rather than replaced or retrained.

## Scope and next decision

The 22 heads are Bfxr, Footsteppr, Transfxr, Birdr, Boomr, Bouncr, Breathr,
Choirr, Clonkr, Crittr, Fractr, Glitchr, Jinglr, Machinr, Pluckr, Riftr, Rustlr,
Signlr, Squishr, Swarmr, Whooshr and Zappr. Jinglr predicts numeric/discrete
controls but keeps a generated TEXT phrase; it does not transcribe target notes.
Retired engines, Chattr text and Mixr/Stackr compositions are outside this model.

Mixr combines two source synths and their controls. Individual inverse experts
are its first-stage proposals; arbitrary mixtures additionally require source
separation and a labelled two-source training set. A Mixr wrapper alone would
not solve those problems.

The new raw predictors can still average ambiguous parameter solutions and miss
pitch. The controlled Bfxr 220 Hz probe's raw Bfxr head missed by 9.25 semitones,
while another neural head plus refinement reached 0.20 semitones. This is evidence
to improve the learned objective and training coverage, not evidence that the
individual inverse problem is solved. Increasing epochs alone is unsupported by
the validation curve. Human gesture, likeness and fun remain the acceptance
criteria; a lower matching score does not establish a listening win.

## Verification and local listening

The first quick-listening feedback batch is now retained in
`listening_data/2026-10-04-neural-v1-quick-01`: five of twelve references, four
best choices and one rejection, yielding seven heard-only strict comparisons.
The neural-selected finalist won once, original Bfxr once and previous audio
twice. These are preferences among familiar development finalists, with no
absolute likeness scores. The user's positive feedback on the new listening
interface is separate from this mixed sound verdict. See
[the partial review](evaluations/neural-v1-quick-01-human-review.json).

The 26 neural implementation/evaluation tests pass. Original Bfxr native/browser
parity checks pass all 19 cases. Spec and code reviews approved the implementation
and the tonal-report repair. Replay verification checks all 372 audition files:
296 candidate renders, 52 synthetic/tonal references and 24 exact historical
PCM copies. Saved controls and seeds reproduce the exported PCM exactly; all
recomputed candidate scores agree with their reports with zero difference.
Independent browser ratings, clearing test ratings, feedback archive creation
and idempotent re-import were exercised. All 122 page/audio HEAD requests return
200 across the existing localhost and LAN servers.

The listening page is
`http://127.0.0.1:8765/tools/multisynth/runs/neural-v1-listening/index.html`;
the existing LAN server also serves it at `192.168.178.131:8765` with the same
path. It has 48 candidate cards (46 unique identities), including 22 new neural
candidates. Exact aliases share ratings. No automated test rating remains on
the page or in the versioned human feedback archives.

Reports under `evaluations/neural-v1-*` retain training history, synthetic and
tonal reconstructions, tagged diagnostics, pitch diagnosis, data integrity and
audition replay checks. To repeat the audio/score verification from the repo root:

```sh
PYTHONPATH=tools python tools/multisynth/evaluations/neural-v1-replay-audit.py
```

[The pitch diagnosis](evaluations/neural-v1-pitch-diagnosis.json) verifies that
the descriptor sees the 220 Hz tone at 220.5 Hz, but the Bfxr data has zero
stationary sine examples under the report's saved-control criterion. Waveform
classification dominates this head's loss and generator ancestry conditioning
strongly changes its pitch prediction. The next learned experiment should add
structured static/rising/falling/jumping coverage across acoustic categories,
retain the general generator/mutation data, mask inaudible controls and weight
pitch through its acoustic sensitivity. Generator ancestry should be ablated
against conditioning on audible categories. These are proposed next training
changes, not features already present in v1. Their acceptance tests must include
fresh pitches and gestures plus real tagged human judgments.
