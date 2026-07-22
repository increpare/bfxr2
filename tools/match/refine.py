from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE, prepare_target
from .bfxr_io import ParamSpace, read_bfxr, write_bfxr
from .objective import MatchObjective
from .optimizer import RENDER_SEED, SQUARE_ONLY_PARAMS, OptimizeSettings, StagedOptimizer
from .renderer import BfxrRenderer
from .report import _spectrogram_data_uri, _wav_data_uri


@dataclass
class RefineSettings:
    max_steps: int = 200
    eps: float = 0.015
    step0: float = 0.05
    backtrack: int = 6
    patience: int = 20  # early-stop after this many non-improving steps
    verbose: bool = True


def free_mask(space: ParamSpace, wave_type: int) -> np.ndarray:
    """True = optimize; False = freeze. waveType is outside the cube."""
    mask = np.ones(space.dim, dtype=bool)
    if int(wave_type) != 0:
        for name in SQUARE_ONLY_PARAMS:
            mask[space.names.index(name)] = False
    return mask


def steepest_descent(
    unit0: np.ndarray,
    wave_type: int,
    evaluate: Callable[[list[np.ndarray]], np.ndarray],
    upper: np.ndarray,
    mask: np.ndarray | None = None,
    settings: RefineSettings | None = None,
) -> tuple[np.ndarray, float, list[tuple[int, float]]]:
    """Coordinate steepest descent on free dims.

    Each step scores ±eps along every free axis and takes the single best
    improving move. (Combined FD gradients are useless on Bfxr's discontinuous
    score landscape — probes jump cliffs.) evaluate(units) -> scores, lower better.
    """
    s = settings or RefineSettings()
    u = np.clip(np.asarray(unit0, dtype=float).copy(), 0.0, upper)
    if mask is None:
        mask = np.ones(u.shape[0], dtype=bool)
    free = np.flatnonzero(mask)
    history: list[tuple[int, float]] = []

    def score_one(x: np.ndarray) -> float:
        return float(evaluate([x])[0])

    f = score_one(u)
    history.append((0, f))
    stall = 0
    # step0/backtrack kept on RefineSettings for API stability; eps is the move size.
    _ = (s.step0, s.backtrack, wave_type)

    for t in range(1, s.max_steps + 1):
        probes: list[np.ndarray] = []
        for i in free:
            up = u.copy()
            dn = u.copy()
            up[i] = min(float(upper[i]), u[i] + s.eps)
            dn[i] = max(0.0, u[i] - s.eps)
            if up[i] != u[i]:
                probes.append(up)
            if dn[i] != u[i]:
                probes.append(dn)
        if not probes:
            break
        scores = np.asarray(evaluate(probes), dtype=np.float64)
        k = int(np.argmin(scores))
        improved = bool(scores[k] < f)
        if improved:
            u = probes[k]
            f = float(scores[k])
            stall = 0
        else:
            stall += 1
        history.append((t, f))
        if s.verbose and (t % 20 == 0 or (improved and t <= 5)):
            print(f"  refine step {t}: score={f:.4f}", file=sys.stderr)
        if stall >= s.patience:
            break
    return u, f, history


def make_evaluate(optimizer: StagedOptimizer, wave_type: int):
    """Score each unit alone.

    MatchObjective pads a batch to max length in the batch, so joint
    scoring makes finite-difference probes contaminate each other.
    """
    def evaluate(units: list[np.ndarray]) -> np.ndarray:
        return np.array(
            [float(optimizer._evaluate([u], [wave_type])[0]) for u in units],
            dtype=np.float64,
        )

    return evaluate


def write_compare_html(
    path: Path,
    stem: str,
    target: np.ndarray,
    before: np.ndarray,
    after: np.ndarray,
    score_before: float,
    score_after: float,
) -> None:
    def card(title: str, wave: np.ndarray, meta: str) -> str:
        return f"""
<section class="card">
  <h2>{title}</h2>
  <div class="meta">{meta}</div>
  <audio controls src="{_wav_data_uri(wave)}"></audio>
  <img src="{_spectrogram_data_uri(wave)}" alt="">
</section>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{stem} refine</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: "IBM Plex Sans", system-ui, sans-serif; margin: 0;
        background: #12141a; color: #e6e8ef; }}
header {{ padding: 1.5rem 2rem; border-bottom: 1px solid #2a2e3a; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
         gap: 1rem; padding: 1.5rem 2rem 3rem; }}
.card {{ background: #1a1d27; border: 1px solid #2a2e3a; border-radius: 6px;
         padding: 1rem; display: flex; flex-direction: column; gap: .7rem; }}
.card img {{ width: 100%; }}
audio {{ width: 100%; }}
.meta {{ color: #9aa3b5; font-size: .85rem; }}
</style></head><body>
<header><h1>{stem} — local refine</h1>
<p>score {score_before:.4f} → {score_after:.4f}</p></header>
<div class="grid">
{card("Target", target, stem)}
{card("Before", before, f"score {score_before:.4f}")}
{card("After", after, f"score {score_after:.4f}")}
</div></body></html>"""
    path.write_text(html)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.refine")
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--seed", type=Path, required=True, help="starting .bfxr")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--eps", type=float, default=0.015)
    p.add_argument("--step0", type=float, default=0.05)
    p.add_argument("--jobs", type=int, default=None)
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    target = prepare_target(args.target)
    params0 = read_bfxr(args.seed)
    space = ParamSpace()
    u0, wave_type = space.unit_from_params(params0)
    objective = MatchObjective(target)
    settings = RefineSettings(max_steps=args.steps, eps=args.eps, step0=args.step0)

    with BfxrRenderer(jobs=args.jobs) as renderer:
        opt = StagedOptimizer(
            space,
            renderer,
            objective,
            OptimizeSettings(budget=10**9, verbose=False),
            target=target,
        )
        mask = free_mask(space, wave_type)
        if wave_type != 0:
            for name in SQUARE_ONLY_PARAMS:
                i = space.names.index(name)
                u0[i] = float(space.defaults_unit()[i])
        evaluate = make_evaluate(opt, wave_type)
        score0 = float(evaluate([u0])[0])
        before = renderer.render(opt.params_for(u0, wave_type), seed=RENDER_SEED)
        u1, score1, hist = steepest_descent(
            u0,
            wave_type,
            evaluate,
            opt.upper,
            mask=mask,
            settings=settings,
        )
        params1 = opt.params_for(u1, wave_type)
        after = renderer.render(params1, seed=RENDER_SEED)

    sf.write(args.out / "before.wav", before, SAMPLE_RATE, subtype="PCM_16")
    sf.write(args.out / "refined.wav", after, SAMPLE_RATE, subtype="PCM_16")
    sf.write(args.out / "target.wav", target, SAMPLE_RATE, subtype="PCM_16")
    write_bfxr(
        args.out / "refined.bfxr",
        params1,
        file_name=f"{args.target.stem}_refined",
    )
    write_compare_html(
        args.out / "compare.html",
        args.target.stem,
        target,
        before,
        after,
        score0,
        score1,
    )
    (args.out / "refine.json").write_text(
        json.dumps(
            {
                "target": str(args.target),
                "seed": str(args.seed),
                "wave_type": wave_type,
                "score_before": score0,
                "score_after": score1,
                "steps": len(hist) - 1,
                "history": hist,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"score {score0:.4f} → {score1:.4f}; wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
