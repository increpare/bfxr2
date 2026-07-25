"""Length / energy ratio histogram over an eval_targets run.

Spec Priority 0 asks whether candidates collapse to a fraction of the target's
duration while still scoring acceptably. This reads each mode's best render
(`<eval_root>/<stem>/<mode>/match.wav`) against its target and reports the
ratio of trimmed durations and of total energy.

    PYTHONPATH=. uv run python -m match.length_report \\
        --eval-root invert/runs/v7_real_ft/eval_new --targets targets/ \\
        --mode one_shot
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE, trim_silence

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}
COLLAPSE_RATIO = 0.5  # spec: flag candidates under 0.5x the target duration


def _safe_stem(stem: str) -> str:
    """Filesystem-friendly directory name.

    Must match invert.eval_targets._safe_stem exactly: that's the function
    that actually creates the per-target output directory an eval run
    writes to. Real target stems include spaces and parentheses (e.g.
    "Mario 3 - jump (nes)"), so this only strips path separators, matching
    eval_targets rather than mangling every non-alnum character.
    """
    return stem.replace("/", "_").replace("\\", "_")


def _read(path: Path) -> np.ndarray:
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(mono) * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono
        ).astype(np.float32)
    return mono


def length_ratios(
    eval_root: Path, targets_dir: Path, mode: str
) -> list[tuple[str, float, float]]:
    rows: list[tuple[str, float, float]] = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        cand_path = eval_root / _safe_stem(target_path.stem) / mode / "match.wav"
        if not cand_path.is_file():
            continue
        target = trim_silence(_read(target_path))
        cand = trim_silence(_read(cand_path))
        if len(target) == 0:
            continue
        dur = len(cand) / len(target)
        t_energy = float(np.sum(target.astype(np.float64) ** 2))
        c_energy = float(np.sum(cand.astype(np.float64) ** 2))
        energy = c_energy / t_energy if t_energy > 0 else 0.0
        rows.append((target_path.stem, dur, energy))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.length_report")
    p.add_argument("--eval-root", type=Path, required=True)
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--mode", default="one_shot",
                   choices=("current", "model_seeded", "one_shot"))
    args = p.parse_args(argv)

    rows = length_ratios(args.eval_root, args.targets, args.mode)
    if not rows:
        print("no matched renders found")
        return 1

    print(f"{'target':40s} {'dur x':>8s} {'energy x':>9s}")
    for stem, dur, energy in sorted(rows, key=lambda r: r[1]):
        flag = "  <-- COLLAPSE" if dur < COLLAPSE_RATIO else ""
        print(f"{stem:40s} {dur:8.2f} {energy:9.2f}{flag}")

    durations = np.array([r[1] for r in rows])
    edges = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, np.inf]
    print("\nduration-ratio histogram:")
    for lo, hi in zip(edges[:-1], edges[1:]):
        n = int(((durations >= lo) & (durations < hi)).sum())
        print(f"  [{lo:4.2f}, {hi:4.2f})  {'#' * n} {n}")

    n_collapse = int((durations < COLLAPSE_RATIO).sum())
    print(f"\ncollapsed (<{COLLAPSE_RATIO}x): {n_collapse}/{len(rows)} "
          f"= {n_collapse / len(rows):.0%}   median {np.median(durations):.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
