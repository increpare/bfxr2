# Multi-synth inverse model

The general-purpose CLI implementation lives in `../neural_invert/`: a shared
whole-sound encoder and separate audio-to-control experts for 22 individual
synths. The acoustic v2 model uses 51,200 actual DSP training examples and
learns controls directly from audio, with pitch-aware supervised loss. It preserves the original Bfxr
neural model and optimizer as an independent candidate. See
[NEURAL_V2.md](NEURAL_V2.md) for the current model and single-sound CLI;
[NEURAL_V1.md](NEURAL_V1.md) retains the first run's training and listening
comparison. Mixr composition and arbitrary phrase transcription remain separate
work; model capacity and parameter validation do not establish audible likeness.

Newer independent-expert experiments are retained alongside that baseline.
[Expanded Transfxr mixtures](NATIVE_MIXTURE_V1.md) now have explicit **very-close**
human judgments for two additional native rises and one filtered bouncing rise.
The same partial submission rejects both Footsteppr transfer options and prefers
an older Boomr recreation rated **roughly similar**. Three native/altered positives
do not establish general success on real recordings. All thirteen feedback sessions,
including exact audition PCM and immediate candidate-scoped adequacy, are retained.

The latest [specialist experiment](evaluations/specialists-v1-plan.json) trains
independent Boomr and Footsteppr models on 12,288 examples each. The older shared
model already had heads for these engines, trained on 2,048 examples each; those
heads remain explicit baselines. These new models start from random weights,
use the existing direct control-head architecture and loss, and select epochs
14 (Boomr) and 57 (Footsteppr) by validation loss after 90 epochs on MPS.
This changes training data and encoder sharing together, so it is not an
isolated architecture ablation or a blanket replacement of the older models.

Each new data set contains 10,445 optimization, 1,827 validation and 16 test rows.
Test control groups are excluded from both optimization and checkpoint selection;
they also do not occur in the old shared model's data. Preset families still
overlap. The benchmark gives all five arms the same audition PCM and four
proposals each: Transfxr mixture, two old shared heads, and two new independent
experts. Engine identity and pitch guards do not select the winner. It covers
155 references: 122 previously monitored cases, 32 new native test controls,
and archived tagged book-close. This is a focused comparison, not an all-synth
or original-Bfxr-search benchmark.

| Native test set | Old same-engine mean distance | New same-engine mean distance | New wins |
| --- | ---: | ---: | ---: |
| Boomr, 16 controls | 2.45703 | 2.48538 | 8/16 |
| Footsteppr, 16 controls | 1.80461 | 1.26481 | 11/16 |

These are actual-render matching distances, not human likeness ratings.
Footsteppr improves its native average by about 30%; Boomr is essentially flat.
Other-engine transfer is mixed, and neither new head wins any of the six tagged
recordings within this five-arm metric comparison. Older expert strengths must
remain available. The [new listening page](runs/specialists-v1-listening/index.html)
contains six short comparisons: familiar footstep and rocket references, the
first frozen native test control from each engine, a Whooshr wingbeat, and the
tagged book-close. It includes numerical losses as well as wins. Historical
human winners are replayed exactly; two trials have a third option to also
retain the older shared head. This selected batch cannot estimate a success rate.

The [specialist listening feedback](evaluations/specialists-quick-01-human-review.json)
now confirms three new wins, all **very close**: familiar footstep, rocket burst,
and Whooshr wingbeat. The older Boomr wins the native short burst, also very close;
the native footstep is a roughly-similar tie. Book-close was not submitted.
Matching distance agrees with 3/5 strict pairs, the frozen learned preference
scorer with 4/5. Preserve both generations. These five selected synthetic
references establish some audible successes, including cross-engine transfer,
but no general real-recording success. The next test uses five newly selected
tagged sources and retains original Bfxr plus the older ensemble.

The [tagged-transfer batch](runs/specialists-tagged-v1-listening/index.html) now
contains exactly five previously unjudged files: wooden footstep, brick break,
block hit, cloth rustle and laser. Selection was frozen before inference; no
source was dropped for a disappointing result. Exclusion covers exact previously
judged files/PCM, not source families or the original Bfxr real-finetuning corpus.
Old proposals span the shared 22-engine model and Transfxr mixture. New proposals
come from Boomr/Footsteppr; each pool gets two 128-mutation refinement starts.
Original Bfxr uses its neural-seeded optimizer with requested budget 2,000;
the existing optimizer actually used 2,015 evaluations on four references and
3,001 on laser. Counts are recorded rather than claiming equal total compute.

The new specialist pool has lower matching distance on one of five (laser).
Older outputs lead the other four, including an almost-tied brick break. These
scores do not establish audible wins; every reference is presented for review.
Three options per trial retain the older pool winner, new specialist winner,
and original Bfxr. Where original Bfxr is already the older winner, the third
option is a distinct raw specialist. All 15 options are verified visible in the
quick questionnaire, and immediate closeness is collected before advancing.

The [completed tagged listening pass](evaluations/specialists-tagged-quick-01-human-review.json)
finds **no very-close matches**. Older Clonkr's wooden footstep is roughly
similar. New Footsteppr wins brick-break and cloth, but both are least-bad;
original Bfxr wins block-hit and laser, also least-bad. Frozen matching distance
agrees with 6/10 heard pairs and preference-neural-v2 with 8/10. These outcomes
reject an interpretation of the native successes as general real-sound
reproduction. Keep candidate generation and selection as separate problems.

A subsequent [candidate-coverage diagnostic](runs/tagged-coverage-v1-listening/index.html)
queries **64,415 optimization presets** from the certified shared22 data and two
specialist datasets. It retrieves four nearest controls per engine using the
existing nine normalized feature groups and four using six groups without pitch
or voicing. Validation/test rows are excluded. It renders 750 distinct retrieved
candidates across the five repeated targets, then refines four starts per target
(two chosen by each frozen scorer, 128 mutations each). The 295 earlier neural
candidates remain in the pool. This is broader candidate generation and search,
**not a newly trained inverse model**, equal-compute comparison, or held-out test.

Both scorers find novel alternatives for all five references. The selected ten
alternatives all originate from refined retrieved controls. Matching and learned
preference disagree markedly on block-hit and laser; neither is automatically
promoted. The new five-trial page preserves each exact previous human winner
alongside both distinct selections. Previously heard alternatives are excluded
from the new slots; this is adaptive development using feedback, not blind
validation. Lower scores merely qualify a distinct sample for listening.

The [protocol](evaluations/tagged-coverage-v1-protocol.json),
[results](evaluations/tagged-coverage-v1-evaluation.json) and
[1,065-candidate exact DSP replay audit](evaluations/tagged-coverage-v1-listening-audit.json)
retain data bindings, control membership, all raw/finalist audio and score checks.
The audit reports zero score error. This tests whether better fitting candidates
exist before attempting to distill them into an inverse network. No least-bad
output is treated as a successful training label. Reproduce with
`evaluations/tagged-coverage-v1.py` and export using
`evaluations/tagged-coverage-v1-gallery.py` into fresh run paths.

The [frozen targets](evaluations/specialists-tagged-v1-targets.json),
[evaluation](evaluations/specialists-tagged-v1-evaluation.json),
[295-candidate replay audit](evaluations/specialists-tagged-v1-listening-audit.json)
and [22-response HTTP audit](evaluations/specialists-tagged-v1-http-audit.json)
bind the run. Reproduce generation with `evaluations/specialists-tagged-v1.py`;
use **`evaluations/specialists-tagged-v1-gallery.py`** for verification/export,
not the unused embedded publish action. The separate exporter corrects a hidden
raw-option role and binds original Bfxr to its actual renderer, while preserving
all evaluated audio. That backend was bound after evaluation, not before it;
every saved original Bfxr output exactly replays against the recorded backend.
No model or metric was retrained or globally promoted in this transfer batch.

The [scorer decomposition](evaluations/specialists-quick-01-components.json)
identifies a testable hypothesis: pitch penalties reverse the otherwise better
new footstep match. The short-burst error has a different pattern. These are
post-feedback diagnostics, not justification for globally removing pitch loss.

The [evaluation](evaluations/specialists-v1-evaluation.json),
[independent verification](evaluations/specialists-v1-audit.json) and
[listening selection](evaluations/specialists-v1-listening-targets.json) bind the
models, data, actual renders and comparison scope. Reproduction scripts are the
`evaluations/specialists-v1-*.py` files; full models/data/audio remain under
`runs/specialists-v1`. No global model promotion follows from these scores.

An earlier reviewed checkpoint is
[pitch-calibration listening](runs/pitch-calibration-listening-v1/index.html),
using frozen v3 Bfxr/Transfxr/Pluckr experts plus bounded DSP pitch correction.
Both changed selections lost their human comparisons; the synthetic pitch gate
does not establish perceptual improvement. The user subsequently confirmed
**zero convincing recreations across all five references**, including the winners.
This requires improving candidate generation as well as selection. See the
[human review](evaluations/pitch-calibration-quick-01-human-review.json) and
[verbatim adequacy follow-up](listening_data/2026-10-05-pitch-calibration-quick-01/qualitative-feedback.json).
The first eight feedback sessions and exact audition PCM remain versioned. A
preference-scorer refit reaches about 73% reference-balanced held-out agreement
overall but only 3/7 on this latest batch; it is experimental and not deployed.

The subsequent [paired fine-onset experiment](ONSET_V1.md) trained four new
checkpoints, but neither engine passed its actual-render promotion gate. Bfxr
regressed static pitch; Transfxr's mean improvement was below the threshold.
No new listening round is requested from that failed experiment.

Follow-up [local gradient checks](FORWARD_AUDIO_PILOT.md) and
[Transfxr pitch-gesture supervision](PHYSICAL_GESTURE_V2.md) also failed their promotion
checks. Exact results and models are retained. The subsequent larger native
Transfxr corpus and mixture results are linked above.

The earlier iterations below use an offline **nonparametric inverse model**: render examples from the app's
preset distributions, encode their audio, retrieve plausible parameters for
each synth, refine several synths independently, then automatically select the
closest result. This is a working baseline for expanding reachable game SFX,
not a newly trained neural network or a validated human preference predictor.

The default model spans **22 active synths**. The headless adapter supports 31,
but nine retired engines cannot be opened through normal collection import,
so matching excludes them. Chattr's text controls and Mixr/Stackr compositions
need separate search representations. Jinglr searches instrument, tuning,
tempo, envelope and timbre while keeping the retrieved phrase intact.

## Run

From `tools/`, with the existing Python environment (`uv sync --group dev`):

```sh
uv run python -m multisynth.cli build \
  -o multisynth/runs/library-v1 --per-preset 16 --jobs 4

uv run python -m multisynth.cli match path/to/sound.wav \
  --library multisynth/runs/library-v1 \
  -o multisynth/runs/my-sound --budget 128 --experts 5

uv run python -m multisynth.cli benchmark /path/to/targets_non_bfxr_big/tags \
  --library multisynth/runs/library-v1 \
  -o multisynth/runs/tagged-v2 --count 36 --max-seconds 4 --budget 64
```

Open the output `index.html` to compare references, winners and alternatives.
Load `matches.bcol` or the benchmark's `winners.bcol` through the app's collection
import. Parameters remain editable. The gallery's WAVs are peak-normalized and
silence-trimmed for comparison; imported presets retain their natural timing
and volume. Bfxr/Footsteppr's browser noise RNG can vary on playback; their exact
search render seeds are recorded in JSON and replayable through this tool.
Generated libraries, reports and source audio stay local under ignored `runs/`.

All commands use deterministic seeds. `--synths Bfxr` provides a single-engine
baseline. `--budget` is the number of additional renders **per expert**; Bfxr is
always added if present in the eligible library, so five experts can mean six
searches. Each finalist also needs one final export replay, separately counted.
The CLI prints progress and writes benchmark results after each completed target.

## Model and objective

The library stores canonical controls, recipe identity, render seed and an audio
descriptor. A fingerprint covers every loaded synth dependency, browser globals,
active-tab registration and adapter implementation; changed synthesis code
requires rebuilding the library. A feature version similarly guards against
incompatible descriptors. No target files are used to build the library.

The compact representation uses 40 mel bands over 32 relative-time frames,
relative and absolute amplitude envelopes, pitch/voicing/noisiness contours,
duration and motion summaries. Weighted L1 distance gives a cheap common
objective for retrieval and refinement. Overall gain and leading/trailing
silence are removed; timing and event order inside a sound remain significant.
The weights are engineering choices, not learned from listening judgments.

Retrieval preserves up to four seeds per synth. The top synths undergo bounded
mixed discrete/continuous mutation, with decreasing step size, multiple elites,
and an initial duration proposal. Actual browser setters clamp/round controls.
The incumbent is retained on every step, so search cannot worsen its objective.
Categorical values and Transfxr endpoints/curves are supported. Texture seeds
remain fixed rather than becoming a way to optimize individual noise samples.

This implementation deliberately leaves the old Bfxr matcher and neural model
unchanged. It also avoids the earlier pitch-structure penalty whose improved
synthetic tests did not translate into a listening win.

## Evaluation and limitations

The benchmark now prefers the supplied corpus's `tags/` subtree when present;
passing the tagged directory directly also works. `--all-collections` restores
the original broad-corpus behavior. It shuffles files deterministically inside
tags and round-robins them (or source collections for a broad run).
It rejects silence, invalid audio, exact
normalized duplicates and files longer than the configured limit. It does not
silently truncate recordings. Filenames are used for display and source
balancing only; the model sees audio, not tags. Manifests include source paths,
SHA-256 hashes, settings and library identity.

The Bfxr comparison uses the same per-preset sampling count and per-expert
search budget. **Multi-synth search uses more total candidates and renders.**
Its score advantage is a search-space comparison under its own objective, not
an equal-compute comparison, nor proof of improvement over the old neural-seeded
matcher. Scores are not percentages of audible likeness. Speech, several
simultaneous sources, precise note sequences and long evolving textures remain
hard. A human A/B listening pass is necessary before calling a preset convincing
or fun. Keep alternate synth results: the numerical winner need not be the most
useful game sound.

## Tests

```sh
node --test ../tests/multisynth-render.test.js
uv run pytest tests/test_multisynth.py
```

Tests cover seeded rendering and replay, every Footsteppr terrain, inventory and
schema, worker error recovery, perceptual orderings, gain/onset invariance,
invalid audio, stale-library rejection, parameter bounds, search budget,
incumbent preservation and editable export round trips.

## First measured run

See [RESULTS.md](RESULTS.md) for the 40-target experiment, independent metric
check, noise-seed audit and local deliverables. To audit another completed run:

```sh
uv run python -m multisynth.audit multisynth/runs/real-v1
```

The audit verifies reference SHA-256 hashes, feature version and DSP source
fingerprint before re-scoring. It reports disagreement with the previous
contour metric rather than concealing it.

The benchmark gallery provides reference/model/Bfxr audio for each target, with
independent 1–5 likeness ratings and optional notes. Ratings persist in browser
local storage, scoped to the experiment and candidate identities. When the
model selected Bfxr itself, both controls share a rating. The bottom-of-page
JSON includes only rated/noted targets, with provenance for matching feedback
back to saved results. Use **Copy feedback JSON** to share it in chat; nothing
is submitted automatically.

## Retained human feedback and current research direction

The current neural listening gallery has a [quick comparison mode](QUICK_LISTENING.md):
one best-match choice per reference, automatic sequential playback, cached audio
that restarts at zero, and optional detailed ratings. Schema-3 choices are
preserved alongside older ratings and feed heard-only ordinal training pairs.

The first listening pass averaged **2/5**, with **30/40** model selections rated
1–2. This baseline is not perceptually successful. See [RESULTS.md](RESULTS.md)
and [listening_data/README.md](listening_data/README.md) for the preserved data
and its use restrictions. Archive future exported feedback with:

```sh
uv run python -m multisynth.listening /path/to/feedback.json \
  --report multisynth/runs/real-v1 \
  --output multisynth/listening_data/NEW-LISTENING-SESSION
```

Unlike disposable `runs/`, these archives are versioned: raw JSON, verified
candidate identities, replay parameters, notes, and lossless audition clips.
The importer rejects mismatched experiments, invalid ratings and conflicting
ratings for a shared candidate. Re-importing identical data verifies the archive.

The user's target is **large-scale gesture and feel**, robust to modest
quantitative differences: impact, build-up, rebound, flutter, rattle, rise/fall,
and decay character. See the [updated design](../../docs/superpowers/specs/2026-10-03-multisynth-approximation-design.md)
for the acceptance criteria. [GESTURE_V2.md](GESTURE_V2.md) documents the next
implemented representation, fitting attempt and 18-tag comparison gallery.
The fitted weights did not improve held-out preference prediction, so this
listening iteration uses the fixed gesture prior with a larger library/search.
**The subsequent human pass rejected that iteration:** 1 win / 13 ties / 4
losses against the previous model on the same references, with mean likeness
1.83 versus 2.06. Its frozen metric also predicts fewer new strict preferences
correctly (8/19 versus auditory-v1's 17/19 after exact-reference overlap is
excluded). The gesture checkpoints are retained as experimental failures, not
recommended replacements. See the human verdict in `GESTURE_V2.md`.
The old auditory-v1 metric remains the CLI default; opt in with
`--gesture-model multisynth/models/gesture-v2-prior.json`, or use
`multisynth.iterate` to generate old/new/Bfxr comparisons together.

The new gallery retains a separately rated **Previous model** card as well as
Bfxr. Feedback export and archival support all three approximation roles while
keeping earlier feedback identities unchanged. The fitting utility uses all
strict preferences among distinct rated candidates, grouping each reference's
pairs together in validation. Neither lower search distance nor successful
synthetic checks establishes audible improvement. Human ratings are the deciding
check; the rejected v2 iteration demonstrates why.

The next [Soundboard coverage diagnostic](COVERAGE_V3.md) uses a frozen copy of
the separately human-refined catalogue, including two-synth compositions. Its
six-reference gallery compares global retrieval, category-guided alternatives,
and the best previously rated audio. It collects likeness and usefulness/fun
separately; both survive immutable schema-2 archival through the same command.
Its completed human pass found useful game sounds but no likeness improvement:
automatic selections scored 1.67/5 against rerated baselines at 2.67/5. All 48
ratings and exact audio are retained. Seven usefulness-4 presets are saved in
`presets/coverage-v3-useful.bcol`; see the verdict in `COVERAGE_V3.md`.

## Large reproduction iteration (v4)

[BIG_V4.md](BIG_V4.md) documents retraining on all three retained sessions and
a 36-reference listening experiment over 25,728 candidate examples, including
the frozen Soundboard catalogue. The learned metric has not beaten auditory-v1
on grouped validation; both select from the expanded shared search pool.
[PERCEPTUAL_RESEARCH.md](PERCEPTUAL_RESEARCH.md) records the psychoacoustic
literature, its limits, and concrete next feature benchmarks.

The subsequent v4 listening pass shows modest progress: preference-v4 won
6 / tied 30 / lost 0 against expanded auditory-v1, but mean likeness was still
1.94/5 and none of the displayed clips exceeded 3/5. All 103 dual-dimension
judgments and exact audio are retained. See the human verdict in `BIG_V4.md`.

## Event/texture iteration and all-engine coverage (v5)

[PERCEPTUAL_V5.md](PERCEPTUAL_V5.md) describes the next fixed experiment: a
30-component event/texture scorer trained on all four saved listening rounds,
with the old feature set refitted on identical held-out reference groups.
The new features score 72/103 preferences versus 75/103 for the old features,
so they remain experimental. A tagged comparison preserves the v4 incumbent
and exact historical best audio. Balanced held-out synthetic recovery is a
separate coverage diagnostic; synthetic matches do not become human labels.
