"""Round-trip: render known bfxr params, use as target, and check the
optimizer gets back to a perceptually close sound.

Necessary but not sufficient — these targets are all perfectly reachable, so
the test proves the optimizer + metric work, not that real-world sounds match
well. Parameter recovery is deliberately not asserted (the parametrization is
redundant: different params can produce near-identical audio).
"""
from pathlib import Path

import pytest

from match.bfxr_io import ParamSpace, read_bfxr
from match.objective import MatchObjective
from match.optimizer import RENDER_SEED, OptimizeSettings, StagedOptimizer
from match.renderer import BfxrRenderer

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.bfxr"))

# Calibrated on 2026-07-22 against the contour-feature metric (budget 1600,
# rng_seed 0 — runs are deterministic): observed best scores up to 3.06
# (sine_powerup; sliding pitch remains the hardest case, and it lands on
# Triangle rather than Sin — a close timbral cousin). Wrong-genre sounds
# score ~5+, silence far higher. The threshold catches regressions (metric
# broken, optimizer stuck); it is not a quality bar.
SCORE_THRESHOLD = 3.5
BUDGET = 1600


@pytest.fixture(scope="module")
def renderer():
    with BfxrRenderer() as r:
        yield r


@pytest.mark.slow
@pytest.mark.parametrize("fixture", FIXTURES, ids=[f.stem for f in FIXTURES])
def test_roundtrip(renderer, fixture):
    space = ParamSpace()
    truth = read_bfxr(fixture)
    target = renderer.render(truth, seed=RENDER_SEED)
    assert target is not None

    objective = MatchObjective(target)
    settings = OptimizeSettings(budget=BUDGET, screen_size=32,
                                stage1_iters=10, verbose=False)
    optimizer = StagedOptimizer(space, renderer, objective, settings, target=target)
    results = optimizer.run()

    best = results[0]
    assert best.score < SCORE_THRESHOLD, (
        f"{fixture.stem}: best score {best.score:.3f} "
        f"(waveType {best.wave_type}, truth {truth['waveType']})"
    )

    # serialization guard: emitted params re-render to the same score
    params = optimizer.params_for(best.unit, best.wave_type)
    rerendered = renderer.render(params, seed=RENDER_SEED)
    assert abs(objective.score(rerendered) - best.score) < 0.05
