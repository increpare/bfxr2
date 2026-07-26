# Headroom Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether search, the match objective, or synth reachability caps the hard slice, so the next multi-week project is chosen from evidence rather than from the next unexplored idea.

**Architecture:** One new setting on `StagedOptimizer` (an IPOP-style restart loop, default off) makes large budgets actually spendable; a driver module runs a four-arm matrix over the hard slice plus an in-domain preset control, re-scores every winner on a held-out render seed, and emits a blind listen page. No model, objective, or shipping default changes.

**Tech Stack:** Python 3.12, `uv`, numpy, `cma`, pytest. Node headless renderer via the existing `BfxrRenderer`.

**Spec:** `docs/superpowers/specs/2026-07-25-headroom-probe-design.md`

## Global Constraints

- Work in `tools/`; run everything as `cd tools && uv run python -m ...` with `PYTHONPATH=.`.
- Branch `feature/inverse-model-structure-metric`. Baseline checkpoint `invert/runs/v7_real_ft/best.pt`.
- **Never edit `js/`.** Never commit `invert/data/` or `invert/runs/` (gitignored).
- `OptimizeSettings.restarts` defaults to `False` and **stays** `False` whatever the probe finds. The shipping path must be unchanged.
- Baseline budget is **2 000** (matches `gateA_legacy`, so existing ear scores cross-check). Big budget is **200 000**.
- `RENDER_SEED = 1234` (`match/optimizer.py:21`) is the search seed. The held-out seed is **`HELDOUT_RENDER_SEED = 8765`** and must never be used during search.
- Decision thresholds are pre-registered in the spec §4. Do not edit them after seeing results.
- Tests must not require the Node renderer unless marked `@pytest.mark.slow`.

---

### Task 1: Restart loop in `StagedOptimizer`

`_run_cma` exits on `es.stop()` (`tolfun=1e-4`). At budget 200 000 a single CMA run converges and stops, leaving most of the budget unspent — a flat probe result would then be an artifact of early stopping rather than evidence of a ceiling. This task makes leftover budget spendable.

**Files:**
- Modify: `tools/match/optimizer.py` (`OptimizeSettings` ~line 93; `_run_cma` ~line 346; `run` ~line 394)
- Test: `tools/tests/test_optimizer_restarts.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `OptimizeSettings.restarts: bool = False`, `OptimizeSettings.restart_popsize_factor: float = 2.0`, `OptimizeSettings.restart_popsize_cap: int = 256`; `StagedOptimizer._run_restarts(wave_types: list[int]) -> None`; `_run_cma(start, max_iters, *, popsize: int | None = None, cma_seed: int | None = None) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_optimizer_restarts.py`. The fakes keep this fast and
deterministic — no Node, no DSP. The fake renderer turns each param dict into a
vector, and the fake objective scores squared distance to a fixed optimum, so
CMA has a smooth basin it converges into quickly (which is exactly the condition
that makes a plain run stop early).

```python
import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import OptimizeSettings, StagedOptimizer


class _FakeRenderer:
    """Encodes each param dict as a vector so scores depend on the unit."""

    def render_batch(self, params_list, seeds=0):
        return [
            np.array([p[k] for k in sorted(p)], dtype=np.float64)
            for p in params_list
        ]


class _FakeObjective:
    target_len = 44100

    def __init__(self, dim):
        self.opt = np.full(dim, 0.3)

    def score_batch(self, waves):
        return np.array(
            [float(np.sum((w - self.opt[: len(w)]) ** 2)) for w in waves]
        )


BUDGET = 20000  # far more than a smooth quadratic basin can absorb


def _opt(**kw) -> StagedOptimizer:
    space = ParamSpace()
    settings = OptimizeSettings(
        budget=BUDGET, verbose=False, wave_types=[0], arp_seeds=False, **kw
    )
    obj = _FakeObjective(len(space.names))
    return StagedOptimizer(space, _FakeRenderer(), obj, settings, target=None)


def test_plain_run_leaves_budget_unspent():
    """Precondition for the whole probe: without restarts, CMA converges and
    stops well short of a large budget."""
    opt = _opt()
    opt.run()
    assert opt.evals < 0.5 * BUDGET


def test_restarts_spend_the_budget():
    opt = _opt(restarts=True)
    opt.run()
    assert opt.evals >= 0.9 * BUDGET


def test_restarts_never_score_worse_at_equal_budget():
    plain = _opt()
    plain_best = min(plain.run()).score
    restarted = _opt(restarts=True)
    restarted_best = min(restarted.run()).score
    assert restarted_best <= plain_best + 1e-12


def test_restart_loop_terminates_when_cma_cannot_spend():
    """Guard against an infinite loop if a restart evaluates nothing."""
    opt = _opt(restarts=True)
    calls = {"n": 0}

    def _noop(start, max_iters, *, popsize=None, cma_seed=None):
        calls["n"] += 1

    opt._run_cma = _noop
    opt.s.budget = 10**9
    opt._run_restarts([0])
    assert calls["n"] <= 2  # bails as soon as a restart makes no progress


def test_restarts_off_does_not_invoke_the_loop():
    opt = _opt()

    def _boom(wave_types):
        raise AssertionError("_run_restarts must not run when restarts=False")

    opt._run_restarts = _boom
    opt.run()  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_optimizer_restarts.py -v`
Expected: FAIL — `TypeError: OptimizeSettings.__init__() got an unexpected keyword argument 'restarts'`.

- [ ] **Step 3: Add the settings fields**

In `tools/match/optimizer.py`, inside `OptimizeSettings`, directly after the
`arp_seeds` field:

```python
    # Spend leftover budget with IPOP-style CMA restarts. A single CMA run
    # stops on tolfun long before a large budget is exhausted; without this a
    # big-budget arm silently under-spends and a flat result would be an
    # artifact of early stopping, not evidence of a ceiling.
    # SHIPPING PATH KEEPS THIS False.
    restarts: bool = False
    restart_popsize_factor: float = 2.0
    restart_popsize_cap: int = 256
```

- [ ] **Step 4: Make `_run_cma` accept per-restart popsize and seed**

Without this every restart from the same start point would be an identical run.
Defaults of `None` reproduce the current values exactly, so `restarts=False` is
bit-identical.

Change the signature and the two `opts` entries in `_run_cma`:

```python
    def _run_cma(
        self,
        start: Candidate,
        max_iters: int | None,
        *,
        popsize: int | None = None,
        cma_seed: int | None = None,
    ) -> None:
        opts = {
            "bounds": [np.zeros(self.space.dim).tolist(), self.upper.tolist()],
            "popsize": self.s.popsize if popsize is None else popsize,
            "seed": (self.s.rng_seed + 1) if cma_seed is None else cma_seed,
            "verbose": -9,
            "tolfun": 1e-4,
        }
```

Leave the rest of `_run_cma` untouched.

- [ ] **Step 5: Implement the restart loop**

Add this method to `StagedOptimizer`, next to `_run_arp_stage`:

```python
    def _run_restarts(self, wave_types: list[int]) -> None:
        """Spend whatever budget stage 2 left on the table.

        Alternates a perturbed archive-best (exploit, keeps that candidate's
        wave type) with a fresh random unit on a survivor wave type (explore),
        growing popsize each time. The shared archive means restarts can only
        improve the final result.
        """
        survivors = sorted({c.wave_type for c in self.archive}) or list(wave_types)
        popsize = self.s.popsize
        i = 0
        while not self._out_of_budget():
            before = self.evals
            popsize = min(
                int(popsize * self.s.restart_popsize_factor),
                self.s.restart_popsize_cap,
            )
            if i % 2 == 0 and self.archive:
                base = min(self.archive)
                unit = np.clip(
                    base.unit + self.rng.normal(0.0, 0.1, size=base.unit.shape),
                    0.0,
                    self.upper,
                )
                start = Candidate(base.score, base.wave_type, unit)
            else:
                wt = survivors[(i // 2) % len(survivors)]
                start = Candidate(float("inf"), wt, self._screen_sample())
            self._log(
                f"restart {i} waveType={start.wave_type} popsize={popsize}"
            )
            self._run_cma(
                start,
                max_iters=None,
                popsize=popsize,
                cma_seed=self.s.rng_seed + 1000 + i,
            )
            i += 1
            if self.evals == before:
                # a restart that evaluates nothing would spin forever
                self._log("restart made no progress; stopping")
                break
```

- [ ] **Step 6: Call it from `run()`**

In `run()`, immediately after the arp block (`self.s.budget = full_budget`) and
**before** the `by_wt = {}` recomputation that builds `results`:

```python
        if self.s.restarts:
            self._run_restarts(wave_types)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_optimizer_restarts.py -v`
Expected: all 5 PASS.

- [ ] **Step 8: Run the full suite for regressions**

Run: `cd tools && uv run pytest -q`
Expected: PASS, no new failures. The `restarts=False` default means every
existing optimizer test must be unaffected.

- [ ] **Step 9: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/optimizer.py tools/tests/test_optimizer_restarts.py
git commit -m "feat(match): IPOP-style CMA restarts so big budgets are spendable

Default off; shipping path unchanged. Needed by the headroom probe: a
single CMA run stops on tolfun long before 200k evals, so a flat
big-budget result would otherwise be an early-stopping artifact.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `--restarts` flag on the match CLI

**Files:**
- Modify: `tools/match/match.py` (`build_parser` ~line 29; `OptimizeSettings` construction ~line 215; report `flags` dict ~line 252)
- Test: `tools/tests/test_optimizer_restarts.py` (append)

**Interfaces:**
- Consumes: `OptimizeSettings.restarts` from Task 1.
- Produces: `--restarts` CLI flag; `report.json["flags"]["restarts"]`.

- [ ] **Step 1: Write the failing test**

Append to `tools/tests/test_optimizer_restarts.py`:

```python
from match.match import build_parser


def test_restarts_flag_defaults_off():
    args = build_parser().parse_args(["x.wav", "-o", "out"])
    assert args.restarts is False


def test_restarts_flag_can_be_enabled():
    args = build_parser().parse_args(["x.wav", "-o", "out", "--restarts"])
    assert args.restarts is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_optimizer_restarts.py -k restarts_flag -v`
Expected: FAIL — `AttributeError: 'Namespace' object has no attribute 'restarts'`.

- [ ] **Step 3: Add the flag**

In `build_parser`, next to the `--budget` argument:

```python
    p.add_argument("--restarts", action="store_true",
                   help="spend leftover budget with CMA restarts (headroom "
                        "experiments; shipping default is off)")
```

In the `OptimizeSettings(...)` construction in `main`, add:

```python
        restarts=args.restarts,
```

In the report `flags` dict, add:

```python
            "restarts": args.restarts,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_optimizer_restarts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/match.py tools/tests/test_optimizer_restarts.py
git commit -m "feat(match): --restarts flag (default off) and report field

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Held-out render-seed re-scoring

`avg_seeds=1`, so the whole search is scored against one fixed render RNG seed
(`RENDER_SEED = 1234`). A 200 000-eval CMA has ample capacity to overfit that
seed's noise. Every arm's winner is therefore re-scored on a seed never used
during search. If a big-budget win evaporates here, the finding is "we overfit
the render seed", not "search has headroom".

**Files:**
- Create: `tools/match/headroom.py`
- Test: `tools/tests/test_headroom_rescore.py` (create)

**Interfaces:**
- Consumes: `match.bfxr_io.read_bfxr`, `match.objective.MatchObjective`, `match.renderer.BfxrRenderer`.
- Produces: `HELDOUT_RENDER_SEED: int = 8765`; `rescore_heldout(bfxr_path: Path, objective, renderer, seed: int = HELDOUT_RENDER_SEED) -> float`.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_headroom_rescore.py`:

```python
from pathlib import Path

import numpy as np

from match.headroom import HELDOUT_RENDER_SEED, rescore_heldout
from match.optimizer import RENDER_SEED

FIXTURE = Path(__file__).parent / "fixtures" / "square_blip.bfxr"


class _RecordingRenderer:
    def __init__(self):
        self.seeds = []

    def render_batch(self, params_list, seeds=0):
        self.seeds.append(seeds)
        return [np.ones(16, dtype=np.float32) for _ in params_list]


class _FakeObjective:
    def score_batch(self, waves):
        return np.array([0.5 for _ in waves])


def test_heldout_seed_differs_from_search_seed():
    assert HELDOUT_RENDER_SEED != RENDER_SEED


def test_rescore_renders_with_the_heldout_seed():
    renderer = _RecordingRenderer()
    score = rescore_heldout(FIXTURE, _FakeObjective(), renderer)
    assert renderer.seeds == [HELDOUT_RENDER_SEED]
    assert score == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_headroom_rescore.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'match.headroom'`.

- [ ] **Step 3: Create the module with the re-score helper**

Create `tools/match/headroom.py`:

```python
"""Headroom probe: does search, the match objective, or synth reachability cap
the hard slice?

Design: docs/superpowers/specs/2026-07-25-headroom-probe-design.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .bfxr_io import read_bfxr

# Never used during search. The search always renders with RENDER_SEED (1234),
# so scoring a winner here detects a candidate that merely overfit that seed's
# noise -- a real risk at 200k evals with avg_seeds=1.
HELDOUT_RENDER_SEED = 8765


def rescore_heldout(
    bfxr_path: Path,
    objective: Any,
    renderer: Any,
    seed: int = HELDOUT_RENDER_SEED,
) -> float:
    """Re-render a saved winner on an unseen render seed and score it."""
    params = read_bfxr(bfxr_path)
    waves = renderer.render_batch([params], seeds=seed)
    return float(objective.score_batch(waves)[0])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_headroom_rescore.py -v`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/headroom.py tools/tests/test_headroom_rescore.py
git commit -m "feat(match): held-out render-seed re-scoring for the headroom probe

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Blind multi-arm listen page

`write_compare_page` handles exactly two roots. The probe has four arms and the
claim gate requires hidden labels. This adds a second entry point to the same
module (existing function and its tests untouched) that shuffles the candidate
columns per row and writes the answer key to a separate JSON file.

**Files:**
- Modify: `tools/match/listen_compare.py` (append after `write_compare_page`, ~line 110)
- Test: `tools/tests/test_headroom_page.py` (create)

**Interfaces:**
- Consumes: `_read`, `_cell`, `_safe_stem`, `AUDIO_EXTS`, `HARD_SLICE` from `match.listen_compare`.
- Produces: `write_arms_page(out: Path, key_out: Path, targets_dir: Path, arms: list[tuple[str, Path]], mode: str = "model_seeded", only: set[str] | None = None, shuffle_seed: int = 0) -> None`.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_headroom_page.py`:

```python
import json

import numpy as np
import soundfile as sf

from match.audio import SAMPLE_RATE
from match.listen_compare import write_arms_page


def _wav(path, value=0.1):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.full(1000, value, dtype=np.float32), SAMPLE_RATE)


def _setup(tmp_path):
    targets = tmp_path / "targets"
    _wav(targets / "Mario 1 - Jump.wav")
    arms = []
    for name in ("baseline_seeded", "big_seeded", "big_unseeded"):
        root = tmp_path / name
        _wav(root / "Mario 1 - Jump" / "model_seeded" / "match.wav")
        arms.append((name, root))
    return targets, arms


def test_key_records_every_arm_and_page_hides_names(tmp_path):
    targets, arms = _setup(tmp_path)
    out = tmp_path / "page.html"
    key_out = tmp_path / "key.json"

    write_arms_page(out, key_out, targets, arms, only={"Mario 1 - Jump"})

    html = out.read_text()
    for name, _ in arms:
        assert name not in html  # labels must not leak into the page

    key = json.loads(key_out.read_text())
    assert sorted(key["Mario 1 - Jump"]) == ["A", "B", "C"]
    assert sorted(key["Mario 1 - Jump"].values()) == sorted(n for n, _ in arms)


def test_shuffle_is_deterministic_for_a_given_seed(tmp_path):
    targets, arms = _setup(tmp_path)
    keys = []
    for i in range(2):
        out = tmp_path / f"page{i}.html"
        key_out = tmp_path / f"key{i}.json"
        write_arms_page(out, key_out, targets, arms,
                        only={"Mario 1 - Jump"}, shuffle_seed=7)
        keys.append(json.loads(key_out.read_text()))
    assert keys[0] == keys[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_headroom_page.py -v`
Expected: FAIL — `ImportError: cannot import name 'write_arms_page'`.

- [ ] **Step 3: Implement `write_arms_page`**

Append to `tools/match/listen_compare.py` (after `write_compare_page`). Note the
`import json` and `import random` go at the top of the file with the other
imports.

```python
def write_arms_page(
    out: Path,
    key_out: Path,
    targets_dir: Path,
    arms: list[tuple[str, Path]],
    mode: str = "model_seeded",
    only: set[str] | None = None,
    shuffle_seed: int = 0,
) -> None:
    """Blind N-arm listen page: candidate columns are shuffled per row and
    labelled A/B/C..., with the mapping written to `key_out` instead of the
    page. Scores and arm names stay hidden so the listener cannot anchor."""
    letters = [chr(ord("A") + i) for i in range(len(arms))]
    key: dict[str, dict[str, str]] = {}
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        rng = random.Random(f"{shuffle_seed}:{target_path.stem}")
        order = list(arms)
        rng.shuffle(order)
        key[target_path.stem] = {
            letter: name for letter, (name, _) in zip(letters, order)
        }
        cells = [f"<td class='name'>{target_path.stem}</td>",
                 _cell(_read(target_path))]
        for _, root in order:
            cells.append(_cell(_read(root / safe / mode / "match.wav")))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    head = "".join(f"<th>{letter}</th>" for letter in letters)
    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Headroom probe - blind arms</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Headroom probe - blind arms</h1>"
        "<p>Score each lettered column 0-5 against the original. Column order "
        "is <b>reshuffled on every row</b> and the arm names are withheld on "
        "purpose - do not guess which is which.</p>"
        f"<table><tr><th>target</th><th>original</th>{head}</tr>"
        + "".join(rows) +
        "</table>"
    )
    key_out.write_text(json.dumps(key, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_headroom_page.py tests/test_listen_compare.py -v`
Expected: all PASS — the new page and the untouched Gate B page both work.

- [ ] **Step 5: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/listen_compare.py tools/tests/test_headroom_page.py
git commit -m "feat(match): blind N-arm listen page with a separate answer key

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: In-domain preset control targets

The reachability reading needs a known-reachable reference: targets bfxr
provably can make, searched with the same arms. Ten preset renders supply the
"what does converged actually look like" floor.

**Deviation from the spec:** the spec says "10 bfxr presets from the existing
`eval_bfxr` set". Those directories are *run outputs*, not target wavs, so this
task regenerates presets from `harvest_preset_params` with a fixed seed instead.
Same intent (known-reachable controls), reproducible from scratch.

**Files:**
- Modify: `tools/match/headroom.py`
- Test: `tools/tests/test_headroom_presets.py` (create)

**Interfaces:**
- Consumes: `invert.presets.harvest_preset_params`, `match.bfxr_io.write_bfxr`, `match.renderer.BfxrRenderer`.
- Produces: `make_preset_targets(out_dir: Path, n: int = 10, seed: int = 4242, renderer=None) -> list[Path]`.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_headroom_presets.py`:

```python
import numpy as np
import soundfile as sf

from match.headroom import make_preset_targets


class _FakeRenderer:
    def render_batch(self, params_list, seeds=0):
        return [np.full(2000, 0.2, dtype=np.float32) for _ in params_list]


def test_writes_one_wav_per_preset(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    paths = make_preset_targets(tmp_path, n=3, renderer=_FakeRenderer())
    assert len(paths) == 3
    for p in paths:
        assert p.suffix == ".wav" and p.is_file()
        data, _ = sf.read(p)
        assert len(data) > 0


def test_names_are_stable_across_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    a = make_preset_targets(tmp_path / "a", n=3, renderer=_FakeRenderer())
    b = make_preset_targets(tmp_path / "b", n=3, renderer=_FakeRenderer())
    assert [p.name for p in a] == [p.name for p in b]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_headroom_presets.py -v`
Expected: FAIL — `ImportError: cannot import name 'make_preset_targets'`.

- [ ] **Step 3: Implement it**

Add to `tools/match/headroom.py` (and add `import soundfile as sf`,
`from invert.presets import harvest_preset_params`, `from .audio import
SAMPLE_RATE`, `from .renderer import BfxrRenderer` at the top):

```python
def make_preset_targets(
    out_dir: Path,
    n: int = 10,
    seed: int = 4242,
    renderer: Any | None = None,
) -> list[Path]:
    """Render N bfxr presets to wavs: the known-reachable control set.

    These are targets the synth provably can hit, so their converged objective
    floor is the reference the real-SFX floor is measured against.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    params_list = harvest_preset_params(n, seed)
    if renderer is None:
        with BfxrRenderer() as owned:
            waves = owned.render_batch(params_list, seeds=HELDOUT_RENDER_SEED)
    else:
        waves = renderer.render_batch(params_list, seeds=HELDOUT_RENDER_SEED)
    paths = []
    for i, wave in enumerate(waves):
        path = out_dir / f"preset_{i:02d}.wav"
        sf.write(path, wave, SAMPLE_RATE)
        paths.append(path)
    return paths
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_headroom_presets.py -v`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/headroom.py tools/tests/test_headroom_presets.py
git commit -m "feat(match): in-domain preset control targets for the headroom probe

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Probe driver

**Files:**
- Modify: `tools/match/headroom.py`
- Test: `tools/tests/test_headroom_driver.py` (create)

**Interfaces:**
- Consumes: `rescore_heldout`, `make_preset_targets` (Tasks 3 & 5); `match.match.main` as `match_main`; `HARD_SLICE` from `match.listen_compare`.
- Produces: `ARMS: dict[str, dict[str, Any]]`; `heldout_for_run(target: Path, bfxr_path: Path, jobs: int | None) -> float`; `run_arm(target: Path, out_dir: Path, arm: str, *, ckpt: Path, jobs: int | None, rng_seed: int) -> dict[str, Any]`; `main(argv: list[str] | None = None) -> int`.

**Why `heldout_for_run` is a separate function:** it is the seam that keeps the
Node renderer out of the unit tests. Building `MatchObjective`/`BfxrRenderer`
inline inside `run_arm` would spawn real render workers (and call
`prepare_target` on a fixture path) even when `rescore_heldout` is monkeypatched,
violating the global constraint that tests must not require Node.

- [ ] **Step 1: Write the failing test**

Create `tools/tests/test_headroom_driver.py`:

```python
import json

from match.headroom import ARMS, run_arm


def test_arm_matrix_matches_the_spec():
    assert set(ARMS) == {
        "baseline_seeded", "big_seeded", "baseline_unseeded", "big_unseeded",
    }
    assert ARMS["baseline_seeded"] == {
        "budget": 2000, "seed_model": True, "restarts": False
    }
    assert ARMS["big_seeded"] == {
        "budget": 200000, "seed_model": True, "restarts": True
    }
    assert ARMS["baseline_unseeded"] == {
        "budget": 2000, "seed_model": False, "restarts": False
    }
    assert ARMS["big_unseeded"] == {
        "budget": 200000, "seed_model": False, "restarts": True
    }


def test_run_arm_builds_the_expected_argv(tmp_path, monkeypatch):
    seen = {}

    def _fake_match_main(argv):
        seen["argv"] = argv
        out = tmp_path / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "evals": 123, "elapsed_seconds": 4.5, "trace": [[64, 3.0]],
            "results": [{"file": "match.bfxr", "score": 1.5,
                         "wave_type": 0, "wave_type_name": "Square"}],
        }))
        return 0

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr("match.headroom.heldout_for_run",
                        lambda *a, **k: 1.9)

    row = run_arm(tmp_path / "t.wav", tmp_path / "out", "big_seeded",
                  ckpt=tmp_path / "best.pt", jobs=2, rng_seed=0)

    argv = seen["argv"]
    assert "--restarts" in argv
    assert argv[argv.index("--budget") + 1] == "200000"
    assert "--seed-model" in argv
    assert row["score"] == 1.5
    assert row["heldout_score"] == 1.9
    assert row["evals"] == 123


def test_baseline_unseeded_omits_the_model(tmp_path, monkeypatch):
    seen = {}

    def _fake_match_main(argv):
        seen["argv"] = argv
        out = tmp_path / "out2"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "evals": 1, "elapsed_seconds": 1.0, "trace": [],
            "results": [{"file": "match.bfxr", "score": 2.0,
                         "wave_type": 0, "wave_type_name": "Square"}],
        }))
        return 0

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr("match.headroom.heldout_for_run", lambda *a, **k: 2.2)

    run_arm(tmp_path / "t.wav", tmp_path / "out2", "baseline_unseeded",
            ckpt=tmp_path / "best.pt", jobs=None, rng_seed=0)

    assert "--seed-model" not in seen["argv"]
    assert "--restarts" not in seen["argv"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_headroom_driver.py -v`
Expected: FAIL — `ImportError: cannot import name 'ARMS'`.

- [ ] **Step 3: Implement the arm matrix and `run_arm`**

Add to `tools/match/headroom.py`. Add `import argparse`, `import json`,
`import sys`, `import traceback`, `from .match import main as match_main`,
`from .objective import MatchObjective`, `from .audio import prepare_target`,
`from .listen_compare import HARD_SLICE, write_arms_page` to the imports.

```python
ARMS: dict[str, dict[str, Any]] = {
    "baseline_seeded":   {"budget": 2000,   "seed_model": True,  "restarts": False},
    "big_seeded":        {"budget": 200000, "seed_model": True,  "restarts": True},
    "baseline_unseeded": {"budget": 2000,   "seed_model": False, "restarts": False},
    "big_unseeded":      {"budget": 200000, "seed_model": False, "restarts": True},
}

# Written by match.py as the best result; see match.main's report "results".
BEST_FILE = "match.bfxr"


def heldout_for_run(target: Path, bfxr_path: Path, jobs: int | None) -> float:
    """Score a saved winner on the held-out render seed.

    Kept separate from run_arm so unit tests can stub it out; building the
    objective and renderer inline would spawn Node workers in every test.
    """
    objective = MatchObjective(prepare_target(target))
    with BfxrRenderer(jobs=jobs) as renderer:
        return rescore_heldout(bfxr_path, objective, renderer)


def run_arm(
    target: Path,
    out_dir: Path,
    arm: str,
    *,
    ckpt: Path,
    jobs: int | None,
    rng_seed: int,
) -> dict[str, Any]:
    """Run one arm on one target, then re-score its winner on a held-out seed."""
    cfg = ARMS[arm]
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        str(target), "-o", str(out_dir),
        "--budget", str(cfg["budget"]),
        "--rng-seed", str(rng_seed),
    ]
    if jobs is not None:
        argv += ["--jobs", str(jobs)]
    if cfg["seed_model"]:
        argv += ["--seed-model", str(ckpt)]
    if cfg["restarts"]:
        argv += ["--restarts"]

    rc = match_main(argv)
    if rc != 0:
        raise RuntimeError(f"match exited with code {rc} for {arm}/{target.name}")
    report = json.loads((out_dir / "report.json").read_text())
    best = report["results"][0]

    heldout = heldout_for_run(target, out_dir / BEST_FILE, jobs)

    return {
        "arm": arm,
        "score": float(best["score"]),
        "heldout_score": heldout,
        "wave_type_name": str(best["wave_type_name"]),
        "evals": int(report["evals"]),
        "elapsed_seconds": float(report["elapsed_seconds"]),
        "trace": report.get("trace", []),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools && uv run pytest tests/test_headroom_driver.py -v`
Expected: all 3 PASS.

- [ ] **Step 5: Add the CLI entry point**

Append to `tools/match/headroom.py`:

```python
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="match.headroom",
        description="Four-arm headroom probe over the hard slice plus an "
                    "in-domain preset control.",
    )
    p.add_argument("--targets", type=Path, required=True,
                   help="directory of real target wavs (hard slice is selected "
                        "from it by name)")
    p.add_argument("--ckpt", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=None)
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--arms", nargs="+", default=list(ARMS),
                   choices=list(ARMS))
    p.add_argument("--presets", type=int, default=10,
                   help="in-domain control targets (0 disables)")
    p.add_argument("--preset-arms", nargs="+",
                   default=["baseline_seeded", "big_seeded"],
                   choices=list(ARMS))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    work: list[tuple[str, Path, list[str]]] = []
    real = [p for p in sorted(args.targets.iterdir())
            if p.stem in set(HARD_SLICE)]
    if len(real) != len(HARD_SLICE):
        found = {p.stem for p in real}
        missing = sorted(set(HARD_SLICE) - found)
        print(f"warning: missing hard-slice targets: {missing}", file=sys.stderr)
    for path in real:
        work.append(("real", path, args.arms))

    if args.presets > 0:
        preset_paths = make_preset_targets(args.out / "preset_targets",
                                           n=args.presets)
        for path in preset_paths:
            work.append(("in_domain", path, args.preset_arms))

    rows: list[dict[str, Any]] = []
    for kind, path, arms in work:
        for arm in arms:
            print(f"[{kind}] {path.stem} :: {arm}", file=sys.stderr)
            out_dir = args.out / arm / _safe_dir(path.stem) / "model_seeded"
            try:
                row = run_arm(path, out_dir, arm, ckpt=args.ckpt,
                              jobs=args.jobs, rng_seed=args.rng_seed)
            except Exception as exc:  # one arm must not kill the overnight run
                traceback.print_exc()
                row = {"arm": arm, "error": f"{type(exc).__name__}: {exc}"}
            row["kind"] = kind
            row["target"] = path.stem
            rows.append(row)
            # written after every arm so an interrupted run is still readable
            (args.out / "results.json").write_text(json.dumps(
                {"ckpt": str(args.ckpt), "rng_seed": args.rng_seed,
                 "heldout_seed": HELDOUT_RENDER_SEED, "rows": rows},
                indent=2,
            ))

    listen_arms = [(a, args.out / a) for a in args.arms if a != "baseline_unseeded"]
    write_arms_page(
        args.out / "headroom.html",
        args.out / "headroom_key.json",
        args.targets,
        listen_arms,
        only=set(HARD_SLICE),
    )
    print(f"wrote {args.out}/results.json and headroom.html", file=sys.stderr)
    return 0


def _safe_dir(stem: str) -> str:
    """Must match invert.eval_targets._safe_stem: keep spaces and parens."""
    return stem.replace("/", "_").replace("\\", "_")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the whole suite**

Run: `cd tools && uv run pytest -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add tools/match/headroom.py tools/tests/test_headroom_driver.py
git commit -m "feat(match): headroom probe driver over the four-arm matrix

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: Harness validation, then the overnight run

A restart-loop bug found after a six-hour run costs the whole night. Validate at
small scale first. **Stop and report to the human if any check fails** — do not
launch the matrix on a suspect harness.

**Files:**
- Create: `docs/superpowers/plans/2026-07-25-headroom-probe-results.md`

- [ ] **Step 1: Verify the shipping path is bit-identical**

The unit tests prove `_run_restarts` is not invoked when `restarts=False`; this
proves the *output* is unchanged against the pre-change commit.

```bash
cd /Users/stephenlavelle/Documents/bfxr2/tools
uv run python -m match.match "targets/Mario 2 - Throw.wav" \
  -o /tmp/headroom_check/after --budget 2000 --rng-seed 0
git stash && git stash list
```

Then check out the commit before Task 1, render the same target to
`/tmp/headroom_check/before`, restore with `git stash pop`, and compare:

```bash
diff <(python3 -c "import json;d=json.load(open('/tmp/headroom_check/before/report.json'));print(d['evals'],d['results'][0]['score'])") \
     <(python3 -c "import json;d=json.load(open('/tmp/headroom_check/after/report.json'));print(d['evals'],d['results'][0]['score'])")
```

Expected: **no diff**. A difference means the `_run_cma` signature change
altered the default path — stop and fix.

- [ ] **Step 2: Smoke-test both budgets on one target**

```bash
cd /Users/stephenlavelle/Documents/bfxr2/tools
uv run python -m match.headroom \
  --targets targets --ckpt invert/runs/v7_real_ft/best.pt \
  -o invert/runs/headroom_smoke --presets 2 --arms baseline_seeded
```

Expected: completes in a couple of minutes; `results.json` has rows for the hard
slice and 2 preset rows; every row has both `score` and `heldout_score`.

- [ ] **Step 3: Confirm restarts actually spend a big budget**

```bash
cd /Users/stephenlavelle/Documents/bfxr2/tools
uv run python -m match.match "targets/Mario 2 - Throw.wav" \
  -o /tmp/headroom_check/big --budget 20000 --restarts \
  --seed-model invert/runs/v7_real_ft/best.pt
python3 -c "import json;d=json.load(open('/tmp/headroom_check/big/report.json'));print('evals',d['evals'],'budget',d['budget'])"
```

Expected: `evals` >= 20000 (the arp stage may push it to ~30000). If `evals` is
far below budget, the restart loop is bailing early — **stop and investigate**
before the overnight run, because this is the exact failure that would make the
probe's result meaningless.

- [ ] **Step 4: Launch the full matrix**

```bash
cd /Users/stephenlavelle/Documents/bfxr2/tools
nohup uv run python -m match.headroom \
  --targets targets --ckpt invert/runs/v7_real_ft/best.pt \
  -o invert/runs/headroom > invert/runs/headroom.log 2>&1 &
```

Expected: ~6 hours. `results.json` is rewritten after every arm, so progress is
readable at any point via `tail -f invert/runs/headroom.log`.

- [ ] **Step 5: Write the results doc against the pre-registered rule**

Create `docs/superpowers/plans/2026-07-25-headroom-probe-results.md` containing:

1. Per-arm table: median `score` and median `heldout_score`, real vs in-domain.
2. Convergence traces: where does the curve flatten? Report the eval count at
   which `big_seeded` reaches within 5% of its final score — that is the knee,
   and the candidate for a future shipping budget.
3. The three pre-registered readings from spec §4, each marked fired / not
   fired:
   - **Search ceiling** — median improves >= 10% at 100x vs baseline.
   - **Metric ceiling** — objective improves >= 10% but blind listen gains < 0.5/5.
   - **Reachability ceiling** — real/in-domain floor ratio does not shrink as
     budget goes 2 000 -> 200 000.
4. **Render-seed overfit check:** if `big_seeded` beats `baseline_seeded` on
   `score` but not on `heldout_score`, report that as the finding and do not
   claim search headroom.
5. Verdict, including "inconclusive" if readings conflict.

- [ ] **Step 6: Blind listen, then reveal**

Open `invert/runs/headroom/headroom.html`, score every lettered column 0-5
**before** opening `headroom_key.json`. Then join scores to arms via the key and
fill the ear column in the results doc.

- [ ] **Step 7: Commit the results doc**

```bash
cd /Users/stephenlavelle/Documents/bfxr2
git add docs/superpowers/plans/2026-07-25-headroom-probe-results.md
git commit -m "docs: headroom probe results and ceiling attribution

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Update the strategy docs**

Add a decision-log row to
`docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md` naming the
ceiling the probe found and the project it selects, and update the handoff note
`docs/superpowers/plans/2026-07-25-handoff-inverse-model.md` so the next cold
agent starts from the verdict rather than from bet (2). Commit.
