"""Headroom probe: does search, the match objective, or synth reachability cap
the hard slice?

Design: docs/superpowers/specs/2026-07-25-headroom-probe-design.md
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from invert.presets import harvest_preset_params

from .audio import SAMPLE_RATE, prepare_target
from .bfxr_io import read_bfxr
from .listen_compare import HARD_SLICE, write_arms_page
from .match import main as match_main
from .objective import MatchObjective
from .renderer import BfxrRenderer

# Never used during search. The search always renders with RENDER_SEED (1234),
# so scoring a winner here detects a candidate that merely overfit that seed's
# noise -- a real risk at 200k evals with avg_seeds=1.
HELDOUT_RENDER_SEED = 8765


def rescore_heldout(
    bfxr_path: Path,
    objective: Any,
    renderer: Any,
    seed: int = HELDOUT_RENDER_SEED,
) -> float:
    """Re-render a saved winner on an unseen render seed and score it."""
    params = read_bfxr(bfxr_path)
    waves = renderer.render_batch([params], seeds=seed)
    return float(objective.score_batch(waves)[0])


def make_preset_targets(
    out_dir: Path,
    n: int = 10,
    seed: int = 4242,
    renderer: Any | None = None,
) -> list[Path]:
    """Render N bfxr presets to wavs: the known-reachable control set.

    These are targets the synth provably can hit, so their converged objective
    floor is the reference the real-SFX floor is measured against.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    params_list = harvest_preset_params(n, seed)
    if renderer is None:
        with BfxrRenderer() as owned:
            waves = owned.render_batch(params_list, seeds=HELDOUT_RENDER_SEED)
    else:
        waves = renderer.render_batch(params_list, seeds=HELDOUT_RENDER_SEED)

    # Validate that we have a healthy control set.
    # Check for None waves (renderer failures).
    for i, wave in enumerate(waves):
        if wave is None:
            raise RuntimeError(
                f"Renderer returned None for preset {i}: control set is invalid"
            )

    # Check for all-silent waves (degenerate: no content).
    all_silent = all(np.max(np.abs(wave)) < 1e-6 for wave in waves)
    if all_silent:
        raise RuntimeError(
            f"All {n} rendered preset waves are silent (max amplitude < 1e-6): "
            "control set is degenerate"
        )

    # Check for too few distinct waves (degenerate: no diversity).
    if n >= 2:
        # Convert waves to a tuple representation for uniqueness checking.
        unique_waves = set()
        for wave in waves:
            unique_waves.add(tuple(wave.astype(np.float32)))
        if len(unique_waves) < 2:
            raise RuntimeError(
                f"Only {len(unique_waves)} distinct wave(s) from {n} presets: "
                "control set is degenerate (all waves identical)"
            )

    paths = []
    for i, wave in enumerate(waves):
        path = out_dir / f"preset_{i:02d}.wav"
        sf.write(path, wave, SAMPLE_RATE)
        paths.append(path)
    return paths


ARMS: dict[str, dict[str, Any]] = {
    "baseline_seeded":   {"budget": 2000,   "seed_model": True,  "restarts": False},
    "big_seeded":        {"budget": 200000, "seed_model": True,  "restarts": True},
    "baseline_unseeded": {"budget": 2000,   "seed_model": False, "restarts": False},
    "big_unseeded":      {"budget": 200000, "seed_model": False, "restarts": True},
}

# Written by match.py as the best result; see match.main's report "results".
BEST_FILE = "match.bfxr"


def heldout_for_run(target: Path, bfxr_path: Path, jobs: int | None) -> float:
    """Score a saved winner on the held-out render seed.

    Kept separate from run_arm so unit tests can stub it out; building the
    objective and renderer inline would spawn Node workers in every test.
    """
    objective = MatchObjective(prepare_target(target))
    with BfxrRenderer(jobs=jobs) as renderer:
        return rescore_heldout(bfxr_path, objective, renderer)


def run_arm(
    target: Path,
    out_dir: Path,
    arm: str,
    *,
    ckpt: Path,
    jobs: int | None,
    rng_seed: int,
) -> dict[str, Any]:
    """Run one arm on one target, then re-score its winner on a held-out seed."""
    cfg = ARMS[arm]
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        str(target), "-o", str(out_dir),
        "--budget", str(cfg["budget"]),
        "--rng-seed", str(rng_seed),
    ]
    if jobs is not None:
        argv += ["--jobs", str(jobs)]
    if cfg["seed_model"]:
        argv += ["--seed-model", str(ckpt)]
    if cfg["restarts"]:
        argv += ["--restarts"]

    rc = match_main(argv)
    if rc != 0:
        raise RuntimeError(f"match exited with code {rc} for {arm}/{target.name}")
    report = json.loads((out_dir / "report.json").read_text())
    best = report["results"][0]

    heldout = heldout_for_run(target, out_dir / BEST_FILE, jobs)

    return {
        "arm": arm,
        "score": float(best["score"]),
        "heldout_score": heldout,
        "wave_type_name": str(best["wave_type_name"]),
        "evals": int(report["evals"]),
        "elapsed_seconds": float(report["elapsed_seconds"]),
        "trace": report.get("trace", []),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="match.headroom",
        description="Four-arm headroom probe over the hard slice plus an "
                    "in-domain preset control.",
    )
    p.add_argument("--targets", type=Path, required=True,
                   help="directory of real target wavs (hard slice is selected "
                        "from it by name)")
    p.add_argument("--ckpt", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=None)
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--arms", nargs="+", default=list(ARMS),
                   choices=list(ARMS))
    p.add_argument("--presets", type=int, default=10,
                   help="in-domain control targets (0 disables)")
    p.add_argument("--preset-arms", nargs="+",
                   default=["baseline_seeded", "big_seeded"],
                   choices=list(ARMS))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    work: list[tuple[str, Path, list[str]]] = []
    real = [p for p in sorted(args.targets.iterdir())
            if p.stem in set(HARD_SLICE)]
    if len(real) != len(HARD_SLICE):
        found = {p.stem for p in real}
        missing = sorted(set(HARD_SLICE) - found)
        print(f"warning: missing hard-slice targets: {missing}", file=sys.stderr)
    for path in real:
        work.append(("real", path, args.arms))

    if args.presets > 0:
        preset_paths = make_preset_targets(args.out / "preset_targets",
                                           n=args.presets)
        for path in preset_paths:
            work.append(("in_domain", path, args.preset_arms))

    rows: list[dict[str, Any]] = []
    for kind, path, arms in work:
        for arm in arms:
            print(f"[{kind}] {path.stem} :: {arm}", file=sys.stderr)
            out_dir = args.out / arm / _safe_dir(path.stem) / "model_seeded"
            try:
                row = run_arm(path, out_dir, arm, ckpt=args.ckpt,
                              jobs=args.jobs, rng_seed=args.rng_seed)
            except Exception as exc:  # one arm must not kill the overnight run
                traceback.print_exc()
                row = {"arm": arm, "error": f"{type(exc).__name__}: {exc}"}
            row["kind"] = kind
            row["target"] = path.stem
            rows.append(row)
            # written after every arm so an interrupted run is still readable
            (args.out / "results.json").write_text(json.dumps(
                {"ckpt": str(args.ckpt), "rng_seed": args.rng_seed,
                 "heldout_seed": HELDOUT_RENDER_SEED, "rows": rows},
                indent=2,
            ))

    listen_arms = [(a, args.out / a) for a in args.arms if a != "baseline_unseeded"]
    write_arms_page(
        args.out / "headroom.html",
        args.out / "headroom_key.json",
        args.targets,
        listen_arms,
        only=set(HARD_SLICE),
    )
    print(f"wrote {args.out}/results.json and headroom.html", file=sys.stderr)
    return 0


def _safe_dir(stem: str) -> str:
    """Must match invert.eval_targets._safe_stem: keep spaces and parens."""
    return stem.replace("/", "_").replace("\\", "_")


if __name__ == "__main__":
    raise SystemExit(main())
