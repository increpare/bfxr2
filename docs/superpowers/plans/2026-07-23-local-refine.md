# Local Refine (Steepest Descent) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add finite-difference steepest-descent polish on continuous Bfxr params (discrete/irrelevant frozen), as a reusable Stage 3 + standalone CLI, demoed on `mega_man_ii_hurt`.

**Architecture:** New `tools/match/refine.py` owns free-mask logic and the descent loop. It evaluates via a caller-supplied `params_for` + `BfxrRenderer` + `MatchObjective` (same contract as `StagedOptimizer`). `StagedOptimizer` optionally runs Stage 3 after CMA; `python -m match.refine` polishes a seed `.bfxr` and writes A/B HTML.

**Tech Stack:** Python 3.12, numpy, existing `match.*` (ParamSpace, MatchObjective, BfxrRenderer), pytest via `uv run`.

**Spec:** `docs/superpowers/specs/2026-07-23-local-refine-design.md`

---

## File map

| File | Role |
|------|------|
| `tools/match/refine.py` | `RefineSettings`, `free_mask`, `steepest_descent`, CLI `main` |
| `tools/match/optimizer.py` | Add `refine_steps` to settings; Stage 3 call |
| `tools/match/match.py` | `--refine-steps` CLI flag |
| `tools/tests/test_refine.py` | Unit tests (mask + descent on mock landscape) |
| `tools/README.md` | One short usage blurb |

---

### Task 1: `free_mask` + settings (TDD)

**Files:**
- Create: `tools/match/refine.py`
- Create: `tools/tests/test_refine.py`

- [ ] **Step 1: Write failing tests for free_mask**

```python
# tools/tests/test_refine.py
from match.bfxr_io import ParamSpace
from match.optimizer import SQUARE_ONLY_PARAMS
from match.refine import free_mask


def test_free_mask_square_all_range_free():
    space = ParamSpace()
    mask = free_mask(space, wave_type=0)
    assert mask.shape == (space.dim,)
    assert mask.dtype == bool
    assert mask.all()


def test_free_mask_nonsquare_freezes_square_only():
    space = ParamSpace()
    mask = free_mask(space, wave_type=9)  # Bitnoise
    for name in SQUARE_ONLY_PARAMS:
        assert not mask[space.names.index(name)]
    # something clearly free stays free
    assert mask[space.names.index("frequency_start")]
```

- [ ] **Step 2: Run tests — expect fail**

```bash
cd tools && uv run pytest tests/test_refine.py::test_free_mask_square_all_range_free tests/test_refine.py::test_free_mask_nonsquare_freezes_square_only -v
```

Expected: `ModuleNotFoundError` or import error for `match.refine`.

- [ ] **Step 3: Minimal implementation**

```python
# tools/match/refine.py
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .optimizer import SQUARE_ONLY_PARAMS


@dataclass
class RefineSettings:
    max_steps: int = 200
    eps: float = 0.015
    step0: float = 0.05
    backtrack: int = 6
    patience: int = 20  # early-stop after this many non-improving steps
    verbose: bool = True


def free_mask(space, wave_type: int) -> np.ndarray:
    """True = optimize; False = freeze. waveType is outside the cube."""
    mask = np.ones(space.dim, dtype=bool)
    if int(wave_type) != 0:
        for name in SQUARE_ONLY_PARAMS:
            mask[space.names.index(name)] = False
    return mask
```

- [ ] **Step 4: Re-run tests — expect pass**

```bash
cd tools && uv run pytest tests/test_refine.py::test_free_mask_square_all_range_free tests/test_refine.py::test_free_mask_nonsquare_freezes_square_only -v
```

- [ ] **Step 5: Commit** (only if user asked for commits)

```bash
git add tools/match/refine.py tools/tests/test_refine.py
git commit -m "Add free_mask for local refine (freeze irrelevant dims)"
```

---

### Task 2: `steepest_descent` on a mock landscape (TDD)

**Files:**
- Modify: `tools/match/refine.py`
- Modify: `tools/tests/test_refine.py`

- [ ] **Step 1: Write failing test with analytic fake scorer**

Do **not** use the real renderer. Inject a callable `evaluate(units: list[np.ndarray]) -> np.ndarray` so the descent loop is testable.

```python
# append to tools/tests/test_refine.py
import numpy as np
from match.bfxr_io import ParamSpace
from match.refine import RefineSettings, free_mask, steepest_descent


def test_steepest_descent_moves_toward_minimum():
    space = ParamSpace()
    dim = space.dim
    target = np.full(dim, 0.3)
    # freeze nothing for this mock (pretend square)
    mask = np.ones(dim, dtype=bool)
    # start far on two free coords; others already at target
    u0 = target.copy()
    u0[0] = 0.9
    u0[1] = 0.1

    def evaluate(units: list[np.ndarray]) -> np.ndarray:
        arr = np.stack(units, axis=0)
        # quadratic bowl on free dims
        return np.sum((arr - target) ** 2, axis=1)

    u_final, score, hist = steepest_descent(
        u0,
        wave_type=0,
        evaluate=evaluate,
        upper=np.ones(dim),
        mask=mask,
        settings=RefineSettings(max_steps=80, eps=0.02, step0=0.1, patience=80, verbose=False),
    )
    assert score < evaluate([u0])[0]
    assert abs(u_final[0] - 0.3) < 0.15
    assert abs(u_final[1] - 0.3) < 0.15
    assert len(hist) > 0
```

- [ ] **Step 2: Run test — expect fail**

```bash
cd tools && uv run pytest tests/test_refine.py::test_steepest_descent_moves_toward_minimum -v
```

Expected: `ImportError` / `steepest_descent` missing.

- [ ] **Step 3: Implement `steepest_descent`**

```python
# in tools/match/refine.py — add:

from collections.abc import Callable
import sys


def steepest_descent(
    unit0: np.ndarray,
    wave_type: int,
    evaluate: Callable[[list[np.ndarray]], np.ndarray],
    upper: np.ndarray,
    mask: np.ndarray | None = None,
    settings: RefineSettings | None = None,
) -> tuple[np.ndarray, float, list[tuple[int, float]]]:
    """FD steepest descent on free dims. evaluate(units) -> scores (lower better)."""
    s = settings or RefineSettings()
    u = np.clip(np.asarray(unit0, dtype=float).copy(), 0.0, upper)
    if mask is None:
        # caller may pass space via free_mask externally; default: all free
        mask = np.ones(u.shape[0], dtype=bool)
    free = np.flatnonzero(mask)
    history: list[tuple[int, float]] = []

    def score_one(x: np.ndarray) -> float:
        return float(evaluate([x])[0])

    f = score_one(u)
    history.append((0, f))
    stall = 0
    step = s.step0

    for t in range(1, s.max_steps + 1):
        # batch: current already known; build ±eps for each free dim
        probes: list[np.ndarray] = []
        for i in free:
            up = u.copy()
            dn = u.copy()
            up[i] = min(upper[i], u[i] + s.eps)
            dn[i] = max(0.0, u[i] - s.eps)
            probes.append(up)
            probes.append(dn)
        scores = evaluate(probes)
        g = np.zeros_like(u)
        for k, i in enumerate(free):
            # scores layout: [up0, dn0, up1, dn1, ...]
            g[i] = (scores[2 * k] - scores[2 * k + 1]) / (2.0 * s.eps)
        nrm = float(np.linalg.norm(g))
        if nrm < 1e-12:
            break
        direction = g / nrm
        improved = False
        trial_step = step
        for _ in range(s.backtrack):
            cand = np.clip(u - trial_step * direction, 0.0, upper)
            # keep frozen dims exactly
            cand = np.where(mask, cand, u)
            fc = score_one(cand)
            if fc < f:
                u, f = cand, fc
                improved = True
                step = min(s.step0, trial_step * 1.2)
                break
            trial_step *= 0.5
        history.append((t, f))
        if s.verbose and (t % 20 == 0 or improved and t <= 5):
            print(f"  refine step {t}: score={f:.4f}", file=sys.stderr)
        if improved:
            stall = 0
        else:
            stall += 1
            if stall >= s.patience:
                break
    return u, f, history
```

Note: `wave_type` is unused inside the loop (mask already encodes freezes); keep it in the signature for API clarity / future logging.

- [ ] **Step 4: Re-run test — expect pass**

```bash
cd tools && uv run pytest tests/test_refine.py -v
```

- [ ] **Step 5: Commit** (only if user asked)

```bash
git add tools/match/refine.py tools/tests/test_refine.py
git commit -m "Add finite-difference steepest_descent for local refine"
```

---

### Task 3: Real eval adapter + standalone CLI

**Files:**
- Modify: `tools/match/refine.py` (add `make_evaluate`, `main`, `__main__` block)
- Modify: `tools/README.md` (short section)

- [ ] **Step 1: Add renderer-backed evaluate helper and CLI**

```python
# append to tools/match/refine.py

import argparse
import json
from pathlib import Path

import soundfile as sf

from .audio import SAMPLE_RATE, prepare_target
from .bfxr_io import ParamSpace, read_bfxr, write_bfxr
from .objective import MatchObjective
from .optimizer import RENDER_SEED, StagedOptimizer, OptimizeSettings
from .renderer import BfxrRenderer, default_jobs
from .report import _spectrogram_data_uri, _wav_data_uri


def make_evaluate(optimizer: StagedOptimizer, wave_type: int):
    def evaluate(units: list[np.ndarray]) -> np.ndarray:
        return optimizer._evaluate(units, [wave_type] * len(units))
    return evaluate


def write_compare_html(
    path: Path,
    stem: str,
    target: np.ndarray,
    before: np.ndarray,
    after: np.ndarray,
    score_before: float,
    score_after: float,
) -> None:
    def card(title: str, wave: np.ndarray, meta: str) -> str:
        return f"""
<section class="card">
  <h2>{title}</h2>
  <div class="meta">{meta}</div>
  <audio controls src="{_wav_data_uri(wave)}"></audio>
  <img src="{_spectrogram_data_uri(wave)}" alt="">
</section>"""
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{stem} refine</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: "IBM Plex Sans", system-ui, sans-serif; margin: 0;
        background: #12141a; color: #e6e8ef; }}
header {{ padding: 1.5rem 2rem; border-bottom: 1px solid #2a2e3a; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
         gap: 1rem; padding: 1.5rem 2rem 3rem; }}
.card {{ background: #1a1d27; border: 1px solid #2a2e3a; border-radius: 6px;
         padding: 1rem; display: flex; flex-direction: column; gap: .7rem; }}
.card img {{ width: 100%; }}
audio {{ width: 100%; }}
.meta {{ color: #9aa3b5; font-size: .85rem; }}
</style></head><body>
<header><h1>{stem} — local refine</h1>
<p>score {score_before:.4f} → {score_after:.4f}</p></header>
<div class="grid">
{card("Target", target, stem)}
{card("Before", before, f"score {score_before:.4f}")}
{card("After", after, f"score {score_after:.4f}")}
</div></body></html>"""
    path.write_text(html)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.refine")
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--seed", type=Path, required=True, help="starting .bfxr")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--eps", type=float, default=0.015)
    p.add_argument("--step0", type=float, default=0.05)
    p.add_argument("--jobs", type=int, default=None)
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    target = prepare_target(args.target)
    params0 = read_bfxr(args.seed)
    space = ParamSpace()
    u0, wave_type = space.unit_from_params(params0)
    objective = MatchObjective(target)
    settings = RefineSettings(max_steps=args.steps, eps=args.eps, step0=args.step0)

    with BfxrRenderer(jobs=args.jobs) as renderer:
        # reuse envelope caps / params_for from StagedOptimizer
        opt = StagedOptimizer(
            space, renderer, objective,
            OptimizeSettings(budget=10**9, verbose=False),
            target=target,
        )
        mask = free_mask(space, wave_type)
        # freeze square-only dims to defaults in the unit vector too
        if wave_type != 0:
            for name in SQUARE_ONLY_PARAMS:
                i = space.names.index(name)
                u0[i] = float(space.defaults_unit()[i])
        evaluate = make_evaluate(opt, wave_type)
        score0 = float(evaluate([u0])[0])
        before = renderer.render(opt.params_for(u0, wave_type), seed=RENDER_SEED)
        u1, score1, hist = steepest_descent(
            u0, wave_type, evaluate, opt.upper, mask=mask, settings=settings,
        )
        params1 = opt.params_for(u1, wave_type)
        after = renderer.render(params1, seed=RENDER_SEED)

    sf.write(args.out / "before.wav", before, SAMPLE_RATE, subtype="PCM_16")
    sf.write(args.out / "refined.wav", after, SAMPLE_RATE, subtype="PCM_16")
    sf.write(args.out / "target.wav", target, SAMPLE_RATE, subtype="PCM_16")
    write_bfxr(args.out / "refined.bfxr", params1, file_name=f"{args.target.stem}_refined")
    write_compare_html(
        args.out / "compare.html", args.target.stem,
        target, before, after, score0, score1,
    )
    (args.out / "refine.json").write_text(json.dumps({
        "target": str(args.target),
        "seed": str(args.seed),
        "wave_type": wave_type,
        "score_before": score0,
        "score_after": score1,
        "steps": len(hist) - 1,
        "history": hist,
    }, indent=2) + "\n")
    print(f"score {score0:.4f} → {score1:.4f}; wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Ensure `ParamSpace.unit_from_params` exists — today the inverse is:

```python
# already on ParamSpace as part of roundtrip — check name:
# tools/match/bfxr_io.py has logic around line 99:
#   values = np.array([params[name] for name in self.names], dtype=float)
#   return self.to_unit(values), int(params["waveType"])
```

If that method is not named `unit_from_params`, either add a thin alias on `ParamSpace`:

```python
def unit_from_params(self, params: dict) -> tuple[np.ndarray, int]:
    values = np.array([params[name] for name in self.names], dtype=float)
    return self.to_unit(values), int(params["waveType"])
```

or inline the same two lines in `main`. Prefer adding `unit_from_params` on `ParamSpace` if missing.

- [ ] **Step 2: README blurb**

Add under tools README matching section:

```markdown
### Local refine (steepest descent)

Polish a seed `.bfxr` on continuous params (wave type + square-only knobs frozen):

```sh
uv run python -m match.refine \
  --target targets/mega_man_ii_hurt.wav \
  --seed metric_compare/mega_man_ii_hurt/current_match.bfxr \
  -o refine_hurt/ --steps 200
open refine_hurt/compare.html
```
```

- [ ] **Step 3: Smoke-import CLI**

```bash
cd tools && uv run python -m match.refine --help
```

Expected: help text with `--target`, `--seed`, `--steps`.

- [ ] **Step 4: Commit** (only if user asked)

---

### Task 4: Hook Stage 3 into matcher

**Files:**
- Modify: `tools/match/optimizer.py`
- Modify: `tools/match/match.py`

- [ ] **Step 1: Extend `OptimizeSettings`**

```python
# in OptimizeSettings dataclass
refine_steps: int = 0  # 0 = skip Stage 3
refine_eps: float = 0.015
refine_step0: float = 0.05
```

- [ ] **Step 2: Call refine at end of `StagedOptimizer.run`**

After building `results` / before the final log, if `self.s.refine_steps > 0`, for each candidate in `results` (or at least the best):

```python
from .refine import RefineSettings, free_mask, steepest_descent

# inside run(), after final by_wt / results list is known, before return:
if self.s.refine_steps > 0:
    from .refine import RefineSettings, free_mask, steepest_descent
    polished: list[Candidate] = []
    for cand in results:
        self._log(f"stage3 refine waveType={cand.wave_type} "
                  f"steps={self.s.refine_steps}")
        mask = free_mask(self.space, cand.wave_type)
        u0 = cand.unit.copy()
        if cand.wave_type != 0:
            for name in SQUARE_ONLY_PARAMS:
                i = self.space.names.index(name)
                u0[i] = float(self.space.defaults_unit()[i])
        evaluate = lambda units, wt=cand.wave_type: self._evaluate(units, [wt] * len(units))
        u1, sc, _ = steepest_descent(
            u0, cand.wave_type, evaluate, self.upper, mask=mask,
            settings=RefineSettings(
                max_steps=self.s.refine_steps,
                eps=self.s.refine_eps,
                step0=self.s.refine_step0,
                verbose=self.s.verbose,
            ),
        )
        polished.append(Candidate(sc, cand.wave_type, u1))
    results = sorted(polished)[: self.s.top_k]
```

Keep default `refine_steps=0` so existing match behavior is unchanged.

- [ ] **Step 3: Wire CLI flag in `match.py`**

```python
p.add_argument("--refine-steps", type=int, default=0,
               help="Stage 3 FD steepest-descent steps (0=off)")
# in OptimizeSettings(...):
refine_steps=args.refine_steps,
```

- [ ] **Step 4: Run unit tests**

```bash
cd tools && uv run pytest tests/test_refine.py tests/test_objective.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit** (only if user asked)

---

### Task 5: Demo on `mega_man_ii_hurt`

**Files:**
- Output only (gitignored ok): `tools/refine_hurt/`

- [ ] **Step 1: Run refine**

```bash
cd tools && uv sync --extra report && uv run python -m match.refine \
  --target targets/mega_man_ii_hurt.wav \
  --seed metric_compare/mega_man_ii_hurt/current_match.bfxr \
  -o refine_hurt/ --steps 200
```

Expected stderr: `score X.XXXX → Y.YYYY` with `Y < X` (or equal if early-stopped with no gain).  
Expected files: `refined.bfxr`, `refined.wav`, `before.wav`, `target.wav`, `compare.html`, `refine.json`.

- [ ] **Step 2: Open compare page**

```bash
open refine_hurt/compare.html
```

- [ ] **Step 3: Report scores to user** (before → after, steps used from `refine.json`).

---

## Spec coverage check

| Spec item | Task |
|-----------|------|
| FD steepest descent, 200 steps, backtracking, patience | Task 2 |
| Freeze waveType + square-only off-square | Task 1 + Task 3/4 |
| Envelope projection via params_for | Task 3 (`StagedOptimizer`) |
| `match.refine` module + CLI | Task 3 |
| Stage 3 / `--refine-steps` | Task 4 |
| Hurt demo + HTML A/B | Task 3 HTML + Task 5 |
| Unit tests | Tasks 1–2 |
| Defaults unchanged (`refine_steps=0`) | Task 4 |

## Placeholder scan

None intentional. If `unit_from_params` is missing, Task 3 adds it explicitly.
