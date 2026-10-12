# Handoff: widen the Mixr sample set beyond the shipped generators

## Goal

Add about one million rendered patches that reach parts of parameter space
the current `runs/mix-1m` set does not, so that regions between and beyond
the shipped generators exist in the data. The new rows feed the same tools
(`tags.py encode`, the mix model, the labelling work) and must not disturb
the existing set.

## Facts about the current set (verified 2026-10-10)

- `sfxmatch/mixdata.py` draws every source patch from one of the synth's own
  generators (`renderer.sample(synth, preset, seed)` runs the shipped
  `generate_*` method), then applies a mode from `sfxmatch/dataset.py`:
  `original` 60% (untouched), `jitter` 25% (a third of the continuous
  controls nudged by N(0, 0.1) in unit range), `sparse` 15% (a sixth of the
  continuous controls redrawn uniformly, each categorical redrawn with
  probability 0.15). There is no uniform draw over a synth's parameter space.
- Consequence, measured on 422,000 CLAP projections: nearest-neighbour gaps
  shrink only like N^-1/6, the set is dense inside the generators' clumps
  and thin between them, and a quarter of midpoints between two renders of
  the same AudioSet label have no render nearby. More rows of the same kind
  will not fix this.
- `neural_invert/schema.py: ControlSchema` encodes a patch as a unit-cube
  vector plus categorical indices and decodes back onto an anchor patch. It
  has an unused `broad` mutate mode (half the controls redrawn). TEXT
  controls (Jinglr's melody) and Transfxr's KNOB_TRANSITION controls are not
  in the unit vector; they come from the anchor.
- Every row records the pair, each source's generator index and the mode.
  `mixbench.json` and the trained models depend on `runs/mix-1m` as it is.
- Bfxr draws with very long, overtone-heavy sounds can render for minutes and
  stall a shard (see LOG.md, 2026-10-07). Cap length at sampling time.

## What to build

Write to a new directory, `runs/mix-cover`, in the same shard format as
`mixdata.py`, with a `mode` value per row that names the new strategy, and
`generator = -1` where no generator was used. Keep the one-in-five singles
share and the current pair and balance logic unless a strategy says
otherwise.

**A. Uniform draws.** For a source: take an anchor from a random generator
(for the TEXT and transition fields), then decode a uniform unit vector and
uniform categoricals onto it. Expect a lot of silence, clicks and
ear-splitting output; gate on audibility (RMS above a floor, length between
about 0.05 s and 4 s) and log the rejection rate per synth. Rejected rows
are not stored. Mixes: both sources uniform, or one from a generator and one
uniform, so existing good sounds also get unfamiliar partners. Pilot about
20,000 rows and look at the rejection rates and the gap statistics before
committing the full budget; tentative split 40% uniform-uniform, 30%
generator-plus-uniform, 30% hole filling.

**B. Hole filling.** A hole is a midpoint in CLAP space whose nearest
embedded render is farther than about 0.11 cosine (the current 90th
percentile gap). Find candidates among pairs of renders that share an
AudioSet label or CLAP tag and sit within about 0.5 of each other. To fill:

- Same synth, single sound: interpolate the continuous controls linearly in
  unit space at a few points along the chord, take each categorical and TEXT
  control from one endpoint at random. Render, store.
- Mixr, same pair of synths: interpolate each source as above and the
  balance.
- Mixr, different pairs: there is no chord in parameter space. Two cheap
  substitutes: cross the ingredients (source A from one endpoint with source
  B from the other, balance between), and interpolate only the shared synth
  when the pairs overlap. Otherwise skip the hole and count it.

Filled rows whose projection still lands far from the hole are evidence
that the hole is in what the synths can make, not in the sampling. Store
them anyway and report how often that happens.

**C. Optional, if time allows: targeted search.** For holes that A and B
cannot reach, CMA-ES over the nearest synth or pair with the objective
`1 - cos(CLAP(render), hole)`. This needs CLAP in the loop, about 13
renders a second on CPU and much faster on the GPU, so budget it per hole
and run it in the background. Do not touch `sfxmatch.objective`.

## How to judge it

Report before and after, on a held-out query set of 3,000 projections:

- median and 90th percentile nearest-neighbour gap;
- share of same-label midpoints whose nearest render is within a quarter of
  the chord (was 75% at 422,000 rows);
- share of new rows farther than 0.1 from everything in `runs/mix-1m` (new
  territory rather than duplicates);
- rejection rate per synth and per strategy;
- how many of the 100 farthest-point picks (`tags.py spread`) now come from
  the new set.

Embed with `tags.py encode --data sfxmatch/runs/mix-cover`; its cache is
keyed by the data directory name.

## Rules

Never edit `js/`. Run from `tools/` with `uv run`. Do not modify
`runs/mix-1m`, `mixbench.json` or the trained models. Tests in
`tests/test_sfxmatch.py` for the new sampling and interpolation code. One
entry in `sfxmatch/LOG.md` per experiment, nothing else. `runs/` is never
committed.
