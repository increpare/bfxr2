import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import SQUARE_ONLY_PARAMS
from match.refine import RefineSettings, free_mask, steepest_descent


def test_free_mask_square_all_range_free():
    space = ParamSpace()
    mask = free_mask(space, wave_type=0)
    assert mask.shape == (space.dim,)
    assert mask.dtype == bool
    assert mask.all()


def test_free_mask_nonsquare_freezes_square_only():
    space = ParamSpace()
    mask = free_mask(space, wave_type=9)  # Bitnoise
    for name in SQUARE_ONLY_PARAMS:
        assert not mask[space.names.index(name)]
    # something clearly free stays free
    assert mask[space.names.index("frequency_start")]


def test_steepest_descent_moves_toward_minimum():
    space = ParamSpace()
    dim = space.dim
    target = np.full(dim, 0.3)
    # freeze nothing for this mock (pretend square)
    mask = np.ones(dim, dtype=bool)
    # start far on two free coords; others already at target
    u0 = target.copy()
    u0[0] = 0.9
    u0[1] = 0.1

    def evaluate(units: list[np.ndarray]) -> np.ndarray:
        arr = np.stack(units, axis=0)
        # quadratic bowl on free dims
        return np.sum((arr - target) ** 2, axis=1)

    u_final, score, hist = steepest_descent(
        u0,
        wave_type=0,
        evaluate=evaluate,
        upper=np.ones(dim),
        mask=mask,
        settings=RefineSettings(max_steps=80, eps=0.02, step0=0.1, patience=80, verbose=False),
    )
    assert score < evaluate([u0])[0]
    assert abs(u_final[0] - 0.3) < 0.15
    assert abs(u_final[1] - 0.3) < 0.15
    assert len(hist) > 0
