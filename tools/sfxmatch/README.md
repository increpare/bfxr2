# sfxmatch

Match a sound with an editable preset on one of the app's 22 synths.
Results and experiment history are in [LOG.md](LOG.md); working rules are in
the repo's `AGENTS.md`.

Run everything from `tools/`.

## Pieces

| Module | What it does |
| --- | --- |
| `render.py` | `FastRenderer` (the shipped synths in Node's main realm: bit-identical to the old worker, about 5x faster) and `RenderPool` (render and featurise across processes). |
| `mel.py` | Model input: log-mel of the first 3 s at 11.6 ms frames, plus the whole sound squeezed into 32 columns. |
| `dataset.py` | Synthetic (features, controls) data straight from the DSP, about 200 rows/s. |
| `model.py`, `train.py` | CNN that names the synth and predicts every control as a distribution over 32 bins. |
| `infer.py` | Sound in, ranked control proposals out. |
| `objective.py` | The one fixed objective. |
| `search.py` | Retrieval over the dataset, then CMA-ES on the best synths. |
| `systems.py` | Run a whole system over the benchmark. |
| `evaluate.py` | Score models by re-rendered audio on held-out native sounds. |
| `benchmark.py` | The frozen benchmark, its blind rating page and the trend table. |
| `agreement.py` | How often each objective agrees with archived human judgments. |
| `guided.py` | Listener-guided search: a local page where you pick the closest candidate and it searches around your pick. |

## Reproduce

```sh
uv run python -m sfxmatch.dataset --out sfxmatch/runs/data-val --total 22000 --seed 2
uv run python -m sfxmatch.dataset --out sfxmatch/runs/data-1m  --total 1000000
uv run python -m sfxmatch.train   --data sfxmatch/runs/data-1m --val sfxmatch/runs/data-val --out sfxmatch/runs/model-1m
uv run python -m sfxmatch.evaluate --checkpoint sfxmatch/runs/model-1m/best.pt --val sfxmatch/runs/data-val
```

Benchmark systems and the listening page:

```sh
uv run python -m sfxmatch.systems oneshot    --checkpoint sfxmatch/runs/model-1m/best.pt --out sfxmatch/runs/systems/oneshot
uv run python -m sfxmatch.systems search     --library sfxmatch/runs/data-1m --checkpoint sfxmatch/runs/model-1m/best.pt --out sfxmatch/runs/systems/search
uv run python -m sfxmatch.systems old-branch --out sfxmatch/runs/systems/old-branch
uv run python -m sfxmatch.systems bfxr       --out sfxmatch/runs/systems/bfxr
uv run python -m sfxmatch.benchmark page m1 oneshot=sfxmatch/runs/systems/oneshot search=sfxmatch/runs/systems/search \
    old=sfxmatch/runs/systems/old-branch bfxr=sfxmatch/runs/systems/bfxr
uv run python -m sfxmatch.benchmark score sfxmatch/ratings/*.json
```

External targets are read from `tools/targets_non_bfxr_big/tags` (symlink the
corpus there, or set `SFX_TARGETS`). The `bfxr` system needs the old Bfxr
inverse checkpoint; set `BFXR_INVERSE_CHECKPOINT` if it has moved.

## Guided search

```sh
uv run python -m sfxmatch.guided          # open http://127.0.0.1:8765
uv run python -m sfxmatch.guided warm ext-001 ext-005   # optional: precompute opening screens
```

Pick a benchmark target (starred ones are the reach-probe set) or give a path
to any audio file. The first screen offers the best candidate from each
promising synth; after that each screen is the current sound plus five
alternatives the objective rates about as good, chosen to sound different from
one another. Finish by rating the result; sessions are saved to
`guided_sessions/` and the current sound can be downloaded as a `.bcol`.

## Tests

```sh
uv run pytest tests/test_sfxmatch.py tests/test_sfxmatch_render.py
```
