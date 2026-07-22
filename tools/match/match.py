"""wav -> bfxr matcher CLI.

    cd tools && uv run python -m match.match target.wav -o out/

Emits app-loadable .bfxr files, rendered wavs, report.json, and (with
--html-report) a listening/comparison page.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .audio import SAMPLE_RATE, prepare_target
from .bfxr_io import ParamSpace, write_bfxr
from .objective import MatchObjective
from .optimizer import RENDER_SEED, OptimizeSettings, StagedOptimizer
from .renderer import BfxrRenderer, default_jobs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="match", description="Approximate a wav with a bfxr sound.")
    p.add_argument("target", type=Path, help="target audio file (wav/flac/ogg/...)")
    p.add_argument("-o", "--out", type=Path, default=Path("out"),
                   help="output directory (default: out/)")
    p.add_argument("--allow-pitch-shift", action="store_true",
                   help="tolerate global pitch shifts of the candidate")
    p.add_argument("--allow-time-stretch", action="store_true",
                   help="tolerate uniform time stretch of the candidate")
    p.add_argument("--budget", type=int, default=5000,
                   help="total render evaluations (default 5000)")
    p.add_argument("--time-budget", type=float, default=None,
                   help="wall-clock cap in seconds")
    p.add_argument("--popsize", type=int, default=28)
    p.add_argument("--avg-seeds", type=int, default=1,
                   help="average score over K render seeds (use ~3 for noisy targets)")
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--wavetypes", type=str, default=None,
                   help="comma-separated internal wave type ids to search (default all)")
    p.add_argument("--top-k", type=int, default=3,
                   help="emit best result for the K best distinct wave types")
    p.add_argument("--jobs", type=int, default=None,
                   help=f"render worker processes (default {default_jobs()})")
    p.add_argument("--html-report", action="store_true",
                   help="write report.html (requires: uv sync --extra report)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    target = prepare_target(args.target)
    print(f"target: {args.target.name}, {len(target)/SAMPLE_RATE:.2f}s after trim",
          file=sys.stderr)

    space = ParamSpace()
    objective = MatchObjective(
        target,
        allow_pitch_shift=args.allow_pitch_shift,
        allow_time_stretch=args.allow_time_stretch,
    )
    settings = OptimizeSettings(
        budget=args.budget,
        time_budget=args.time_budget,
        popsize=args.popsize,
        avg_seeds=args.avg_seeds,
        rng_seed=args.rng_seed,
        wave_types=[int(w) for w in args.wavetypes.split(",")] if args.wavetypes else None,
        top_k=args.top_k,
    )

    t0 = time.perf_counter()
    with BfxrRenderer(jobs=args.jobs) as renderer:
        optimizer = StagedOptimizer(space, renderer, objective, settings, target=target)
        results = optimizer.run()

        import soundfile as sf
        matches = []
        for rank, cand in enumerate(results, start=1):
            stem = "match" if rank == 1 else f"match_{rank}"
            params = optimizer.params_for(cand.unit, cand.wave_type)
            wave = renderer.render(params, seed=RENDER_SEED)
            write_bfxr(args.out / f"{stem}.bfxr", params,
                       file_name=f"{args.target.stem}_{stem}")
            sf.write(args.out / f"{stem}.wav", wave, SAMPLE_RATE, subtype="PCM_16")
            matches.append({
                "name": f"{stem} ({space.wave_type_names[cand.wave_type]})",
                "wave": wave,
                "score": cand.score,
                "params": params,
            })

    elapsed = time.perf_counter() - t0
    report = {
        "target": str(args.target),
        "target_seconds": len(target) / SAMPLE_RATE,
        "flags": {
            "allow_pitch_shift": args.allow_pitch_shift,
            "allow_time_stretch": args.allow_time_stretch,
            "avg_seeds": args.avg_seeds,
        },
        "budget": args.budget,
        "evals": optimizer.evals,
        "elapsed_seconds": round(elapsed, 1),
        "freq_seeds": [round(f, 4) for f in optimizer.freq_seeds],
        "results": [
            {
                "file": ("match" if i == 1 else f"match_{i}") + ".bfxr",
                "score": r.score,
                "wave_type": r.wave_type,
                "wave_type_name": space.wave_type_names[r.wave_type],
            }
            for i, r in enumerate(results, start=1)
        ],
        "trace": optimizer.trace[:: max(1, len(optimizer.trace) // 100)],
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=1))

    if args.html_report:
        from .report import write_html_report
        write_html_report(args.out / "report.html", args.target.name, target, matches)

    print(f"best score {results[0].score:.4f} "
          f"({space.wave_type_names[results[0].wave_type]}) "
          f"in {elapsed:.0f}s, outputs in {args.out}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
