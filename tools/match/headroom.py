"""Headroom probe: does search, the match objective, or synth reachability cap
the hard slice?

Design: docs/superpowers/specs/2026-07-25-headroom-probe-design.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .bfxr_io import read_bfxr

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
