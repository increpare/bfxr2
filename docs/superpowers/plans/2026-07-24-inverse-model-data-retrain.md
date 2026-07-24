# Inverse-Model Data-Retrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the inverse model on real/general SFX and discrete-note structure by upgrading the synthetic data generator (structured sampler + retro-degradation augmentation + degenerate-culling), then training two candidate models and picking the winner on a held-out real-SFX eval.

**Architecture:** Pure data-generator changes in `invert/` — a new `structured` sampler mode that builds coherent arpeggios, a retro-degradation augmentation chain, and a tightened acceptance gate. Regenerate the dataset as `v5`, train a from-scratch model and a v6-finetune, decide on the real-SFX eval. No model-architecture change; loss config held identical to v6.

**Tech Stack:** Python 3.12 (`uv`), NumPy, PyTorch (CPU), the existing Node headless renderer.

## Global Constraints

- Run all module commands from `tools/` with `uv` (e.g. `cd tools && uv run pytest`). Python >=3.12,<3.13.
- Never edit anything under `js/` (browser app). Reading it is fine.
- Never commit anything under `invert/data/**` or `invert/runs/**` (gitignored).
- Final `MIX` (must sum to 1.0): `biased 0.20 / uniform 0.10 / kknob 0.25 / preset 0.20 / structured 0.25`. **Preset stays 0.20.**
- Default `augment_p` = **0.4** (baked augmentation → keep clean data the majority; the retro chain is strong, so a moderate rate suffices). Effective heavy-degradation rate is lower still (retro stage has its own 0.6 sub-probability).
- `DATASET_VERSION` = **"v5"**. Dataset size is chosen by a **staged scan (500k → 750k → 1M)**, growing only while the eval still improves (see Task 6 stop-gate); shard dirs are `invert/data/v5_500k` / `v5_750k` / `v5_1m` (gitignored, ~9–18 GB). Scale training epochs so examples-seen ≈ v6's run at each size.
- Tonal wave types (arpeggios): `(0, 1, 2, 4, 5, 6, 7, 8, 10, 11)` — exclude White(3) and Bitnoise(9).
- `[-1,1]`-range params (`pitch_jump_amount`, `pitch_jump_2_amount`, `lpFilterCutoffSweep`) need `unit = (value+1)/2`; all others here are `[0,1]` so `unit = value`.
- Loss config for BOTH training arms held identical to v6 (param loss + surrogate spectral term + identifiability weighting) — the only change under test is the data.
- End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File structure

- `invert/constants.py` — MODIFY: `DATASET_VERSION` → `"v5"`; add `ACCEPT_PEAK`, `MIN_AUDIBLE_SAMPLES`.
- `invert/sampler.py` — MODIFY: add `TONAL_WAVE_TYPES`, `_to_unit`, `_structured_unit`, `"structured"` branch in `sample_unit`.
- `invert/augment.py` — MODIFY: add retro-chain helpers + a wired, bounded retro stage in `maybe_augment`.
- `invert/dataset.py` — MODIFY: tighten `_is_acceptable_wave`; new `MIX` + `structured` specs in `_build_generation_specs`; default `augment_p` 0.4.
- `invert/train.py` — MODIFY: add `--init-weights` to load a checkpoint before training (finetune arm).
- `tests/test_invert_sampler.py`, `tests/test_invert_augment.py`, `tests/test_invert_dataset.py` — MODIFY (extend).

---

### Task 1: Structured sampler mode

**Files:**
- Modify: `invert/sampler.py`
- Test: `tests/test_invert_sampler.py`

**Interfaces:**
- Consumes: `ParamSpace` (`.names`, `.mins`, `.maxs`, `.defaults_unit()`), `match.optimizer.freq_param_from_hz`, `match.notes.pitch_jump_param_from_ratio`.
- Produces: `sampler.TONAL_WAVE_TYPES: tuple[int,...]`, `sampler._structured_unit(space, rng) -> np.ndarray`, and `sample_unit(space, rng, mode="structured")` returning a structured unit.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_invert_sampler.py
import numpy as np
from match.bfxr_io import ParamSpace
from invert.sampler import TONAL_WAVE_TYPES, sample_unit, _structured_unit


def _idx(space, name):
    return space.names.index(name)


def test_structured_unit_sets_a_pitch_jump_and_audible_envelope():
    space = ParamSpace()
    rng = np.random.default_rng(0)
    u = _structured_unit(space, rng)
    assert u.shape == (space.dim,)
    assert np.all((u >= 0.0) & (u <= 1.0))
    # at least the first jump is non-default (default pitch_jump_amount unit = 0.5)
    assert abs(u[_idx(space, "pitch_jump_amount")] - 0.5) > 1e-6
    # onset ordered when a second jump is present
    a2 = u[_idx(space, "pitch_jump_2_amount")]
    if abs(a2 - 0.5) > 1e-6:
        assert u[_idx(space, "pitch_jump_onset2_percent")] >= u[_idx(space, "pitch_jump_onset_percent")]
    # envelope has real sustain (audible), not the degenerate near-zero
    assert u[_idx(space, "sustainTime")] > 0.2


def test_structured_unit_is_deterministic_under_seed():
    space = ParamSpace()
    a = _structured_unit(space, np.random.default_rng(7))
    b = _structured_unit(space, np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_sample_unit_structured_mode_dispatches():
    space = ParamSpace()
    u = sample_unit(space, np.random.default_rng(1), mode="structured")
    assert u.shape == (space.dim,)
    assert abs(u[_idx(space, "pitch_jump_amount")] - 0.5) > 1e-6


def test_tonal_wave_types_exclude_noise():
    assert 3 not in TONAL_WAVE_TYPES and 9 not in TONAL_WAVE_TYPES
    assert 0 in TONAL_WAVE_TYPES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_sampler.py -k "structured or tonal" -v`
Expected: FAIL (ImportError: cannot import name `TONAL_WAVE_TYPES` / `_structured_unit`).

- [ ] **Step 3: Write minimal implementation**

Add to the top of `invert/sampler.py` (imports section):

```python
from match.optimizer import (
    ENVELOPE_PARAMS,
    ENVELOPE_SAMPLES_PER_UNIT,
    SQUARE_ONLY_PARAMS,
    freq_param_from_hz,
)
from match.notes import pitch_jump_param_from_ratio
```

(The first three names are already imported from `match.optimizer`; just add `freq_param_from_hz`. Add the `match.notes` import as a new line.)

Add near the top-level constants:

```python
# tonal oscillators — pitch jumps read as pitched notes here (exclude
# White(3) and Bitnoise(9), whose "pitch" is noise)
TONAL_WAVE_TYPES = (0, 1, 2, 4, 5, 6, 7, 8, 10, 11)


def _to_unit(space: ParamSpace, name: str, value: float) -> float:
    i = space.names.index(name)
    lo, hi = float(space.mins[i]), float(space.maxs[i])
    span = hi - lo
    return float(np.clip((value - lo) / span, 0.0, 1.0)) if span else 0.0


def _structured_unit(space: ParamSpace, rng: np.random.Generator) -> np.ndarray:
    """A coherent arpeggio: 1-2 pitch jumps at musical intervals with an
    envelope sized so every note is audible, plus optional repeat / vibrato /
    filter-sweep variants. Returns a unit vector; wave type is chosen by the
    caller (tonal). Non-overridden params keep their defaults (e.g. no slide)."""
    unit = space.defaults_unit().copy()

    base_hz = float(np.exp(rng.uniform(np.log(200.0), np.log(2000.0))))
    fs = freq_param_from_hz(base_hz)
    unit[space.names.index("frequency_start")] = _to_unit(
        space, "frequency_start", fs if fs is not None else 0.3)

    def _ratio() -> float:
        semis = int(rng.integers(2, 25)) * (1 if rng.random() < 0.5 else -1)
        return float(2.0 ** (semis / 12.0))

    on1 = float(rng.uniform(0.2, 0.5))
    unit[space.names.index("pitch_jump_amount")] = _to_unit(
        space, "pitch_jump_amount", pitch_jump_param_from_ratio(_ratio()))
    unit[space.names.index("pitch_jump_onset_percent")] = _to_unit(
        space, "pitch_jump_onset_percent", on1)
    if rng.random() < 0.6:  # second jump most of the time
        unit[space.names.index("pitch_jump_2_amount")] = _to_unit(
            space, "pitch_jump_2_amount", pitch_jump_param_from_ratio(_ratio()))
        unit[space.names.index("pitch_jump_onset2_percent")] = _to_unit(
            space, "pitch_jump_onset2_percent", float(rng.uniform(on1 + 0.15, 0.9)))

    unit[space.names.index("attackTime")] = _to_unit(
        space, "attackTime", float(rng.uniform(0.0, 0.05)))
    unit[space.names.index("sustainTime")] = _to_unit(
        space, "sustainTime", float(rng.uniform(0.25, 0.6)))
    unit[space.names.index("decayTime")] = _to_unit(
        space, "decayTime", float(rng.uniform(0.15, 0.5)))

    if rng.random() < 0.25:  # repeating motif
        unit[space.names.index("pitch_jump_repeat_speed")] = _to_unit(
            space, "pitch_jump_repeat_speed", float(rng.uniform(0.1, 0.6)))
    if rng.random() < 0.25:  # vibrato
        unit[space.names.index("vibratoDepth")] = _to_unit(
            space, "vibratoDepth", float(rng.uniform(0.1, 0.5)))
        unit[space.names.index("vibratoSpeed")] = _to_unit(
            space, "vibratoSpeed", float(rng.uniform(0.2, 0.7)))
    if rng.random() < 0.25:  # filter sweep
        unit[space.names.index("lpFilterCutoffSweep")] = _to_unit(
            space, "lpFilterCutoffSweep", float(rng.uniform(-0.5, 0.5)))

    return np.clip(unit, 0.0, 1.0)
```

Add the `"structured"` branch inside `sample_unit`, before the `raise ValueError(mode)`:

```python
    if mode == "structured":
        return _structured_unit(space, rng)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_sampler.py -v`
Expected: PASS (all, including pre-existing sampler tests).

- [ ] **Step 5: Commit**

```bash
cd tools && git add invert/sampler.py tests/test_invert_sampler.py
git commit -m "Add structured arpeggio sampler mode

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Retro-degradation augmentation

**Files:**
- Modify: `invert/augment.py`
- Modify: `invert/constants.py` (add `ACCEPT_PEAK`)
- Test: `tests/test_invert_augment.py`

**Interfaces:**
- Consumes: `constants.ACCEPT_PEAK`.
- Produces: `augment._retro_degrade(x, rng) -> np.ndarray`; `maybe_augment` now applies a bounded retro stage.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_invert_augment.py
import numpy as np
from invert.augment import maybe_augment, _retro_degrade
from invert.constants import ACCEPT_PEAK


def _tone(n=8000, hz=440, sr=44100):
    t = np.arange(n) / sr
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_retro_degrade_stays_finite_and_same_length():
    x = _tone()
    y = _retro_degrade(x, np.random.default_rng(0))
    assert y.shape == x.shape and y.dtype == np.float32
    assert np.isfinite(y).all()


def test_retro_degrade_is_seed_deterministic():
    x = _tone()
    a = _retro_degrade(x, np.random.default_rng(3))
    b = _retro_degrade(x, np.random.default_rng(3))
    assert np.array_equal(a, b)


def test_augment_never_silences_an_audible_input():
    x = _tone()
    for s in range(30):
        y = maybe_augment(x, rng=np.random.default_rng(s), p=1.0)
        assert float(np.max(np.abs(y))) >= ACCEPT_PEAK
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_augment.py -k "retro or silences" -v`
Expected: FAIL (ImportError `_retro_degrade`; and `ACCEPT_PEAK` not in constants).

- [ ] **Step 3: Write minimal implementation**

Add to `invert/constants.py`:

```python
ACCEPT_PEAK = 0.02          # perceptual audibility floor (peak, post-render)
MIN_AUDIBLE_SAMPLES = 882   # ~20 ms @ 44100: reject degenerate "click" renders
```

Add to `invert/augment.py`:

```python
from .constants import ACCEPT_PEAK


def _retro_degrade(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Console-sample degradation: sample-rate crush (with aliasing), bit-depth
    crush, mu-law companding, occasional hard clip. Real target SFX are
    downsampled SNES/NES samples, so this teaches the model to recover the
    clean sound underneath."""
    y = np.asarray(x, dtype=np.float32).copy()
    n = len(y)
    if n == 0:
        return y

    # sample-rate crush: decimate then hold (aliasing leaks -> authentic)
    if rng.random() < 0.8:
        factor = int(rng.integers(3, 8))  # ~5.5-14.7 kHz effective
        ds = y[::factor]
        y = np.repeat(ds, factor)[:n].astype(np.float32)
        if len(y) < n:
            pad = np.full(n - len(y), y[-1] if len(y) else 0.0, dtype=np.float32)
            y = np.concatenate([y, pad])

    # bit-depth crush
    if rng.random() < 0.7:
        bits = int(rng.integers(4, 9))
        step = 2.0 / (2 ** bits)
        y = (np.round(y / step) * step).astype(np.float32)

    # mu-law companding grit
    if rng.random() < 0.5:
        mu = float(rng.choice([15.0, 31.0, 63.0, 255.0]))
        comp = np.sign(y) * np.log1p(mu * np.abs(y)) / np.log1p(mu)
        comp = np.round(comp * 32) / 32
        y = (np.sign(comp) * (1.0 / mu) * ((1.0 + mu) ** np.abs(comp) - 1.0)).astype(np.float32)

    # occasional hard clip / drive
    if rng.random() < 0.3:
        t = float(rng.uniform(0.3, 0.8))
        y = np.clip(y, -t, t).astype(np.float32)

    return y
```

In `maybe_augment`, after the existing roughening block and before the final return, add the bounded retro stage:

```python
    # console-sample degradation (retro chain)
    pre_peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if rng.random() < 0.6:
        x = _retro_degrade(x, rng)

    # bound: never turn an audible input into a (near-)silent pair — the aug is
    # baked into the shard, so a silenced aug is a bad training pair
    post_peak = float(np.max(np.abs(x))) if len(x) else 0.0
    if pre_peak >= ACCEPT_PEAK and 0.0 < post_peak < ACCEPT_PEAK:
        x = (x * (pre_peak / post_peak)).astype(np.float32)

    return x
```

(If `maybe_augment` currently returns `x` at multiple points, ensure the bound runs on the augmented path; keep the early `if rng.random() >= p: return x` short-circuit unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_augment.py -v`
Expected: PASS (all, including pre-existing augment tests).

- [ ] **Step 5: Commit**

```bash
cd tools && git add invert/augment.py invert/constants.py tests/test_invert_augment.py
git commit -m "Add bounded retro-degradation augmentation chain

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Degenerate-culling in the acceptance gate

**Files:**
- Modify: `invert/dataset.py` (`_is_acceptable_wave`)
- Test: `tests/test_invert_dataset.py`

**Interfaces:**
- Consumes: `constants.ACCEPT_PEAK`, `constants.MIN_AUDIBLE_SAMPLES` (added in Task 2).
- Produces: stricter `_is_acceptable_wave(wave) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_invert_dataset.py
import numpy as np
from invert.dataset import _is_acceptable_wave
from invert.constants import ACCEPT_PEAK, MIN_AUDIBLE_SAMPLES


def _tone(n, peak=0.5, hz=440, sr=44100):
    t = np.arange(n) / sr
    return (peak * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_accepts_normal_and_legit_short():
    assert _is_acceptable_wave(_tone(20000))            # normal
    assert _is_acceptable_wave(_tone(3000))             # ~68 ms blip is fine


def test_rejects_degenerate_click():
    click = np.zeros(20000, dtype=np.float32)
    click[:200] = 0.6                                   # ~4.5 ms of content
    assert not _is_acceptable_wave(click)


def test_rejects_near_mute():
    assert not _is_acceptable_wave(_tone(20000, peak=0.01))   # below ACCEPT_PEAK


def test_rejects_none_empty_nonfinite():
    assert not _is_acceptable_wave(None)
    assert not _is_acceptable_wave(np.zeros(0, dtype=np.float32))
    bad = _tone(20000); bad[5] = np.nan
    assert not _is_acceptable_wave(bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_dataset.py -k "accept or reject or degenerate or mute" -v`
Expected: FAIL (near-mute at peak 0.01 and the 4.5 ms click currently pass the old `1e-3` gate).

- [ ] **Step 3: Write minimal implementation**

Replace `_is_acceptable_wave` in `invert/dataset.py`, and update the import from constants to include the new names:

```python
def _is_acceptable_wave(wave: np.ndarray | None) -> bool:
    """True if wave is usable training audio: finite, audibly loud, and not a
    degenerate (pathologically short) click."""
    if wave is None or len(wave) == 0:
        return False
    w = np.asarray(wave)
    if not np.isfinite(w).all():
        return False
    peak = float(np.max(np.abs(w)))
    if not np.isfinite(peak) or peak < ACCEPT_PEAK:
        return False
    floor = peak * 10 ** (-40 / 20)   # -40 dB below peak
    if int(np.sum(np.abs(w) >= floor)) < MIN_AUDIBLE_SAMPLES:
        return False
    return True
```

Update the constants import at the top of `invert/dataset.py` (it currently imports `SILENCE_PEAK`; add the two new names and drop `SILENCE_PEAK` if now unused — grep first):

```python
from .constants import (
    DATASET_VERSION,
    FEATURES_MEL_SCALE_IDX,
    N_CHANNELS,
    N_FRAMES,
    ACCEPT_PEAK,
    MIN_AUDIBLE_SAMPLES,
    SQUARE_ONLY,
)
```

(Run `grep -n SILENCE_PEAK invert/dataset.py` — if no other use remains, remove it from the import; otherwise keep it.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_dataset.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
cd tools && git add invert/dataset.py tests/test_invert_dataset.py
git commit -m "Cull degenerate (near-mute / too-short) renders from training data

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: New MIX + structured integration + augment_p default

**Files:**
- Modify: `invert/dataset.py` (`MIX`, `_build_generation_specs`, mode-probability constants, `augment_p` default)
- Modify: `invert/constants.py` (`DATASET_VERSION` → `"v5"`)
- Test: `tests/test_invert_dataset.py`

**Interfaces:**
- Consumes: `sampler.TONAL_WAVE_TYPES`, `sampler.sample_unit(..., mode="structured")` (Task 1).
- Produces: `dataset.MIX` with `structured` key; `_build_generation_specs` emitting structured specs with tonal wave types.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_invert_dataset.py
from invert.dataset import MIX, _build_generation_specs
from invert.sampler import TONAL_WAVE_TYPES
from match.bfxr_io import ParamSpace


def test_mix_sums_to_one_and_keeps_preset():
    assert abs(sum(MIX.values()) - 1.0) < 1e-9
    assert MIX["preset"] == 0.20
    assert MIX["structured"] == 0.25


def test_generation_specs_have_structured_with_tonal_wave_types():
    space = ParamSpace()
    n = 400
    rng = np.random.default_rng(0)
    # preset harvest shells out to node; skip it here by requesting no presets
    specs = _build_generation_specs(space, n, seed=0, rng=rng)
    structured = [s for s in specs if s.get("kind") == "sample" and s.get("mode") == "structured"]
    assert len(specs) == n
    # ~25% structured (allow rounding slack)
    assert 0.20 * n <= len(structured) <= 0.30 * n
    assert all(s["wave_type"] in TONAL_WAVE_TYPES for s in structured)
```

Note: `_build_generation_specs` harvests presets via Node. If the test environment has Node + `render/preset_cli.js`, the test runs as-is. If not, guard the preset harvest with a small `try/except` in the test or run with `MIX["preset"]` temporarily — but prefer running with Node available (it is, in this repo).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_dataset.py -k "mix or structured_with_tonal" -v`
Expected: FAIL (`MIX` has no `structured` key; specs contain no structured entries).

- [ ] **Step 3: Write minimal implementation**

In `invert/dataset.py`, replace the `MIX` and mode-probability constants:

```python
MIX = {
    "biased": 0.20,
    "uniform": 0.10,
    "kknob": 0.25,
    "preset": 0.20,
    "structured": 0.25,
}
_RANDOM_MODES = ("biased", "uniform", "kknob")
# probabilities within the non-preset, non-structured share (0.55), normalized
_RANDOM_MODE_P = (0.20 / 0.55, 0.10 / 0.55, 0.25 / 0.55)
```

Add the import near the other sampler imports:

```python
from .sampler import (
    TONAL_WAVE_TYPES,
    finalize_example,
    sample_example,
    sample_unit,
    wave_type_index_map,
)
```

Replace `_build_generation_specs` body:

```python
def _build_generation_specs(
    space: ParamSpace,
    n: int,
    seed: int,
    rng: np.random.Generator,
) -> list[dict]:
    n_preset = round(n * MIX["preset"])
    n_structured = round(n * MIX["structured"])
    n_random = n - n_preset - n_structured

    preset_rows = harvest_preset_params(n_preset, seed) if n_preset else []
    specs: list[dict] = [{"kind": "preset", "row": row} for row in preset_rows]

    for _ in range(n_structured):
        wt = int(rng.choice(TONAL_WAVE_TYPES))
        specs.append({"kind": "sample", "mode": "structured", "wave_type": wt})

    for wt in _stratified_wave_types(space, n_random, rng):
        mode = str(rng.choice(_RANDOM_MODES, p=_RANDOM_MODE_P))
        specs.append({"kind": "sample", "mode": mode, "wave_type": int(wt)})

    rng.shuffle(specs)
    return specs
```

`_example_from_spec` needs **no change**: its `sample` branch already calls `sample_unit(space, rng, mode=spec["mode"])`, which now handles `"structured"` (Task 1).

Update the default `augment_p` (both the `write_shard`/`_pack_shard_payload` caller default and the CLI arg) from `0.25` to `0.4`:

```python
    p.add_argument("--augment-p", type=float, default=0.4)
```

and the function signature default (`augment_p: float = 0.4`).

In `invert/constants.py`:

```python
DATASET_VERSION = "v5"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_dataset.py -v`
Expected: PASS (all).

- [ ] **Step 5: Run the full suite (integration guard)**

Run: `cd tools && uv run pytest -q`
Expected: PASS (all; no regressions in sampler/augment/dataset/train tests).

- [ ] **Step 6: Commit**

```bash
cd tools && git add invert/dataset.py invert/constants.py tests/test_invert_dataset.py
git commit -m "Rebalance training MIX with structured slice; bump augment_p; v5

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `--init-weights` for the finetune arm

**Files:**
- Modify: `invert/train.py`
- Test: `tests/test_invert_train_metrics.py`

**Interfaces:**
- Consumes: the existing checkpoint format written by `train()` / read by `invert.predict.load_checkpoint`.
- Produces: `train(..., init_weights: Path | None = None)` and a `--init-weights` CLI flag that loads a model `state_dict` before the training loop.

- [ ] **Step 1: Read the checkpoint contract**

Read `invert/predict.py:load_checkpoint` and the checkpoint-saving code in `invert/train.py` to confirm the exact state-dict key (e.g. `ckpt["model_state"]`) and the model constructor/args. Use those exact names below.

- [ ] **Step 2: Write the failing test**

```python
# add to tests/test_invert_train_metrics.py
import torch
from pathlib import Path
from invert.train import build_parser


def test_init_weights_flag_parses(tmp_path):
    args = build_parser().parse_args(
        ["--data", str(tmp_path), "--out", str(tmp_path / "o"),
         "--init-weights", str(tmp_path / "w.pt")]
    )
    assert args.init_weights == tmp_path / "w.pt"
```

(If a heavier end-to-end test is warranted, add one that trains 1 epoch on a tiny generated shard with `--init-weights` pointing at a just-saved checkpoint and asserts the run completes and the first-step loss reflects the loaded weights. Keep the parse test as the fast gate.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py -k init_weights -v`
Expected: FAIL (`unrecognized arguments: --init-weights`).

- [ ] **Step 4: Write minimal implementation**

Add the CLI arg in `build_parser`:

```python
    p.add_argument("--init-weights", type=Path, default=None,
                   help="load model weights from this checkpoint before training "
                        "(finetune); architecture flags must match the checkpoint")
```

Add `init_weights: Path | None = None` to the `train(...)` signature, and after the model is constructed (and moved to `device`) but before the optimizer/training loop, load the weights (use the exact key confirmed in Step 1):

```python
    if init_weights is not None:
        state = torch.load(init_weights, map_location=device)
        model.load_state_dict(state["model_state"])
```

Thread the CLI value into the `train(...)` call in `main`:

```python
        init_weights=args.init_weights,
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd tools && uv run pytest tests/test_invert_train_metrics.py -v`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
cd tools && git add invert/train.py tests/test_invert_train_metrics.py
git commit -m "train: add --init-weights to finetune from a checkpoint

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Staged data-scaling, train, evaluate, decide (operational)

**Files:** none committed (outputs are gitignored `invert/data/**`, `invert/runs/**`). This task produces a written results note.

**Not TDD** — this is the compute run. Use the exact commands; record numbers as you go. The dataset size grows **adaptively**: start at 500k, grow to 1M only while the eval is still improving. The staged scan runs on the **from-scratch arm only**; the finetune arm is trained once at the chosen size (avoids doing the ladder twice).

**Stop-gate ("still improving?"):** after each size round, stop growing when **both** hold vs the previous round: real-SFX seeded-median improves by **< 0.05**, *and* held-out synthetic val loss improves by **< 1%**. Otherwise grow to the next size (cap 1M).

- [ ] **Step 1: Generate the 500k base dataset**

Confirm flags with `uv run python -m invert.dataset --help`, then:

```bash
cd tools && uv run python -m invert.dataset --out invert/data/v5_500k --n 500000 --augment-p 0.4 --seed 0
```
Expected: shards + `manifest.json`; manifest `mix` shows the new proportions and `augment_p 0.4`. (~18 KB/example → ~9 GB at 500k, gitignored.)

- [ ] **Step 2: Sanity-check the dataset**

Load a shard: confirm wave-type distribution (~25% structured, ~20% preset), that culling is active (no near-mute/degenerate pairs), and render a few structured labels to confirm they audibly step through discrete notes.

- [ ] **Step 3: Round 1 — train from scratch on 500k, eval**

Match v6's loss flags (confirm the surrogate path + `--spectral-weight` from v6's run config). Scale `--epochs` so examples-seen ≈ v6's run (500k is ~1.7× v4 → ≈ v6_epochs / 1.7):

```bash
cd tools && uv run python -m invert.train --data invert/data/v5_500k --out invert/runs/v7_scratch_500k \
  --surrogate invert/runs/surrogate/surrogate.pt --spectral-weight <v6_value> [other v6 flags]
```
Then eval (val loss is in the run log; real-SFX below):

```bash
cd tools && uv run python -m invert.eval_targets --targets targets/ \
  --ckpt invert/runs/v7_scratch_500k/best.pt --budget 2000 --duration-floor 0.5 \
  -o invert/runs/v7_scratch_500k/eval_targets
```
Record: real-SFX median + val loss.

- [ ] **Step 4: Round 2 — grow to 750k, continue training, eval**

Generate a fresh 750k dataset (distinct seed; generation is cheap, so regenerate rather than splice shards):

```bash
cd tools && uv run python -m invert.dataset --out invert/data/v5_750k --n 750000 --augment-p 0.4 --seed 1
```
Continue training from round 1 (warm start) on the larger set, then eval:

```bash
cd tools && uv run python -m invert.train --data invert/data/v5_750k --out invert/runs/v7_scratch_750k \
  --init-weights invert/runs/v7_scratch_500k/best.pt \
  --surrogate invert/runs/surrogate/surrogate.pt --spectral-weight <v6_value> [other v6 flags]
cd tools && uv run python -m invert.eval_targets --targets targets/ \
  --ckpt invert/runs/v7_scratch_750k/best.pt --budget 2000 --duration-floor 0.5 \
  -o invert/runs/v7_scratch_750k/eval_targets
```
Apply the stop-gate vs round 1. If improving, continue to Step 5; else the winning size is 500k — skip to Step 6 with `v7_scratch_500k`.

- [ ] **Step 5: Round 3 — grow to 1M, continue, eval (cap)**

```bash
cd tools && uv run python -m invert.dataset --out invert/data/v5_1m --n 1000000 --augment-p 0.4 --seed 2
cd tools && uv run python -m invert.train --data invert/data/v5_1m --out invert/runs/v7_scratch_1m \
  --init-weights invert/runs/v7_scratch_750k/best.pt \
  --surrogate invert/runs/surrogate/surrogate.pt --spectral-weight <v6_value> [other v6 flags]
cd tools && uv run python -m invert.eval_targets --targets targets/ \
  --ckpt invert/runs/v7_scratch_1m/best.pt --budget 2000 --duration-floor 0.5 \
  -o invert/runs/v7_scratch_1m/eval_targets
```
The winning from-scratch size `N*` = the last round that cleared the stop-gate (cap 1M). Call its checkpoint `v7_scratch` and its dataset dir `invert/data/v5_<N*>`.

Note: warm-start continuation measures *marginal data value* cheaply; it is not a pristine from-scratch-at-each-size ablation (acceptable — the goal is to pick a good size, not a scaling law).

- [ ] **Step 6: Train the finetune arm once at N\***

```bash
cd tools && uv run python -m invert.train --data invert/data/v5_<N*> --out invert/runs/v7_finetune \
  --init-weights invert/runs/v6_spectral/best.pt \
  --surrogate invert/runs/surrogate/surrogate.pt --spectral-weight <v6_value> [other v6 flags]
cd tools && uv run python -m invert.eval_targets --targets targets/ \
  --ckpt invert/runs/v7_finetune/best.pt --budget 2000 --duration-floor 0.5 \
  -o invert/runs/v7_finetune/eval_targets
```

- [ ] **Step 7: Arp one-shot probe + in-domain sanity**

- Re-run the discrete-note one-shot check (the controlled arpeggio target + Throw/cursor/leeneBell) for `v7_scratch`, `v7_finetune`, and v6; confirm the **raw one-shot** predicts discrete notes better than v6.
- On a small held-out synthetic set (fresh seed), measure param R² / spectral score for each model to quantify any in-domain cost.

- [ ] **Step 8: Decide + write results note**

Write `docs/superpowers/plans/2026-07-24-inverse-model-data-retrain-results.md`: the data-scaling curve (real-SFX median + val loss at 500k/750k/1M), the chosen size `N*`, real-SFX medians (v6 vs v7_scratch vs v7_finetune), the arp one-shot verdict, and in-domain cost. **Winner = best real-SFX median without catastrophic in-domain regression.** If neither v7 beats v6, keep v6 and report the negative result (do not ship a regression). Commit the results note (not the runs).

---

## Self-Review

**Spec coverage:** Structured sampler (Task 1) ✓; retro augmentation (Task 2) ✓; degenerate-culling (Task 3) ✓; MIX rebalance + preset-retained + augment_p (Task 4) ✓; DATASET_VERSION v5 (Task 4) ✓; finetune `--init-weights` (Task 5) ✓; two-arm train + real-SFX eval + in-domain guardrail + arp probe + keep-v6-if-no-win (Task 6) ✓. Real-audio distillation is out of scope per spec (not planned) ✓.

**Placeholder scan:** The only intentionally-deferred literals are `<v6_value>` / `[other v6 flags]` in Task 6 — these are read from v6's run config at execution time (the spec fixes "loss config identical to v6"), and Task 5 Step 1 / Task 6 Step 3 tell the implementer exactly where to read them. All code tasks (1–5) contain complete code.

**Type consistency:** `_to_unit(space, name, value)`, `_structured_unit(space, rng)`, `TONAL_WAVE_TYPES` used identically across sampler and dataset; `ACCEPT_PEAK`/`MIN_AUDIBLE_SAMPLES` defined in Task 2, consumed in Task 3; `MIX`/`_RANDOM_MODES`/`_RANDOM_MODE_P` consistent; `--init-weights`→`init_weights` consistent.
