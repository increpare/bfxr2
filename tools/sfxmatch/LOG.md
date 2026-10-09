# Experiment log

One short entry per experiment: what was expected, what changed, the numbers,
the verdict. Newest first.

## 2026-10-09 — Ratings: milestone m1, two-layer probe, guided sessions

**m1** (mean likeness; external excludes the 12 probe targets):

| System | External (38) | Probe (12) | Native (43) |
| --- | ---: | ---: | ---: |
| new search | 1.71 | 1.75 | 4.00 (74% rated 4+) |
| new one-shot | 1.76 | 1.42 | 3.81 (67%) |
| old branch pipeline | 1.37 | 1.42 | 3.28 (49%) |
| original Bfxr | 1.39 | 1.58 | 1.35 |

On all 50 external targets search beat the old branch on 19, tied 26, lost 5;
against one-shot it won 15, tied 24, lost 11. One external clip in 200 was
rated 4 for each new system. Search has no result for nat-025.

**Two layers.** 1.67 against 1.58 for the single-synth anchor: better on 2,
equal on 9, worse on 1. No real gain.

**Guided search.** 18 rated sessions on external targets, one to two minutes
and one to nine screens each: fourteen 2s and four 3s (mean 2.2), every one
marked "stuck". On the 12 probe targets that is 2.33, level with automatic
search's best-of-three (2.58) and no better.

**Verdict.** In-domain the system works: native sounds come back "close" or
better three times in four, and one forward pass of the model is nearly as
good as 7,000 renders of search. On recordings, three objectives' worth of
search, layering and the listener's own ear all stop at 2 to 3. The limit is
what these synths can produce, not how we look for it.

## 2026-10-07 — Inverse model on the full 1M

**Change.** Topped the dataset up to 1,000,000 examples and continued the
645k model for 3 more epochs (65 minutes).

**Numbers.** 440 held-out native sounds, objective v2 (a random preset of the
right synth scores 8.8; these are not comparable with the v1 table further down):

| | 645k | 1M | old MLP |
| --- | ---: | ---: | ---: |
| Validation loss | 2.004 | 1.929 | – |
| One-shot, mean distance | 2.60 | 2.53 | 3.70 |
| Best of 24 sampled | 2.13 | 2.11 | 3.26 (best of 44) |
| Beats old MLP one-shot on | 83% | 86% | – |

**Verdict.** A small gain, as the scaling curve predicted. `runs/model-1m` is
the current model; the m1 benchmark systems were produced with the 645k one.

**Note.** A few Bfxr draws render for minutes (very long, overtone-heavy
sounds) and stall their shard, because the fast worker has no render timeout
and the pool waits for every task. One shard took 23 minutes. Cap sound
length at sampling time before generating more.

## 2026-10-07 — Two-layer probe (not yet rated)

**Question.** Does mixing in a second synth, as Mixr does, extend reach?

**Setup.** Layer A is one of round 2's three single-synth results; layer B
(2 synths x 1,500 renders per base) and the balance are searched under v2.

**Numbers.** Mean objective on the 12 probe targets: 2.90 single, 2.70 with
two layers; lower on all 12, by 0-15%. In three cases the balance is above
0.9, so the "second" layer has effectively replaced the first.

**Verdict.** Pending ratings (`runs/pages/layers-probe`). On the calibration
below, a 0.2 drop in score is worth a fraction of a rating point, so do not
expect much.

## 2026-10-07 — What a score means

Across the 108 clips rated in the two reach probes, rating and v2 score
correlate at 0.44 (Spearman). Mean score by rating: 4.40 for 1, 3.43 for 2,
2.86 for 3, 2.41 for 4. Clips scoring under 2.5 were rated 3 or better 46%
of the time; above 3.5, 4% of the time. On the benchmark the light search
gets under 2.5 on 9 of 50 external targets and 40 of 43 native ones.

## 2026-10-07 — Milestone m1: all systems on the frozen benchmark (not yet rated)

Mean objective v2 (lower is closer) from each system's saved audio, and the
share of targets where it is the closest:

| System | Renders per target | External (50) | Native (43) |
| --- | ---: | ---: | ---: |
| new search (library + model seeds, CMA-ES on 3 synths) | about 7,200 | 3.21, best on 96% | 1.34, best on 86% |
| library seed only (no optimisation) | about 1,150 | 3.71 | 1.53 |
| old branch pipeline | about 300 | 4.04 | 1.95 |
| new one-shot (model only) | 24 | 4.81 | 1.95 |
| original Bfxr | 2,000–3,000 | 5.67 | 5.15 |

The objective is the search's own target, so these numbers favour the search
systems by construction; only ratings settle it. Listening page:
`runs/pages/m1` (served at `/pages/m1/` by `sfxmatch.guided`). Note that
search does not recover native presets exactly (1.34 against a floor near 0).

## 2026-10-07 — Listener-guided search (tool built, no rated sessions yet)

`python -m sfxmatch.guided`: pick the nearest synth, then keep picking the
closest of six (the current sound plus five alternatives the objective rates
about as good, chosen to sound different). About 2 s per screen. Purpose: a
session that reaches "close" proves reach; one that stalls is the best
evidence of a limit. Sessions without a final rating are play, not data.

## 2026-10-07 — Retrieving by the model's embedding

**Expected.** The CNN's 512-d embedding should be a better index than the
raw whole-sound spectrum, since it was trained to separate control settings.

**Numbers.** Best seed score among 96 neighbours, v2 objective: external
4.25 by embedding (cosine) against 3.99 by raw spectrum, better on 3 of 12;
native 1.37 against 1.37. L2 instead of cosine changes nothing.

**Verdict.** No. Raw spectrum plus a duration term stays the index.

## 2026-10-07 — Reach probe, round 2 (objective v2)

**Question.** Does fixing the spectral blind spot make heavy search land closer?

**Setup.** Same 12 recordings and budget as round 1, objective v2, seeds from
the 645k model. Round 1's best candidate was replayed blind as an anchor.

**Result** (mean likeness, n = 12 each):

| System | Mean | Rated 3+ |
| --- | ---: | ---: |
| round 2, best synth | 2.25 | 3 |
| round 2, 2nd synth | 2.08 | 5 |
| round 2, 3rd synth | 1.75 | 3 |
| round 1 best, replayed | 2.08 | 4 |

Best of three per target rose from 2.17 to 2.58: five 3s and one 4, no 1s
(round 1: two 3s, one 4, two 1s). Against the anchor in the same session,
round 2's best was better on 4 targets, equal on 6, worse on 2. The anchor
itself drifted from 1.83 to 2.08 between sessions, so compare within a session.
The search cut mean spectral error from 11.8 dB to 7.2 dB at the same gesture
score. v2 agreed with 67% of round 2's 46 strict pairs, its first independent
test; the 82% on round 1 was optimistic.

**Verdict.** A modest, real gain; still "same family" to "roughly similar",
never "close" for the top pick. Two objectives and about 42,000 renders per
target have not produced a close match to a real recording, so more search
budget is not the answer. What remains open is whether the synths cannot make
these sounds or the objective cannot find them. A listener-guided search
(listener picks, system mutates) would settle that.

## 2026-10-07 — Where good seeds come from

Best seed score under v2 on 12 external and 8 native targets:

| Seeds | External | Native |
| --- | ---: | ---: |
| 96 model proposals (6 synths x 16) | 4.27 | 1.63 |
| 96 library neighbours (about 4 per synth) | 3.99 | 1.37 |
| 1,056 library neighbours (48 per synth) | 3.77 | 1.32 |

The model beat the 96 neighbours on 5 of 12 external and 1 of 8 native
targets. **A nearest-neighbour lookup in the 645k library is at least as good
a seed source as the trained model.** The model is far better than the old
MLP, but for seeding a search the library is the asset. The model earns its
place only where a library cannot go (one forward pass, about 100 MB).

## 2026-10-07 — Reach probe, round 1 (objective v1)

**Question.** With compute no longer the constraint, can the synth pool get
close to external recordings?

**Setup.** 12 benchmark recordings. Seeds: 48 nearest library rows per synth
plus 96 model proposals. CMA-ES on the 4 best synths, 2 restarts of 2,500
renders each (about 21,000 renders per target). Listener rated the best three
synths' results blind, next to the old branch pipeline and original Bfxr.

**Result** (mean likeness, 1–5, n = 12 each):

| System | Mean | Rated 3+ |
| --- | ---: | ---: |
| search, best synth | 1.83 | 2 |
| search, 2nd synth | 1.75 | 2 |
| search, 3rd synth | 1.33 | 0 |
| old branch pipeline | 1.42 | 1 |
| original Bfxr | 1.17 | 0 |

Best candidate per target: one 4 (velcro rip, Rustlr), two 3s (monster roar,
mini jump), seven 2s, two 1s (error thump, slime).

**Verdict.** Heavy search beats both old pipelines but is nowhere near
"close". The search was not the limit: the objective was. On the slime
target every result was about 25 dB too loud below 800 Hz and v1 barely
charged for it; on velcro v1 ranked the candidate rated 4 below one rated 2.
Led directly to objective v2.

## 2026-10-07 — Objective v2 (gesture + audible spectrum)

**Change.** Added a multi-scale log-mel distance, weighted by audibility so
silent stretches cannot dilute it, to soft-periodicity. Weight set in
advance (10 dB mean error = 1.0), not fitted.

**Numbers.** Agreement with the 270 archived pairs: 64.4% (v1 64.4%).
Agreement with the 61 strict pairs from reach-probe round 1: 82% (v1 75%);
this set motivated the change, so it is not an independent test. Among the
five round-1 candidates per target, v2 ranks first one rated 2.08 on average
(v1 1.83, best available 2.17).

**Lesson.** Archived pairs compare finalists of earlier searches, which
already matched the spectrum, so pairwise agreement could not show what an
objective does when it drives a search. Check what the optimum sounds like.

## 2026-10-07 — Inverse model at scale

**Expected.** The old shared MLP (51,200 examples, hand-made features,
parameter regression, under 5 minutes of training) was starved; more data and
a spectrogram model should help a lot.

**Change.** `FastRenderer` (4.7x faster, bit-identical), 645,000 examples at
100–270 rows/s depending on machine load, CNN on log-mel, synth classifier
plus 32-bin distributions per control, feature-domain augmentation.

**Numbers.** Held-out native sounds, judged by re-rendered audio under
objective v1 (lower is closer; a random preset of the right synth scores
6.4, the true controls with a different noise seed score 0.00 at the median):

| | 220k, 29 min | 470k, 61 min | 645k, +56 min | old MLP |
| --- | ---: | ---: | ---: | ---: |
| Validation loss | 2.190 | 2.048 | 2.004 | – |
| Synth identified | 99.6% | 99.8% | 99.8% | – |
| One-shot, mean distance | 2.22 | 2.11 | 2.09 | 2.85–2.90 |
| Best of 24 sampled | 1.85 | 1.76 | 1.72 | 2.51–2.55 (best of 44) |

The first two columns use 176 sounds, the last 440. The 645k model beats the
old MLP one-shot on 82% of sounds and best-of-24 against best-of-44 on 92%.

**Verdict.** Clear win over the old model. Returns from more data are now
small (2.22 to 2.09 for 3x the data), and one-shot is still far from exact
(2.09 against a floor near 0), so the next gain on native sounds is local
refinement from the model's proposal, not a bigger dataset. Worst engines:
Glitchr, Jinglr (its melody text cannot be predicted), Bfxr.

## 2026-10-07 — Renderer speed

Loading the synth sources into Node's main realm instead of a `vm` context
is 4.7x faster on average (up to 18x for Footsteppr and Pluckr) with
identical samples for 308 of 308 test renders. JSON and base64 encoding was
about 1 ms per render, so a binary protocol would not have helped.

## 2026-10-07 — Baseline of objectives against archived judgments

270 strict pairs from the 32 archived sessions. Agreement: soft-periodicity
64.4%, preference-neural-v2 65.2% (fitted on some of these), auditory-v1
57.8%, legacy contour 56.3%, plain log-mel 55.6%. On sessions from 10-05
onward (147 pairs) nothing exceeds 60%.
