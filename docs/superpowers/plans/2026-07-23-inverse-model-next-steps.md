# Inverse Model Next Steps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the inverse model actually learn parameter regression (the v1 run learned ~nothing on the knobs), then close the gap on bfxr's own preset sounds.

**Architecture:** Three gated waves. Wave 1 fixes model + loss (time-preserving readout instead of global average pooling, rebalanced loss, per-param R² instrumentation) and retrains on the *existing* 300k shards. Wave 2 fixes the data distribution (harvest the app's own preset generators headlessly, add few-knobs-changed sampling) and regenerates. Wave 3 attacks residual multimodality (per-wavetype heads, Huber loss). Each wave has a numeric gate; don't start the next wave until the previous gate is evaluated.

**Tech Stack:** PyTorch (MPS), numpy, existing `tools/invert/` + `tools/match/` packages, Node `tools/render/bfxr_context.js` for preset harvesting, native renderer for audio.

**Related docs:**
- `docs/superpowers/specs/2026-07-23-inverse-model-design.md` — approved design.
- `docs/superpowers/specs/2026-07-23-inverse-model-next-steps.md` — v1 postmortem this plan implements. One deliberate deviation: the postmortem sequences "fix loss first, architecture after loss moves"; this plan does both in wave 1, because the per-param R² evidence below shows time-structured params (`sustainTime` R² 0.00) cannot be recovered through a global average pool *at any loss weight* — and Task 1's instrumentation will attribute the improvement anyway.

## Diagnosis (evidence from run `invert/runs/v1`)

Trained 30 epochs on 300k examples:

- `unit_mse` 0.076 → 0.073 — **≈ the prior variance of the labels**, i.e. the regression head predicts per-param marginal means, conditioned on nothing. Train ≈ val from epoch 1: failing to fit, not overfitting.
- Wave-type classification learned *something* but overfits: train CE 0.94 vs val CE 1.55 by epoch 30; best val was around epoch 8. (Top-1 56% / top-3 81% measured on the train split; val will be measured properly once Task 1 lands.)
- Per-param R² (6k examples): `frequency_start` **0.20** — the f0 contour is an input channel; `sustainTime` **0.00**, `decayTime` **0.02** — the volume envelope is an input channel. Best params: `attackTime` 0.37, `compressionAmount` 0.36. These failures are on *fully identifiable* params — multimodality is NOT the current bottleneck.
- Match evals: seeded wins vs current only 3/9 on bfxr presets, 7/32 on real targets; one-shot scores 2.8–11.8 on bfxr's own presets (good ≈ <1). Seeds currently contribute ~nothing.

Two structural causes fit all of this:

1. **GAP bottleneck** — `AdaptiveAvgPool1d(1)` averages the whole timeline into one vector before the heads. *When* things happen (sustain vs decay, rising vs falling, jump onset) is exactly what gets destroyed; the worst-R² params are the time-structured ones.
2. **Loss imbalance** — `loss = unit_mse + ce` with CE ≈ 1.5 vs MSE ≈ 0.073: classification outweighs regression ~20:1 on the shared encoder, and `best.pt` selection uses the CE-dominated total (so it also selects for the overfit-prone term).

## Global Constraints

- All commands run from `tools/` (`cd /Users/stephenlavelle/Documents/bfxr2/tools`); Python via `uv run …`.
- `js/` stays untouched (browser app). `tools/render/bfxr_context.js` is tools-side and may be extended, but the render path (`__render`, worker protocol, goldens) must not change behavior — native parity tests must keep passing.
- Existing checkpoints must keep loading: any new model constructor arg needs a backward-compatible default at load time (`ckpt.get(...)`).
- Directory naming gotcha: `invert/data/v1` currently holds shards with `DATASET_VERSION="v2"` (dir name is historical). Wave 1 reuses those shards as-is; wave 2 writes `invert/data/v3`.
- Fast test suite must stay green after every task: `uv run pytest -q` (currently 71 passed, 6 deselected).
- Known upstream app bug, deliberately NOT fixed here: `generate_pickup_coin`/`generate_powerup` call `set_param("pitch_jump_Speed", …)` (`js/synths/Bfxr.js:335,428`) — the param doesn't exist (real name `pitch_jump_repeat_speed`), so `set_param` no-ops with a console.error. Harvested preset data reproduces the app's *actual* behavior, which is what the eval targets contain. Fixing the app is a separate user decision (it would change what the presets sound like in the app itself).

---

# Wave 1 — make the regression head learn (no data regen needed)

### Task 1: Per-param R² + wave-type accuracy instrumentation

Without this, every future run is a black box. Metrics land in `train_log.jsonl` so runs are comparable.

**Files:**
- Modify: `tools/invert/train.py`
- Test: `tools/tests/test_invert_train_metrics.py` (new)

**Interfaces:**
- Produces: `per_param_r2(pred: torch.Tensor, tgt: torch.Tensor, names: list[str]) -> dict[str, float]`; `wavetype_topk_accuracy(logits: torch.Tensor, class_idx: torch.Tensor, k: int) -> float`; `select_unit_pred(out: dict, class_idx: torch.Tensor, version: int) -> torch.Tensor` — all importable from `invert.train`. Validation rows in `train_log.jsonl` gain `val.r2` (dict param→float), `val.wavetype_top1`, `val.wavetype_top3`.

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_invert_train_metrics.py
import torch

from invert.train import per_param_r2, select_unit_pred, wavetype_topk_accuracy
from match.bfxr_io import ParamSpace


def test_per_param_r2_perfect_prediction_is_one():
    tgt = torch.rand(200, 30)
    names = list(ParamSpace().names)
    r2 = per_param_r2(tgt, tgt, names)
    assert set(r2) == set(names)
    assert all(v > 0.999 for v in r2.values())


def test_per_param_r2_mean_prediction_is_zero():
    tgt = torch.rand(500, 30)
    pred = tgt.mean(dim=0, keepdim=True).expand_as(tgt)
    r2 = per_param_r2(pred, tgt, list(ParamSpace().names))
    assert all(abs(v) < 0.02 for v in r2.values())


def test_wavetype_topk_accuracy():
    # logits rank class 0 first, class 1 second for every row
    logits = torch.tensor([[3.0, 2.0, 1.0]] * 4)
    cls = torch.tensor([0, 1, 1, 2])
    assert wavetype_topk_accuracy(logits, cls, 1) == 0.25
    assert wavetype_topk_accuracy(logits, cls, 2) == 0.75


def test_select_unit_pred_versions():
    out_v1 = {"unit": torch.rand(4, 30)}
    assert torch.equal(select_unit_pred(out_v1, torch.zeros(4).long(), 1), out_v1["unit"])
    per_class = torch.rand(4, 12, 30)
    cls = torch.tensor([0, 3, 7, 11])
    got = select_unit_pred({"unit_per_class": per_class}, cls, 2)
    for b in range(4):
        assert torch.equal(got[b], per_class[b, cls[b]])
```

- [ ] **Step 2: Run tests, verify failure**

Run: `uv run pytest tests/test_invert_train_metrics.py -q`
Expected: ImportError (`per_param_r2` not defined).

- [ ] **Step 3: Implement in `invert/train.py`**

Add the three helpers, and refactor `invert_loss` to use `select_unit_pred` (it currently duplicates the v1/v2 selection inline):

```python
def select_unit_pred(
    out: dict[str, torch.Tensor], class_idx: torch.Tensor, version: int
) -> torch.Tensor:
    if version == 1:
        return out["unit"]
    if version == 2:
        b = torch.arange(class_idx.shape[0], device=class_idx.device)
        return out["unit_per_class"][b, class_idx]
    raise ValueError(version)


def per_param_r2(
    pred: torch.Tensor, tgt: torch.Tensor, names: list[str]
) -> dict[str, float]:
    """1 - MSE/Var per param. ~0 = predicting the mean; 1 = perfect."""
    mse = ((pred - tgt) ** 2).mean(dim=0)
    var = tgt.var(dim=0, unbiased=False).clamp_min(1e-8)
    r2 = 1.0 - mse / var
    return {n: float(r2[i]) for i, n in enumerate(names)}


def wavetype_topk_accuracy(
    logits: torch.Tensor, class_idx: torch.Tensor, k: int
) -> float:
    topk = logits.topk(k, dim=1).indices
    return float((topk == class_idx[:, None]).any(dim=1).float().mean())
```

In `invert_loss`, replace the `if version == 1 / elif version == 2` block with `unit_pred = select_unit_pred(out, class_idx, version)`.

In `_run_epoch`, when `optimizer is None` (validation), accumulate predictions on CPU and merge extra metrics into the returned dict:

```python
    # before the loop
    collect = optimizer is None
    preds, tgts, all_logits, all_cls = [], [], [], []
    ...
    # inside the loop, after computing `out`
    if collect:
        preds.append(select_unit_pred(out, cls, model.version).detach().cpu())
        tgts.append(unit.detach().cpu())
        all_logits.append(out["wavetype_logits"].detach().cpu())
        all_cls.append(cls.detach().cpu())
    ...
    # after the loop, alongside the existing loss/unit_mse/ce averages
    if collect and preds:
        pred_cat, tgt_cat = torch.cat(preds), torch.cat(tgts)
        logit_cat, cls_cat = torch.cat(all_logits), torch.cat(all_cls)
        metrics["r2"] = per_param_r2(pred_cat, tgt_cat, list(space.names))
        metrics["wavetype_top1"] = wavetype_topk_accuracy(logit_cat, cls_cat, 1)
        metrics["wavetype_top3"] = wavetype_topk_accuracy(logit_cat, cls_cat, 3)
```

In `train()`, after each epoch print a one-line summary to stderr so long runs are watchable (`import sys` at top):

```python
            if "r2" in val_metrics:
                worst = sorted(val_metrics["r2"].items(), key=lambda kv: kv[1])[:3]
                print(
                    f"epoch {epoch}: val unit_mse {val_metrics['unit_mse']:.4f} "
                    f"top3 {val_metrics['wavetype_top3']:.2%} "
                    f"worst r2: " + ", ".join(f"{n}={v:.2f}" for n, v in worst),
                    file=sys.stderr,
                )
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_invert_train_metrics.py -q` → PASS, then `uv run pytest -q` → all green.

- [ ] **Step 5: Commit**

```bash
git add tools/invert/train.py tools/tests/test_invert_train_metrics.py
git commit -m "Add per-param R2 + wavetype accuracy to invert validation"
```

### Task 2: Time-preserving readout (kill the GAP bottleneck)

Replace global average pooling with a flatten of the 16-frame conv map. Keep the attribute name `self.encoder` and its Sequential indices so old checkpoints still load (the pool at index 8 had no weights).

**Files:**
- Modify: `tools/invert/model.py`, `tools/invert/train.py` (save `readout`), `tools/invert/predict.py` (load `readout`)
- Modify: `tools/tests/test_invert_predict.py`, `tools/tests/test_invert_match_seed.py` (checkpoint fixture dicts gain `"readout"`)
- Test: `tools/tests/test_invert_model.py` (extend)

**Interfaces:**
- Produces: `InverseModel(version: int = 1, width: int = 128, readout: str = "flatten")` with `readout in ("gap", "flatten")`; checkpoints gain a `"readout"` key; `load_checkpoint` reads it with default `"gap"` (all pre-existing checkpoints were GAP) and exposes it in `meta["readout"]`.

- [ ] **Step 1: Write the failing tests** (append to `tools/tests/test_invert_model.py`)

```python
def test_flatten_readout_forward_shapes():
    import torch
    from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
    from invert.model import InverseModel

    for version in (1, 2):
        model = InverseModel(version=version, readout="flatten")
        x = torch.randn(3, N_CHANNELS, N_FRAMES)
        out = model(x, torch.zeros(3))
        assert out["wavetype_logits"].shape == (3, N_WAVETYPES)
        if version == 1:
            assert out["unit"].shape == (3, N_PARAMS)
        else:
            assert out["unit_per_class"].shape == (3, N_WAVETYPES, N_PARAMS)


def test_gap_checkpoint_still_loads(tmp_path):
    """Pre-readout checkpoints (no 'readout' key) must load as GAP models."""
    import torch
    from invert.model import InverseModel
    from invert.predict import load_checkpoint
    from match.bfxr_io import ParamSpace

    space = ParamSpace()
    old = InverseModel(version=1, readout="gap")
    ckpt = {
        "model_state": old.state_dict(),
        "version": 1,
        "space_names": list(space.names),
        "wave_types_order": sorted(space.wave_types),
        "best_val": 0.0,
        # deliberately no "readout" key
    }
    path = tmp_path / "gap_ckpt.pt"
    torch.save(ckpt, path)
    model, meta = load_checkpoint(path)
    assert meta["readout"] == "gap"
    assert model.readout == "gap"
```

- [ ] **Step 2: Run tests, verify failure**

Run: `uv run pytest tests/test_invert_model.py -q`
Expected: TypeError (`readout` unexpected keyword).

- [ ] **Step 3: Implement in `invert/model.py`**

```python
class InverseModel(nn.Module):
    def __init__(self, version: int = 1, width: int = 128, readout: str = "flatten"):
        super().__init__()
        if version not in (1, 2):
            raise ValueError(version)
        if readout not in ("gap", "flatten"):
            raise ValueError(readout)
        self.version = version
        self.readout = readout
        # keep the name/indices of the old encoder (minus its weightless pool)
        # so pre-readout checkpoints still load
        self.encoder = nn.Sequential(
            nn.Conv1d(N_CHANNELS, width, 5, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width * 2, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
        )
        n_out_frames = N_FRAMES // 8  # three stride-2 convs: 128 -> 16
        if readout == "gap":
            feat_dim = width * 2
        else:
            self.proj = nn.Sequential(
                nn.Linear(width * 2 * n_out_frames, 512),
                nn.ReLU(inplace=True),
            )
            feat_dim = 512
        enc_dim = feat_dim + 1  # + log_duration
        self.wavetype_head = nn.Linear(enc_dim, N_WAVETYPES)
        if version == 1:
            self.unit_head = nn.Linear(enc_dim, N_PARAMS)
        else:
            self.unit_heads = nn.ModuleList(
                [nn.Linear(enc_dim, N_PARAMS) for _ in range(N_WAVETYPES)]
            )

    def encode(self, x: torch.Tensor, log_duration: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x)
        if self.readout == "gap":
            h = h.mean(dim=-1)
        else:
            h = self.proj(h.flatten(1))
        return torch.cat([h, log_duration.unsqueeze(-1)], dim=-1)
```

(`N_FRAMES` needs importing from `.constants`; `forward` is unchanged.)

In `invert/train.py`: the `torch.save({...})` dict gains `"readout": model.readout`; `InverseModel(version=version)` in `train()` stays default — flatten is now the default, which is the point.

In `invert/predict.py` `load_checkpoint`:

```python
    readout = str(ckpt.get("readout", "gap"))  # all pre-readout checkpoints were GAP
    model = InverseModel(version=version, readout=readout)
```
and add `"readout": readout` to `meta`.

In `tools/tests/test_invert_predict.py` and `tools/tests/test_invert_match_seed.py`, find the hand-built checkpoint dicts and add `"readout": model.readout` next to `"version"` (they construct `InverseModel()` which now defaults to flatten; without the key, load would rebuild a GAP model and `load_state_dict` would fail on `proj.*` keys).

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all green (model, predict, and match-seed suites all exercise the new path).

- [ ] **Step 5: Commit**

```bash
git add tools/invert/model.py tools/invert/train.py tools/invert/predict.py \
  tools/tests/test_invert_model.py tools/tests/test_invert_predict.py \
  tools/tests/test_invert_match_seed.py
git commit -m "Replace GAP with flatten readout; keep GAP checkpoints loadable"
```

### Task 3: Loss rebalance + select best.pt on regression, not CE

**Files:**
- Modify: `tools/invert/train.py`, `tools/Makefile`
- Test: `tools/tests/test_invert_train_metrics.py` (extend)

**Interfaces:**
- Produces: `invert_loss(..., unit_weight: float = 10.0, ce_weight: float = 0.5)`; CLI flags `--unit-weight`, `--ce-weight`; `best.pt` selected on **val `unit_mse`** and stores `"selection_metric": "val_unit_mse"`. `parts` returned by `invert_loss` stay *unweighted* (comparable across runs).

- [ ] **Step 1: Write the failing test** (append to `tools/tests/test_invert_train_metrics.py`)

```python
def test_invert_loss_weighted_sum_and_raw_parts():
    import torch
    from invert.train import invert_loss
    from match.bfxr_io import ParamSpace

    space = ParamSpace()
    out = {"unit": torch.rand(8, 30), "wavetype_logits": torch.randn(8, 12)}
    tgt = torch.rand(8, 30)
    wt = torch.zeros(8).long()
    cls = torch.zeros(8).long()
    loss, parts = invert_loss(out, tgt, wt, cls, space, version=1,
                              unit_weight=10.0, ce_weight=0.5)
    expected = 10.0 * parts["unit_mse"] + 0.5 * parts["ce"]
    assert abs(float(loss) - expected) < 1e-5
```

- [ ] **Step 2: Run test, verify failure**

Run: `uv run pytest tests/test_invert_train_metrics.py -q`
Expected: TypeError (`unit_weight` unexpected keyword).

- [ ] **Step 3: Implement**

In `invert_loss` add `unit_weight: float = 10.0, ce_weight: float = 0.5` to the signature; the total becomes `loss = unit_weight * unit_mse + ce_weight * ce` (parts unchanged/raw). Thread both values through `train(...)` and `_run_epoch(...)` as keyword args, add `--unit-weight`/`--ce-weight` CLI flags, and change the best-checkpoint logic:

```python
            val_metric = val_metrics["unit_mse"]
            if val_metric < best_val:
                best_val = val_metric
                torch.save({..., "selection_metric": "val_unit_mse", ...}, best_path)
```

In `tools/Makefile`, parameterize the version and point new runs at a new dir (lines 12–13 defaults, and both train invocations at lines 44/47):

```make
VERSION      ?= 1
DATA         ?= invert/data/v1
RUN          ?= invert/runs/v2_flatten
```
```make
	uv run python -m invert.train --data $(DATA) --out $(RUN) --version $(VERSION) --epochs $(EPOCHS)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest -q` → all green.

- [ ] **Step 5: Commit**

```bash
git add tools/invert/train.py tools/tests/test_invert_train_metrics.py tools/Makefile
git commit -m "Weight invert loss toward regression; select best.pt on val unit_mse"
```

### Task 4: Use checkpoint-stored channel stats in predict (latent-bug fix)

`load_checkpoint` already reads `channel_mean/std` into `meta`, but `predict_wave` normalizes with the *current constants* — if the constants are ever re-estimated, old checkpoints silently break.

**Files:**
- Modify: `tools/invert/features_pack.py`, `tools/invert/predict.py`
- Test: `tools/tests/test_invert_features_pack.py` (extend)

**Interfaces:**
- Produces: `normalize_channels(x: torch.Tensor, mean=None, std=None)` — sequences of floats or `None` (falls back to the constants); `predict_wave` passes `meta["channel_mean"]/meta["channel_std"]`.

- [ ] **Step 1: Failing test** (append to `tools/tests/test_invert_features_pack.py`)

```python
def test_normalize_channels_accepts_custom_stats():
    import torch
    from invert.constants import N_CHANNELS
    from invert.features_pack import normalize_channels

    x = torch.ones(2, N_CHANNELS, 8)
    default = normalize_channels(x)
    custom = normalize_channels(x, mean=[0.0] * N_CHANNELS, std=[1.0] * N_CHANNELS)
    assert torch.equal(custom, x)          # (x - 0) / 1
    assert not torch.equal(default, custom)
```

- [ ] **Step 2: Run, verify failure** — TypeError on the new kwargs.

- [ ] **Step 3: Implement**

```python
def normalize_channels(x: torch.Tensor, mean=None, std=None) -> torch.Tensor:
    """Z-score each input channel. x: (..., C, T) float32."""
    _ensure_backends()
    m = _channel_mean if mean is None else torch.tensor(
        list(mean), dtype=torch.float32).view(-1, 1)
    s = _channel_std if std is None else torch.tensor(
        list(std), dtype=torch.float32).view(-1, 1)
    m = m.to(device=x.device, dtype=x.dtype)
    s = s.to(device=x.device, dtype=x.dtype)
    while m.ndim < x.ndim:
        m = m.unsqueeze(0)
        s = s.unsqueeze(0)
    return (x - m) / s
```

In `predict_wave`: `x = normalize_channels(..., mean=meta["channel_mean"], std=meta["channel_std"])`. (`train.py` keeps using the constants — training is what defines them.)

- [ ] **Step 4: Run tests** — `uv run pytest -q` → all green.

- [ ] **Step 5: Commit**

```bash
git add tools/invert/features_pack.py tools/invert/predict.py tools/tests/test_invert_features_pack.py
git commit -m "predict: normalize with the checkpoint's channel stats, not current constants"
```

### Task 5: Wave-1 retrain + gate (run task — no code)

**Files:** none (produces `invert/runs/v2_flatten/`).

- [ ] **Step 1: Retrain on the existing shards** (hours; background, MPS)

```bash
make train_inverse_model RUN=invert/runs/v2_flatten EPOCHS=15
```

- [ ] **Step 2: Evaluate the gate** from the last line of `invert/runs/v2_flatten/train_log.jsonl` (`val.r2`, `val.wavetype_top3`):

| metric | gate |
| --- | --- |
| `frequency_start` R² | ≥ 0.8 |
| `sustainTime` R² | ≥ 0.7 |
| `attackTime` R² | ≥ 0.7 |
| `decayTime` R² | ≥ 0.6 |
| wavetype top-3 | ≥ 0.90 |

(Judgment thresholds; the point is "the model reads pitch and envelope off inputs that literally contain pitch and envelope.")

- [ ] **Step 3: In-domain one-shot check** (the postmortem's "true invert diagnostic"): re-render held-out examples' ground truth and one-shot predictions, score perceptually:

```bash
uv run python - <<'EOF'
import numpy as np, torch
from invert.dataset import InvertShardDataset
from invert.features_pack import normalize_channels
from invert.predict import load_checkpoint
from match.bfxr_io import ParamSpace
from match.objective import MatchObjective
from match.optimizer import RENDER_SEED
from match.renderer import BfxrRenderer

ds = InvertShardDataset("invert/data/v1")
model, meta = load_checkpoint("invert/runs/v2_flatten/best.pt")
space = ParamSpace()
scores = []
with BfxrRenderer() as r, torch.no_grad():
    for i in range(len(ds) - 64, len(ds)):        # val tail
        x = normalize_channels(ds.features[i:i+1].float(),
                               mean=meta["channel_mean"], std=meta["channel_std"])
        out = model(x, ds.log_duration[i:i+1].float())
        cls = int(out["wavetype_logits"][0].argmax())
        wt = int(meta["wave_types_order"][cls])
        pred_params = space.params_dict(out["unit"][0].numpy(), wt)
        tgt_params = space.params_dict(ds.unit[i].float().numpy(), int(ds.wave_type[i]))
        tgt = r.render(tgt_params, seed=RENDER_SEED)
        pred = r.render(pred_params, seed=RENDER_SEED)
        if tgt is not None and pred is not None:
            scores.append(MatchObjective(tgt).score(pred))
print(f"in-domain one-shot: median {np.median(scores):.3f} mean {np.mean(scores):.3f} n={len(scores)}")
EOF
```
The v1 baseline for this number is "terrible" (one-shot 2.8–11.8 on preset renders); it must drop substantially. Note ~half the val tail is augmented, so this understates clean performance slightly — fine for trend tracking.

- [ ] **Step 4 (only if the gate fails): input-sanity canary before blaming the model.** Verify the *input* carries the signal, independent of any network:

```bash
uv run python - <<'EOF'
import numpy as np
from invert.dataset import InvertShardDataset
from match.bfxr_io import ParamSpace
ds = InvertShardDataset("invert/data/v1", max_shards=5)
x = ds.features.float()
f0, voiced = x[:, 1, :], x[:, 2, :]
mean_f0 = (f0 * voiced).sum(1) / voiced.sum(1).clamp(min=1)
j = list(ParamSpace().names).index("frequency_start")
r = np.corrcoef(mean_f0.numpy(), ds.unit[:, j].float().numpy())[0, 1]
print(f"corr(mean voiced f0, frequency_start) = {r:.3f}  (expect |r| > 0.7)")
EOF
```
If the correlation is high but the model still can't learn → escalate capacity (width 192, or one dilated conv `nn.Conv1d(width*2, width*2, 5, padding=4, dilation=2)` before the last ReLU), or try the postmortem's two-phase alternative (train wavetype, freeze encoder, train knobs). If the correlation is *low* → the bug is in `features_pack`/label pairing; stop and investigate there.

- [ ] **Step 5: Run both match evals and record the numbers** (everything later is judged against this run)

```bash
make eval_inverse_model_all RUN=invert/runs/v2_flatten
```
Expect: one-shot column in `invert/runs/v2_flatten/eval_bfxr/results.md` clearly below v1's 2.8–11.8; model-seeded ≥ parity with current. Keep logs/results in the run dir (shards/checkpoints stay gitignored).

**GATE: do not start Wave 3 until this gate passes. Wave 2 may proceed regardless (it's orthogonal), but only after this run's numbers are recorded — you need the before/after.**

---

# Wave 2 — train on the sounds bfxr actually makes

The `eval_bfxr` targets come from the app's preset generator buttons (`generate_pickup_coin`, …) whose param distributions (pitch jumps, specific envelope shapes) the current 50%-default/uniform sampler barely visits. Harvest those generators headlessly — labels come free — and add few-knobs-changed sampling.

### Task 6: Headless preset harvesting (Node side)

**Files:**
- Modify: `tools/render/bfxr_context.js`
- Create: `tools/render/preset_cli.js`

**Interfaces:**
- Produces: `createBfxrContext()` return value gains `samplePreset(name: string, seed: number) -> string|null` (JSON of the full params dict, or null for unknown name). `node render/preset_cli.js --preset all|<name> --count N --seed S` emits NDJSON lines `{"preset": ..., "seed": ..., "params": {...}}` on stdout.

- [ ] **Step 1: Add `__samplePreset` to the context script** in `bfxr_context.js`, next to `__render`:

```js
function __samplePreset(name, seed) {
    if (typeof __synth[name] !== 'function') return null;
    __setSeed(seed);
    // pickup_coin/powerup hit a known set_param typo that console.errors;
    // mute it during harvest (behavior is identical either way)
    var err = console.error;
    console.error = function () {};
    try {
        __synth[name]();   // generators reset_params() first, then randomize
    } finally {
        console.error = err;
    }
    return JSON.stringify(__synth.params);
}
```
and extend the completion value: `({ render: __render, paramInfo: __paramInfo, samplePreset: __samplePreset });`

Safe because `__render` merges onto `__defaults` (not `__synth.params`), so harvesting can't contaminate rendering.

- [ ] **Step 2: Create `tools/render/preset_cli.js`**

```js
// Emit NDJSON {preset, seed, params} for the app's preset generators.
//   node render/preset_cli.js --preset all --count 100 --seed 0
'use strict';
const { createBfxrContext } = require('./bfxr_context.js');

const PRESETS = [
    'generate_pickup_coin', 'generate_laser_shoot', 'generate_explosion',
    'generate_powerup', 'generate_hit_hurt', 'generate_jump',
    'generate_blip_select', 'randomize_params',
];

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
    args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
}
const preset = args.preset || 'all';
const count = parseInt(args.count || '1', 10);
const seed0 = parseInt(args.seed || '0', 10);
if (preset !== 'all' && !PRESETS.includes(preset)) {
    process.stderr.write(`unknown preset ${preset}; known: ${PRESETS.join(', ')}\n`);
    process.exit(1);
}

const ctx = createBfxrContext();
const lines = [];
for (let i = 0; i < count; i++) {
    const name = preset === 'all' ? PRESETS[i % PRESETS.length] : preset;
    const json = ctx.samplePreset(name, seed0 + i);
    if (json !== null) {
        lines.push(JSON.stringify({ preset: name, seed: seed0 + i, params: JSON.parse(json) }));
    }
}
process.stdout.write(lines.join('\n') + '\n');
```

- [ ] **Step 3: Verify determinism + render-path safety**

```bash
node render/preset_cli.js --preset all --count 64 --seed 0 | shasum
node render/preset_cli.js --preset all --count 64 --seed 0 | shasum   # identical hash
node render/preset_cli.js --preset generate_pickup_coin --count 4 --seed 1  # eyeball params
uv run pytest tests/test_renderer.py -q   # render path untouched
```

- [ ] **Step 4: Commit**

```bash
git add tools/render/bfxr_context.js tools/render/preset_cli.js
git commit -m "Harvest app preset-generator params headlessly (preset_cli)"
```

### Task 7: Preset slice + k-knob sampling in the dataset

**Files:**
- Create: `tools/invert/presets.py`
- Modify: `tools/invert/sampler.py`, `tools/invert/dataset.py`, `tools/invert/constants.py`
- Test: `tools/tests/test_invert_presets.py` (new), `tools/tests/test_invert_sampler.py` (extend)

**Interfaces:**
- Consumes: `preset_cli.js` from Task 6.
- Produces: `invert.presets.harvest_preset_params(n: int, seed: int) -> list[dict]` (each `{"preset": str, "seed": int, "params": dict}`); `invert.sampler.finalize_example(space, unit, wave_type) -> dict` (the shared pin/project/round-trip logic); `sample_unit(..., mode: str = "biased")` with modes `"biased" | "uniform" | "kknob"`; dataset mixture `biased 0.35 / uniform 0.15 / kknob 0.30 / preset 0.20`; `DATASET_VERSION = "v3"`; `--augment-p` default `0.25`.

- [ ] **Step 1: Write the failing tests**

```python
# tools/tests/test_invert_presets.py
from invert.presets import harvest_preset_params
from invert.sampler import finalize_example
from match.bfxr_io import ParamSpace


def test_harvest_is_deterministic_and_convertible():
    rows_a = harvest_preset_params(16, seed=5)
    rows_b = harvest_preset_params(16, seed=5)
    assert len(rows_a) == 16
    assert rows_a == rows_b
    space = ParamSpace()
    for row in rows_a:
        unit, wt = space.unit_from_params(row["params"])
        ex = finalize_example(space, unit, wt)
        assert ex["wave_type"] == wt
        assert 0.0 <= ex["unit"].min() and ex["unit"].max() <= 1.0
```

Append to `tools/tests/test_invert_sampler.py`:

```python
def test_kknob_moves_few_params():
    import numpy as np
    from invert.sampler import sample_unit
    from match.bfxr_io import ParamSpace

    space = ParamSpace()
    rng = np.random.default_rng(3)
    for _ in range(20):
        unit = sample_unit(space, rng, mode="kknob")
        moved = int((unit != space.defaults_unit()).sum())
        assert 1 <= moved <= 6
```

- [ ] **Step 2: Run, verify failure** — ImportError / TypeError.

- [ ] **Step 3: Implement**

`invert/sampler.py` — restructure `sample_unit` around modes and extract `finalize_example` from the tail of `sample_example`:

```python
def sample_unit(space, rng, *, mode: str = "biased",
                fully_uniform: bool | None = None) -> np.ndarray:
    if fully_uniform is not None:            # backward compat with old kwarg
        mode = "uniform" if fully_uniform else "biased"
    if mode == "uniform":
        return rng.random(space.dim)
    if mode == "kknob":
        unit = space.defaults_unit().copy()
        k = int(rng.integers(1, 7))          # 1..6 knobs off default
        idx = rng.choice(space.dim, size=k, replace=False)
        unit[idx] = rng.random(k)
        return unit
    if mode == "biased":
        unit = space.defaults_unit().copy()
        mask = rng.random(space.dim) > 0.5
        unit[mask] = rng.random(int(mask.sum()))
        return unit
    raise ValueError(mode)


def finalize_example(space, unit, wave_type: int) -> dict:
    """Pin square-only params, cap the envelope, round-trip through params
    so labels live in exactly the space search explores."""
    unit = np.asarray(unit, dtype=np.float64).copy()
    if wave_type != 0:
        du = space.defaults_unit()
        for name in SQUARE_ONLY_PARAMS:
            unit[space.names.index(name)] = float(du[space.names.index(name)])
    cap = TRAIN_CAP_SECONDS * SAMPLE_RATE
    params = space.params_dict(unit, wave_type)
    _project_envelope(params, cap)
    unit, _ = space.unit_from_params(params)
    id_to_cls, _ = wave_type_index_map(space)
    return {"unit": unit.astype(np.float64), "wave_type": int(wave_type),
            "class_idx": id_to_cls[int(wave_type)]}
```
`sample_example` becomes: pick mode (respecting its existing `uniform_frac` behavior when no mode given), pick wave type, `sample_unit` + `finalize_example`.

`invert/presets.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

PRESET_CLI = Path(__file__).resolve().parent.parent / "render" / "preset_cli.js"


def harvest_preset_params(n: int, seed: int, node: str = "node") -> list[dict]:
    out = subprocess.run(
        [node, str(PRESET_CLI), "--preset", "all", "--count", str(n), "--seed", str(seed)],
        capture_output=True, text=True, check=True,
    ).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]
```

`invert/constants.py`: `DATASET_VERSION = "v3"` with comment `# v3: mixture sampling (biased/uniform/kknob/preset), augment_p 0.25`.

`invert/dataset.py` — in `generate_shards`: harvest `n_preset = round(n * 0.20)` rows up front; build a flat spec list — preset rows plus `(mode, forced_wave_type)` entries for the rest, modes drawn with `rng.choice(["biased", "uniform", "kknob"], p=[0.4375, 0.1875, 0.375])` (= 0.35/0.15/0.30 renormalized over the non-preset 0.80) and wave types from the existing stratified list over the non-preset portion — then `rng.shuffle` the combined list and chunk as today. Preset specs convert via `space.unit_from_params(row["params"])` → `finalize_example`. Failed/silent renders resample with the same mode (preset resample: draw a fresh seed from `rng`, call `harvest_preset_params(1, new_seed)`; keep the existing 8-attempt bound). Record the mixture in `manifest.json` (`"mix": {...}`). Change the `--augment-p` default to `0.25` (the robustness dial comes back up in a later run, once in-domain learning is proven — postmortem's "augmentation last").

- [ ] **Step 4: Run tests** — `uv run pytest -q` → all green (the preset test shells out to node; the suite already depends on node for the renderer).

- [ ] **Step 5: Smoke a tiny generation end-to-end**

```bash
uv run python -m invert.dataset --out /tmp/inv_v3_smoke --n 64 --shard-size 32 --seed 1
uv run python -c "
from invert.dataset import InvertShardDataset
ds = InvertShardDataset('/tmp/inv_v3_smoke'); print(len(ds), 'examples ok')"
```

- [ ] **Step 6: Commit**

```bash
git add tools/invert/presets.py tools/invert/sampler.py tools/invert/dataset.py \
  tools/invert/constants.py tools/tests/test_invert_presets.py tools/tests/test_invert_sampler.py
git commit -m "Dataset v3: preset-generator slice + k-knob sampling, augment_p 0.25"
```

### Task 8: Wave-2 regen + retrain + eval (run task — no code)

- [ ] **Step 1:** `make rebuild_inverse_model DATA=invert/data/v3 RUN=invert/runs/v3 EPOCHS=15` (dataset gen ~1–2 h, feature packing dominates; training a few hours on MPS).
- [ ] **Step 2:** `make eval_inverse_model_all DATA=invert/data/v3 RUN=invert/runs/v3` and rerun the Task 5 Step 3 in-domain one-shot snippet against `invert/data/v3` + `invert/runs/v3/best.pt`.
- [ ] **Step 3: Judge against wave 1's recorded numbers.** Success bar:
  - `eval_bfxr` one-shot better than the wave-1 run on the clear majority of the 9 preset targets (now in-distribution — this is the "can it invert itself" test).
  - `eval_bfxr` model-seeded ≤ current on most targets.
  - `eval_targets` hard-target spotlight: seeded wins on at least some of flame/beam-out/jumps.
  - Per-param R² for `pitch_jump_amount` / `pitch_jump_onset_percent` visibly off the v1 floor of ~0.03 (presets exercise them).

---

# Wave 3 — residual multimodality (only after the Wave 1 gate passed)

### Task 9: Huber unit loss + per-wavetype heads run

**Files:**
- Modify: `tools/invert/train.py`
- Test: `tools/tests/test_invert_train_metrics.py` (extend)

**Interfaces:**
- Produces: `invert_loss(..., unit_loss: str = "mse")` accepting `"mse" | "huber"`; CLI `--unit-loss`; a trained v2-heads run at `invert/runs/v4_v2heads`.

- [ ] **Step 1: Failing test**

```python
def test_invert_loss_huber_option():
    import torch
    from invert.train import invert_loss
    from match.bfxr_io import ParamSpace

    space = ParamSpace()
    out = {"unit": torch.rand(8, 30), "wavetype_logits": torch.randn(8, 12)}
    tgt = torch.rand(8, 30)
    wt = torch.zeros(8).long(); cls = torch.zeros(8).long()
    l_mse, _ = invert_loss(out, tgt, wt, cls, space, version=1, unit_loss="mse")
    l_hub, _ = invert_loss(out, tgt, wt, cls, space, version=1, unit_loss="huber")
    assert float(l_mse) != float(l_hub)
```

- [ ] **Step 2: Run, verify failure** — TypeError.

- [ ] **Step 3: Implement.** In `invert_loss`, replace the squared-error line with:

```python
    if unit_loss == "mse":
        err = (unit_pred - unit_tgt) ** 2
    elif unit_loss == "huber":
        err = F.smooth_l1_loss(unit_pred, unit_tgt, reduction="none", beta=0.1)
    else:
        raise ValueError(unit_loss)
    unit_mse = (err * mask).sum() / mask.sum().clamp(min=1)
```
(The `parts` key stays `unit_mse` for log compatibility; note in the `--unit-loss` help text that huber values aren't numerically comparable to mse values.) Add the CLI flag and thread it through `train`/`_run_epoch`.

- [ ] **Step 4: Run tests, commit**

```bash
uv run pytest -q
git add tools/invert/train.py tools/tests/test_invert_train_metrics.py
git commit -m "Add --unit-loss huber option to invert training"
```

- [ ] **Step 5: Train + eval the wave-3 candidate**

```bash
uv run python -m invert.train --data invert/data/v3 --out invert/runs/v4_v2heads \
  --version 2 --epochs 15 --unit-loss huber
make eval_inverse_model_all RUN=invert/runs/v4_v2heads
```
Compare per-param R² and both eval tables against `invert/runs/v3`.

### Backlog (documented, deliberately not implemented — YAGNI)

- **K-hypothesis heads** only on evidence of within-wavetype mode-averaging: `frequency_start` R² plateauing with a *bimodal error histogram* at ±1 octave, or envelope params bimodal between "short blip" and "long tail". If that appears: K=5 param sets per wavetype head, winner-takes-all loss, predict emits all K as search seeds.
- **Distill from matcher solutions** (postmortem §4): add (audio → params-that-won-search) pairs so labels align with the perceptual metric. Revisit after wave 2 — needs a corpus of search wins first.
- **Augmentation strength/scheduling** back up from 0.25 once clean self-inversion works (that's its job: cross-app robustness, not in-domain learning).

---

## Sequencing summary

1. Tasks 1–4 are pure code, all cheap — land in order (1 → 2 → 3 → 4), suite green after each.
2. Task 5 is the wave-1 experiment: retrain on existing shards, record gate + in-domain one-shot + eval numbers. **Everything later is judged relative to this run.**
3. Tasks 6–7 can land while Task 5 trains (they don't touch the training path).
4. Task 8 is the wave-2 experiment (full regen — the only expensive step).
5. Task 9 only after wave 1's gate passed; backlog items only on documented evidence.

## Success criteria (from the approved design spec)

- v1 bar: model-seeded search beats the current f0-heuristic pipeline on the hard targets at equal budget (`eval_targets` spotlight table).
- Growth metric: one-shot score trending down across runs — on the in-domain holdout and `eval_bfxr` first ("can it invert itself"), real targets second.
- Instrument panel: per-param R² each epoch; identifiable params (pitch, envelope) must be high before drawing conclusions about hard params.
