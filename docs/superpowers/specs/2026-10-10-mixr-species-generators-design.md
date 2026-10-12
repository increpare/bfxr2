# Mixr species generators: labelling, propagation and mining

## Outcome

Mixr ships with a list of generators that each produce a recognisable kind of
game sound, the way Bfxr's "jump" button does. The list is mined from the
synth's own output, verified by the listener, and shipped in the recipe format
Mixr already has. No model runs in the browser; the artifact is kilobytes.

The same pipeline later gives the single synths better generators for free,
because every render the listener files under one source alone is evidence for
that source synth.

## Vocabulary

Terminology is part of the deliverable. Use these words and no others.

- **Synth.** A parametric DSP with a control space. Bfxr, Boomr, Mixr.
- **Patch.** One point in a synth's control space; what a `.bfxr` file stores.
- **Render.** The audio of a patch. "Sound" is not a term.
- **Generator.** What a button is: a distribution over one synth's control
  space. Each click draws a patch. The code's "preset", "template" and
  "recipe" all mean this; "preset" stays only as the user-facing word.
- **Species.** A perceptual kind: jump, coin, wet squelch. Defined only by
  its specimens, never by a mechanism. Species overlap; a render can belong
  to several.
- **Specimen.** A render filed under a species.
- **Specimen exemplars.** The listener-confirmed specimens that define a
  species. **Propagated specimens** are machine-assigned and provisional.
- **Role** and **character.** Two kinds of tag. A role is what a game uses
  the sound for: coin, jump, hurt, confirm. A character is what it is or
  sounds like: metallic, wet, rising, buzzy. A species name may be either.
- **Cell.** Synth A with one of its generators, synth B with one of its
  generators, and a balance interval. "Any generator" is allowed on a side;
  the shipped recipes are cells with "any" on both sides.
- **Purity** of a generator for a species: the share of its draws a listener
  would file under that species. **Spread**: how unlike one another its draws
  are, measured as mean pairwise cosine distance in CLAP space.

A generator targets one species. A species may have generators on several
synths. Synth is to generator as genus is to species, and "Bfxr jump" is a
binomial.

## What ships

A Mixr generator is a species name plus a list of cells, drawn uniformly
(generator names below are illustrative):

```json
{"id": "clockwork_aviary", "name": "Clockwork Aviary", "kind": "character",
 "cells": [{"a": ["Machinr", "generate_ratchet"], "b": ["Birdr", "generate_chirp"], "balance": [0.31, 0.49]},  
           {"a": ["Machinr", "*"],                "b": ["Birdr", "generate_trill"], "balance": [0.35, 0.55]}],
 "purity": 0.84, "spread": 0.41, "exemplars": ["mix-1m/0012/0345", "mix-1m/0031/0007"]}
```

Generators are named by their method name in the renderer's inventory
(`generate_*`, or `randomize_params` for Footsteppr), which is what Mixr's
`source.generator` already accepts. The mined list is written to
`tools/sfxmatch/generators/mixr.json`, with a sibling `mixr.js` snippet in
Mixr's `recipes` shape for pasting. Nothing under `js/` is edited by tools.

Tighter encodings inside a cell, per-source interval boxes or exemplar
families, are a fallback for a species whose cells all fail the purity bar
because only a corner of a source generator mixes well. Not built until a
species needs it.

## Data

- Embed renders from the existing `runs/mix-1m` shards until every cell that
  occurs has about ten embedded renders: roughly 200,000 renders. `tags.py
  encode` already caches CLAP vectors and AudioSet probabilities per shard and
  resumes; extend it to also embed each source rendered alone, which is what
  the coherence probe compares against.
- Audio for the page is rendered on demand by the guided server from the
  stored patches, with a small disk cache. Nothing is pre-rendered.
- Rows whose sources were perturbed (the `jitter` and `sparse` modes) still
  count as evidence for their cell. Mining measures purity on fresh,
  unperturbed draws, so the bias is removed where it matters.

## The sorting page

Served by `sfxmatch.guided` at `/sort`. One item is one render id.

- Plays: mix, source A alone, source B alone. Keys 1, 2, 3. Space replays.
- Tag entry with autocomplete over existing species; a new name creates a
  species. Each tag carries a kind, role or character, chosen once per
  species. Several tags per render.
- Negatives: mute, terrible, only A, only B. "Only A" files the A render,
  not the mix, as a specimen of the typed species on synth A, and marks the
  mix incoherent. Skip is allowed and recorded.
- Hints beside each item, never defaults: nearest CLAP tag, top AudioSet
  label, the cell.
- Queues, chosen per item or set for a session:
  - **discovery**: farthest from every labelled render in CLAP space,
    starting from the most typical render (the existing `spread` routine);
  - **typical**: centres of k-means clusters over the embedded set, nearest
    unlabelled render first, so the common mass gets named too;
  - **verify S**: propagated specimens of species S nearest its boundary
    (lowest nearest-neighbour margin), then random propagated specimens;
  - **random**.
  Discovery and typical alternate by default.
- Label store: `tools/sfxmatch/labels/*.jsonl`, append-only, one session per
  file, committed like ratings. A record is `{id, cell, scope, species,
  negatives, queue, seconds, time}` where scope is `mix`, `a` or `b`.
  Renaming or merging species is a rewrite of names in these files; ids never
  change.

## Propagation and the numbers

- Propagation: nearest neighbours in CLAP space, cosine, k = 5, from specimen
  exemplars to every embedded render; a render takes a species when at least
  three neighbours carry it. Multi-label.
- Leave-one-out precision and recall per species over the exemplars, printed
  as a table. A species below 0.6 precision with ten or more exemplars is
  flagged as scattered, not a region.
- Per-cell purity: share of the cell's embedded renders propagated to the
  species.
- Per-pair coherence: among labelled mixes of each synth pair, the share
  marked only A, only B or terrible. This table is the "which synths
  complement each other" answer.
- Coherence probe, automatic: a mix is carried by one source when that source
  alone is at least as near the species' exemplars as the mix is. Reported
  per cell; the listener's "only A" labels are the check on the probe.

## Mining cells into generators

For each species with at least ten specimen exemplars:

1. Candidate cells: every cell holding an exemplar, plus cells whose
   propagated purity is 0.5 or more.
2. For each candidate, draw 50 fresh patches through the real Mixr with the
   cell's balance interval, embed, propagate. Purity is the share landing in
   the species; spread is their mean pairwise distance.
3. Keep a cell when purity is at least 0.7 and exceeds the purity of either
   source's generator alone for the same species, measured the same way: 50
   draws from that generator on its own synth, embedded and propagated. A
   cell that fails only the second test is written to that source synth's
   candidate list instead.
4. Balance interval: the 10th to 90th percentile of exemplar balances,
   widened by 0.05 each side and clipped to [0, 1].
5. The generator is the kept cells; its purity and spread are draw-weighted
   means. Species with no kept cell are reported, not shipped.

## Sessions and stop conditions

Each session answers one question. Budget: the listener handles about 60
clips in 15 minutes; an item is three clips.

1. **Discovery, about an hour, about 150 items.** Produces the first species
   and the share of mixes that are incoherent or terrible by synth pair.
   Stop early if most items are negatives: that means the data's balance or
   generator mix needs changing before labelling continues.
2. **Verify, about 30 minutes.** Boundary items for every species with ten or
   more exemplars. Produces the scattered-versus-region table.
3. **Accept, one session.** Three draws per candidate generator, keep or
   drop. The kept list is what gets pasted into Mixr.

Further discovery sessions are worth running only while they keep creating
species; when a session creates none, the taxonomy has converged for this
data.

## Non-goals

No change to `sfxmatch.objective`, the benchmark, or the inverse models. No
text-to-sound feature in the app. No editing of `js/`. No new hand-written
taxonomy: species are born from exemplars, and the corpus and CLAP tags are
hints only.

## Testing

- Label store: append, read back, rename a species across files, ids
  untouched.
- Queues: discovery reproduces `spread` on a fixed embedding; verify orders
  by margin; typical returns cluster centres first.
- Propagation and mining on a synthetic embedding with planted clusters:
  precision and purity come out as planted, the coherence rule routes a
  one-source cell to the source synth.
- Render test: a mined generator's cells replay through the real Mixr, and a
  pasted `.bcol` from the page replays bit-identically (the existing check).

## Decisions taken

- Cells, not parameter boxes, are the unit of a Mixr generator.
- The taxonomy starts empty.
- Labels are multi-label with a kind per species.
- Purity and spread are the only numbers that judge a generator; likeness
  ratings stay with the matching benchmark.
