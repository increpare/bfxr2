# Inverse Model — Spectral/Audio Loss Alternative Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop optimizing the inverse model against parameter-MSE alone; add (a) an identifiability-weighted, curriculum-scheduled parameter loss and (b) a differentiable **surrogate synth** that supplies a spectral/audio-matching loss, so the model is rewarded for predicting parameters that *render to the right sound* rather than the exact ground-truth knobs.

**Architecture:** Two phases on top of the already-built v4 time features. Phase 1 measures each parameter's audio sensitivity by finite-differencing the real renderer, bakes those into per-parameter loss weights, and anneals an easy-first curriculum — cheap, no new model. Phase 2 trains a small neural surrogate `params → normalized feature stack` on the *existing* shards (no new rendering), freezes it, and adds `spectral_weight · MSE(surrogate(pred_params), input_features)` to the training loss. This is the standard fix for the many-to-one inverse (Masuda & Saito ISMIR 2021; the field's finding is parameter-loss < spectral-loss < combined).

**Tech Stack:** PyTorch (MPS default on this M1 Max), the existing `invert` + `match` packages, the native Node renderer for offline sensitivity probing.

**Related:**
- `docs/superpowers/plans/2026-07-23-inverse-model-v3-diagnosis.md` (diagnosis; Recs 1b/2/2b/4 are implemented here)
- `docs/superpowers/plans/2026-07-23-invert-time-features.md` (v4 pack — Tasks 1–3 done, Task 4 train+gate is a prerequisite of this plan)

## Global Constraints

- Python `>=3.12,<3.13`; run all module commands from `tools/` (module imports assume cwd `tools/`).
- Never edit `js/` (browser app). Never commit anything under `invert/data/` or `invert/runs/` (gitignored).
- `DATASET_VERSION` is currently `"v4"`; this plan does **not** change the feature pack, so it stays `"v4"` — no data regeneration is required for Phases 1–2.
- Default training device is MPS; keep `--device` overridable (`cpu`/`mps`/`cuda`) exactly as `invert/train.py` already exposes it.
- `masterVolume` is permalocked and not in the 30 searchable params; `SQUARE_ONLY = ("squareDuty", "dutySweep")` are inaudible off the square wavetype and are masked in the loss — every new loss term must preserve that mask.
- Feature stack is `(N_CHANNELS=70, N_FRAMES=128)`: 6 contours (`env_db, f0_log2, voiced, t_abs, centroid_log2, noisiness`) + 64 unblurred log-mel bands. Parameters are `unit ∈ [0,1]^30` (see `ParamSpace.names`), plus a categorical wavetype (`class_idx ∈ 0..11`).

**Prerequisite (from the time-features plan, do first if not already done):**

- [ ] Run `invert-time-features` Task 4: `make rebuild_inverse_model DATA=invert/data/v4 RUN=invert/runs/v4 EPOCHS=15 N=300000` (or, since `invert/data/v4` already exists, just `make train_inverse_model DATA=invert/data/v4 RUN=invert/runs/v4 EPOCHS=15`), then write `tools/invert/runs/v4/gate.md` comparing sustain/decay/frequency R² and in-domain one-shot median vs `v3`. **This `v4` param-only run is the baseline every gate below is measured against.**

---

## Scope

**In scope (this plan):**
- Phase 1 — observability analysis → identifiability-weighted parameter loss + easy-first curriculum + honest re-gate.
- Phase 2 — differentiable surrogate synth + combined (parameter + spectral) loss.

**Out of scope — separate follow-on plans (specified at the end), each depends on Phase 2 landing:**
- General-purpose regime: spectral-loss fine-tuning on unlabeled real SFX (needs the frozen surrogate + spectral loss from Phase 2).
- Grouped representation heads / cascade (diagnosis Rec 2b) and distributional (K-hypothesis) heads.

Each phase below produces a working, testable, independently gated deliverable.

---

## File Structure

**New files:**
- `tools/invert/observability.py` — offline per-parameter audio-sensitivity measurement (renderer finite differences) + sensitivity→weight transform.
- `tools/invert/surrogate.py` — `SurrogateSynth` module + `train_surrogate()` + CLI.
- `tools/tests/test_invert_observability.py`
- `tools/tests/test_invert_surrogate.py`
- `tools/tests/test_invert_spectral_loss.py`

**Modified files:**
- `tools/invert/constants.py` — add `IDENTIFIABILITY_WEIGHT` (30 floats) + `EASY_PARAM_COUNT`.
- `tools/invert/train.py` — weighted loss, curriculum schedule, optional surrogate/spectral term, new CLI flags.
- `tools/tests/test_invert_train_metrics.py` — extend for weighted loss + curriculum.
- `tools/Makefile` — `observability`, `train_surrogate`, and spectral-loss training targets.

---

# Phase 1 — Identifiability-weighted loss + curriculum

### Task 1: Per-parameter audio sensitivity (observability analysis)

**Files:**
- Create: `tools/invert/observability.py`
- Test: `tools/tests/test_invert_observability.py`

**Interfaces:**
- Consumes: `ParamSpace` (`.names`, `.wave_types`, `.params_dict(unit, wave_type)`, `.defaults_unit()`), `BfxrRenderer` (`.render(params, seed)`), `sample_unit(space, rng, *, mode)`, `pack_features(wave) -> (np.ndarray (70,128), float)`, `RENDER_SEED`, `SQUARE_ONLY`.
- Produces:
  - `param_sensitivity(space, renderer, *, n_probes=200, delta=0.05, seed=0) -> dict[str, float]` — mean ‖Δfeatures‖ per unit-perturbation for each of the 30 params.
  - `sensitivity_to_weights(sens: dict[str, float], names: list[str], *, floor: float = 0.1) -> list[float]` — per-param loss weights normalized to mean 1.0 over params above the floor, each clamped to `[floor, 4.0]`.

- [ ] **Step 1: Write the failing test for the pure transform**

```python
# tools/tests/test_invert_observability.py
from invert.observability import sensitivity_to_weights


def test_sensitivity_to_weights_normalizes_and_floors():
    names = ["a", "b", "c", "d"]
    # b is dead (0), a is very sensitive, c/d moderate
    sens = {"a": 10.0, "b": 0.0, "c": 2.0, "d": 3.0}
    w = sensitivity_to_weights(sens, names, floor=0.1)
    assert len(w) == 4
    # dead param floored, not zero
    assert w[1] == 0.1
    # sensitive param capped at 4.0
    assert w[0] == 4.0
    # weights are finite and positive
    assert all(0.0 < x <= 4.0 for x in w)
    # mean over non-floored params is ~1.0 before clamping bites; c and d straddle 1
    assert w[2] < w[3]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_observability.py::test_sensitivity_to_weights_normalizes_and_floors -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'invert.observability'`.

- [ ] **Step 3: Implement `observability.py`**

```python
# tools/invert/observability.py
from __future__ import annotations

import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import RENDER_SEED
from match.renderer import BfxrRenderer

from .constants import SILENCE_PEAK, SQUARE_ONLY
from .features_pack import pack_features
from .sampler import sample_unit


def _acceptable(wave) -> bool:
    if wave is None or len(wave) == 0:
        return False
    w = np.asarray(wave)
    if not np.isfinite(w).all():
        return False
    peak = float(np.max(np.abs(w)))
    return np.isfinite(peak) and peak >= SILENCE_PEAK


def param_sensitivity(
    space: ParamSpace,
    renderer: BfxrRenderer,
    *,
    n_probes: int = 200,
    delta: float = 0.05,
    seed: int = 0,
) -> dict[str, float]:
    """Mean ‖Δfeatures‖ / Δunit per parameter, over random operating points.

    A near-zero value means perturbing that knob does not change the rendered
    audio (unidentifiable from sound). Uses the REAL renderer so weights are
    truthful, not surrogate-approximated.
    """
    rng = np.random.default_rng(seed)
    names = list(space.names)
    accum = np.zeros(len(names), dtype=np.float64)
    counts = np.zeros(len(names), dtype=np.int64)
    wave_types = sorted(space.wave_types)

    for _ in range(n_probes):
        wt = int(rng.choice(wave_types))
        base_unit = sample_unit(space, rng, mode="biased")
        base_wave = renderer.render(space.params_dict(base_unit, wt), seed=RENDER_SEED)
        if not _acceptable(base_wave):
            continue
        base_feat, _ = pack_features(base_wave)
        for j, name in enumerate(names):
            if name in SQUARE_ONLY and wt != 0:
                continue  # inaudible off square; measured only on square
            u2 = base_unit.copy()
            step = delta if u2[j] + delta <= 1.0 else -delta
            u2[j] = float(np.clip(u2[j] + step, 0.0, 1.0))
            dstep = abs(u2[j] - base_unit[j])
            if dstep < 1e-9:
                continue
            wave2 = renderer.render(space.params_dict(u2, wt), seed=RENDER_SEED)
            if not _acceptable(wave2):
                continue
            feat2, _ = pack_features(wave2)
            accum[j] += float(np.linalg.norm(base_feat - feat2)) / dstep
            counts[j] += 1

    sens = accum / np.maximum(counts, 1)
    return {name: float(sens[j]) for j, name in enumerate(names)}


def sensitivity_to_weights(
    sens: dict[str, float],
    names: list[str],
    *,
    floor: float = 0.1,
) -> list[float]:
    """Per-param loss weights, mean ~1.0 over active params, clamped [floor, 4.0]."""
    vals = np.array([sens[n] for n in names], dtype=np.float64)
    active = vals > 0.0
    scale = vals[active].mean() if active.any() else 1.0
    if scale <= 0:
        scale = 1.0
    w = vals / scale
    w = np.clip(w, floor, 4.0)
    return [float(x) for x in w]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    p = argparse.ArgumentParser(description="Measure per-param audio sensitivity")
    p.add_argument("--n-probes", type=int, default=200)
    p.add_argument("--delta", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--jobs", type=int, default=None)
    args = p.parse_args(argv)

    space = ParamSpace()
    with BfxrRenderer(jobs=args.jobs) as renderer:
        sens = param_sensitivity(
            space, renderer, n_probes=args.n_probes, delta=args.delta, seed=args.seed
        )
    weights = sensitivity_to_weights(sens, list(space.names))
    out = {
        "sensitivity": sens,
        "weights": {n: weights[i] for i, n in enumerate(space.names)},
        "weights_list": weights,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the pure-transform test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_observability.py::test_sensitivity_to_weights_normalizes_and_floors -v`
Expected: PASS.

- [ ] **Step 5: Add a renderer-backed smoke test (asserts audible > dead)**

```python
# tools/tests/test_invert_observability.py  (append)
from match.bfxr_io import ParamSpace
from match.renderer import BfxrRenderer
from invert.observability import param_sensitivity


def test_param_sensitivity_ranks_audible_above_dead():
    space = ParamSpace()
    with BfxrRenderer(jobs=1) as renderer:
        sens = param_sensitivity(space, renderer, n_probes=12, seed=1)
    assert set(sens) == set(space.names)
    # frequency_start audibly changes the sound; flangerSweep barely does.
    assert sens["frequency_start"] > sens["flangerSweep"]
```

- [ ] **Step 6: Run the smoke test**

Run: `cd tools && uv run pytest tests/test_invert_observability.py -v`
Expected: PASS (needs Node renderer; ~a few seconds for 12 probes).

- [ ] **Step 7: Commit**

```bash
git add tools/invert/observability.py tools/tests/test_invert_observability.py
git commit -m "Add per-param audio-sensitivity (observability) analysis"
```

---

### Task 2: Bake identifiability weights into constants + weighted loss

**Files:**
- Modify: `tools/invert/constants.py`
- Modify: `tools/invert/train.py` (`invert_loss`)
- Modify: `tools/tests/test_invert_train_metrics.py`
- Modify: `tools/Makefile`

**Interfaces:**
- Consumes: `IDENTIFIABILITY_WEIGHT` (tuple of 30 floats, aligned to `ParamSpace.names` order).
- Produces: `invert_loss(..., unit_loss_weights: torch.Tensor | None = None)` — training loss uses weighted masked MSE; `parts["unit_mse"]` stays the **unweighted** masked MSE (comparable across runs and to prior gates).

- [ ] **Step 1: Generate the real weights and write them into constants**

Run: `cd tools && uv run python -m invert.observability --n-probes 300 --seed 0 > /tmp/obs.json`
Then read `/tmp/obs.json`'s `weights_list` (30 floats) and paste them into `constants.py` as below (values shown are the *shape*; use the generated numbers). Keep them in `ParamSpace.names` order.

```python
# tools/invert/constants.py  (append after CHANNEL_STD)

# Per-param loss weights ∝ audio sensitivity (invert.observability, n_probes=300,
# real renderer). Mean ~1.0 over audible params; dead params floored at 0.1.
# Order matches ParamSpace.names. Re-measure if the feature pack changes.
IDENTIFIABILITY_WEIGHT = (
    # <-- paste 30 floats from /tmp/obs.json "weights_list" here, one-per-param -->
)

# Easy-first curriculum: the N most-sensitive params are supervised from epoch 1;
# the rest ramp in (see train.curriculum_weights).
EASY_PARAM_COUNT = 12
```

- [ ] **Step 2: Add an assertion that the constant has the right length**

```python
# tools/invert/constants.py  (append at end of file)
assert len(IDENTIFIABILITY_WEIGHT) == N_PARAMS, (
    f"IDENTIFIABILITY_WEIGHT has {len(IDENTIFIABILITY_WEIGHT)}, expected {N_PARAMS}"
)
```

- [ ] **Step 3: Write the failing test for weighted loss**

```python
# tools/tests/test_invert_train_metrics.py  (append)
import torch
from match.bfxr_io import ParamSpace
from invert.train import invert_loss


def _fake_out(space, batch=4):
    n = len(space.names)
    return {
        "unit": torch.rand(batch, n, requires_grad=True),
        "wavetype_logits": torch.randn(batch, 12, requires_grad=True),
    }


def test_invert_loss_weights_scale_reported_mse_is_unweighted():
    space = ParamSpace()
    n = len(space.names)
    torch.manual_seed(0)
    out = _fake_out(space)
    tgt = torch.rand(4, n)
    wt = torch.zeros(4, dtype=torch.long)   # square, so no square-only masking
    cls = torch.zeros(4, dtype=torch.long)

    w_uniform = torch.ones(n)
    w_skew = torch.ones(n)
    w_skew[0] = 4.0  # up-weight param 0

    loss_u, parts_u = invert_loss(out, tgt, wt, cls, space, unit_loss_weights=w_uniform)
    loss_s, parts_s = invert_loss(out, tgt, wt, cls, space, unit_loss_weights=w_skew)

    # reported unit_mse is the plain masked MSE — identical regardless of weights
    assert abs(parts_u["unit_mse"] - parts_s["unit_mse"]) < 1e-6
    # the training loss does change when weights change
    assert abs(float(loss_u) - float(loss_s)) > 1e-6
```

- [ ] **Step 4: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py::test_invert_loss_weights_scale_reported_mse_is_unweighted -v`
Expected: FAIL with `TypeError: invert_loss() got an unexpected keyword argument 'unit_loss_weights'`.

- [ ] **Step 5: Implement weighted loss in `train.py`**

Replace the body of `invert_loss` (currently lines ~50–74) with:

```python
def invert_loss(
    out: dict[str, torch.Tensor],
    unit_tgt: torch.Tensor,
    wave_types: torch.Tensor,
    class_idx: torch.Tensor,
    space: ParamSpace,
    version: int = 1,
    unit_weight: float = 10.0,
    ce_weight: float = 0.5,
    unit_loss_weights: torch.Tensor | None = None,
) -> tuple[torch.Tensor, dict[str, float]]:
    unit_pred = select_unit_pred(out, class_idx, version)

    mask = torch.ones_like(unit_tgt)
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        mask[:, j] = (wave_types == 0).float()

    sq_err = (unit_pred - unit_tgt) ** 2
    # Reported unit_mse stays UNWEIGHTED so it is comparable across runs/gates.
    unit_mse = (sq_err * mask).sum() / mask.sum().clamp(min=1)

    if unit_loss_weights is None:
        weighted_mse = unit_mse
    else:
        w = unit_loss_weights.to(sq_err.device, sq_err.dtype).view(1, -1)
        wm = mask * w
        weighted_mse = (sq_err * wm).sum() / wm.sum().clamp(min=1)

    ce = F.cross_entropy(out["wavetype_logits"], class_idx.long())
    loss = unit_weight * weighted_mse + ce_weight * ce
    parts = {
        "unit_mse": float(unit_mse.detach()),
        "ce": float(ce.detach()),
    }
    return loss, parts
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py::test_invert_loss_weights_scale_reported_mse_is_unweighted -v`
Expected: PASS.

- [ ] **Step 7: Add a Makefile target for regenerating weights**

```makefile
# tools/Makefile  (add to .PHONY list and as a target)
observability:
	uv run python -m invert.observability --n-probes 300 --seed 0
```

- [ ] **Step 8: Run the full metrics test file to confirm no regressions**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py -v`
Expected: PASS (all).

- [ ] **Step 9: Commit**

```bash
git add tools/invert/constants.py tools/invert/train.py tools/tests/test_invert_train_metrics.py tools/Makefile
git commit -m "Identifiability-weighted invert loss (unweighted mse still reported)"
```

---

### Task 3: Easy-first curriculum schedule

**Files:**
- Modify: `tools/invert/train.py` (`curriculum_weights`, wire into `train()` + `_run_epoch`)
- Modify: `tools/tests/test_invert_train_metrics.py`

**Interfaces:**
- Produces: `curriculum_weights(base_weights: torch.Tensor, easy_mask: torch.Tensor, epoch: int, curriculum_epochs: int) -> torch.Tensor` — easy params keep `base_weights`; hard params scale by `alpha = min(1, epoch / max(1, curriculum_epochs))` toward `base_weights`; `curriculum_epochs == 0` returns `base_weights` unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_invert_train_metrics.py  (append)
from invert.train import curriculum_weights


def test_curriculum_ramps_hard_params_only():
    base = torch.tensor([2.0, 2.0, 1.0, 1.0])
    easy = torch.tensor([1.0, 1.0, 0.0, 0.0])  # first two are "easy"
    # epoch 1 of 4: hard params at 0.25 * base; easy unchanged
    w1 = curriculum_weights(base, easy, epoch=1, curriculum_epochs=4)
    assert torch.allclose(w1, torch.tensor([2.0, 2.0, 0.25, 0.25]))
    # at/after curriculum end: full base weights
    w4 = curriculum_weights(base, easy, epoch=4, curriculum_epochs=4)
    assert torch.allclose(w4, base)
    # disabled: returns base unchanged
    w0 = curriculum_weights(base, easy, epoch=1, curriculum_epochs=0)
    assert torch.allclose(w0, base)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py::test_curriculum_ramps_hard_params_only -v`
Expected: FAIL with `ImportError: cannot import name 'curriculum_weights'`.

- [ ] **Step 3: Implement `curriculum_weights` in `train.py`**

```python
# tools/invert/train.py  (add near invert_loss)
def curriculum_weights(
    base_weights: torch.Tensor,
    easy_mask: torch.Tensor,
    epoch: int,
    curriculum_epochs: int,
) -> torch.Tensor:
    """Easy params keep base weight from epoch 1; hard params ramp in linearly."""
    if curriculum_epochs <= 0:
        return base_weights
    alpha = min(1.0, epoch / max(1, curriculum_epochs))
    hard_scale = easy_mask + (1.0 - easy_mask) * alpha
    return base_weights * hard_scale
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py::test_curriculum_ramps_hard_params_only -v`
Expected: PASS.

- [ ] **Step 5: Wire weights + curriculum into `train()` and `_run_epoch`**

In `_run_epoch`, add a keyword arg `unit_loss_weights: torch.Tensor | None = None` and pass it into the `invert_loss(...)` call:

```python
        loss, parts = invert_loss(
            out, unit, wt, cls, space,
            version=model.version,
            unit_weight=unit_weight,
            ce_weight=ce_weight,
            unit_loss_weights=unit_loss_weights,
        )
```

In `train()`, after `space = ParamSpace()` build the base weights + easy mask once:

```python
    from .constants import IDENTIFIABILITY_WEIGHT, EASY_PARAM_COUNT
    base_w = torch.tensor(IDENTIFIABILITY_WEIGHT, dtype=torch.float32, device=device_t)
    easy_idx = torch.topk(base_w, k=EASY_PARAM_COUNT).indices
    easy_mask = torch.zeros_like(base_w)
    easy_mask[easy_idx] = 1.0
```

Add `curriculum_epochs: int = 0` to `train()`'s signature. Inside the epoch loop, compute the epoch's weights and pass them to both train and val `_run_epoch` calls:

```python
            epoch_w = curriculum_weights(base_w, easy_mask, epoch, curriculum_epochs)
```

(pass `unit_loss_weights=epoch_w` to the train `_run_epoch`; pass `unit_loss_weights=None` to the val `_run_epoch` so validation reports the plain unweighted `unit_mse` used by `best.pt` selection and the gate.)

- [ ] **Step 6: Add `--curriculum-epochs` to the CLI**

```python
    p.add_argument("--curriculum-epochs", type=int, default=0,
                   help="Ramp hard-param loss weights in over N epochs (0=off)")
```
and thread `curriculum_epochs=args.curriculum_epochs` into the `train(...)` call in `main`.

- [ ] **Step 7: Smoke-run one training epoch to confirm wiring (tiny synthetic shard)**

```python
# tools/tests/test_invert_train_metrics.py  (append)
import numpy as np
from pathlib import Path
from invert.dataset import write_shard
from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES, N_PARAMS
from invert.train import train


def test_train_smoke_with_curriculum(tmp_path: Path):
    n = 32
    payload = {
        "features": torch.rand(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.zeros(n),
        "unit": torch.rand(n, N_PARAMS),
        "wave_type": torch.zeros(n, dtype=torch.long),
        "class_idx": torch.zeros(n, dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    data = tmp_path / "data"
    write_shard(data / "shard_0000.pt", payload)
    (data / "manifest.json").write_text('{"n": %d}' % n)
    best = train(data, tmp_path / "run", epochs=2, batch_size=16,
                 curriculum_epochs=2, device="cpu")
    assert best.is_file()
```

- [ ] **Step 8: Run the smoke test**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py::test_train_smoke_with_curriculum -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add tools/invert/train.py tools/tests/test_invert_train_metrics.py
git commit -m "Easy-first curriculum schedule for invert loss weights"
```

---

### Task 4 (run): Train weighted+curriculum model and re-gate honestly

**Files:**
- Create: `tools/invert/runs/v5_weighted/gate.md` (not committed — gitignored dir)
- Modify: `tools/Makefile` (parameterize train target for weights/curriculum)

- [ ] **Step 1: Add a Makefile convenience target**

```makefile
# tools/Makefile
CURRICULUM  ?= 5
train_inverse_weighted:
	uv run python -m invert.train --data $(DATA) --out $(RUN) \
		--version $(VERSION) --epochs $(EPOCHS) --curriculum-epochs $(CURRICULUM)
```
(reuse the existing `VERSION ?= 1`, `EPOCHS`, `DATA`, `RUN` vars; add `VERSION ?= 1` if not already present.)

- [ ] **Step 2: Train on the existing v4 shards**

Run: `cd tools && make train_inverse_weighted DATA=invert/data/v4 RUN=invert/runs/v5_weighted EPOCHS=15 CURRICULUM=5`
Expected: 15 epochs; stderr per-epoch `val unit_mse … top3 … worst r2 …`.

- [ ] **Step 3: Evaluate seeder + one-shot**

Run: `cd tools && make eval_inverse_model_all RUN=invert/runs/v5_weighted CKPT=invert/runs/v5_weighted/best.pt`
Expected: `eval_bfxr/results.md` and `eval_targets/results.md` written.

- [ ] **Step 4: Write `gate.md`** comparing to the `v4` param-only baseline. **Honest gate (not the old blanket R²≥0.8):**
  - R² of the `EASY_PARAM_COUNT` most-identifiable params should each be ≥ their `v4` value (no regression on recoverable knobs);
  - dead-param R² is *not* gated (expected ~0);
  - in-domain one-shot median ≤ `v4`;
  - `eval_targets` seeded-wins ≥ `v4` (currently 8/32).

- [ ] **Step 5: Commit the gate note reference (doc only, runs dir is gitignored)**

```bash
git add docs/superpowers/plans/2026-07-23-inverse-model-spectral-loss.md
git commit -m "Phase 1 complete: weighted+curriculum invert run v5_weighted gated"
```

**Gate decision:** if Phase 1 improves the seeder/one-shot, proceed to Phase 2. If not (weights help nothing), Phase 2's spectral loss is still warranted — it attacks the same ill-posedness more directly — so proceed regardless, but record the Phase 1 outcome.

---

# Phase 2 — Differentiable surrogate + spectral loss

### Task 5: `SurrogateSynth` module

**Files:**
- Create: `tools/invert/surrogate.py`
- Test: `tools/tests/test_invert_surrogate.py`

**Interfaces:**
- Produces: `SurrogateSynth(width=128)` with `forward(unit: (B,30), wavetype_onehot: (B,12), log_duration: (B,)) -> (B, 70, 128)` predicting the **normalized** feature stack (same space as `normalize_channels(features)`).

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_invert_surrogate.py
import torch
from invert.surrogate import SurrogateSynth
from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES


def test_surrogate_shapes_and_backward():
    m = SurrogateSynth(width=32)
    b = 5
    unit = torch.rand(b, N_PARAMS, requires_grad=True)
    onehot = torch.nn.functional.one_hot(
        torch.zeros(b, dtype=torch.long), N_WAVETYPES
    ).float()
    log_dur = torch.zeros(b)
    out = m(unit, onehot, log_dur)
    assert out.shape == (b, N_CHANNELS, N_FRAMES)
    out.sum().backward()
    assert unit.grad is not None and torch.isfinite(unit.grad).all()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_surrogate.py::test_surrogate_shapes_and_backward -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'invert.surrogate'`.

- [ ] **Step 3: Implement `SurrogateSynth`**

```python
# tools/invert/surrogate.py
from __future__ import annotations

import torch
import torch.nn as nn

from .constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES


class SurrogateSynth(nn.Module):
    """Differentiable approximation of params -> normalized feature stack.

    Trained to imitate the (renderer -> pack_features -> normalize) pipeline on
    the existing shards, then frozen to supply a spectral/audio loss to the
    inverse model (bfxr's real DSP is not differentiable).
    """

    def __init__(self, width: int = 128):
        super().__init__()
        self.width = width
        self.n0 = N_FRAMES // 8  # 16 -> upsample x8 -> 128
        in_dim = N_PARAMS + N_WAVETYPES + 1
        self.fc = nn.Sequential(
            nn.Linear(in_dim, width * 2 * self.n0),
            nn.ReLU(inplace=True),
        )
        self.deconv = nn.Sequential(
            nn.ConvTranspose1d(width * 2, width * 2, 4, stride=2, padding=1),  # 16->32
            nn.ReLU(inplace=True),
            nn.ConvTranspose1d(width * 2, width, 4, stride=2, padding=1),      # 32->64
            nn.ReLU(inplace=True),
            nn.ConvTranspose1d(width, width, 4, stride=2, padding=1),          # 64->128
            nn.ReLU(inplace=True),
            nn.Conv1d(width, N_CHANNELS, 5, padding=2),
        )

    def forward(
        self,
        unit: torch.Tensor,
        wavetype_onehot: torch.Tensor,
        log_duration: torch.Tensor,
    ) -> torch.Tensor:
        x = torch.cat([unit, wavetype_onehot, log_duration.unsqueeze(-1)], dim=-1)
        h = self.fc(x).view(-1, self.width * 2, self.n0)
        return self.deconv(h)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_surrogate.py::test_surrogate_shapes_and_backward -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/invert/surrogate.py tools/tests/test_invert_surrogate.py
git commit -m "Add SurrogateSynth (params -> normalized features) module"
```

---

### Task 6: Train the surrogate on existing shards

**Files:**
- Modify: `tools/invert/surrogate.py` (add `train_surrogate()` + CLI)
- Modify: `tools/tests/test_invert_surrogate.py`
- Modify: `tools/Makefile`

**Interfaces:**
- Consumes: `InvertShardDataset`, `normalize_channels`, `wave_type_index_map`.
- Produces: `train_surrogate(data, out, *, epochs=10, batch_size=64, lr=1e-3, width=128, device=None) -> Path` writing `surrogate.pt` = `{"model_state", "width", "channel_mean", "channel_std"}`.

- [ ] **Step 1: Write the failing test (loss decreases on a tiny synthetic shard)**

```python
# tools/tests/test_invert_surrogate.py  (append)
from pathlib import Path
from invert.surrogate import train_surrogate
from invert.dataset import write_shard
from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES, N_PARAMS


def test_train_surrogate_writes_checkpoint(tmp_path: Path):
    n = 48
    payload = {
        "features": torch.rand(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.zeros(n),
        "unit": torch.rand(n, N_PARAMS),
        "wave_type": torch.zeros(n, dtype=torch.long),
        "class_idx": torch.zeros(n, dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    data = tmp_path / "data"
    write_shard(data / "shard_0000.pt", payload)
    (data / "manifest.json").write_text('{"n": %d}' % n)
    out = train_surrogate(data, tmp_path / "sur", epochs=3, batch_size=16, device="cpu")
    assert out.is_file()
    ck = torch.load(out, weights_only=False)
    assert ck["width"] == 128 and "model_state" in ck
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_surrogate.py::test_train_surrogate_writes_checkpoint -v`
Expected: FAIL with `ImportError: cannot import name 'train_surrogate'`.

- [ ] **Step 3: Implement `train_surrogate()` + CLI**

```python
# tools/invert/surrogate.py  (append)
from pathlib import Path

import torch.nn.functional as F
from torch.utils.data import DataLoader

from .constants import CHANNEL_MEAN, CHANNEL_STD, N_WAVETYPES
from .dataset import InvertShardDataset
from .features_pack import normalize_channels


def _default_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def train_surrogate(
    data: Path,
    out: Path,
    *,
    epochs: int = 10,
    batch_size: int = 64,
    lr: float = 1e-3,
    width: int = 128,
    device: str | None = None,
) -> Path:
    device_t = torch.device(device or _default_device())
    manifest = Path(data) / "manifest.json"
    ds_version = None
    if manifest.is_file():
        import json
        ds_version = json.loads(manifest.read_text()).get("dataset_version")
    ds = InvertShardDataset(data, dataset_version=ds_version)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model = SurrogateSynth(width=width).to(device_t)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ckpt = out / "surrogate.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        total, nb = 0.0, 0
        for batch in loader:
            feats = normalize_channels(batch["features"].to(device_t).float())
            unit = batch["unit"].to(device_t).float()
            onehot = F.one_hot(batch["class_idx"].to(device_t), N_WAVETYPES).float()
            log_dur = batch["log_duration"].to(device_t).float()
            opt.zero_grad(set_to_none=True)
            pred = model(unit, onehot, log_dur)
            loss = F.mse_loss(pred, feats)
            loss.backward()
            opt.step()
            total += float(loss.detach())
            nb += 1
        import sys
        print(f"surrogate epoch {epoch}: mse {total / max(nb,1):.4f}", file=sys.stderr)

    torch.save(
        {
            "model_state": model.state_dict(),
            "width": width,
            "channel_mean": list(CHANNEL_MEAN),
            "channel_std": list(CHANNEL_STD),
        },
        ckpt,
    )
    return ckpt


def load_surrogate(path: Path, device: torch.device) -> SurrogateSynth:
    ck = torch.load(Path(path), weights_only=False)
    model = SurrogateSynth(width=ck["width"]).to(device)
    model.load_state_dict(ck["model_state"])
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return model


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Train the differentiable surrogate synth")
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--device", choices=("cpu", "mps", "cuda"), default=None)
    args = p.parse_args(argv)
    out = train_surrogate(
        args.data, args.out, epochs=args.epochs, batch_size=args.batch_size,
        lr=args.lr, width=args.width, device=args.device,
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_surrogate.py -v`
Expected: PASS (all).

- [ ] **Step 5: Add Makefile target and train the real surrogate**

```makefile
# tools/Makefile
SURROGATE   ?= invert/runs/surrogate
train_surrogate:
	uv run python -m invert.surrogate --data $(DATA) --out $(SURROGATE) --epochs $(EPOCHS)
```
Run: `cd tools && make train_surrogate DATA=invert/data/v4 SURROGATE=invert/runs/surrogate EPOCHS=20`
Expected: decreasing `surrogate epoch N: mse …`; `invert/runs/surrogate/surrogate.pt` written.

- [ ] **Step 6: Sanity-gate the surrogate** — confirm it is directionally correct (a one-off, record the number in the commit message): the surrogate's reconstruction MSE on a held-out shard should be well below the variance of the normalized features (which is ~1.0 by construction), e.g. < 0.3. If it is ~1.0, the surrogate learned nothing and Phase 2 must not proceed until it trains.

- [ ] **Step 7: Commit**

```bash
git add tools/invert/surrogate.py tools/tests/test_invert_surrogate.py tools/Makefile
git commit -m "Train differentiable surrogate synth on existing shards"
```

---

### Task 7: Combined (parameter + spectral) loss in inverse training

**Files:**
- Modify: `tools/invert/train.py` (`invert_loss` spectral term; `_run_epoch` + `train()` wiring; CLI)
- Create: `tools/tests/test_invert_spectral_loss.py`

**Interfaces:**
- Produces: `invert_loss(..., surrogate=None, spectral_weight=0.0, norm_features=None, log_duration=None)`. When `surrogate` is provided and `spectral_weight > 0`, add `spectral_weight * MSE(surrogate(pred_unit, onehot(class_idx), log_duration), norm_features)`; `parts` gains `"spectral"`. Uses **ground-truth** `class_idx` for the onehot (isolates the knob/spectral effect; soft-wavetype is a documented follow-on).

- [ ] **Step 1: Write the failing test**

```python
# tools/tests/test_invert_spectral_loss.py
import torch
from match.bfxr_io import ParamSpace
from invert.surrogate import SurrogateSynth
from invert.train import invert_loss
from invert.constants import N_CHANNELS, N_FRAMES


def test_spectral_term_added_and_backprops_to_unit():
    space = ParamSpace()
    n = len(space.names)
    b = 4
    out = {
        "unit": torch.rand(b, n, requires_grad=True),
        "wavetype_logits": torch.randn(b, 12),
    }
    tgt = torch.rand(b, n)
    wt = torch.zeros(b, dtype=torch.long)
    cls = torch.zeros(b, dtype=torch.long)
    surrogate = SurrogateSynth(width=16).eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)
    norm_feats = torch.rand(b, N_CHANNELS, N_FRAMES)
    log_dur = torch.zeros(b)

    loss_no, parts_no = invert_loss(out, tgt, wt, cls, space)
    assert "spectral" not in parts_no

    loss_sp, parts_sp = invert_loss(
        out, tgt, wt, cls, space,
        surrogate=surrogate, spectral_weight=1.0,
        norm_features=norm_feats, log_duration=log_dur,
    )
    assert "spectral" in parts_sp and parts_sp["spectral"] >= 0.0
    loss_sp.backward()
    assert out["unit"].grad is not None and torch.isfinite(out["unit"].grad).all()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_spectral_loss.py -v`
Expected: FAIL with `TypeError: invert_loss() got an unexpected keyword argument 'surrogate'`.

- [ ] **Step 3: Extend `invert_loss` with the spectral term**

Add the new keyword args and the spectral block. Full updated signature + additions (keep the Task 2 weighted body; insert the spectral term before building `loss`):

```python
def invert_loss(
    out, unit_tgt, wave_types, class_idx, space,
    version: int = 1,
    unit_weight: float = 10.0,
    ce_weight: float = 0.5,
    unit_loss_weights: torch.Tensor | None = None,
    surrogate=None,
    spectral_weight: float = 0.0,
    norm_features: torch.Tensor | None = None,
    log_duration: torch.Tensor | None = None,
):
    # ... unchanged: unit_pred, mask, unit_mse, weighted_mse, ce ...
    loss = unit_weight * weighted_mse + ce_weight * ce
    parts = {"unit_mse": float(unit_mse.detach()), "ce": float(ce.detach())}

    if surrogate is not None and spectral_weight > 0.0:
        assert norm_features is not None and log_duration is not None
        onehot = F.one_hot(class_idx.long(), out["wavetype_logits"].shape[1]).float()
        pred_feat = surrogate(unit_pred, onehot, log_duration)
        spectral = F.mse_loss(pred_feat, norm_features)
        loss = loss + spectral_weight * spectral
        parts["spectral"] = float(spectral.detach())

    return loss, parts
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_spectral_loss.py -v`
Expected: PASS.

- [ ] **Step 5: Wire surrogate into `_run_epoch` and `train()`**

In `_run_epoch`, accept `surrogate=None, spectral_weight=0.0`, and pass `surrogate=surrogate, spectral_weight=spectral_weight, norm_features=x, log_duration=log_dur` into `invert_loss` (note `x` is already the normalized features; `log_dur` is already in scope). Accumulate `parts.get("spectral", 0.0)` into a `total_spectral` and add `"spectral"` to the returned metrics dict.

In `train()`, add params `surrogate_path: Path | None = None, spectral_weight: float = 0.0`. After building the model:

```python
    surrogate = None
    if surrogate_path is not None and spectral_weight > 0.0:
        from .surrogate import load_surrogate
        surrogate = load_surrogate(surrogate_path, device_t)
```
Pass `surrogate=surrogate, spectral_weight=spectral_weight` into both `_run_epoch` calls. Add `"spectral_weight": spectral_weight` and `"surrogate": str(surrogate_path) if surrogate_path else None` to the saved `best.pt` dict for provenance.

- [ ] **Step 6: Add CLI flags**

```python
    p.add_argument("--surrogate", type=Path, default=None,
                   help="Path to surrogate.pt; enables spectral loss")
    p.add_argument("--spectral-weight", type=float, default=0.0)
```
and thread `surrogate_path=args.surrogate, spectral_weight=args.spectral_weight` into `train(...)`.

- [ ] **Step 7: Smoke-run combined-loss training (synthetic shard + tiny surrogate)**

```python
# tools/tests/test_invert_spectral_loss.py  (append)
from pathlib import Path
from invert.surrogate import train_surrogate
from invert.dataset import write_shard
from invert.constants import DATASET_VERSION, N_PARAMS
from invert.train import train


def test_train_with_spectral_loss_smoke(tmp_path: Path):
    n = 48
    payload = {
        "features": torch.rand(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.zeros(n),
        "unit": torch.rand(n, N_PARAMS),
        "wave_type": torch.zeros(n, dtype=torch.long),
        "class_idx": torch.zeros(n, dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    data = tmp_path / "data"
    write_shard(data / "shard_0000.pt", payload)
    (data / "manifest.json").write_text('{"n": %d}' % n)
    sur = train_surrogate(data, tmp_path / "sur", epochs=2, batch_size=16, device="cpu")
    best = train(data, tmp_path / "run", epochs=2, batch_size=16,
                 surrogate_path=sur, spectral_weight=1.0, device="cpu")
    assert best.is_file()
```

- [ ] **Step 8: Run the smoke test**

Run: `cd tools && uv run pytest tests/test_invert_spectral_loss.py -v`
Expected: PASS (all).

- [ ] **Step 9: Commit**

```bash
git add tools/invert/train.py tools/tests/test_invert_spectral_loss.py
git commit -m "Combined parameter+spectral invert loss via frozen surrogate"
```

---

### Task 8 (run): Train the combined-loss model and gate vs Phase 1

**Files:**
- Create: `tools/invert/runs/v6_spectral/gate.md` (gitignored)
- Modify: `tools/Makefile`

- [ ] **Step 1: Add a Makefile target**

```makefile
# tools/Makefile
SPECTRAL_W  ?= 1.0
train_inverse_spectral:
	uv run python -m invert.train --data $(DATA) --out $(RUN) \
		--version $(VERSION) --epochs $(EPOCHS) --curriculum-epochs $(CURRICULUM) \
		--surrogate $(SURROGATE)/surrogate.pt --spectral-weight $(SPECTRAL_W)
```

- [ ] **Step 2: Train combined-loss model**

Run: `cd tools && make train_inverse_spectral DATA=invert/data/v4 RUN=invert/runs/v6_spectral SURROGATE=invert/runs/surrogate EPOCHS=15 CURRICULUM=5 SPECTRAL_W=1.0`
Expected: 15 epochs; `train_log.jsonl` rows now include `spectral` in train/val parts.

- [ ] **Step 3: Sweep spectral weight if needed** — if one-shot does not improve, try `SPECTRAL_W=0.3` and `SPECTRAL_W=3.0` (two more runs) to find the balance where re-rendered one-shot audio improves without wrecking `unit_mse`/top-3.

- [ ] **Step 4: Evaluate**

Run: `cd tools && make eval_inverse_model_all RUN=invert/runs/v6_spectral CKPT=invert/runs/v6_spectral/best.pt`

- [ ] **Step 5: Write `gate.md`** vs `v5_weighted` and `v4`. **Primary gate is the audio metric, per the research** (spectral > parameter loss for perceptual match):
  - in-domain one-shot median strictly below `v5_weighted` (the headline: combined loss should be where one-shot finally moves);
  - `eval_bfxr` seeded-wins ≥ `v5_weighted`;
  - `eval_targets` seeded-wins ≥ `v5_weighted` (≥ 8/32);
  - `unit_mse` and top-3 not materially worse (spectral loss trading exact params for right sound is acceptable and expected).

- [ ] **Step 6: Commit the plan progress**

```bash
git add docs/superpowers/plans/2026-07-23-inverse-model-spectral-loss.md tools/Makefile
git commit -m "Phase 2 complete: combined-loss run v6_spectral gated"
```

---

## Follow-on plans (out of scope here — write with superpowers:writing-plans when Phase 2 lands)

These are separable subsystems that each depend on the frozen surrogate + spectral loss existing:

1. **General-purpose regime — spectral-loss fine-tuning on unlabeled real SFX.** The surrogate + spectral loss lets you fine-tune on `targets/` and `targets_from_bfxr/` audio *with no parameter labels* (loss = spectral only, since ground-truth params don't exist for real sounds). Directly mirrors Masuda & Saito's semi-supervised result (best out-of-domain matches came from spectral-loss adaptation on real audio). Needs: a real-audio `Dataset` that packs wavs through `pack_features`, a fine-tune entry point that runs spectral-only loss with a low LR from a Phase-2 checkpoint, and a train/holdout split of the real targets so gains are measured on held-out sounds. Watch the domain-shift caveat from the diagnosis (the model may hallucinate bfxr-specific fine structure on off-manifold audio — pair with domain-robustness augmentation if seeds degrade).

2. **Grouped representation heads / cascade (diagnosis Rec 2b) + distributional heads.** Shared trunk → representation branches (envelope/pitch on time-resolved contours; timbre on sharp mel) → grouped heads, with the conditional cascade (wavetype + gross pitch first, hard knobs conditioned on the residual). Subsumes the existing `version=2` per-wavetype heads. K-hypothesis output only if post–Phase-2 `frequency_start` residual histograms show bimodal ±octave error (they were unimodal at v3 — no trigger yet).

---

## Self-Review

- **Spec coverage:** Rec 2 (identifiability weighting) → Tasks 1–2; Rec 2b observability analysis → Task 1; curriculum (the mid-turn idea, recast as a supervision schedule) → Task 3; Rec 4 / research spectral loss via differentiable surrogate → Tasks 5–8; honest re-gate → Tasks 4 & 8; two-regime general-purpose + grouped/distributional heads → explicitly deferred to named follow-on plans. v4 time-fix (Rec 1/1b) is a prerequisite, already implemented.
- **Placeholders:** the only intentional fill-in is `IDENTIFIABILITY_WEIGHT`'s 30 numbers in Task 2 Step 1 — they are *generated by a command in that same step* (`uv run python -m invert.observability`), not left to guesswork; every code/test step contains complete code.
- **Type consistency:** `invert_loss` keyword args (`unit_loss_weights`, `surrogate`, `spectral_weight`, `norm_features`, `log_duration`) are introduced in Tasks 2/7 and consumed with the same names in `_run_epoch`/`train()`; `curriculum_weights(base_weights, easy_mask, epoch, curriculum_epochs)` matches between Task 3 definition and use; `SurrogateSynth.forward(unit, wavetype_onehot, log_duration)` matches between Tasks 5/6/7; `train_surrogate(...) -> Path` / `load_surrogate(...)` names are consistent across Tasks 6/7.
