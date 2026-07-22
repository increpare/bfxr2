"""Run the matcher over every audio file in a directory and build one
combined index page.

    cd tools && uv run python -m match.batch targets/ -o batch_out/ --html-report
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .match import main as match_main

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="batch", description="Match every audio file in a directory.")
    parser.add_argument("target", type=Path, help="directory of audio files")
    parser.add_argument("-o", "--out", type=Path, default=Path("batch_out"))
    parser.add_argument("--allow-pitch-shift", action="store_true")
    parser.add_argument("--allow-time-stretch", action="store_true")
    parser.add_argument("--budget", type=int, default=5000)
    parser.add_argument("--time-budget", type=float, default=None)
    parser.add_argument("--popsize", type=int, default=28)
    parser.add_argument("--avg-seeds", type=int, default=1)
    parser.add_argument("--rng-seed", type=int, default=0)
    parser.add_argument("--wavetypes", type=str, default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--jobs", type=int, default=None)
    parser.add_argument("--html-report", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="skip targets whose outputs already exist")
    args = parser.parse_args(argv)

    files = sorted(
        f for f in args.target.iterdir()
        if f.suffix.lower() in AUDIO_EXTS and not f.name.startswith(".")
    )
    if not files:
        print(f"no audio files found in {args.target}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in files:
        sub = args.out / f.stem
        done = (sub / "report.json").exists() and f.with_suffix(".bfxr.wav").exists()
        if args.resume and done:
            print(f"\n=== {f.name} === (already done, skipping)", file=sys.stderr)
            rows.append((f.stem, json.loads((sub / "report.json").read_text())))
            continue
        print(f"\n=== {f.name} ===", file=sys.stderr)
        forwarded = [str(f), "-o", str(sub)]
        for flag in ("--allow-pitch-shift", "--allow-time-stretch", "--html-report"):
            if getattr(args, flag.lstrip("-").replace("-", "_")):
                forwarded.append(flag)
        forwarded += ["--budget", str(args.budget), "--top-k", str(args.top_k),
                      "--rng-seed", str(args.rng_seed),
                      "--avg-seeds", str(args.avg_seeds),
                      "--popsize", str(args.popsize)]
        if args.time_budget is not None:
            forwarded += ["--time-budget", str(args.time_budget)]
        if args.jobs is not None:
            forwarded += ["--jobs", str(args.jobs)]
        if args.wavetypes:
            forwarded += ["--wavetypes", args.wavetypes]
        try:
            match_main(forwarded)
        except Exception:  # one bad target must not kill the batch
            import traceback
            traceback.print_exc()
            continue
        report = json.loads((sub / "report.json").read_text())
        rows.append((f.stem, report))
        # best match beside the original: X.wav -> X.bfxr + X.bfxr.wav
        shutil.copyfile(sub / "match.bfxr", f.with_suffix(".bfxr"))
        shutil.copyfile(sub / "match.wav", f.with_suffix(".bfxr.wav"))

    lines = ["<!DOCTYPE html><html><head><meta charset='utf-8'>",
             "<title>bfxr batch match</title>",
             "<style>body{font-family:system-ui;margin:2em;background:#1b1b1f;color:#e8e8ea}",
             "table{border-collapse:collapse}td,th{padding:.5em 1em;border-bottom:1px solid #333;text-align:left}",
             "a{color:#7cb8ff}</style></head><body><h1>bfxr batch match</h1><table>",
             "<tr><th>target</th><th>best score</th><th>wave type</th><th>report</th></tr>"]
    for stem, report in rows:
        best = report["results"][0]
        link = (f"<a href='{stem}/report.html'>report</a>"
                if (args.out / stem / "report.html").exists() else "")
        lines.append(f"<tr><td>{stem}</td><td>{best['score']:.3f}</td>"
                     f"<td>{best['wave_type_name']}</td><td>{link}</td></tr>")
    lines.append("</table></body></html>")
    index = args.out / "index.html"
    index.write_text("\n".join(lines))
    print(f"\nwrote {index}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
