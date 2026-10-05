# Expanded-coverage multi-patch experiment

The new four-patch expert supplies useful additional numerical matches, but does
not replace the older models. The five tagged recordings still have no selected
median pitch within one semitone. Human listening is required before interpreting
any numerical gain as convincing reproduction.

## Controlled training

Both arms start from the frozen expanded Transfxr checkpoint and receive the same
4,000 updates, learning rate, normalization and independently seeded identical
minibatches (64 native + 64 structured). No new audio or feedback is added to
training. The single arm retains one complete control prediction; the mixture
arm predicts four complete patches. Earlier categorical beams vary discrete
wave/curve choices but share one set of numeric controls.

The mixture copies the encoder and first head exactly; seeded 0.02 weight noise
breaks symmetry in its other three copied heads. Existing mixture acoustic loss
and routing regularization are unchanged. Checkpoints are selected using original
balanced validation loss including step zero, not transfer-test scores. Single
selects step 2,400; mixture selects 3,800. All four heads remain active (roughly
19%, 32%, 32%, 18% validation posterior mass). Differently shaped mixture losses
are not compared as a measure of audible success. Training ran on local MPS;
inference and the validation replay use CPU.

## Actual synthesis, four proposals per arm

| Evaluation scope | Frozen expanded | Retrained single | Retrained four-patch |
| --- | ---: | ---: | ---: |
| 32 additional native validation controls | 4.67184 | 4.93848 | 4.01860 |
| 21 other-synth references | 8.02898 | 7.20118 | 7.51322 |
| 5 repeated tagged recordings | 8.81975 | 8.67875 | 8.00562 |
| 8 previously tested clean native controls | 3.63146 | 4.12020 | 3.03325 |

Values are mean actual-render matching distance, not absolute likeness ratings.
The four-patch model beats frozen expanded on 22/32 additional native targets and
matched retrained single on 23/32. Among 20 reliably tracked native targets, nine
selected medians are within one semitone for each retrained arm, versus five for
frozen expanded. Shared training preset families remain a limitation; these are
new control groups from an already monitored validation population.

On other synths, the mixture wins 17/21 individual comparisons against frozen
expanded, but the retrained single has the better overall mean. Its Footsteppr
match improves strongly while the mixture's remains poor. Both regress badly on
the Bfxr-source example. A single example per source synth is not an engine ranking.
The published earlier transfer ensemble contains an additional old expert; the
frozen-expanded column here is only its expanded member, not that stronger bundle.

Seven altered-input groups use the same eight base sounds as the earlier transfer
experiment. Compared with frozen expanded, mixture mean distance improves for
MP3-32k, MP3-96k, PCM8, low-pass and both transpositions; high-pass worsens
5.83737 to 6.07896. These altered variants share source families and are correlated.
The known good clean warble and texture also regress. No codec/filter invariance
or general real-recording success is inferred.

All 122 targets produce four audible candidates per arm with no missing slots.
The mixture produces four distinct numeric parameter settings per target, while
both single-head arms produce one. There is no local search in this experiment.
Older experts and exact historical human evidence remain available.

## Listening selection

Six comparisons are deliberately selected after inspecting outcomes, with the
selection reasons stored in `evaluations/native-mixture-v1-listening-targets.json`:

- A new mild rise where distance and pitch diagnostics agree on improvement.
- A new wide sweep where aggregate distance improves but contour error worsens.
- Footsteppr transfer from the retrained single expert.
- Boomr transfer from the mixture versus the exact previous human winner.
- Low-pass filtered bouncing rise, not previously judged in that altered form.
- A regression check on the previously very-close clean warble.

The first two use the frozen expanded-four comparison. Footsteppr and filtered
rise use the earlier eight-proposal guarded ensemble. Boomr and warble replay
exact archived audition PCM. These listening comparisons diagnose complete
outputs; their varying historical baselines do not isolate an architecture effect.
They are not a representative six-item quality-rate estimate. The tagged real
outputs still miss pitch badly, so they are not sent for another repetitive rating.

New galleries collect absolute likeness immediately after each best/tie, with
same-reference replay. None/skip advance directly. Original submissions remain
unchanged and unknown historical absolute likeness stays unknown. Never ask for
retrospective reconstruction of anonymous choices.

## Reproducibility

Models, original histories, frozen targets and all FLOAT render WAVs are retained
under `runs/native-mixture-v1`. Training/evaluation modules are
`tools/neural_invert/coverage_mixture.py` and `coverage_mixture_eval.py`.
`evaluations/native-mixture-v1-audit.py` binds targets to the exact frozen list,
checks dataset exclusions, replays selected DSP audio and rescores it, and
recomputes original validation losses on CPU. The JSON audit records the observed
counts and numerical discrepancies; descriptor pitch is not independently
re-estimated by that audit. The listening exporter separately verifies selected
DSP replay, exact archived PCM, one audition transform and distinct alternatives.

Completed audit: 1,586 file/PCM checks, 366 selected DSP replays, zero rescore
error; CPU validation loss agrees within 4.3e-8. 47 focused tests pass. HTTP
delivers the exact HTML, results and all 18 audition WAVs. Browser shows six
unanswered comparisons with playback ready; no assistant listening judgments or
audition telemetry were entered.

Listening page: `runs/native-mixture-v1-listening/index.html`, experiment
`31d337163dcb3009bbebbdcbb95efa25cdea449820209b96414e1cf2273eb5f6`.
Await human quality feedback before promoting the new expert or changing ranking.
