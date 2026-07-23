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
    p.add_argument("--refine-steps", type=int, default=0,
                   help="Stage 3 FD steepest-descent steps (0=off)")
    p.add_argument("--jobs", type=int, default=None,
                   help=f"render worker processes (default {default_jobs()})")
    p.add_argument("--html-report", action="store_true",
                   help="write report.html (requires: uv sync --extra report)")
    p.add_argument("--seed-model", type=Path, default=None,
                   help="invert checkpoint to replace stage-0 random screen")
    p.add_argument("--one-shot", action="store_true",
                   help="emit raw model top prediction only (requires --seed-model)")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.one_shot and args.seed_model is None:
        parser.error("--one-shot requires --seed-model")
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

    seed_units = None
    if args.seed_model is not None:
        from invert.predict import load_checkpoint, predict_wave

        model, meta = load_checkpoint(args.seed_model, device="cpu")
        top_k = 1 if args.one_shot else 3
        guesses = predict_wave(model, meta, target, top_k=top_k)
        seed_units = [(g["wave_type"], g["unit"]) for g in guesses]

    if args.one_shot:
        assert seed_units is not None and len(seed_units) >= 1
        wt, unit = seed_units[0]
        t0 = time.perf_counter()
        with BfxrRenderer(jobs=args.jobs) as renderer:
            # params_for needs envelope projection; reuse optimizer helper
            opt = StagedOptimizer(
                space, renderer, objective,
                OptimizeSettings(budget=1, verbose=False),
                target=target,
            )
            params = opt.params_for(unit, wt)
            import soundfile as sf
            wave = renderer.render(params, seed=RENDER_SEED)
            score = float(objective.score_batch([wave])[0])
            write_bfxr(args.out / "match.bfxr", params,
                       file_name=f"{args.target.stem}_match")
            sf.write(args.out / "match.wav", wave, SAMPLE_RATE, subtype="PCM_16")
            matches = [{
                "name": f"match ({space.wave_type_names[wt]})",
                "wave": wave,
                "score": score,
                "params": params,
            }]
        elapsed = time.perf_counter() - t0
        report = {
            "target": str(args.target),
            "target_seconds": len(target) / SAMPLE_RATE,
            "flags": {
                "allow_pitch_shift": args.allow_pitch_shift,
                "allow_time_stretch": args.allow_time_stretch,
                "avg_seeds": args.avg_seeds,
                "one_shot": True,
                "seed_model": str(args.seed_model),
            },
            "budget": 0,
            "evals": 0,
            "elapsed_seconds": round(elapsed, 1),
            "freq_seeds": [],
            "results": [{
                "file": "match.bfxr",
                "score": score,
                "wave_type": wt,
                "wave_type_name": space.wave_type_names[wt],
            }],
            "trace": [],
        }
        (args.out / "report.json").write_text(json.dumps(report, indent=1))
        if args.html_report:
            from .report import write_html_report
            write_html_report(args.out / "report.html", args.target.name, target, matches)
        print(f"one-shot score {score:.4f} ({space.wave_type_names[wt]}) "
              f"in {elapsed:.0f}s, outputs in {args.out}/", file=sys.stderr)
        return 0

    settings = OptimizeSettings(
        budget=args.budget,
        time_budget=args.time_budget,
        popsize=args.popsize,
        avg_seeds=args.avg_seeds,
        rng_seed=args.rng_seed,
        wave_types=[int(w) for w in args.wavetypes.split(",")] if args.wavetypes else None,
        top_k=args.top_k,
        refine_steps=args.refine_steps,
        seed_units=seed_units,
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
            "seed_model": str(args.seed_model) if args.seed_model else None,
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
