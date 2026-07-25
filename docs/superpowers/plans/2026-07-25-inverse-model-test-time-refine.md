# Test-Time Surrogate Refine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** At inference, sharpen inverse-model seeds by Adam steps on the predicted unit through the frozen `SurrogateSynth`, then gate the gain with a hard-slice listen (refined one-shot vs raw).

**Architecture:** New `invert/refine.py` owns the pure refine loop. `match.match` calls it after `predict_wave` when `--surrogate-refine-steps > 0`. Flags are named to avoid clashing with existing Stage 3 `--refine-steps` (FD steepest descent). No retrain. Default remains off until the listen gate passes.

**Tech Stack:** PyTorch, existing `SurrogateSynth` / `pack_features` / `ParamSpace`, `match.match` CLI, pytest via `cd tools && uv run pytest`.

**Spec:** `docs/superpowers/specs/2026-07-25-inverse-model-test-time-refine-design.md`  
**Strategy:** `docs/superpowers/plans/2026-07-25-inverse-model-next-bets.md`

**Checkpoints (worktree paths; symlink or pass absolute paths):**
- Inverse: `.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt`
- Surrogate: `.worktrees/inverse-model-next/tools/invert/runs/surrogate/surrogate.pt`

**Approved CLI deviation from first design draft:** use `--surrogate-refine-steps` / `--surrogate-refine-lr` / `--surrogate`, not `--refine-steps` (already Stage 3). Spec updated accordingly.

---

## File structure

| File | Role |
| --- | --- |
| `tools/invert/refine.py` | **Create.** `refine_unit(...)` Adam loop + square-only pin |
| `tools/tests/test_invert_refine.py` | **Create.** Loss-drop, bounds, pin, steps=0 semantics |
| `tools/match/match.py` | **Modify.** Flags, call refine after predict, report JSON |
| `tools/tests/test_invert_match_seed.py` | **Modify.** Smoke with surrogate refine on |
| `tools/invert/eval_targets.py` | **Modify.** Passthrough flags for batch A/B |
| `tools/match/listen_refine_compare.py` | **Create.** Hard-slice listen page: original / raw / refined / seeded |
| `docs/superpowers/plans/2026-07-25-test-time-refine-results.md` | **Create** after listen (Task 5) |

---

### Task 1: `refine_unit` core (TDD)

**Files:**
- Create: `tools/invert/refine.py`
- Create: `tools/tests/test_invert_refine.py`

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_invert_refine.py`:

```python
import numpy as np
import torch
import torch.nn.functional as F

from invert.constants import N_PARAMS, N_WAVETYPES, SQUARE_ONLY
from invert.surrogate import SurrogateSynth
from match.bfxr_io import ParamSpace


def _mse(surrogate, unit, onehot, log_dur, target_feat):
    with torch.no_grad():
        pred = surrogate(unit, onehot, log_dur)
        return float(F.mse_loss(pred, target_feat))


def test_refine_unit_reduces_surrogate_mse():
    from invert.refine import refine_unit

    torch.manual_seed(0)
    surrogate = SurrogateSynth(width=16)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    unit_true = torch.rand(1, N_PARAMS)
    # non-square so square-only pin is exercised later
    wave_type = 2
    onehot = F.one_hot(torch.tensor([wave_type]), N_WAVETYPES).float()
    log_dur = torch.zeros(1)
    target_feat = surrogate(unit_true, onehot, log_dur).detach()

    noise = 0.15 * torch.randn_like(unit_true)
    unit0 = (unit_true + noise).clamp(0, 1).numpy().astype(np.float64).reshape(-1)

    u0 = torch.tensor(unit0, dtype=torch.float32).unsqueeze(0)
    mse0 = _mse(surrogate, u0, onehot, log_dur, target_feat)

    refined = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=80, lr=5e-2, device=torch.device("cpu"),
    )
    assert refined.shape == (N_PARAMS,)
    assert np.all(refined >= 0.0) and np.all(refined <= 1.0)

    u1 = torch.tensor(refined, dtype=torch.float32).unsqueeze(0)
    # rebuild onehot the same way refine does (wave_type fixed)
    mse1 = _mse(surrogate, u1, onehot, log_dur, target_feat)
    assert mse1 < mse0


def test_refine_pins_square_only_for_non_square():
    from invert.refine import refine_unit

    torch.manual_seed(1)
    surrogate = SurrogateSynth(width=8)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    space = ParamSpace()
    wave_type = 2  # not square
    unit0 = np.random.default_rng(0).random(N_PARAMS).astype(np.float64)
    # force square-only dims away from defaults so pin is visible
    for name in SQUARE_ONLY:
        unit0[space.names.index(name)] = 0.9

    onehot = F.one_hot(torch.tensor([wave_type]), N_WAVETYPES).float()
    log_dur = torch.zeros(1)
    target_feat = surrogate(
        torch.tensor(unit0, dtype=torch.float32).unsqueeze(0), onehot, log_dur
    ).detach()

    refined = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=5, lr=1e-2, device=torch.device("cpu"),
    )
    defaults = space.defaults_unit()
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        assert abs(refined[j] - float(defaults[j])) < 1e-6


def test_refine_steps_zero_returns_pinned_copy():
    from invert.refine import refine_unit

    space = ParamSpace()
    wave_type = 2
    unit0 = np.linspace(0.1, 0.9, N_PARAMS).astype(np.float64)
    for name in SQUARE_ONLY:
        unit0[space.names.index(name)] = 0.77

    # dummy tensors unused when steps=0
    target_feat = torch.zeros(1, 70, 128)
    log_dur = torch.zeros(1)
    surrogate = SurrogateSynth(width=4)

    out = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=0, lr=1e-2, device=torch.device("cpu"),
    )
    defaults = space.defaults_unit()
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        assert abs(out[j] - float(defaults[j])) < 1e-6
    # other dims unchanged
    for j, name in enumerate(space.names):
        if name in SQUARE_ONLY:
            continue
        assert abs(out[j] - unit0[j]) < 1e-9
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tools && uv run pytest tests/test_invert_refine.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `invert.refine`.

- [ ] **Step 3: Implement `tools/invert/refine.py`**

```python
"""Inference-time Adam refine of predicted unit through frozen SurrogateSynth.

    See docs/superpowers/specs/2026-07-25-inverse-model-test-time-refine-design.md
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

from match.bfxr_io import ParamSpace

from .constants import N_WAVETYPES, SQUARE_ONLY


def _pin_square_only(unit: np.ndarray, wave_type: int, space: ParamSpace) -> np.ndarray:
    out = np.asarray(unit, dtype=np.float64).copy()
    if wave_type != 0:
        defaults = space.defaults_unit()
        for name in SQUARE_ONLY:
            j = space.names.index(name)
            out[j] = float(defaults[j])
    return out


def refine_unit(
    unit: np.ndarray,
    wave_type: int,
    target_features_norm: torch.Tensor,
    log_duration: torch.Tensor,
    surrogate: torch.nn.Module,
    *,
    steps: int,
    lr: float,
    device: torch.device,
) -> np.ndarray:
    """Optimize `unit` to match `target_features_norm` under frozen surrogate.

    `target_features_norm` and `log_duration` must already be on `device` (or
    will be moved). Wavetype is fixed (hard one-hot). Returns a pinned numpy
    unit in [0, 1]. When steps <= 0, only pins and returns.
    """
    space = ParamSpace()
    unit_np = _pin_square_only(unit, wave_type, space)
    if steps <= 0:
        return unit_np

    surrogate = surrogate.to(device)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    x = target_features_norm.to(device).float()
    if x.dim() == 2:
        x = x.unsqueeze(0)
    log_dur = log_duration.to(device).float().reshape(-1)
    if log_dur.numel() == 1 and x.shape[0] == 1:
        pass
    onehot = F.one_hot(
        torch.tensor([int(wave_type)], device=device), N_WAVETYPES
    ).float()

    u = torch.tensor(unit_np, dtype=torch.float32, device=device).unsqueeze(0)
    u = u.detach().clone().requires_grad_(True)
    opt = torch.optim.Adam([u], lr=lr)

    for _ in range(int(steps)):
        opt.zero_grad(set_to_none=True)
        pred = surrogate(u, onehot, log_dur)
        loss = F.mse_loss(pred, x)
        loss.backward()
        opt.step()
        with torch.no_grad():
            u.clamp_(0.0, 1.0)

    out = u.detach().cpu().numpy().reshape(-1).astype(np.float64)
    return _pin_square_only(out, wave_type, space)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tools && uv run pytest tests/test_invert_refine.py -v
```

Expected: PASS (3 tests). If `test_refine_unit_reduces_surrogate_mse` flakes, bump `steps` to 120 or `lr` to `1e-1` in the test only — do not weaken the assertion to `<=`.

- [ ] **Step 5: Commit**

```bash
git add tools/invert/refine.py tools/tests/test_invert_refine.py
git commit -m "feat(invert): test-time Adam refine through SurrogateSynth"
```

---

### Task 2: Wire into `match.match`

**Files:**
- Modify: `tools/match/match.py`
- Modify: `tools/tests/test_invert_match_seed.py`

- [ ] **Step 1: Add failing CLI smoke for surrogate refine**

Append to `tools/tests/test_invert_match_seed.py`:

```python
def test_match_one_shot_surrogate_refine_smoke(tmp_path):
    from invert.surrogate import SurrogateSynth
    import torch
    from invert import constants

    ckpt = tmp_path / "ckpt.pt"
    wav = tmp_path / "target.wav"
    out = tmp_path / "out_ref"
    sur_path = tmp_path / "surrogate.pt"
    _write_random_ckpt(ckpt)
    _write_short_wav(wav)
    m = SurrogateSynth(width=8)
    torch.save(
        {
            "model_state": m.state_dict(),
            "width": 8,
            "channel_mean": list(constants.CHANNEL_MEAN),
            "channel_std": list(constants.CHANNEL_STD),
        },
        sur_path,
    )

    rc = main(
        [
            str(wav),
            "--seed-model", str(ckpt),
            "--one-shot",
            "--surrogate-refine-steps", "5",
            "--surrogate", str(sur_path),
            "-o", str(out),
            "--jobs", "1",
        ]
    )
    assert rc == 0
    assert (out / "match.bfxr").is_file()
    report = __import__("json").loads((out / "report.json").read_text())
    assert report["flags"]["surrogate_refine_steps"] == 5
```

- [ ] **Step 2: Run to verify fail**

```bash
cd tools && uv run pytest tests/test_invert_match_seed.py::test_match_one_shot_surrogate_refine_smoke -v
```

Expected: FAIL (`unrecognized arguments: --surrogate-refine-steps` or missing report key).

- [ ] **Step 3: Modify `tools/match/match.py`**

In `build_parser()`, **after** the existing `--refine-steps` (Stage 3) argument, add:

```python
    p.add_argument("--surrogate-refine-steps", type=int, default=0,
                   help="Adam steps on seed unit through SurrogateSynth (0=off; "
                        "requires --seed-model and --surrogate)")
    p.add_argument("--surrogate-refine-lr", type=float, default=1e-2,
                   help="Adam lr for --surrogate-refine-steps (default 1e-2)")
    p.add_argument("--surrogate", type=Path, default=None,
                   help="SurrogateSynth checkpoint for --surrogate-refine-steps")
```

In `main()`, after parsing, validate:

```python
    if args.surrogate_refine_steps > 0:
        if args.seed_model is None:
            parser.error("--surrogate-refine-steps requires --seed-model")
        if args.surrogate is None:
            parser.error("--surrogate-refine-steps requires --surrogate")
```

Replace the seed-model block with refine wiring (keep Stage 3 `refine_steps` untouched):

```python
    seed_units = None
    if args.seed_model is not None:
        from invert.predict import load_checkpoint, predict_wave
        from invert.features_pack import normalize_channels, pack_features
        from invert.surrogate import load_surrogate
        from invert.refine import refine_unit
        import torch

        model, meta = load_checkpoint(args.seed_model, device="cpu")
        top_k = 1 if args.one_shot else 3
        guesses = predict_wave(model, meta, target, top_k=top_k)

        if args.surrogate_refine_steps > 0:
            feat, log_dur = pack_features(target)
            device = torch.device("cpu")
            x = normalize_channels(
                torch.from_numpy(feat).unsqueeze(0).float(),
                mean=meta["channel_mean"],
                std=meta["channel_std"],
            )
            log_duration = torch.tensor([log_dur], dtype=torch.float32)
            surrogate = load_surrogate(args.surrogate, device)
            refined = []
            for g in guesses:
                unit = refine_unit(
                    g["unit"], g["wave_type"], x, log_duration, surrogate,
                    steps=args.surrogate_refine_steps,
                    lr=args.surrogate_refine_lr,
                    device=device,
                )
                refined.append((g["wave_type"], unit))
            seed_units = refined
        else:
            seed_units = [(g["wave_type"], g["unit"]) for g in guesses]
```

Add to **both** report `flags` dicts (one-shot and search):

```python
                "surrogate_refine_steps": args.surrogate_refine_steps,
                "surrogate_refine_lr": args.surrogate_refine_lr,
                "surrogate": str(args.surrogate) if args.surrogate else None,
```

- [ ] **Step 4: Run seed + refine tests**

```bash
cd tools && uv run pytest tests/test_invert_match_seed.py tests/test_invert_refine.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/match/match.py tools/tests/test_invert_match_seed.py
git commit -m "feat(match): --surrogate-refine-steps wires test-time proxy refine"
```

---

### Task 3: `eval_targets` passthrough

**Files:**
- Modify: `tools/invert/eval_targets.py`

- [ ] **Step 1: Add CLI + `run_mode` passthrough**

In `build_parser()`:

```python
    p.add_argument("--surrogate-refine-steps", type=int, default=0)
    p.add_argument("--surrogate-refine-lr", type=float, default=1e-2)
    p.add_argument("--surrogate", type=Path, default=None,
                   help="required when --surrogate-refine-steps > 0")
```

Extend `run_mode` / `eval_one_target` / `main` signatures with:

```python
    surrogate_refine_steps: int = 0,
    surrogate_refine_lr: float = 1e-2,
    surrogate: Path | None = None,
```

In `run_mode` argv building, after structure-objective block:

```python
    if surrogate_refine_steps > 0:
        if surrogate is None:
            raise ValueError("--surrogate-refine-steps requires --surrogate")
        argv += [
            "--surrogate-refine-steps", str(surrogate_refine_steps),
            "--surrogate-refine-lr", str(surrogate_refine_lr),
            "--surrogate", str(surrogate),
        ]
```

Thread the three args from `main` → `eval_one_target` → `run_mode` the same way as `structure_objective`.

- [ ] **Step 2: Smoke import / help**

```bash
cd tools && PYTHONPATH=. uv run python -m invert.eval_targets --help | grep surrogate-refine
```

Expected: shows `--surrogate-refine-steps`.

- [ ] **Step 3: Commit**

```bash
git add tools/invert/eval_targets.py
git commit -m "feat(invert): passthrough surrogate refine flags in eval_targets"
```

---

### Task 4: Hard-slice listen page generator

**Files:**
- Create: `tools/match/listen_refine_compare.py`

- [ ] **Step 1: Implement the page writer**

Create `tools/match/listen_refine_compare.py` (reuse `_safe_stem`, `_read`, `_cell`, `HARD_SLICE` patterns from `listen_compare.py`):

```python
"""Listen page: original vs raw one-shot vs refined one-shot vs seeded.

    PYTHONPATH=. uv run python -m match.listen_refine_compare \\
        --targets targets/ \\
        --raw invert/runs/tt_raw \\
        --refined invert/runs/tt_refined \\
        --seeded invert/runs/tt_seeded \\
        -o invert/runs/tt_refine_listen.html --hard-slice
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE
from .listen_compare import HARD_SLICE, _safe_stem
from .report import _spectrogram_data_uri, _wav_data_uri

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}


def _read(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(mono) * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono
        ).astype(np.float32)
    return mono


def _cell(wave: np.ndarray | None) -> str:
    if wave is None or len(wave) == 0:
        return "<td class='miss'>-</td>"
    return (
        "<td>"
        f"<audio controls preload='none' src='{_wav_data_uri(wave)}'></audio>"
        f"<br><img src='{_spectrogram_data_uri(wave)}' alt=''>"
        "</td>"
    )


def write_page(
    out: Path,
    targets_dir: Path,
    raw_root: Path,
    refined_root: Path,
    seeded_root: Path,
    *,
    only: set[str] | None = None,
) -> None:
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        cells = [
            f"<td class='name'>{target_path.stem}</td>",
            _cell(_read(target_path)),
            _cell(_read(raw_root / safe / "one_shot" / "match.wav")),
            _cell(_read(refined_root / safe / "one_shot" / "match.wav")),
            _cell(_read(seeded_root / safe / "model_seeded" / "match.wav")),
        ]
        rows.append("<tr>" + "".join(cells) + "</tr>")

    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Test-time refine - raw vs refined one-shot</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Test-time refine — raw vs refined one-shot</h1>"
        "<p>Is the <b>refined</b> one-shot acceptably better than <b>raw</b>? "
        "Seeded is the ceiling reference. Scores hidden on purpose.</p>"
        "<table><tr><th>target</th><th>original</th>"
        "<th>raw one-shot</th><th>refined one-shot</th>"
        "<th>model seeded</th></tr>"
        + "".join(rows) +
        "</table>"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.listen_refine_compare")
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--refined", type=Path, required=True)
    p.add_argument("--seeded", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--hard-slice", action="store_true")
    args = p.parse_args(argv)
    write_page(
        args.out, args.targets, args.raw, args.refined, args.seeded,
        only=set(HARD_SLICE) if args.hard_slice else None,
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `eval_targets` writes per-mode dirs `one_shot` / `model_seeded` under each target stem — confirm against `eval_one_target` layout before running; if the layout uses different names, fix paths here to match (do not invent a second layout).

- [ ] **Step 2: Commit**

```bash
git add tools/match/listen_refine_compare.py
git commit -m "feat(match): listen page for raw vs surrogate-refined one-shot"
```

---

### Task 5: Run hard-slice A/B + listen gate (operational)

**Files:**
- Create (after listen): `docs/superpowers/plans/2026-07-25-test-time-refine-results.md`
- Outputs gitignored under `invert/runs/`

**Not TDD** — compute + human listen.

Suggested steps count for the candidate arm: **100** (spec: 50–100). lr default `1e-2`.

- [ ] **Step 1: Locate checkpoints**

```bash
CKPT=../.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt
SUR=../.worktrees/inverse-model-next/tools/invert/runs/surrogate/surrogate.pt
# from tools/; adjust if running from repo root
ls "$CKPT" "$SUR"
```

- [ ] **Step 2: Eval raw one-shot (hard slice only if eval_targets supports filtering; else full 32 and page uses --hard-slice)**

`eval_targets` currently runs all modes per target. For a cheaper gate, either:

**(A)** Loop hard-slice stems with `match.match` directly, or  
**(B)** Run full `eval_targets` once per arm (slower).

Prefer **(A)** for speed — shell loop over `HARD_SLICE` writing into `invert/runs/tt_raw/<stem>/one_shot/` etc. Example for one target:

```bash
cd tools
STEM="chrono_trigger_leeneBell"
PYTHONPATH=. uv run python -m match.match "targets/${STEM}.wav" \
  --seed-model "$CKPT" --one-shot \
  -o "invert/runs/tt_raw/${STEM}/one_shot" --jobs 4
PYTHONPATH=. uv run python -m match.match "targets/${STEM}.wav" \
  --seed-model "$CKPT" --one-shot \
  --surrogate-refine-steps 100 --surrogate "$SUR" \
  -o "invert/runs/tt_refined/${STEM}/one_shot" --jobs 4
PYTHONPATH=. uv run python -m match.match "targets/${STEM}.wav" \
  --seed-model "$CKPT" --budget 2000 \
  -o "invert/runs/tt_seeded/${STEM}/model_seeded" --jobs 4
```

Repeat for every name in `HARD_SLICE` (exact filenames under `targets/` — some have spaces/parens). Use a small Python driver in-repo if the shell quoting hurts; keep it uncommitted or commit as `tools/invert/run_tt_refine_ab.py` only if reused.

- [ ] **Step 3: Build listen page**

```bash
PYTHONPATH=. uv run python -m match.listen_refine_compare \
  --targets targets/ \
  --raw invert/runs/tt_raw \
  --refined invert/runs/tt_refined \
  --seeded invert/runs/tt_seeded \
  -o invert/runs/tt_refine_listen.html --hard-slice
```

Expected: every hard-slice row has audio in all four match columns (no `-`).

- [ ] **Step 4: STOP — hand to user for listen**

Ask: is **refined** acceptably better than **raw** one-shot on structure/timbre, without new mutes? Seeded is ceiling only.

Do **not** claim improvement from surrogate MSE alone.

- [ ] **Step 5: Record verdict**

Write `docs/superpowers/plans/2026-07-25-test-time-refine-results.md` with per-target notes and mean scores if given. If FAIL: leave default steps at 0; point to next-bets (2). If PASS: note candidate default (e.g. 100) but still keep CLI default 0 until product wiring chooses otherwise — or flip default only with explicit user approval.

```bash
git add docs/superpowers/plans/2026-07-25-test-time-refine-results.md
git commit -m "docs: test-time refine listen verdict"
```

---

## Self-review (plan vs spec)

| Spec section | Plan task |
| --- | --- |
| Algorithm (Adam, clamp, hard one-hot, pin) | Task 1 |
| Integration match CLI | Task 2 |
| eval_targets passthrough | Task 3 |
| Tests: loss drop, bounds, pin, steps=0 | Task 1 |
| Listen page + hard slice | Tasks 4–5 |
| No retrain / structure term untouched | All tasks |
| CLI name ≠ Stage 3 `--refine-steps` | Spec + Tasks 2–3 |

**Placeholder scan:** none intentional. Hard-slice file names must match `targets/` exactly (same as Gate B).

**Type consistency:** `refine_unit(unit, wave_type, target_features_norm, log_duration, surrogate, *, steps, lr, device) -> np.ndarray` used identically in Task 1 tests and Task 2 call site.

---

## Out of scope (do not implement in this plan)

- Soft wavetype refine
- Surrogate or inverse retrain
- Multi-hypothesis sampling beyond existing top_k
- Changing `structure_pitch` default
- Declaring product-ready one-shot
