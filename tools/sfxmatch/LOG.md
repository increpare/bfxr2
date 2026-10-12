# Experiment log

One short entry per experiment: what was expected, what changed, the numbers,
the verdict. Newest first.

## 2026-10-10 — All 1,000,000 mixes through CLAP and the AudioSet model

**Change.** `tags.py encode`: each mix rendered once, both spectrograms made
in the render workers, both networks on the GPU, output stored per dataset
shard (2.1 GB in all). The three pages now draw on the full million.

**Numbers.** 47 sounds a second end to end, 5.8 hours; no failed renders.
GPU alone: CLAP about 190 a second at batch 32, EfficientAT about 115, so the
GPU, not rendering, sets the pace.

- CLAP tags: smallest bucket "door" 2,518, largest "cloth" 51,040.
- AudioSet: 326 of 527 labels now have a sound above 0.15 (213 from 20,000).
  Most confident: Boing 0.96, Squeak, Zipper, Static 0.95, Caw, Hoot 0.94.
- Most different 100: the hundredth pick is 0.58 from the rest (0.51 from
  20,000), so the bigger pool does reach further out. 18 are single sounds.

**Verdict.** Done. The stored vectors make any further tag list, threshold
or selection a matter of seconds.

## 2026-10-10 — Coverage pilot: uniform draws widen the set; hole recipes repeat

Expected uniform controls to reach beyond generators and interpolation to fill
CLAP holes. Added `mixcover.py`/`covereval.py`, source and mix gates (RMS ≥1e-4,
0.05–4 s), a Bfxr envelope cap, resumable shards and training support for
`generator=-1`. Rendered and embedded 20,000 rows, including 4,000 singles.

Compared with a fixed 455,000-row encoded `mix-1m` snapshot; its encoder is still
running. No failed encodings or misaligned shards.

| Strategy | Rows | Gap > 0.1 from reference | Source rejection | Repeated audio recipes |
| --- | ---: | ---: | ---: | ---: |
| both uniform | 8,000 | 48.3% | 15.9% | 0 |
| generator + uniform | 6,000 | 35.7% | 11.3% | 0 |
| hole interpolation/crossing | 6,000 | 26.2% | 3.0% | 4,098 |

Overall novelty: 37.9%. On 3,000 held-out queries, median gap fell
0.05704 → 0.05690 and p90 0.11110 → 0.11054. Four of 100 merged spread picks
came from the new set. Fixed same-label midpoint coverage rose 54.13% → 55.70%
using a quarter of endpoint cosine distance; the quarter-Euclidean-chord measure
stayed 0%. This sample/definition is not comparable to the handoff's 75%.
The 3,000 midpoints contain 2,466 unique endpoint pairs.

Hole rows missed their target by >0.11 in 94.1% of cases; 67.2% of bank targets
remained far from the merged set. The bank has 232 entries but only 162 unique
chords. Mining now deduplicates chords; bounded retries skip repeated endpoints
and infeasible durations (five selections skipped). Full per-synth rates and
measurements: `runs/cover-report.json`.

**Verdict.** Uniform draws justify more sampling. Hold the million-row budget:
the current 30% hole allocation repeats recipes in 68.3% of rows and rarely
lands at its target. Pilot a larger, diverse bank or a different filling method
first. These misses do not establish that the synths cannot reach the holes.

## 2026-10-10 — Judges tested on the 719 stored ratings; no listening

**Judges.** `judges.py` pairs every rated clip with its reference and asks
each judge which of two differently rated candidates it prefers.

| Judge | All (598 pairs) | Recordings (334) | Native (193) | Mixes (71) |
| --- | ---: | ---: | ---: | ---: |
| objective v2 | 72% | 64% | 86% | 76% |
| CLAP likeness | 80% | 73% | 90% | 86% |
| AudioSet-profile likeness | 80% | 75% | 87% | 80% |
| all three, standardised and added | 83% | 78% | 90% | 87% |

None is fitted to the ratings. The combined score rises steadily with rating
(mean -2.1 for clips rated 1, -0.3 for 2, +1.1 for 3, +2.6 for 4, +3.3 for 5)
and means the same on recordings as elsewhere (over-predicts them by 0.06).

**Choosing was never the problem on recordings.** Across 110 rated sets the
average candidate was 1.69 and the best one shown averaged 2.32. Each judge's
first choice would have been rated 1.85 (objective) to 2.03 (combined).

**Is a close match in the library?** For each of the 50 benchmark recordings,
the best of 475,000 random mixes by the combined judge (CLAP and AudioSet
shortlist of 300, then the objective): expected rating 1.9 on average, none
of 50 reaching 3.5, one reaching 3 (a wing flap, Footsteppr + Whooshr). For
the 12 probe recordings it expects 1.96; their actual best-of-three ratings
were 2.2 to 2.6, so the prediction is, if anything, slightly low.

**Verdict.** Random sampling of Mixr does not land near these recordings, and
doubling the library will not change that. If close matches exist they are
rare settings that have to be steered to. The combined judge replaces the
objective for choosing between candidates; it is not yet tested as something
to search on.

## 2026-10-10 — Ratings: nearest library sounds by CLAP; and stop asking for ratings

12 probe recordings; the three nearest of 380,000 library mixes by CLAP
likeness, plus the round 2 anchor.

| Candidate | Mean | Rated 3+ |
| --- | ---: | ---: |
| CLAP neighbour 1 | 1.75 | 2 |
| CLAP neighbour 2 | 1.92 | 2 |
| CLAP neighbour 3 | 2.17 | 3 |
| Round 2 search (anchor) | 1.75 | 2 |

Best of the three neighbours: 2.50 (better than the anchor on 9, same on 1,
worse on 2). CLAP's own ranking of its three is backwards: its first choice
rates lowest.

**Verdict.** A fourth route to the same place. Search on two objectives, the
mix model, and CLAP retrieval all land between 1.8 and 2.6 on these recordings.

**Process.** The listener is tired of rating, and of re-rating these 12
recordings in particular: seven sessions and 719 clips in four days, five of
them on this set. That repeats the failure the original audit criticised. No
more rating pages for small variations. The 719 ratings are now the test set
for automatic judges (`judges.py`).

## 2026-10-10 — Ratings: the mix model on recordings, no search

12 probe recordings; the mix model's 96 proposals per recording, one chosen
by the objective and one by CLAP likeness; round 2's searched result as anchor.

| Candidate | Mean | Rated 3+ |
| --- | ---: | ---: |
| Mix model, objective's pick | 1.92 | 3 |
| Mix model, CLAP's pick | 1.83 | 2 |
| Round 2 search (anchor) | 1.92 | 2 |

Objective's pick against CLAP's: better on 3, same on 7, worse on 2. Best of
the three per recording: 2.33.

**Verdict.** No gain, and neither judge is better at choosing. The model has
only ever heard synth output, so this does not separate "cannot reach" from
"cannot find": its proposals on recordings score far worse by the objective
(3 to 7.7) than its proposals on Mixr's own sounds (2.7). Follow-up page
`probe-clap`: the three nearest of 380,000 library sounds by CLAP, which uses
neither the model nor the objective.

## 2026-10-10 — Ratings: Mixr reproduces its own output; searching on the objective makes it worse

40 frozen held-out Mixr sounds (`mixbench.json`), three blind candidates each.

| System | Two-source sounds (34) | Rated 4+ | Single sounds (6) |
| --- | ---: | ---: | ---: |
| Mix model, best of 24 proposals | 4.12 | 32 of 34 | 4.00 |
| Mix model + joint search (2,000 renders) | 3.88 | 26 of 34 | 3.67 |
| Single-synth model | 2.50 | 7 of 34 | 4.33 |

The mix model beat the single-synth model on 25 targets, tied 12, lost 3.

**The search result matters most.** Joint search lowered the objective on
every target (2.75 to 2.17 on average) and the listener rated the result
lower on 11, higher on 4, the same on 25. Worst case: a Jinglr sound went
from score 3.89 to 2.92 and from rating 3 to 1. Across the 120 clips rating
and score correlate at only 0.38.

**Verdict.** The gate is passed: a mix can be taken apart and rebuilt to
"close". And the objective is now shown to be the weak part: below a score of
about 3 it no longer points towards what sounds right. Every recording result
so far came from searching on it, so those results say little about what the
synths can reach. Do not refine model proposals with objective search.

## 2026-10-10 — First 200 species labels: do species form regions in CLAP space?

**Setup.** The listener filed 188 renders on the sorting page (`sort.py`),
mostly in discovery order, into 61 species with 295 assignments (101
renders carry two or more species); 19 of 142 two-source renders marked
incoherent. Automatic checks only, no listening.

**Numbers.** Leave-one-out: the nearest other labelled render shares a
species 61% of the time (3-nearest vote 48%). Per species it splits
cleanly. Tight, with a median chord between exemplars under 0.45 and a
nearest neighbour to the midpoint within a quarter of it on 90% of chords:
crash, strum, explosion, waves, bell, confirm, laser. Diffuse, median chord
0.75 to 0.9 and nearest-neighbour agreement near zero: engine, hit,
power-up, animal, alert, power-down, tear, swarm. Propagated to the million
at a cosine radius of 0.10, the tight species hold 7,000 to 24,000 renders
each and sit on the synths you would guess (explosion on Boomr, laser on
Zappr, choir on Choirr, teleport on Riftr, strum on Pluckr). The CLAP hint
named one of the listener's species in its top three on 44 of 104 renders
where the names coincide.

**Verdict.** As predicted: species named for what a sound is form regions,
species named for what a game would use it for, or umbrella names, do not.
Those need to be given as a list of tighter species, or named by hand on
top of regions found by ear. Nothing here fits an objective. Enough signal
to start the verify and chord queues on the tight species.

## 2026-10-10 — The 100 Mixr sounds least like one another

**Change.** `tags.py spread`: greedy farthest-point picks over the 20,000
cached CLAP vectors (cosine distance), starting from the most typical sound.
Blips under 50 ms are left out. Page `runs/pages/mix-spread`, with a
play-all button; sounds are filed under their nearest CLAP tag for navigation.

**Numbers.** Distance from earlier picks when chosen: 1.09 for the second,
0.78 for the tenth, 0.59 for the fiftieth, 0.51 for the hundredth. The most
typical sound stands for 15.6% of the set; 24 picks are single sounds (the
pool is 20% singles); every one of the 22 synths appears.

**Verdict.** A listening aid, not a measurement. Farthest-point picking
favours extremes, so it shows the edges of the range rather than what is
common; cluster centres would show the reverse.

## 2026-10-10 — Mixr: full model (1M mixes) and joint search

**Change.** 1,000,000 mixes (2 h 35 min to generate); the mix model
continued from the 200k one through 340k to the full set, about 2.5 hours of
training in all. Joint CMA-ES over both sources and the balance, 1,000 Mixr
renders from each of the two best differently-structured proposals.

**Numbers.** 300 held-out mixes, objective v2, floor 0.1:

| | Singles (69) | Pairs (218) | Same synth twice (13) |
| --- | ---: | ---: | ---: |
| Structure right first time | 97% | 93% | 69% |
| Mix model, one-shot | 2.90 | 3.00 | 3.86 |
| Mix model, best of 24 | 2.55 | 2.70 | 3.13 |
| Single-synth model, best of 24 | 2.25 | 3.70 | 3.59 |

On the 40 frozen mixes in `mixbench.json` (32 pairs): single-synth model
3.71, mix one-shot 3.31, best of 24 2.88, plus search 2.35. The mix model
beats the single-synth model on 85% of two-source sounds.

**Verdict.** Five times the data moved pairs from 2.87 to 2.70: useful, not
transformative, the same flattening as for single sounds. Search from the
model's proposal is the bigger step (2.88 to 2.35) and is nowhere near the
floor, so search on mixes is still the weak link. Awaiting ratings on
`runs/pages/mix-m1` before judging any of this on recordings.

## 2026-10-10 — The same 20,000 mixes against AudioSet's 527 labels

**Change.** `tags.py audioset`: EfficientAT mn10 (18 MB). A label is shown
once some sound reaches probability 0.15; each keeps its three most probable.

**Numbers.** 213 of 527 labels have at least one sound. Most confident:
Boing 0.92, Ringtone 0.89, Caw 0.88, Frog 0.86 (Riftr), Explosion 0.85
(Boomr), Ding, Clang, Machine gun 0.84 (Swarmr), Zipper 0.83. "Music"
swallows 8,924 sounds and "Explosion" 1,363.

**Gotcha.** The model needs ten-second input. On anything shorter it returns
logits near 100 and probability 1.0 for unrelated labels. Padding with
silence works and reads as a one-off event; looping the clip makes nearly
everything "Music". Adding a noise floor does not help.

**Verdict.** Complements CLAP: fixed vocabulary, but finds things nobody
would think to ask for (frog, zipper, machine gun). Page:
`runs/pages/mix-audioset`.

## 2026-10-10 — Mixr: full mix model (1M mixes)

**Change.** Continued the 200k model on 340k and then on the full 1,000,000
mixes (4 epochs, 96 minutes).

**Numbers.** 300 held-out mixes, objective v2 (floor 0.1):

| | Singles (69) | Pairs (218) | Same synth twice (13) |
| --- | ---: | ---: | ---: |
| Structure right first time | 97% | 93% | 69% |
| Within six guesses | 100% | 98% | 85% |
| Mix model, one-shot | 2.90 | 3.00 | 3.86 |
| Mix model, best of 24 | 2.55 | 2.70 | 3.13 |
| Single-synth model, best of 24 | 2.25 | 3.70 | 3.59 |

The mix model beats the single-synth model on 85% of two-source sounds
(79% at 200k). Validation: structure exact 91.4%, kind 96.6%. Validation
loss stopped improving in the last epoch (4.349 then 4.350) while training
loss kept falling, so more passes over this data will not help.

**Verdict.** Structure is close to solved; controls are not (2.7 against a
floor of 0.1). Singles are worse than with the dedicated single-synth model.
Awaiting the listening page over `mixbench.json`, which adds joint search.

## 2026-10-10 — Pretrained audio taggers against the hand-tagged files

441 readable files, 34 tags ('step' counted as 'footstep', the one 'misc'
file left out). Always guessing "footstep" scores 12%.

| Model | Zero-shot top-1 | Zero-shot top-3 | Nearest neighbours |
| --- | ---: | ---: | ---: |
| Microsoft CLAP 2023 | 34% | 57% | 64% |
| LAION-CLAP larger | 23% | 45% | 66% |
| LAION-CLAP base | 20% | 43% | 67% |
| AST (AudioSet labels only) | – | – | 57% |
| PANNs CNN14 (AudioSet labels only) | – | – | 37% |

Zero-shot picks the tag whose plain description is nearest the sound.
Nearest neighbours is leave-one-out over the files themselves (5 nearest,
tags with 5+ files). PANNs called nearly every file "Music"; it may simply
handle very short clips badly, which I did not investigate.

**Verdict.** Describing these tags in words is unreliable: the tags say what
a sound is for in a game, and short game sounds all look alike to a model
trained on recordings ("a cartoon jump" swallowed footsteps, birds and
swords). Tagging by example is much better and barely depends on the model.
AST's own labels are too generic to use ("Sound effect", "Boing", "Beep").
Prompt wording moved zero-shot by several points; I changed it once, to
drop "video game" from the descriptions, and did not tune further.

## 2026-10-10 — Sorting random Mixr sounds into game-audio tags with CLAP

**Change.** `tags.py`: 20,000 random mixes from the training set, 55 tags
written as phrases, `laion/clap-htsat-unfused`. Each sound goes to the tag it
matches most unusually well (scores standardised per tag); each tag keeps
its three best, from different pairs of synths.

**Numbers.** All 55 tags filled. Smallest bucket "door" (42 sounds), largest
"cloth" (1,026). The winners follow the synths' intent without being told:
explosion picks Boomr mixes, bubbles Squishr, choir Choirr, plucked string
Pluckr, wind Footsteppr, sword Whooshr pairs. About 13 sounds a second on CPU.

**Verdict.** Works as a browser of what Mixr makes. Not yet checked against
the 446 hand-tagged recordings, so how often CLAP's tag is the right one is
unmeasured. Page: `runs/pages/mix-tags`; presets downloaded from it replay
bit-identically through Mixr (12 of 12).

## 2026-10-10 — Mixr: first mix-aware model (200k mixes)

**Why.** The owner disputes that recordings are out of reach and points at
Mixr as by far the richest synth. He is right that it was barely tested: the
single-synth model has never seen a mix, and the two-layer probe searched
only a second layer on top of a frozen first one. Stackr and the retired
synths are gone from master; their bridges here were deleted.

**Change.** Real Mixr rendering in the fast renderer (bit-identical to the
sandboxed one). `mixdata`: every pair of the 22 sources equally likely,
including a synth with itself, one row in five a single sound, balance set
from a random level difference so both sources are audible. `mixmodel`:
multi-label "which synths", per-synth heads conditioned on the partner,
order-free loss for the same synth twice, balance head.

**Numbers** after 200,000 mixes and 30 minutes, on 240 held-out mixes,
objective v2 (true controls with new noise seeds score 0.11):

| | Singles (52) | Pairs (179) | Same synth twice (9) |
| --- | ---: | ---: | ---: |
| Structure right first time | 98% | 87% | 56% |
| Mix model, best of 24 | 2.76 | 2.87 | 3.55 |
| Single-synth model, best of 24 | 2.30 | 3.69 | 3.33 |

The mix model beats the single-synth model on 79% of two-source sounds. It
is overfitting at this size (train loss 3.8, validation 5.0), so the 1M run
should help more than it did for single sounds.

**Verdict.** Mixes can be taken apart. Next: the full 1M model, joint search
from its proposals, and a listening page over the frozen mixes in
`mixbench.json`. Only if Mixr's own output comes back "close" is it fair to
judge it on recordings.

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
