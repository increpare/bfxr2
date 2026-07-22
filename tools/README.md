# bfxr2 offline tools

Offline tooling for bfxr2. Nothing here ships with the web app — the synth
sources under `js/` are loaded unmodified (read-only) by a headless renderer.

Current contents: the **wav→bfxr matcher** — give it a sound file, it searches
Bfxr's 30-dimensional parameter space for the closest-sounding bfxr sound and
emits an app-loadable `.bfxr` file. It is also the foundation (batch renderer,
perceptual distance) for mining tag-labeled preset regions later.

## Setup

Requires `node` (any recent version) and [`uv`](https://docs.astral.sh/uv/).

```sh
cd tools
uv sync --extra report --group dev   # torch CPU build; first sync is big
```

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

## Headless rendering (Node, no npm deps)

```sh
node render/render_cli.js --dump-info                 # param metadata JSON
node render/render_cli.js --in sound.bfxr --out out.wav --seed 1
```

`render/render_worker.js` is the persistent batch protocol used by Python
(NDJSON requests on stdin, binary frames on stdout). Renders are
deterministic per seed — `Math.random` is replaced by a seeded PRNG inside
the vm context.

## Tests

```sh
uv run pytest              # fast suite (renderer protocol, metric sanity)
uv run pytest -m slow      # round-trip: render known params -> re-find them
```

## How matching works

- **Objective**: multi-scale log-mel spectrogram L1 distance (4 scales,
  loudness normalized, slight frequency blur so near-miss pitches still get
  a gradient). Strict about timing/pitch/duration unless relaxed by flags.
- **Search**: per-wave-type random screening seeded with the target's
  estimated fundamental, then CMA-ES on the best few wave types, then a full
  CMA-ES run on the winner (`match/optimizer.py`). The DSP is not
  differentiable, so everything is black-box.
- **Speed**: renders fan out over multiple Node worker processes; candidate
  envelope parameters are capped/projected so nothing renders much longer
  than the target.
