"""Headroom probe: does search, the match objective, or synth reachability cap
the hard slice?

Design: docs/superpowers/specs/2026-07-25-headroom-probe-design.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from invert.presets import harvest_preset_params

from .audio import SAMPLE_RATE
from .bfxr_io import read_bfxr
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
