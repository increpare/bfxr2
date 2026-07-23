# bfxr2 offline tools

Offline tooling for bfxr2. Nothing here ships with the web app — the synth
sources under `js/` are loaded unmodified (read-only) by a headless renderer.

Current contents: the **wav→bfxr matcher** — give it a sound file, it searches
Bfxr's 30-dimensional parameter space for the closest-sounding bfxr sound and
emits an app-loadable `.bfxr` file. It is also the foundation (batch renderer,
perceptual distance) for mining tag-labeled preset regions later.

## Setup

Requires `node` (any recent version), a C++17 compiler, and [`uv`](https://docs.astral.sh/uv/).

```sh
cd tools
make -C bfxr_native                  # fast native renderer (preferred)
uv sync --extra report --group dev   # torch CPU build; first sync is big
```

Matching/rendering prefers `bfxr_native/build/bfxr_worker` when present. Set
`BFXR_RENDER_NATIVE=0` to force the Node worker (oracle/debug). Node remains
required to regenerate goldens and as a fallback.

## Usage

Match a single sound:

```sh
uv run python -m match.match path/to/target.wav -o out/ --html-report
```

Outputs in `out/`: `match.bfxr` (+ `match_2.bfxr`, … for other good wave
types), rendered `match.wav`s, `report.json` (scores/trace), and
`report.html` — audio players plus spectrograms for target and matches.
Load the `.bfxr` in the app via its Load button.

Useful flags:

- `--allow-pitch-shift` / `--allow-time-stretch` — tolerate a transposed or
  uniformly stretched match instead of requiring exact alignment.
- `--budget N` (default 5000 renders, ~1–2 min) or `--time-budget SECONDS`.
- `--avg-seeds 3` — steadier scores for noise-based targets.
- `--wavetypes 0,3,9` — restrict the wave type search.

Match a whole directory (e.g. the samples in `targets/`):

```sh
uv run python -m match.batch targets/ -o batch_out/ --html-report
open batch_out/index.html
```

### Local refine (steepest descent)

Polish a seed `.bfxr` on continuous params (wave type + square-only knobs frozen):

```sh
uv run python -m match.refine \
  --target targets/mega_man_ii_hurt.wav \
  --seed metric_compare/mega_man_ii_hurt/current_match.bfxr \
  -o refine_hurt/ --steps 200
open refine_hurt/compare.html
```

## Inverse model (seeder)

Optional neural Stage-0: train a wav→params model on synthetic renders, then
use it to seed (or replace) the matcher search.

```sh
# 1) generate ~300k feature shards (~1–2h dominated by feature extract)
uv run python -m invert.dataset --out invert/data/v1 --n 300000 --seed 0

# 2) train (MPS on Apple Silicon)
uv run python -m invert.train --data invert/data/v1 --out invert/runs/v1 --version 1 --epochs 30

# 3) match with model Stage-0
uv run python -m match.match targets/mega_man_ii_hurt.wav -o out/ \
  --seed-model invert/runs/v1/best.pt --budget 5000 --html-report

# 4) one-shot growth metric
uv run python -m match.match targets/mega_man_ii_hurt.wav -o out_os/ \
  --seed-model invert/runs/v1/best.pt --one-shot

# 5) eval table
uv run python -m invert.eval_targets --targets targets/ \
  --ckpt invert/runs/v1/best.pt --budget 2000 -o invert/runs/v1/eval/
```

`--seed-model` replaces the stage-0 random screen; CMA-ES / refine still run
unless `--one-shot` (raw model top prediction only). Eval writes
`results.json` / `results.md` with columns current | model-seeded | one-shot.

## Metric bake-off (fixed library, fair compare)

Build one short-biased library of N bfxr renders, then for each target find
the nearest library sound under each metric (same candidates for everyone):

```sh
make -C bfxr_native
uv run python -m match.metric_bakeoff build-lib -o metric_lib/ --n 5000
uv run python -m match.metric_bakeoff rank targets/ --lib metric_lib/ -o metric_compare/
open metric_compare/index.html
```

Metrics: `current` (contour objective), `harmonic` (partial fingerprint),
`zimtohrli`, `clap`. Setup:

```sh
uv sync --extra report --extra bakeoff   # matplotlib + zimtohrli + transformers
```

## Headless rendering

Native (preferred after `make -C bfxr_native`):

```sh
bfxr_native/build/bfxr_render --dump-info
bfxr_native/build/bfxr_render --in sound.bfxr --out out.wav --seed 1
```

Node fallback (no npm deps; also the parity oracle):

```sh
node render/render_cli.js --dump-info
node render/render_cli.js --in sound.bfxr --out out.wav --seed 1
```

Both expose the same persistent worker protocol used by Python (NDJSON on
stdin, binary float32 frames on stdout). Renders are deterministic per seed
(mulberry32 PRNG). See `bfxr_native/README.md`.

## Tests

```sh
uv run pytest              # fast suite (renderer protocol, metric sanity, native parity)
uv run pytest -m slow      # round-trip: render known params -> re-find them
```

## How matching works

- **Objective**: a weighted sum of per-frame perceptual contour distances —
  volume envelope (dB, peak-normalized), pitch contour from an
  autocorrelation f0 tracker with a voiced/noise flag, pitch slope
  (rising/falling/jumps), and timbre contour (spectral centroid +
  noise-vs-tonal axis) — plus a low-weight multi-scale blurred log-mel term
  for residual detail (`match/features.py`, `match/objective.py`). A raw
  spectrogram distance can't rank structural errors (rising vs falling
  sweeps are equally far from a rising target in mel space);
  `tests/test_metric_rankings.py` pins the orderings that matter.
- **Search**: per-wave-type random screening seeded with the target's
  estimated fundamental, then CMA-ES on the best few wave types, then a full
  CMA-ES run on the winner (`match/optimizer.py`). The DSP is not
  differentiable, so everything is black-box.
- **Speed**: renders fan out over multiple worker processes (native C++ when
  built, otherwise Node); candidate envelope parameters are capped/projected
  so nothing renders much longer than the target.
