# First multi-synth approximation experiment — 2026-10-03

Working baseline: a nonparametric inverse library plus per-synth search and an
automatic selector. No neural network was trained. Everything is isolated on
`codex/multisynth-approximation`, based on `d7fc918`.

## Experiment

- **3,648 exemplars**, 16 draws per preset, across **22 active synths**.
- Original recipe draws mixed with shorter/longer variants; **0 rejected renders**.
- Build seed **1729**, four render workers, **90.4 seconds** to build.
- **40 real targets from 19 source collections**, selected with seed **1234**
  from the local `tools/targets_non_bfxr_big`; files 25 ms–4 s, normalized
  duplicates rejected. The `tags` directory is also a source collection.
- Five retrieved synths per target, plus Bfxr when it is not already among them;
  four retrieval seeds per synth; **64 additional evaluations per expert**.
- **14,912 search renders**, plus **233 export replays**. Benchmark matching
  took **1,198.8 seconds**; median per target **19.5 seconds**.
- The target corpus was not used to generate the model library. Filenames/tags
  did not enter descriptors or selection scores.

Reproduce from `tools/`:

```sh
uv run python -m multisynth.cli build -o multisynth/runs/library-v1 --per-preset 16 --jobs 4
uv run python -m multisynth.cli benchmark /path/to/targets_non_bfxr_big \
  --library multisynth/runs/library-v1 -o multisynth/runs/real-v1 \
  --count 40 --max-seconds 4 --budget 64 --experts 5 --seed 1234 --all-collections
uv run python -m multisynth.audit multisynth/runs/real-v1
```

## Findings

Under the new auditory descriptor distance, a non-Bfxr synth wins on **33/40**
targets. Bfxr remains the winner on seven. Median distance reduction relative to
the same run's Bfxr expert is **23.0%**; mean is **25.3%**. These percentages are
**not percentages of audible similarity**.

| Selected synth | Targets |
| --- | ---: |
| Bfxr / Clonkr | 7 each |
| Transfxr | 5 |
| Machinr | 4 |
| Crittr / Riftr | 3 each |
| Whooshr / Bouncr / Squishr | 2 each |
| Choirr / Signlr / Zappr / Boomr / Fractr | 1 each |

The selector can use a synth outside the obvious semantic category: Clonkr wins
a bass-drop reference and Zappr wins a grass-footstep reference. This is an
interesting source of preset candidates, not proof that those matches sound
convincing.

### Independent metric check

Re-scoring the saved winners with the pre-existing contour objective (which was
not used by this run) produces **18 wins / 7 ties / 15 losses** against Bfxr.
Median contour distance is **8.514** for multi-synth winners versus **9.003** for
Bfxr. This mixed agreement limits the result: it does not establish consistent
perceptual improvement. Both metrics can be wrong. The subsequent human pass
below found poor likeness despite these metric gains.

The Bfxr noise-seed audit repeats each chosen Bfxr candidate with the search seed
and two held-out seeds. The largest distance range is **0.122**, on a Minecraft
footstep target; a knife target varies by **0.078**, and the remaining candidates
show no variation in this audit. This checks final candidates at two additional
seeds, not all potential noise realizations.

### Comparison limits

Multi-synth search uses a larger library and more total renders. Bfxr receives
the same per-preset sampling count and per-expert refinement budget, but this is
not an equal-compute comparison. The old neural-seeded Bfxr matcher was not run
as a competing system. Because Bfxr is retained as a candidate, non-worsening
under the selection metric is built in; the observed margins and selected synth
mix are the useful measurements.

## Local deliverables

- `runs/library-v1/`: reusable saved inverse model, canonical parameters and
  source/feature provenance.
- `runs/real-v1/index.html`: all 40 reference/winner pairs with links to every
  finalist's audio, parameters and score components.
- `runs/real-v1/winners.bcol`: 40 editable recreations; each target also has a
  `matches.bcol` containing its alternative synths.
- `runs/real-v1/six-pairs.wav`: 22-second shortlist, reference then recreation:
  punch, bass drop, glass hit, synthetic frog, thermometer beep, grass footstep.
  Chosen to illustrate different effects; it is not a blinded quality sample.
- `manifest.json`, `results.json`, `audit.json`: target hashes, model identity,
  budgets, traces, objective measurements and noise-seed checks.

Scratch generated artifacts remain ignored and local; the subsequent listening
archive retains versioned copies of judged audio. No synth or
preset source on the parallel `claude/determined-sagan-khz12h` branch was edited.
After integrating newer DSP changes, rebuild the library; stale source hashes
are rejected.

## Verification

The focused suites contain **11 Python tests and 5 Node tests**. They cover
actual rendering, all Footsteppr terrains, reproducible
replay, parameter schemas, objective orderings, library persistence, budget and
incumbent invariants, audit source identity, and collection consumption by the
real app importer with inert UI hooks. Final Python suite: **200 passed,
19 skipped, 6 deselected** (one existing PyTorch warning). Final focused Node
suite: **5 passed**. Full Node suite: **419 passed, 1 inherited failure**.

The full app suite at this branch point has an existing Mixr catalog assertion
expecting Breathr where the recipe uses Whooshr. It also fails in a pristine
archive of `d7fc918`; this work leaves it unchanged.

## Human listening follow-up — 2026-10-03

The user rated all 40 reference/model/Bfxr triples in the labeled gallery.
This was not blinded. There are **73 unique rated candidates** after accounting
for seven shared Bfxr/model selections. The raw JSON, parameters, provenance,
and exact audition audio are retained in
[listening_data/2026-10-03-real-v1/manifest.json](listening_data/2026-10-03-real-v1/manifest.json).

| Measure | Result |
| --- | ---: |
| Mean selected likeness (1–5) | 2.0 |
| Mean Bfxr likeness (1–5) | 1.6 |
| Selected ratings 1 / 2 / 3 / 4 / 5 | 13 / 17 / 7 / 3 / 0 |
| Selected wins / ties / losses against Bfxr | 15 / 21 / 4 |

**30/40 selected matches scored only 1–2/5.** Relative improvement over Bfxr
does not make this a successful perceptual model. The four human-preferred Bfxr
results include Mario's tail sound, a tagged motorcycle horn, a bass drop and
a sci-fi door opening. Do not promote the earlier illustrative shortlist as
listener-approved: even the bass drop lost to Bfxr in this feedback.

## Next experiment

Focus on the curated `tags/` directory, now preferred by the benchmark CLI.
The next target selection is frozen in
[evaluations/tagged-v2-targets.json](evaluations/tagged-v2-targets.json).
Treat reused rated references as development data, and check related takes
before calling the rest held out. No new model benchmark has been run yet.

Prioritize large-scale gesture and feel over exact contour fit: impacts,
build-up/release, rise/fall, pulse structure, weight and texture. Probe whether
plausible candidates exist before fitting a selector; a reranker cannot recover
a recreation absent from its candidate pool. Use these ratings for regression
and model development, with independent listening for validation. Collect fun
or game usefulness separately rather than infer it from likeness scores.
