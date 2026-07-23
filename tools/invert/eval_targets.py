"""Equal-budget eval table: current vs model-seeded vs one-shot.

    cd tools && uv run python -m invert.eval_targets \\
      --targets /Users/stephenlavelle/Documents/bfxr2/tools/targets/ \\
      --ckpt invert/runs/v1/best.pt \\
      --budget 2000 \\
      -o invert/runs/v1/eval/
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from match.match import main as match_main

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}

# Pass/fail commentary only — not used to gate the run.
DEFAULT_TARGETS = Path("/Users/stephenlavelle/Documents/bfxr2/tools/targets")
HARD_TARGET_NEEDLES = (
    "flame",
    "beam-out",
    "beam_out",
    "jump",
)

MODES = (
    ("current", {"seed_model": False, "one_shot": False}),
    ("model_seeded", {"seed_model": True, "one_shot": False}),
    ("one_shot", {"seed_model": True, "one_shot": True}),
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="invert.eval_targets",
        description="Per-target table: current | model-seeded | one-shot",
    )
    p.add_argument(
        "--targets",
        type=Path,
        default=DEFAULT_TARGETS,
        help=f"target .wav or directory (default: {DEFAULT_TARGETS})",
    )
    p.add_argument("--ckpt", type=Path, required=True,
                   help="invert checkpoint (.pt)")
    p.add_argument("--budget", type=int, default=2000,
                   help="render budget for current and model-seeded (default 2000)")
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--jobs", type=int, default=None)
    p.add_argument("-o", "--out", type=Path, required=True,
                   help="output directory for results.json / results.md")
    return p


def list_targets(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in AUDIO_EXTS:
            raise SystemExit(f"not an audio file: {path}")
        return [path]
    if not path.is_dir():
        raise SystemExit(f"targets path not found: {path}")
    files = sorted(
        f for f in path.iterdir()
        if f.is_file()
        and f.suffix.lower() in AUDIO_EXTS
        and not f.name.startswith(".")
        and not f.name.lower().endswith(".bfxr.wav")
    )
    if not files:
        raise SystemExit(f"no audio files found in {path}")
    return files


def _is_hard_target(stem: str) -> bool:
    s = stem.lower()
    return any(n in s for n in HARD_TARGET_NEEDLES)


def _best_from_report(report: dict[str, Any]) -> dict[str, Any]:
    best = report["results"][0]
    return {
        "score": float(best["score"]),
        "wave_type": int(best["wave_type"]),
        "wave_type_name": str(best["wave_type_name"]),
    }


def run_mode(
    target: Path,
    out_dir: Path,
    *,
    ckpt: Path,
    budget: int,
    rng_seed: int,
    jobs: int | None,
    seed_model: bool,
    one_shot: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [str(target), "-o", str(out_dir), "--rng-seed", str(rng_seed)]
    if jobs is not None:
        argv += ["--jobs", str(jobs)]
    if one_shot:
        argv += ["--seed-model", str(ckpt), "--one-shot"]
    elif seed_model:
        argv += ["--budget", str(budget), "--seed-model", str(ckpt)]
    else:
        argv += ["--budget", str(budget)]

    rc = match_main(argv)
    if rc != 0:
        raise RuntimeError(f"match exited with code {rc}")
    report_path = out_dir / "report.json"
    if not report_path.is_file():
        raise RuntimeError(f"missing report.json in {out_dir}")
    return _best_from_report(json.loads(report_path.read_text()))


def eval_one_target(
    target: Path,
    out_root: Path,
    *,
    ckpt: Path,
    budget: int,
    rng_seed: int,
    jobs: int | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "target": target.name,
        "stem": target.stem,
        "hard": _is_hard_target(target.stem),
        "current": None,
        "model_seeded": None,
        "one_shot": None,
        "error": None,
    }
    try:
        for mode_name, flags in MODES:
            sub = out_root / _safe_stem(target.stem) / mode_name
            print(f"  [{mode_name}] {target.name}", file=sys.stderr)
            try:
                row[mode_name] = run_mode(
                    target,
                    sub,
                    ckpt=ckpt,
                    budget=budget,
                    rng_seed=rng_seed,
                    jobs=jobs,
                    seed_model=flags["seed_model"],
                    one_shot=flags["one_shot"],
                )
            except Exception as exc:  # one mode failure should not kill others
                traceback.print_exc()
                row[mode_name] = {"error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:
        traceback.print_exc()
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def _safe_stem(stem: str) -> str:
    """Filesystem-friendly directory name (spaces ok; strip path separators)."""
    return stem.replace("/", "_").replace("\\", "_")


def _fmt_cell(cell: dict[str, Any] | None) -> str:
    if cell is None:
        return "—"
    if "error" in cell and "score" not in cell:
        return f"ERR: {cell['error']}"
    return f"{cell['score']:.4f} ({cell['wave_type_name']})"


def write_results_md(path: Path, rows: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    lines = [
        "# Invert target eval",
        "",
        f"- checkpoint: `{meta['ckpt']}`",
        f"- budget: {meta['budget']}",
        f"- rng-seed: {meta['rng_seed']}",
        f"- n targets: {len(rows)}",
        "",
        "| target | current | model-seeded | one-shot |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['target']} | {_fmt_cell(row.get('current'))} | "
            f"{_fmt_cell(row.get('model_seeded'))} | {_fmt_cell(row.get('one_shot'))} |"
        )

    hard = [r for r in rows if r.get("hard")]
    lines += [
        "",
        "## Hard-target spotlight",
        "",
        "Commentary targets (flame, beam-out, mario jumps). "
        "Not a code gate — use for pass/fail notes after a real training run.",
        "",
    ]
    if not hard:
        lines.append("_No hard-target names matched in this run._")
    else:
        lines += [
            "| target | current | model-seeded | one-shot | seeded ≤ current? |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in hard:
            cur = row.get("current") or {}
            seeded = row.get("model_seeded") or {}
            if "score" in cur and "score" in seeded:
                wins = "yes" if seeded["score"] <= cur["score"] else "no"
            else:
                wins = "—"
            lines.append(
                f"| {row['target']} | {_fmt_cell(row.get('current'))} | "
                f"{_fmt_cell(row.get('model_seeded'))} | {_fmt_cell(row.get('one_shot'))} | "
                f"{wins} |"
            )
    path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.ckpt.is_file():
        print(f"checkpoint not found: {args.ckpt}", file=sys.stderr)
        return 1

    targets = list_targets(args.targets)
    args.out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for i, target in enumerate(targets, start=1):
        print(f"\n=== [{i}/{len(targets)}] {target.name} ===", file=sys.stderr)
        try:
            row = eval_one_target(
                target,
                args.out,
                ckpt=args.ckpt,
                budget=args.budget,
                rng_seed=args.rng_seed,
                jobs=args.jobs,
            )
        except Exception as exc:
            traceback.print_exc()
            row = {
                "target": target.name,
                "stem": target.stem,
                "hard": _is_hard_target(target.stem),
                "current": None,
                "model_seeded": None,
                "one_shot": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        rows.append(row)

    meta = {
        "ckpt": str(args.ckpt.resolve()),
        "targets": str(args.targets.resolve()),
        "budget": args.budget,
        "rng_seed": args.rng_seed,
        "jobs": args.jobs,
    }
    payload = {**meta, "results": rows}
    (args.out / "results.json").write_text(json.dumps(payload, indent=2))
    write_results_md(args.out / "results.md", rows, meta)

    print("\n=== Hard-target spotlight ===", file=sys.stderr)
    hard = [r for r in rows if r.get("hard")]
    if not hard:
        print("(none matched)", file=sys.stderr)
    for row in hard:
        print(
            f"  {row['target']}: "
            f"current={_fmt_cell(row.get('current'))} | "
            f"seeded={_fmt_cell(row.get('model_seeded'))} | "
            f"one-shot={_fmt_cell(row.get('one_shot'))}",
            file=sys.stderr,
        )
    print(f"\nwrote {args.out / 'results.json'} and {args.out / 'results.md'}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
