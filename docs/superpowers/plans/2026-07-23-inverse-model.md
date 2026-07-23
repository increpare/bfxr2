# Inverse Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train a neural seeder that maps audio features → bfxr params, wire it into `match.py` as `--seed-model` / `--one-shot`, and eval it against the current f0-heuristic pipeline on `tools/targets/`.

**Architecture:** New `tools/invert/` package generates (features, params) shards via the native renderer, trains a small 1-D CNN (v1 single-head, then v2 per-wavetype heads), and exposes predictions that replace Stage 0 random screening in `StagedOptimizer`. Features reuse `match.features` contours + the 64-band blurred log-mel from `match.objective`.

**Tech Stack:** Python 3.12, numpy, torch (MPS on M1), existing `match.*` (ParamSpace, BfxrRenderer, FeatureExtractor, MatchObjective), pytest via `uv run`.

**Spec:** `docs/superpowers/specs/2026-07-23-inverse-model-design.md`

---

## File map

| File | Role |
|------|------|
| `tools/invert/__init__.py` | Package marker |
| `tools/invert/constants.py` | Shared sizes, versions, wave-type index maps |
| `tools/invert/sampler.py` | Stage-0-style + uniform param sampling + envelope projection |
| `tools/invert/augment.py` | Noise / reverb / EQ / level jitter on audio |
| `tools/invert/features_pack.py` | Wave → fixed `(C,T)` tensor + `log_duration` |
| `tools/invert/dataset.py` | Render → pack → shard I/O + `gen_data` CLI |
| `tools/invert/model.py` | `InverseModel` v1 + v2 |
| `tools/invert/train.py` | Training loop CLI |
| `tools/invert/predict.py` | Checkpoint → ranked `.bfxr` guesses |
| `tools/invert/eval_targets.py` | Per-target table: current / model-seeded / one-shot |
| `tools/match/optimizer.py` | Accept optional model seed candidates; replace Stage 0 |
| `tools/match/match.py` | `--seed-model`, `--one-shot` flags |
| `tools/tests/test_invert_*.py` | Unit + smoke tests |
| `tools/.gitignore` | Ignore `invert/data/`, `invert/runs/` |
| `tools/README.md` | Short invert usage blurb |

**Locked constants (use everywhere):**

```python
# tools/invert/constants.py
N_FRAMES = 128
N_CONTOURS = 6          # env_db, f0_log2, voiced, active, centroid_log2, noisiness
N_MELS = 64             # SCALES entry (512, 128, 64) in match.objective
N_CHANNELS = N_CONTOURS + N_MELS  # 70
N_PARAMS = 30
N_WAVETYPES = 12
DATASET_VERSION = "v1"  # bump when features_pack / sampler label rules change
SILENCE_PEAK = 1e-3
TRAIN_CAP_SECONDS = 1.5
FEATURES_MEL_SCALE_IDX = 2  # SCALES[2] == 64 mel bands
```

Wave-type class index: `sorted(ParamSpace().wave_types)` → indices `0..11`. Never use raw DSP ids as softmax indices (they are not `0..11` contiguous in order).

---

### Task 1: Package skeleton + gitignore

**Files:**
- Create: `tools/invert/__init__.py`
- Create: `tools/invert/constants.py`
- Modify: `tools/.gitignore`

- [ ] **Step 1: Create package + constants**

```python
# tools/invert/__init__.py
"""Audio features → bfxr params inverse model (offline seeder)."""

# tools/invert/constants.py
from __future__ import annotations

N_FRAMES = 128
N_CONTOURS = 6
N_MELS = 64
N_CHANNELS = N_CONTOURS + N_MELS
N_PARAMS = 30
N_WAVETYPES = 12
DATASET_VERSION = "v1"
SILENCE_PEAK = 1e-3
TRAIN_CAP_SECONDS = 1.5
FEATURES_MEL_SCALE_IDX = 2
SQUARE_ONLY = ("squareDuty", "dutySweep")
```

- [ ] **Step 2: Gitignore data/runs**

Append to `tools/.gitignore`:

```
invert/data/
invert/runs/
```

- [ ] **Step 3: Commit**

```bash
git add tools/invert/__init__.py tools/invert/constants.py tools/.gitignore
git commit -m "Scaffold invert package for audio→params seeder"
```

---

### Task 2: Sampler (TDD)

**Files:**
- Create: `tools/invert/sampler.py`
- Create: `tools/tests/test_invert_sampler.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/tests/test_invert_sampler.py
import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, SQUARE_ONLY_PARAMS
from match.audio import SAMPLE_RATE
from invert.constants import TRAIN_CAP_SECONDS
from invert.sampler import sample_example, wave_type_index_map


def test_wave_type_index_map_bijective():
    space = ParamSpace()
    id_to_cls, cls_to_id = wave_type_index_map(space)
    assert len(id_to_cls) == 12
    for wt, cls in id_to_cls.items():
        assert cls_to_id[cls] == wt


def test_sampler_determinism():
    space = ParamSpace()
    a = sample_example(space, rng=np.random.default_rng(0))
    b = sample_example(space, rng=np.random.default_rng(0))
    assert np.allclose(a["unit"], b["unit"])
    assert a["wave_type"] == b["wave_type"]


def test_sampler_nonsquare_pins_square_only():
    space = ParamSpace()
    rng = np.random.default_rng(1)
    for _ in range(40):
        ex = sample_example(space, rng=rng, force_wave_type=9)  # Bitnoise
        for name in SQUARE_ONLY_PARAMS:
            i = space.names.index(name)
            assert abs(ex["unit"][i] - space.defaults_unit()[i]) < 1e-9


def test_sampler_envelope_under_cap():
    space = ParamSpace()
    rng = np.random.default_rng(2)
    cap = TRAIN_CAP_SECONDS * SAMPLE_RATE
    for _ in range(50):
        ex = sample_example(space, rng=rng)
        params = space.params_dict(ex["unit"], ex["wave_type"])
        total = sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)
        assert total <= cap + 1.0  # float slack
```

- [ ] **Step 2: Run — expect fail**

```bash
cd tools && uv run pytest tests/test_invert_sampler.py -v
```

Expected: import error for `invert.sampler`.

- [ ] **Step 3: Implement sampler**

```python
# tools/invert/sampler.py
from __future__ import annotations

import numpy as np

from match.audio import SAMPLE_RATE
from match.bfxr_io import ParamSpace
from match.optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, SQUARE_ONLY_PARAMS

from .constants import TRAIN_CAP_SECONDS


def wave_type_index_map(space: ParamSpace) -> tuple[dict[int, int], dict[int, int]]:
    ordered = sorted(space.wave_types)
    id_to_cls = {wt: i for i, wt in enumerate(ordered)}
    cls_to_id = {i: wt for wt, i in id_to_cls.items()}
    return id_to_cls, cls_to_id


def _project_envelope(params: dict, cap_samples: float) -> None:
    total = sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)
    if total > cap_samples:
        scale = float(np.sqrt(cap_samples / total))
        for n in ENVELOPE_PARAMS:
            params[n] *= scale


def sample_unit(space: ParamSpace, rng: np.random.Generator, *, fully_uniform: bool) -> np.ndarray:
    if fully_uniform:
        return rng.random(space.dim)
    unit = space.defaults_unit().copy()
    mask = rng.random(space.dim) > 0.5
    unit[mask] = rng.random(int(mask.sum()))
    return unit


def sample_example(
    space: ParamSpace,
    rng: np.random.Generator,
    *,
    force_wave_type: int | None = None,
    uniform_frac: float = 0.2,
) -> dict:
    """Return {unit, wave_type, class_idx} with labels in search-reachable space."""
    fully_uniform = bool(rng.random() < uniform_frac)
    unit = sample_unit(space, rng, fully_uniform=fully_uniform)
    if force_wave_type is None:
        wave_type = int(rng.choice(space.wave_types))
    else:
        wave_type = int(force_wave_type)

    if wave_type != 0:
        du = space.defaults_unit()
        for name in SQUARE_ONLY_PARAMS:
            unit[space.names.index(name)] = float(du[space.names.index(name)])

    cap = TRAIN_CAP_SECONDS * SAMPLE_RATE
    params = space.params_dict(unit, wave_type)
    _project_envelope(params, cap)
    unit, _ = space.unit_from_params(params)

    id_to_cls, _ = wave_type_index_map(space)
    return {
        "unit": unit.astype(np.float64),
        "wave_type": wave_type,
        "class_idx": id_to_cls[wave_type],
    }
```

- [ ] **Step 4: Run — expect pass**

```bash
cd tools && uv run pytest tests/test_invert_sampler.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/invert/sampler.py tools/tests/test_invert_sampler.py
git commit -m "Add invert sampler with envelope projection and square-only pins"
```

---

### Task 3: Augmentation (TDD)

**Files:**
- Create: `tools/invert/augment.py`
- Create: `tools/tests/test_invert_augment.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/tests/test_invert_augment.py
import numpy as np

from invert.augment import maybe_augment


def test_augment_can_noop():
    rng = np.random.default_rng(0)
    x = np.random.default_rng(1).standard_normal(8000).astype(np.float32) * 0.2
    y = maybe_augment(x, rng=rng, p=0.0)
    assert np.allclose(x, y)


def test_augment_finite_and_same_length():
    rng = np.random.default_rng(2)
    x = np.random.default_rng(3).standard_normal(12000).astype(np.float32) * 0.3
    y = maybe_augment(x, rng=rng, p=1.0)
    assert y.shape == x.shape
    assert np.isfinite(y).all()


def test_augment_does_not_mutate_input():
    rng = np.random.default_rng(4)
    x = np.ones(4000, dtype=np.float32) * 0.1
    x_copy = x.copy()
    _ = maybe_augment(x, rng=rng, p=1.0)
    assert np.allclose(x, x_copy)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd tools && uv run pytest tests/test_invert_augment.py -v
```

- [ ] **Step 3: Implement**

```python
# tools/invert/augment.py
from __future__ import annotations

import numpy as np


def maybe_augment(
    wave: np.ndarray,
    rng: np.random.Generator,
    *,
    p: float = 0.5,
) -> np.ndarray:
    """Rough up audio ~half the time. Labels must stay unchanged at the call site."""
    x = np.asarray(wave, dtype=np.float32).copy()
    if rng.random() >= p:
        return x

    # level jitter
    x *= float(rng.uniform(0.5, 1.4))

    # additive noise floor
    if rng.random() < 0.8:
        noise_db = float(rng.uniform(-45, -25))
        amp = 10 ** (noise_db / 20.0)
        x = x + rng.standard_normal(len(x)).astype(np.float32) * amp

    # cheap one-tap "reverb" (decaying echo)
    if rng.random() < 0.5 and len(x) > 2000:
        delay = int(rng.integers(800, 2400))
        decay = float(rng.uniform(0.15, 0.45))
        y = x.copy()
        y[delay:] += x[:-delay] * decay
        x = y

    # gentle EQ tilt via 1st-order IIR high/low shelf approximation
    if rng.random() < 0.7:
        tilt = float(rng.uniform(-0.35, 0.35))
        # simple first-difference blend
        dx = np.diff(x, prepend=x[:1])
        x = x + tilt * dx

    peak = float(np.max(np.abs(x))) + 1e-12
    if peak > 0.98:
        x *= 0.98 / peak
    return x.astype(np.float32)
```

- [ ] **Step 4: Run — expect pass**

```bash
cd tools && uv run pytest tests/test_invert_augment.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/invert/augment.py tools/tests/test_invert_augment.py
git commit -m "Add invert audio augmentation that leaves param labels untouched"
```

---

### Task 4: Feature packing (TDD)

**Files:**
- Create: `tools/invert/features_pack.py`
- Create: `tools/tests/test_invert_features_pack.py`

Pack a mono wave into:
- `x`: `float32` array shape `(N_CHANNELS, N_FRAMES)` = contours (6) stacked with 64-band blurred log-mel
- `log_duration`: `log(duration_seconds + eps)`
- Unvoiced `f0_log2` zero-filled; `voiced`/`active` remain as mask channels

Reuse `FeatureExtractor`, `stretch_to`, and the mel bank from `match.objective` (scale index `FEATURES_MEL_SCALE_IDX`).

- [ ] **Step 1: Write failing tests**

```python
# tools/tests/test_invert_features_pack.py
import numpy as np
import torch

from invert.constants import N_CHANNELS, N_FRAMES
from invert.features_pack import pack_features


def test_pack_features_shape_and_finite():
    # 0.3s of noise
    sr = 44100
    w = (np.random.default_rng(0).standard_normal(int(0.3 * sr)) * 0.2).astype(np.float32)
    feat, log_dur = pack_features(w)
    assert feat.shape == (N_CHANNELS, N_FRAMES)
    assert np.isfinite(feat).all()
    assert np.isfinite(log_dur)


def test_pack_features_determinism():
    w = (np.random.default_rng(1).standard_normal(10000) * 0.15).astype(np.float32)
    a, da = pack_features(w)
    b, db = pack_features(w)
    assert np.allclose(a, b)
    assert da == db
```

- [ ] **Step 2: Run — expect fail**

```bash
cd tools && uv run pytest tests/test_invert_features_pack.py -v
```

- [ ] **Step 3: Implement**

```python
# tools/invert/features_pack.py
from __future__ import annotations

import numpy as np
import torch

from match.audio import SAMPLE_RATE, normalize_peak
from match.features import FeatureExtractor, stretch_to, frame_count
from match.objective import (
    LOG_EPS,
    MIN_WAVE_LEN,
    SCALES,
    TAIL_PAD,
    _blur_matrix,
    MEL_BLUR_SIGMA,
)
import torchaudio

from .constants import FEATURES_MEL_SCALE_IDX, N_FRAMES, N_MELS


_extractor: FeatureExtractor | None = None
_mel_transform = None
_mel_blur: torch.Tensor | None = None


def _ensure_backends():
    global _extractor, _mel_transform, _mel_blur
    if _extractor is None:
        _extractor = FeatureExtractor()
        n_fft, hop, n_mels = SCALES[FEATURES_MEL_SCALE_IDX]
        assert n_mels == N_MELS
        _mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            hop_length=hop,
            n_mels=n_mels,
            f_min=30.0,
            f_max=18000.0,
            power=2.0,
        )
        _mel_blur = _blur_matrix(n_mels, MEL_BLUR_SIGMA * n_mels / 128)


@torch.no_grad()
def pack_features(wave: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (channels, N_FRAMES) float32 + scalar log_duration."""
    _ensure_backends()
    assert _extractor is not None and _mel_transform is not None and _mel_blur is not None

    w = normalize_peak(np.asarray(wave, dtype=np.float32))
    duration_s = max(len(w), 1) / SAMPLE_RATE
    log_duration = float(np.log(duration_s + 1e-4))

    target_len = max(len(w), MIN_WAVE_LEN)
    batch = torch.zeros(1, target_len + TAIL_PAD)
    batch[0, : len(w)] = torch.from_numpy(w)

    feats = _extractor.extract(batch).slice(0, frame_count(target_len))
    feats = stretch_to(feats, N_FRAMES)

    f0 = feats.f0_log2.clone()
    f0 = torch.where(feats.voiced, f0, torch.zeros_like(f0))

    contours = torch.stack(
        [
            feats.env_db,
            f0,
            feats.voiced.float(),
            feats.active.float(),
            feats.centroid_log2,
            feats.noisiness,
        ],
        dim=1,
    )[
        0
    ]  # (6, T)

    n_fft, hop, _ = SCALES[FEATURES_MEL_SCALE_IDX]
    mel = _mel_blur @ torch.log(_mel_transform(batch)[0] + LOG_EPS)
    mel = mel[:, : target_len // hop + 1]  # (64, Tm)
    mel_t = torch.nn.functional.interpolate(
        mel.unsqueeze(0), size=N_FRAMES, mode="linear", align_corners=False
    ).squeeze(0)

    x = torch.cat([contours, mel_t], dim=0).numpy().astype(np.float32)
    return x, log_duration
```

- [ ] **Step 4: Run — expect pass**

```bash
cd tools && uv run pytest tests/test_invert_features_pack.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/invert/features_pack.py tools/tests/test_invert_features_pack.py
git commit -m "Add fixed-size feature packing for invert model input"
```

---

### Task 5: Dataset shard I/O + tiny gen_data path (TDD)

**Files:**
- Create: `tools/invert/dataset.py`
- Create: `tools/tests/test_invert_dataset.py`

Shard format per file `shard_XXXX.pt` (torch.save dict):

```python
{
  "features": FloatTensor[N, C, T],      # float16 ok on disk via .half()
  "log_duration": FloatTensor[N],
  "unit": FloatTensor[N, 30],
  "wave_type": LongTensor[N],            # raw DSP ids
  "class_idx": LongTensor[N],
  "meta": {"dataset_version": DATASET_VERSION, "n": N, ...},
}
```

- [ ] **Step 1: Write failing round-trip test**

```python
# tools/tests/test_invert_dataset.py
from pathlib import Path

import numpy as np
import torch

from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES
from invert.dataset import write_shard, read_shard


def test_shard_round_trip(tmp_path: Path):
    n = 4
    payload = {
        "features": torch.randn(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.randn(n),
        "unit": torch.rand(n, 30),
        "wave_type": torch.tensor([0, 9, 1, 4], dtype=torch.long),
        "class_idx": torch.tensor([2, 9, 3, 0], dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    path = tmp_path / "shard_0000.pt"
    write_shard(path, payload)
    loaded = read_shard(path)
    assert loaded["meta"]["dataset_version"] == DATASET_VERSION
    assert torch.equal(loaded["wave_type"], payload["wave_type"])
    assert torch.allclose(loaded["features"].float(), payload["features"].float())
    assert torch.allclose(loaded["unit"], payload["unit"])
```

- [ ] **Step 2: Run — expect fail**

```bash
cd tools && uv run pytest tests/test_invert_dataset.py::test_shard_round_trip -v
```

- [ ] **Step 3: Implement write/read + Dataset class + gen_data CLI core**

Implement in `tools/invert/dataset.py`:

1. `write_shard` / `read_shard`
2. `InvertShardDataset(torch.utils.data.Dataset)` that globs `dir/shard_*.pt`, concatenates in `__init__` for small sets or memory-maps list of tensors for large sets (v1: load all shards into RAM lists and index — 300k × 70 × 128 × 2 bytes ≈ 5GB; accept that, document `--max-shards` for smoke)
3. `generate_shards(out_dir, n, seed, jobs, shard_size=2048, augment_p=0.5)`:
   - Stratify wave types evenly
   - `sample_example` → `BfxrRenderer.render_batch` with `RENDER_SEED` (store that seed in meta)
   - Reject `wave is None` or `peak < SILENCE_PEAK`; resample replacement (up to 8 tries)
   - `maybe_augment` then `pack_features`
   - Write float16 feature shards + manifest.json `{n, seed, dataset_version, feature_note, render_seed}`
4. CLI: `python -m invert.dataset --out invert/data/v1 --n 300000 --seed 0`

Keep CLI `main()` thin; put logic in functions for tests.

Also add a tiny integration helper used by tests:

```python
def generate_shards(...):  # as above
```

- [ ] **Step 4: Tiny end-to-end gen test (slow-ish but small n)**

```python
def test_generate_tiny_shard(tmp_path: Path):
    from invert.dataset import generate_shards, read_shard
    generate_shards(tmp_path, n=8, seed=0, jobs=1, shard_size=8, augment_p=0.5)
    shards = sorted(tmp_path.glob("shard_*.pt"))
    assert len(shards) == 1
    data = read_shard(shards[0])
    assert data["features"].shape[0] == 8
    assert data["features"].shape[1:] == (N_CHANNELS, N_FRAMES)
```

Run:

```bash
cd tools && uv run pytest tests/test_invert_dataset.py -v
```

Expected: PASS (needs native or node worker available — same as other renderer tests).

- [ ] **Step 5: Commit**

```bash
git add tools/invert/dataset.py tools/tests/test_invert_dataset.py
git commit -m "Add invert shard I/O and dataset generation CLI"
```

---

### Task 6: Model v1 forward shapes (TDD)

**Files:**
- Create: `tools/invert/model.py`
- Create: `tools/tests/test_invert_model.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/tests/test_invert_model.py
import torch

from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
from invert.model import InverseModel


def test_v1_forward_shapes():
    m = InverseModel(version=1)
    x = torch.randn(2, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(2)
    out = m(x, log_dur)
    assert out["unit"].shape == (2, N_PARAMS)
    assert out["wavetype_logits"].shape == (2, N_WAVETYPES)
    # unit in [0,1] via sigmoid
    assert float(out["unit"].min()) >= 0.0
    assert float(out["unit"].max()) <= 1.0


def test_v2_forward_shapes():
    m = InverseModel(version=2)
    x = torch.randn(3, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(3)
    out = m(x, log_dur)
    assert out["unit_per_class"].shape == (3, N_WAVETYPES, N_PARAMS)
    assert out["wavetype_logits"].shape == (3, N_WAVETYPES)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd tools && uv run pytest tests/test_invert_model.py -v
```

- [ ] **Step 3: Implement CNN**

```python
# tools/invert/model.py
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .constants import N_CHANNELS, N_PARAMS, N_WAVETYPES


class InverseModel(nn.Module):
    def __init__(self, version: int = 1, width: int = 128):
        super().__init__()
        if version not in (1, 2):
            raise ValueError(version)
        self.version = version
        self.encoder = nn.Sequential(
            nn.Conv1d(N_CHANNELS, width, 5, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width * 2, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        enc_dim = width * 2 + 1  # + log_duration
        self.wavetype_head = nn.Linear(enc_dim, N_WAVETYPES)
        if version == 1:
            self.unit_head = nn.Linear(enc_dim, N_PARAMS)
        else:
            self.unit_heads = nn.ModuleList(
                [nn.Linear(enc_dim, N_PARAMS) for _ in range(N_WAVETYPES)]
            )

    def encode(self, x: torch.Tensor, log_duration: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x).squeeze(-1)
        return torch.cat([h, log_duration.unsqueeze(-1)], dim=-1)

    def forward(self, x: torch.Tensor, log_duration: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.encode(x, log_duration)
        logits = self.wavetype_head(h)
        if self.version == 1:
            unit = torch.sigmoid(self.unit_head(h))
            return {"unit": unit, "wavetype_logits": logits}
        units = torch.stack(
            [torch.sigmoid(head(h)) for head in self.unit_heads], dim=1
        )
        return {"unit_per_class": units, "wavetype_logits": logits}
```

- [ ] **Step 4: Run — expect pass**

```bash
cd tools && uv run pytest tests/test_invert_model.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/invert/model.py tools/tests/test_invert_model.py
git commit -m "Add InverseModel v1/v2 CNN with unit + wavetype heads"
```

---

### Task 7: Training loop + loss masking

**Files:**
- Create: `tools/invert/train.py`
- Modify: `tools/tests/test_invert_model.py` (add loss helper test)

Loss:
- `MSE(unit_pred, unit_tgt)` with square-only dims masked out when `wave_type != 0`
- `CE(wavetype_logits, class_idx)`
- v2: for each example, only the matching class head contributes unit MSE

- [ ] **Step 1: Add loss unit test**

```python
# in test_invert_model.py
from invert.train import invert_loss
from match.bfxr_io import ParamSpace
from invert.sampler import wave_type_index_map


def test_invert_loss_masks_square_only():
    space = ParamSpace()
    id_to_cls, _ = wave_type_index_map(space)
    sq_idx = [space.names.index(n) for n in ("squareDuty", "dutySweep")]
    unit_tgt = torch.rand(2, 30)
    unit_pred = unit_tgt.clone()
    unit_pred[0, sq_idx[0]] += 1.0  # huge error on square-only
    # example 0 = nonsquare, example 1 = square
    wave_types = torch.tensor([9, 0])
    class_idx = torch.tensor([id_to_cls[9], id_to_cls[0]])
    logits = torch.zeros(2, 12)
    logits[range(2), class_idx] = 10.0
    out = {"unit": unit_pred, "wavetype_logits": logits}
    loss, parts = invert_loss(out, unit_tgt, wave_types, class_idx, space, version=1)
    # nonsquare square-only error must not dominate — loss finite and smallish
    assert torch.isfinite(loss)
    assert parts["unit_mse"] < 0.1
```

- [ ] **Step 2: Implement `invert_loss` + CLI train loop**

`train.py` responsibilities:
- argparse: `--data`, `--out`, `--epochs`, `--batch-size`, `--lr`, `--version {1,2}`, `--device {cpu,mps,cuda}`
- default device: `mps` if `torch.backends.mps.is_available()` else cpu
- AdamW, cosine LR optional (simple StepLR fine for v1)
- each epoch: train + val (last 5% of examples or `val_ratio=0.05` split by index)
- checkpoint: `runs/<name>/best.pt` with `{model_state, version, space_names, wave_types_order, best_val}`
- log JSONL lines to `train_log.jsonl`

```python
def invert_loss(out, unit_tgt, wave_types, class_idx, space, version=1):
    ...
```

Square-only mask:

```python
mask = torch.ones_like(unit_tgt)
for name in ("squareDuty", "dutySweep"):
    j = space.names.index(name)
    mask[:, j] = (wave_types == 0).float()
unit_mse = ((out["unit"] - unit_tgt) ** 2 * mask).sum() / mask.sum().clamp(min=1)
```

- [ ] **Step 3: Smoke-train on tiny synthetic batch (no real shards)**

```python
def test_train_step_smoke():
    space = ParamSpace()
    m = InverseModel(version=1)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    x = torch.randn(8, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(8)
    unit = torch.rand(8, 30)
    wt = torch.tensor([0, 9, 1, 4, 2, 3, 5, 6])
    id_to_cls, _ = wave_type_index_map(space)
    cls = torch.tensor([id_to_cls[int(t)] for t in wt])
    out = m(x, log_dur)
    loss, _ = invert_loss(out, unit, wt, cls, space, version=1)
    loss.backward()
    opt.step()
    assert torch.isfinite(loss)
```

- [ ] **Step 4: Run tests**

```bash
cd tools && uv run pytest tests/test_invert_model.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tools/invert/train.py tools/tests/test_invert_model.py
git commit -m "Add invert training loss and train CLI"
```

---

### Task 8: `predict.py` standalone

**Files:**
- Create: `tools/invert/predict.py`
- Create: `tools/tests/test_invert_predict.py`

- [ ] **Step 1: Test load + predict shapes with random checkpoint**

```python
def test_predict_topk_from_random_checkpoint(tmp_path):
    from invert.model import InverseModel
    from invert.predict import load_checkpoint, predict_wave
    space = ParamSpace()
    m = InverseModel(version=1)
    ckpt = {
        "model_state": m.state_dict(),
        "version": 1,
        "wave_types_order": sorted(space.wave_types),
        "space_names": space.names,
    }
    path = tmp_path / "ckpt.pt"
    torch.save(ckpt, path)
    model, meta = load_checkpoint(path, device="cpu")
    w = (torch.randn(8000).numpy() * 0.2).astype("float32")
    guesses = predict_wave(model, meta, w, top_k=3)
    assert len(guesses) == 3
    assert guesses[0]["unit"].shape == (30,)
    assert "wave_type" in guesses[0]
```

- [ ] **Step 2: Implement**

`predict_wave` for v1:
1. pack features
2. forward
3. top-k classes from softmax
4. same unit vector paired with each of top-k wave types (v1 shares one regression head)
5. pin square-only defaults when wave_type != 0

For v2:
- for each top-k class, take `unit_per_class[:, class, :]`

Also CLI:

```bash
uv run python -m invert.predict target.wav --ckpt invert/runs/v1/best.pt -o guesses/ --top-k 3
```

Writes `guess_1.bfxr` … via `write_bfxr`.

- [ ] **Step 3: Run tests + commit**

```bash
cd tools && uv run pytest tests/test_invert_predict.py -v
git add tools/invert/predict.py tools/tests/test_invert_predict.py
git commit -m "Add invert.predict checkpoint → ranked bfxr guesses"
```

---

### Task 9: Matcher integration (`--seed-model`, `--one-shot`)

**Files:**
- Modify: `tools/match/optimizer.py`
- Modify: `tools/match/match.py`
- Create: `tools/tests/test_invert_match_seed.py`

Behavior from spec:
- `--seed-model <ckpt>`: model top-3 wave types + their units, plus jittered copies, **replace** Stage 0 random screen. Stages 1/2/refine unchanged.
- `--one-shot`: render raw top prediction only (no search). Growth metric.

- [ ] **Step 1: Extend `OptimizeSettings` + Stage 0**

```python
# OptimizeSettings additions
seed_units: list[tuple[int, np.ndarray]] | None = None  # (wave_type, unit)
# when set, _stage0 evaluates these (+ jitter) instead of _screen_sample
seed_jitter: float = 0.05
seed_jitter_copies: int = 8  # per model seed
```

`_stage0` change:
- If `self.s.seed_units` is None: existing behavior (keep f0 heuristic sampling).
- Else: for each `(wt, unit)` in seed_units, evaluate `unit` plus `seed_jitter_copies` Gaussian jitters clipped to `[0, upper]`, grouping best per wave type as today. Do **not** iterate all wave types.

- [ ] **Step 2: Wire CLI in `match.py`**

```python
p.add_argument("--seed-model", type=Path, default=None,
               help="invert checkpoint to replace stage-0 random screen")
p.add_argument("--one-shot", action="store_true",
               help="emit raw model top prediction only (requires --seed-model)")
```

Flow:
- if `--one-shot`: require `--seed-model`; predict top-1; render; write outputs; skip optimizer.
- if `--seed-model` without one-shot: `predict_wave(..., top_k=3)` → fill `OptimizeSettings.seed_units` (optionally expand with jitter inside optimizer).

- [ ] **Step 3: Smoke test with random checkpoint + 1 target, tiny budget**

```python
# tools/tests/test_invert_match_seed.py
def test_seed_model_smoke(tmp_path):
    # write random ckpt, run match.main on a short synthetic wav OR a tiny
    # fixture wav with --budget 20 --seed-model ckpt -o tmp
    # assert exit 0 and match.bfxr exists
```

Use a generated sine wav written to `tmp_path` (no dependency on gitignored `targets/`).

- [ ] **Step 4: Run + commit**

```bash
cd tools && uv run pytest tests/test_invert_match_seed.py -v
git add tools/match/optimizer.py tools/match/match.py tools/tests/test_invert_match_seed.py
git commit -m "Wire invert checkpoint into match --seed-model and --one-shot"
```

---

### Task 10: Eval script on `tools/targets/`

**Files:**
- Create: `tools/invert/eval_targets.py`

Columns: `current | model-seeded | one-shot` for every wav under `tools/targets/`.

- [ ] **Step 1: Implement CLI**

```bash
uv run python -m invert.eval_targets \
  --targets targets/ \
  --ckpt invert/runs/v1/best.pt \
  --budget 2000 \
  -o invert/runs/v1/eval/
```

For each target (try/except so one failure doesn't kill the run):
1. Run current pipeline (no seed model) with fixed `--budget` / `--rng-seed`
2. Run model-seeded with same budget
3. Run one-shot
4. Record best perceptual scores + wave type names

Write `results.json` + `results.md` markdown table.

Hard-target spotlight list (for pass/fail commentary, not code gating):
`mario 3 - flame`, `mega_man_ii_beam-out`, mario jumps, etc. — print a summary section.

- [ ] **Step 2: Manual dry-run with random ckpt + 1 file** (agent verifies CLI parses and runs)

```bash
cd tools && uv run python -m invert.eval_targets --targets targets/mega_man_ii_hurt.wav \
  --ckpt /tmp/rand.pt --budget 40 -o /tmp/eval_smoke --jobs 2
```

- [ ] **Step 3: Commit**

```bash
git add tools/invert/eval_targets.py
git commit -m "Add invert target eval table (current vs seeded vs one-shot)"
```

---

### Task 11: README + full-data training recipe

**Files:**
- Modify: `tools/README.md`

- [ ] **Step 1: Document**

```markdown
## Inverse model (seeder)

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
```

- [ ] **Step 2: Commit**

```bash
git add tools/README.md
git commit -m "Document invert dataset/train/seed-model workflow"
```

---

### Task 12: v1 quality gate (manual, after real train)

Not automated CI. After Task 11 code is in:

1. Generate 300k shards
2. Train v1 to convergence on MPS
3. Run `eval_targets` at equal budget
4. **Pass:** model-seeded beats current on hard targets (flame, beam-out, mario jumps)
5. Also check in-domain held-out: sample 256 generated sounds, predict, re-render, perceptual score should be near-perfect; if not, debug model/data before trusting real-target numbers
6. Only then implement/train **v2** (already coded in `InverseModel(version=2)`): re-run train with `--version 2`, compare eval table

If within-wavetype mode-averaging shows up (v1/v2 both mediocre in-domain for multimodal classes), stop and revisit Option 3 from the spec — do not invent it in this plan.

---

## Self-review checklist (author)

**Spec coverage:**
| Spec item | Task |
|-----------|------|
| `sampler.py` stage-0 + 20% uniform + envelope project + square pins | Task 2 |
| Silent/failed render filter | Task 5 |
| Native worker pool renders, stored seed | Task 5 |
| 300k shards, float16 features, version tag | Task 5 / 11 |
| Augmentation 50%, labels unchanged | Task 3 / 5 |
| Contours + 64 mel + log-duration, 128 frames, fill+mask | Task 4 |
| v1 CNN heads MSE+CE, square-only loss mask | Task 6 / 7 |
| v2 per-wavetype heads | Task 6 / 7 / 12 |
| `--seed-model` replaces stage 0; stages 1/2/refine unchanged | Task 9 |
| `--one-shot` | Task 9 |
| `predict.py` standalone | Task 8 |
| Eval table 3 columns on 32 targets | Task 10 |
| Tests listed in spec | Tasks 2–5, 6, 9 |

**Placeholders:** none intentional — Task 12 is an explicit manual gate, not a TBD in code.

**Type consistency:** `unit` always length-30 unit-space; `wave_type` = DSP id; `class_idx` = index into `sorted(wave_types)`.
