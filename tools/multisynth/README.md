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
do not establish general success on real recordings. All thirty feedback archives,
including exact audition PCM and immediate candidate-scoped adequacy, are retained.

The latest [matched-objective human review](evaluations/legacy-transfer-v1-quick-01-human-review.json)
finds two wins each for legacy-scored newer synths, preference-scored newer synths,
and original Bfxr. Four winners are least-bad, two similar, none very-close.
All18 options were heard; all24 exact reference/candidate PCM files are retained.
This rejects a claim that swapping the scorer alone has solved transfer. The
six files occur in historical original-Bfxr training, and its budget differs.

The [four-trial native Stackr pilot](runs/stackr-events-v1-listening/index.html)
tests the book-flip and coin movement failures alongside the similar attack and
bell controls. A separate native bridge preserves all earlier renderer identities.
Waveform-only boundaries condition existing shared22/Transfxr inverse proposals
on individual events, with128 native control mutations per event and128 timeline
mutations per reference. Native Stackr owns placement, gain, pitch and saturation;
no reference audio is inserted into a patch. No neural weights are retrained.

Each trial retains the exact earlier human winner, a scheduled Stackr patch, and
the same final components starting together. Exact duplicate options merge; the
bell has no interior boundary and only two distinct options. All four references
remain regardless of scores, including possible regressions. These are repeated
external development references, not new-source validation, and historical Bfxr
overlap remains. The comparison diagnoses representation rather than equal-budget
model superiority. The completed human review below supplies the outcome.

See [protocol](evaluations/stackr-events-v1-protocol.json),
[results](evaluations/stackr-events-v1-evaluation.json), and
[independent verification](evaluations/stackr-events-v1-verification.json).
Reproduce with `PYTHONPATH=tools python tools/multisynth/evaluations/stackr-events-v1.py`
followed by `freeze`, `run`, and `publish` in a fresh output location. The existing
paths are immutable; do not overwrite a published or partially completed run.

The completed [Stackr event feedback](evaluations/stackr-events-v1-quick-01-human-review.json)
finds one local gain: scheduled coin wins as similar against the previous
least-bad Transfxr clip and the simultaneous ablation. Movement/rhythm remains
imperfect. Previous book and attack win as least-bad and similar; previous Boomr
bell is now very-close, but that is unchanged audio with a different contextual
rating. All11 options were heard, supplying seven strict pairs and four scoped
qualitative labels. No broad Stackr promotion follows from this result.

A new **13,281-parameter event-timing CNN** is trained on1,536 actual native
Stackr sequences, with384 validation and384 untouched test sequences. The
256 constituent patches come from eight engines; canonical controls and exact
source PCM are disjoint across splits. Preset families can overlap. Components
are short and have prompt attacks, so this is a restricted timing model, not a
new all-synth control inverse. Source-bank corrections happened before training
and are retained in the preflight receipts.

The fixed40-epoch CPU run chooses epoch38 by validation BCE (0.0764866484),
reproduced after loading the checkpoint. Native interior-event F1 is85.85%,
versus67.73% for the old waveform splitter; exact event-count accuracy is81.51%
versus64.32%. On4-bit audio, F1 is84.62% versus69.89%; on1500Hz low-pass audio,
83.21% versus64.08%. It passes the predeclared timing gate. These are native
schedule-label measurements within25ms, **not perceptual recreation accuracy**.
Neither real references nor human-selected patches enter this timing dataset.
The small checkpoint is retained in version control at
[models/event-timing-v1.pt](models/event-timing-v1.pt), with its feature/code
bindings in [metadata](models/event-timing-v1.json). It remains experimental.

See [protocol](evaluations/event-timing-v1-protocol.json),
[data audit](evaluations/event-timing-v1-data-audit.json),
[training](evaluations/event-timing-v1-training-audit.json),
[test evaluation](evaluations/event-timing-v1-evaluation.json),
[independent verification](evaluations/event-timing-v1-verification.json), and
[all-row native source/label check](evaluations/event-timing-v1-source-label-check.json).
An additional [tempo stress diagnostic](evaluations/event-timing-v1-tempo-stress.json)
was explicitly exploratory after viewing external boundary proposals. Halving
start spacing lowers learned F1 to72.78% (heuristic63.10%); stretching spacing
by1.5 gives87.43% (heuristic65.01%). Source duration stays fixed, so overlap also
changes. This exposes restricted tempo coverage and does not revise the original
gate or checkpoint. The frozen external comparison remains unchanged.

The implementation is `neural_invert.event_timing`; reproduce the fixed experiment
with `evaluations/event-timing-v1.py bank`, `data`, `train`, `evaluate` using a fresh
output directory. Preserve existing experiment paths.

The [five-trial external timing comparison](runs/learned-events-v1-listening/index.html)
compares learned and heuristic boundaries through the same frozen shared22 and
Transfxr experts, alongside the exact latest human winner. This includes the
newly preferred Stackr coin, not its superseded Transfxr anchor. Each event gets
128 native control mutations and each timeline128 mutations; differing event
counts mean different total work and different segment-conditioned proposals.
This tests the full segmentation-assisted pipeline, not an isolated boundary
metric or equal-total-budget superiority. All six repeated external sources
are fitted, with exact PCM aliases merged. The bell is omitted from listening
because its entire reference/option PCM set was already heard and judged; this
filter uses no ratings or score outcomes. Historical Bfxr training overlap remains;
the completed feedback rejects external improvement: all five exact earlier
clips win, with three least-bad and two similar labels. The learned timing model
has zero wins and remains experimental. Coin is the unchanged heuristic Stackr
winner, not a new gain. All13 options were heard, yielding eight strict pairs.
See the [human review](evaluations/learned-events-v1-quick-01-human-review.json).
See [frozen comparison protocol](evaluations/learned-events-v1-protocol.json) and
[replay/provenance checks](evaluations/learned-events-v1-verification.json).

The joint event-control pilot exposed a concrete scoring defect: adding digital
silence lowers historical MatchObjective distance on all five latest exact human
winners. The optimizer can exploit its envelope/mel averages over the longest
buffer. One native footstep fit lasted10.328seconds, while its last sample above
-60dB relative peak occurred at0.573seconds. See the
[unchanged-audio padding probe](evaluations/joint-events-v1-padding-probe.json).
The pilot's results are retained as a diagnostic, not the next requested audition.

Its post-fit verifier also mistakenly exported PCM a second time. This changed
21,260 samples by at most one PCM step and moved that clip's score from1.1733 to
1.3306. Search itself used one export. The separate recovery script verifies the
original PCM with bare MatchObjective and requires exact replay of the interrupted
fit. Completed fits remain unchanged; the interrupted2048 attempts are repeated
with the same seed, disclosed as duplicate compute. See the
[recovery receipt](evaluations/joint-events-v1-recovery.json).

The experimental `multisynth.support_objective.SupportObjective` analyzes through
the final sample above .001 of peak plus20ms context, retaining onset delay and
later audible events. It leaves audition PCM unchanged. This removes the silent
buffer incentive; it is an explicit analysis policy, not a complete audibility
model. Historical scoring and model defaults remain intact. Unit tests and20
padding checks on all five external reference/candidate pairs verify exact
invariance; neither those checks nor score gains establish better human ranking.
See [the support audit](evaluations/support-objective-v1-audit.json).

The [four-case corrected comparison](runs/joint-support-v2-listening/index.html)
uses the same initial heuristic Stackr patches for book, metal footstep, attack
and coin. Each gets768 timing-only and768 joint-control attempts under the
experimental corrected objective. Joint fitting can adjust native source controls
in the complete sound context; the old event pipeline locked these after fitting
isolated crops. Engines, layer count and random seed remain fixed. Your latest
human winner is copied exactly as a third option, and exact audio aliases merge.
No neural weights are retrained. These repeated external development references
overlap historical Bfxr training; all four remain regardless of score.

See [plan](../../docs/superpowers/plans/2026-10-06-joint-support.md),
[protocol](evaluations/joint-support-v2-protocol.json), and
[native source-overlap audit](evaluations/joint-events-v1-context.json).
All eight fitted patches replay exactly, all12 options and four references have
verified delivery hashes, and the browser loads0/4 judged without logged warnings
or errors. The run made6144 attempts. Joint scoring is lower on three cases and
higher on attack; these are numerical results, with human likeness still unknown.
See [verification](evaluations/joint-support-v2-verification.json) and
[served-file audit](evaluations/joint-support-v2-http-audit.json).

Execute the corrected recipe with `joint-support-v2.py freeze`, then
`joint-support-v2-parallel.py`, then `joint-support-v2.py publish`, using new paths
for reproduction rather than overwriting any completed experiment.

The new [Squishr specialist](NEURAL_V2.md#dedicated-squishr-experiment-2026-10-05)
follows a **very-close** tagged wooden-footstep search result. Its 8,192-example
synthetic dataset reserves validation and native test controls; the human-approved
reference and preset stay outside fitting. The first five human judgments tie
both refined heads and the retained footstep as very-close, but reject both fresh
footstep options and rate the other three tagged winners least-bad. Better tagged
transfer is not demonstrated. The completed native half has five very-close
winners/ties, but shared wins two, specialist one, and two tie. Native success
does not establish off-model success or specialist superiority. See the
[complete human review](evaluations/squishr-v1-quick-02-human-review.json).

The [eight-trial external transfer page](runs/off-model-transfer-v1-listening/index.html)
tests the full existing expert pool on eight unjudged tagged files. All 464 raw
proposals rendered, followed by 4,096 neural mutation attempts across two frozen
scorers and original Bfxr's independent optimizer (19,080 actual evaluations).
Three distinct options per reference retain scorer alternatives and original Bfxr.
There is no retraining or quality claim in this selection/transfer diagnostic.

These are external inputs for the newer synthetic-trained experts. The historical
original-Bfxr real-finetune manifest contains six in its training list and two in
its holdout list: it is a familiar anchor, **not an unseen baseline**. All files
in the eight chosen tag strata occur in that old manifest. This overlap is
disclosed in the questionnaire. Exact prior feedback file/PCM duplicates were
excluded, but source-family independence is not established. See the
[frozen targets](evaluations/off-model-transfer-v1-targets.json),
[evaluation](evaluations/off-model-transfer-v1-evaluation.json), and
[historical Bfxr overlap audit](evaluations/off-model-transfer-v1-bfxr-training-overlap.json).

The first five external-transfer judgments contain **two similar, one least-bad,
and two none-close** outcomes; no convincing recreation. Similar choices are
Transfxr-mixture metallic footstep and shared Rustlr cloth. The footstep supplies
only an absolute label because no other option was recorded as heard. Four
strict pairs across cloth and belt/chain agree with soft and legacy scores,
while preference-neural-v2 agrees on one. Three trials remain unsubmitted. See the
[partial human review](evaluations/off-model-transfer-v1-quick-01-human-review.json).

The completed external batch adds **very-close original Bfxr coin**, **least-bad
Squishr cloth-belt**, and **none-close laser**. None of the newer experts has a
very-close external judgment here. Native success therefore has not established
convincing transfer. Eight strict heard pairs remain after cumulative-export
deduplication; the footstep contributes adequacy only. See the
[complete human review](evaluations/off-model-transfer-v1-quick-02-human-review.json).

The [four-trial Mixr composition probe](runs/mixr-transfer-v1-listening/index.html)
compares exact earlier audio with single-source controls and actual two-source
Mixr patches. It reuses the rejected hit, door and laser plus the roughly similar
cloth reference; these are development cases, not held-out validation. Existing
predictions supply the sources: **no inverse model was retrained**. The frozen
search evaluates 330 mixtures per reference (1,320 total), selecting with the
soft-periodicity scorer. Only laser improves that score over the best single;
all four cases remain in the listening batch. No audible improvement is claimed.

The renderer uses shipped Mixr/Stackr synthesis with replayable source controls,
and checks exact uncached native replay against cached rendering. Thirty source
engines are supported; Footsteppr's separate host is excluded. Each source was
predicted from the whole reference, and voices start together: this does not test
onset/residual-conditioned models or temporal composition. A negative result
would therefore reject this narrow search, not composition in general. The page
contains 2/3/3/3 distinct options after exact-audio deduplication, with immediate
adequacy questions. See the [protocol](evaluations/mixr-transfer-v1-protocol.json),
[numerical results](evaluations/mixr-transfer-v1-evaluation.json),
[audio replay receipt](evaluations/mixr-transfer-v1-listening-audit.json), and
[served-file verification](evaluations/mixr-transfer-v1-http-audit.json).

The [complete Mixr human feedback](evaluations/mixr-transfer-v1-quick-01-human-review.json)
finds **no very-close recreation**: two-source hit wins but is least-bad; door
remains none-close; laser ties as least-bad and cloth ties as similar. All eleven
options were heard. The sole strict pair favors the mixture despite worse soft
and frozen-preference scores; legacy agrees. This does not validate either
composition adequacy or the newer scorers. Preserve the relative win separately
from the failed absolute quality check.


The [joint-fitting page](runs/mixr-joint-v1-listening/index.html) now tests source
co-adaptation: four external development references, two frozen scorers, and
single/pair arms with four starts and 512 mutation attempts apiece. All 8,192
attempts completed without failed renders. Every one of the 16 finalists replays
exactly through native Mixr and reproduces its audition scores. The eight quick
trials retain exact earlier audio and both newly fitted options, three per trial.
No neural checkpoint was retrained and none of these fits is an approved teacher.

| Reference | Soft single | Soft pair | Preference single | Preference pair |
| --- | ---: | ---: | ---: | ---: |
| Hit/pat | 2.9200 | 2.0536 | 0.8704 | 0.8632 |
| Door | 2.7505 | 2.7481 | 1.0703 | 0.9770 |
| Laser | 2.9776 | 2.8057 | 0.6037 | 0.4962 |
| Cloth | 2.0476 | 1.9942 | 0.6169 | 0.5303 |

Lower is better within each scorer; the two score scales are not comparable.
All pairs beat their single control numerically, sometimes by tiny margins.
Different starting patches and extra parameters remain confounds: this is not
an isolated causal test of layering. The soft hit pair's weaker source is about
28 dB below the stronger source by energy, so two stored voices do not prove two
perceptually important components. The post-run audit also scores each fitted
source alone; it does not change selection or establish audible improvement.
Only listening can establish likeness. References have already been judged and
are not an unseen test set.

See the [frozen protocol](evaluations/mixr-joint-v1-protocol.json),
[search results](evaluations/mixr-joint-v1-evaluation.json),
[native replay and source ablation](evaluations/mixr-joint-v1-replay-audit.json),
and [HTTP verification](evaluations/mixr-joint-v1-http-audit.json).
A partial first attempt was stopped when review found missing scorer dependency
bindings, a missing frozen-protocol check and a missing gallery PCM recheck. Its
protocol and executed script remain in ignored `runs/mixr-joint-v1-interrupted-01`;
the published run was restarted from the corrected protocol. The corrections
passed independent review. Five joint-search tests, 44 feedback tests and five
native composition tests passed; all 34 served page/audio assets match local
hashes. No user choices or audition telemetry were fabricated during verification.

The [complete joint-fitting feedback](evaluations/mixr-joint-v1-quick-02-human-review.json)
now contains all eight judgments, with the first five unchanged. The additional
laser comparison prefers Boomr + Transfxr and rates it roughly similar; cloth
prefers the Boomr single, also roughly similar; door still fails. None is
very-close. Four strict heard preference pairs are new. The complete archive
preserves twenty-four exact PCM clips and all context-dependent adequacy labels.
This motivates a genuine mixture-trained fixed Boomr/Transfxr inverse pilot;
search results are not substituted for exact synthetic control supervision.

A genuine mixture-supervised pilot now lives in `neural_invert.pair_model` and
`neural_invert.pair_train`: a fixed **Boomr + Transfxr** Mixr inverse, not an
all-synth replacement. Four complete hypotheses predict both sources, balance,
and whether either source should be absent. The 879,012-parameter temporal CNN
trains on 6,144 actual Mixr renders, validates on 768, and reserves 96 native
tests. The 1,408 canonical component controls and their exact source PCM are
disjoint across splits; preset families still overlap and old baseline experts
may know those native components. No fitted real-audio patch becomes a label.

The fixed 60-epoch run selects epoch 7: validation loss 0.523243, reproduced after
reload on both MPS and CPU. Later training overfits, so its smaller training loss
does not replace the selected checkpoint. This is a parameter-space result, not
a claim of perceptual accuracy. See the [data audit](evaluations/pair-inverse-v1-data-audit.json),
[training audit](evaluations/pair-inverse-v1-training-audit.json), and
[frozen evaluation protocol](evaluations/pair-inverse-v1-protocol.json).

Actual-render results do **not** establish an overall improvement. On the 96
native tests the trained pair beats independent composition on 48 preference
scores and 38 soft-periodicity scores. Eight low-pass cases expose a weakness:
only 2/8 preference wins and 0/8 soft-periodicity wins. Other degradation groups
are mixed. On eight repeated tagged external inputs, equal 256-attempt refinement
gives 4/8 preference wins and 3/8 soft-periodicity wins. These are score comparisons,
not listener judgments; no checkpoint is promoted. See the
[native/perturbation results](evaluations/pair-inverse-v1-native.json) and
[external results](evaluations/pair-inverse-v1-external.json).

The [eight-trial listening page](runs/pair-inverse-v1-listening/index.html) preserves
each earlier clip exactly and compares it with both newly fitted approaches.
All eight references are external, all have three distinct visible choices, and
all 34 served HTML/report/audio files match local hashes. Immediate likeness is
collected in the existing buffered interface. The completed [human review](evaluations/pair-inverse-v1-quick-01-human-review.json)
selects no trained-pair candidate. Independent inference wins footstep as similar
and hit as least-bad; retained cloth and original Bfxr coin are very-close, laser
similar, chains least-bad, and door/bell none-close. All 24 candidates were heard.
No pair checkpoint is promoted. These remain repeated development cases; the
unchanged older cloth rating differs by session and is not a new recreation.

The current preference fitting objective agrees with 8/12 new strict choices,
versus 11/12 for frozen soft-periodicity. The separate [listener metric experiment](evaluations/listener-metric-v1-evaluation.json)
fits 21 nonnegative weights on strict external preferences, holding connected
source/tag groups out in five fixed folds. Across 187 pairs / 64 references /
44 groups, reference-balanced agreement is 75.35%, versus 72.65% for the historical
preference metric and 69.34% for soft-periodicity. The gain of 2.70 percentage
points fails the predeclared 3-point gate, so no full-data checkpoint is saved
or deployed. The historical comparator saw some older labels; these are
retrospective ranking results, not new audible recreations or statistical proof.
Both newest listener errors concern the least-bad chains choice. Inverse
generation failures remain unresolved.

The [fresh eight-reference batch](runs/fresh-gesture-v1-listening/index.html)
uses the existing expert pool and two frozen scorers on unjudged clothes,
footstep, hit, bell, laser and collect sounds. Its target identities are fixed
before inference; all eight remain in the page. All eight occur in original
Bfxr's historical real-training list, disclosed in both page views. These are
external inputs for the newer synthetic-trained experts, not an unseen Bfxr test.
No retrained model is promoted. See the [protocol/targets](evaluations/fresh-gesture-v1-targets.json)
and [evaluation](evaluations/fresh-gesture-v1-evaluation.json). All 464 proposals
rendered successfully, followed by 4,096 neural refinement attempts and 18,094
original-Bfxr evaluations. All 24 final presets replay exactly; all 34 served
HTML/report/audio files match their saved hashes in the
[delivery audit](evaluations/fresh-gesture-v1-http-audit.json).

A separately versioned quick controller offers an optional biggest-mismatch
question immediately after similar, least-bad or none-close responses. Pitch,
movement/rhythm, texture/timbre, attack/decay, several things and unsure choices
are stored as scoped notes identifying exact candidate IDs. Replay remains
available; S skips the question. Undo restores the earlier note and judgment.
Existing published controllers and feedback schemas remain unchanged.

The [completed fresh human review](evaluations/fresh-gesture-v1-quick-01-human-review.json)
has **three very-close, four similar and one least-bad** choices. Shared Pluckr's
bell is an external success; the very-close water-jump and collect are original
Bfxr with known real-training overlap. The collect's `soft` selection label does
not make it a newer expert. All five mismatch notes are preserved with exact
candidate scope. Twenty-three candidates were heard, yielding 15 strict pairs;
preference/legacy agree on 8, soft on 6. No inverse checkpoint changed in this
round and no global metric improvement follows from these choices.

The [seven controlled follow-ups](runs/control-diagnosis-v1-listening/index.html)
keep each exact chosen clip and vary one native control family. Two pitch-noted
sounds test frequency-related controls separately from filter/noise colour;
carpet and laser test texture controls. The previously very-close Pluckr bell
is included as an agreement control. All variants are predetermined and shown,
not selected by score; no waveform pitch shifting or time stretching is used.
Some controls couple multiple audible cues, so these are interventions rather
than pure perceptual axes. Five external development references appear in seven
trials; repeated references test different adjustments. See the
[protocol](evaluations/control-diagnosis-v1-protocol.json) and
[native replay/score audit](evaluations/control-diagnosis-v1-evaluation.json).

The [completed control feedback](evaluations/control-diagnosis-v1-quick-01-human-review.json)
has **zero variant wins, four ties and three unchanged-clip wins**. No comparison
was judged very close. Twenty of 21 options were recorded heard; the unplayed
bell variant contributes no strict preference pair. All seven scoped notes and
24 unique exact reference/candidate PCM files are retained. Five strict heard
pairs agree with preference/soft scores on four and legacy on three; this tiny
selected probe does not validate those scorers. Identical footstep, carpet,
laser and bell audio received lower adequacy than in the previous context.
Both sessions remain intact; neither is silently rewritten into a timeless label.

The [memory-head initialization experiment](runs/memory-inverse-v1-listening/index.html)
fits a nonparametric output head over the **frozen shared22 encoder**: 43,525
synthetic training presets, excluding 7,675 validation rows. It retrieves complete
native controls using standardized learned-embedding distance. No neural weights
were retrained and no real reference or human-selected patch was added to memory.
The same eight external development references compare this initialization with
the current regressed controls and the exact earlier human choice. Both fitted
arms use identical per-engine proposal quotas, frozen preference scorer, and
two distinct-engine starts with 128 native mutation attempts each. Final listening
options retain all predeclared cases and deduplicate exact audio aliases.

This tests coherent preset initialization, not a new claim of perceptual quality.
Memory also retains prototype text/random state and scans a dense bank, so equal
rendered proposal/search budgets do not isolate regression averaging or total
compute. These repeated references overlap original Bfxr's historical training.
See the [protocol](evaluations/memory-inverse-v1-protocol.json),
[fit receipt](evaluations/memory-inverse-v1-fit.json), and
[numerical results](evaluations/memory-inverse-v1-evaluation.json). Reproduction:
`PYTHONPATH=tools python tools/multisynth/evaluations/memory-inverse-v1.py freeze`,
then `fit`, then `run`; publication uses `memory-inverse-v1-publish.py`.
Existing experiment directories are deliberately preserved against overwrites.

All 672 proposals rendered; all 336 memory proposals matched their original
training audio hashes exactly. Both arms completed 4,096 combined mutation
attempts. Memory achieved a lower selection score on six of eight references;
that is **not a human likeness result**. The published batch retains all eight
references and 24 distinct comparison options, with exact final native replay
and unchanged prior-choice audio verified. See the
[listening audit](evaluations/memory-inverse-v1-listening-audit.json) and
[served-file audit](evaluations/memory-inverse-v1-http-audit.json).

The [memory-head human verdict](evaluations/memory-inverse-v1-quick-01-human-review.json)
rejects it as an improvement: **zero memory wins, five earlier-clip wins, two
new regression wins and one tie**. Both regression winners (Transfxr case closure
and Riftr laser) are least-bad. The only very-close choice is earlier original
Bfxr collect. Earlier cloth, footstep, water-jump and bell win as similar; carpet
ties least-bad. Twenty-two of 24 options were recorded heard. Six of seven scoped
notes identify texture/timbre; water-jump identifies pitch. On12 strict heard
pairs, preference scores agree on 3, soft on 8, legacy MatchObjective on9.
Memory's six numerical score improvements did not yield a human win.

The [texture-listener experiment](evaluations/texture-listener-v1-evaluation.json)
adds six auditory-envelope blocks (marginals, cross-band correlation and modulation)
to the 21 existing listener components. The new representation is a compact
research-inspired approximation, not a reproduction of a validated auditory model.
Five fixed folds hold out connected source/tag groups across 219 external strict
pairs, 72 exact references and44 groups. Training scales and reference weights
use only each fold's training data. The same-data21-component ablation is explicit.

The fixed gate **failed**: texture68.09% reference-balanced accuracy versus
base21 67.99%, frozen preference70.16% and soft67.44%. Texture improves the latest
batch from base21's6/12 to8/12, but that selected subset cannot override the broader
failure. No full-data texture checkpoint is saved, no default changes, and no
generated quality improvement is claimed. The code, tests and negative result
remain available for future hypotheses. See the
[frozen protocol](evaluations/texture-listener-v1-protocol.json) and
[design](../../docs/superpowers/plans/2026-10-06-texture-listener.md).

The next [six-reference scorer comparison](runs/legacy-transfer-v1-listening/index.html)
uses fresh-to-listening card, footstep, hit, bell, laser and collect files.
Both general-synth arms receive the same 58 proposals from the existing shared
and specialist inverses. Each chooses two distinct engines and makes 512 native
mutation attempts per start, one under original MatchObjective and one under
frozen preference-neural-v2. Each selects only its own fits and the common raw
pool; neither borrows the competing scorer's refinements. Original Bfxr remains
the independent third option with its historical neural model and 2000-budget
StagedOptimizer. Only the two general-synth arms have matched search budgets.

The clothes category had no eligible short unjudged file, so card handling was
substituted before inference. All six references are new to retained listening
feedback, but occur in original Bfxr's historical training list. Source families
can overlap prior trials. No inverse weights or failed texture metric are used
as a new default. This tests matching objectives on external inputs; human
likeness is unknown until the next response. The page retains immediate adequacy
and optional mismatch questions, with exact native replay and audio verification.

The completed run rendered all 348 raw proposals, made 12,288 general-arm mutation
attempts, and recorded 17,028 actual original-Bfxr evaluations (its adaptive
optimizer can exceed the nominal budget). All 18 finalists replay exactly and
their audition scores reproduce. The six-reference page serves 24 WAVs plus its
HTML/report successfully; browser loading has no logged warnings or errors and
was checked at 0/6 judged. See [targets](evaluations/legacy-transfer-v1-targets.json),
[results](evaluations/legacy-transfer-v1-evaluation.json),
[listening audit](evaluations/legacy-transfer-v1-listening-audit.json), and
[delivery/accounting verification](evaluations/legacy-transfer-v1-http-audit.json).

A read-only [Soundboard branch inspection](evaluations/soundboard-e006519-inspection.json)
records `claude/determined-sagan-khz12h` at `e006519`: nine synth-class recipe/variety
changes and updated examples since the earlier `db9f5f8` snapshot, with no changed
`js/audio` files. Those recipes are a possible future synthetic sampling source,
not new target-likeness labels. They are kept outside this frozen scorer experiment;
native parameter replay still needs verification before incorporating them.


Reproduction commands, from the repository root with `PYTHONPATH=tools` and the
existing Torch environment, are `python -m neural_invert.pair_data bank`,
`python -m neural_invert.pair_data generate`, and
`python -m neural_invert.pair_train --output tools/multisynth/runs/pair-inverse-v1/model`.
These preserve existing artifacts by refusing to overwrite them. The Python
`pair_train.load` / `predict` API returns four native Mixr parameter dictionaries;
no default expert or production UI is replaced.

The [first joint-fitting feedback](evaluations/mixr-joint-v1-quick-01-human-review.json)
contains **five of eight trials**, with no very-close recreation. Soft-score hit,
door and laser are none-close; cloth is a similar tie. The first preference-score
trial favors the exact earlier hit mixture as similar. No new pair has established
improved audible likeness. The soft hit pair has no recorded audition, so its
individual adequacy remains uncertain. The preference-block hit winner was heard
in an earlier trial but not logged in the current one; preserve its explicit
judgment without inventing a current-trial strict training pair. Three existing
comparisons remain pending. These results are not verified training teachers,
and the partial export must not be presented as a completed eight-trial verdict.

The earlier [specialist experiment](evaluations/specialists-v1-plan.json) trains
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

A frozen pretrained-audio diagnostic then tested LAION CLAP final embeddings and
intermediate mean/std features on 162 strict historical preferences across 62
conservative source families. With identical family folds, the current metric
refit scores 69.27% family-balanced agreement; the hybrid scores 71.17%
(112 versus 114 of 162 pairs). The predeclared five-point improvement screen
fails; the family-bootstrap gain interval spans -0.16 to +5.47 points. Standalone
CLAP final/style features score 102/162 and 98/162. No selector or inverse model
is promoted. This is development evidence, not untouched validation or evidence
of adequate recreations. See [protocol](evaluations/embedding-v1-protocol.json)
and [evaluation](evaluations/embedding-v1-evaluation.json).

The [five-comparison cue calibration](runs/cue-calibration-v1-listening/index.html)
uses **deliberately edited originals, not synth reproductions**. Fixed attack,
filter, timing, pitch and tail changes probe local likeness preferences with two
options per reference and immediate adequacy. All contrasts are retained, even
when metrics agree. These are candidate-scoped comparisons, not universal cue
weights or successful inverse training labels. Processing can introduce coupled
artifacts, and edit strengths are unequal. Post-generation QA found the footstep
filter is nearly an identity edit (-59.5 dB difference RMS relative to the
reference), while the attack edit is substantial; it remains as a sanity check.
Do not interpret its outcome as a universal attack/texture weight. See [protocol](evaluations/cue-calibration-v1-protocol.json).

Cue feedback is now retained: all five preferred edits are very close. The
listener tolerates 25% longer brick/cloth and a two-semitone charm shift in these
specific contrasts. Matching gets 2/5 choices, preference and both CLAP variants
4/5. These are edited references, not successful synthesis.

An isolated `SoftPeriodicityObjective` replaces unstable hard pitch decisions
with continuous short-time autocorrelation maps and motion. It fixes the nearly
unchanged footstep failure and passes self-distance, register, sweep and batching
checks. Historical strict agreement improves 91/162 to 108/162; latest calibration
remains 2/5. Across all167 comparisons,34 improve and17 worsen. The original
matcher/checkpoints remain untouched; this is an experimental search objective,
not a promoted selector or newly trained inverse. The report's gate field is
named historicalNonRegression but checks all167; the separately audited historical
subset also passes. See [evaluation](evaluations/soft-periodicity-v1-evaluation.json).

The [new five-trial listening comparison](runs/soft-periodicity-v1-listening/index.html)
compares equal-budget actual-render searches: two identical starting controls,
256 mutation attempts per start under each objective, 5,120 attempts total.
Starting controls come from the prior training-preset search; each arm selects
its own best of two refined results. It also retains the most recent explicit
human best synth candidate (brick falls back one session because its latest
three options were all rejected). These are actual synth outputs, unlike the
preceding edited-original calibration. All twenty finalists replay exactly and
are rescored on the actual audition PCM. This tests the scoring change within
hybrid inversion, not new neural weights.

The [completed soft-search feedback](evaluations/soft-periodicity-quick-01-human-review.json)
marks the new Squishr footstep **very close** and the new Transfxr block-hit
**similar**. Only block-hit's chosen option was auditioned, so it creates no
strict comparisons against the others. Brick remains none-close; earlier cloth
is least-bad and the unchanged earlier Bfxr laser is similar. Six strict heard
pairs favor legacy/soft scoring 2/6 each and preference-neural-v2 4/6. This gives
one convincing reachable real-sound example while leaving selector reliability
and wider reproduction quality unresolved.

The earlier [candidate-coverage diagnostic](runs/tagged-coverage-v1-listening/index.html)
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

Human feedback on this diagnostic is now retained: new Squishr footstep is
similar, new Transfxr cloth only least-bad, original Bfxr retains block-hit and
laser as least-bad, and none of the brick options is close. Zero very-close
judgments. Matching distance agrees with 2/8 heard preference pairs; the frozen
preference scorer agrees with 6/8. This does not establish an intrinsic synth
limit. See the [human review](evaluations/tagged-coverage-quick-01-human-review.json).

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
