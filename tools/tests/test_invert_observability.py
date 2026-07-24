from invert.observability import sensitivity_to_weights


def test_sensitivity_to_weights_normalizes_and_floors():
    names = ["a", "b", "c", "d"]
    # b is dead (0), a is very sensitive, c/d moderate
    sens = {"a": 10.0, "b": 0.0, "c": 2.0, "d": 3.0}
    w = sensitivity_to_weights(sens, names, floor=0.1)
    assert len(w) == 4
    # dead param floored, not zero
    assert w[1] == 0.1
    # sensitive param capped at 4.0
    assert w[0] == 4.0
    # weights are finite and positive
    assert all(0.0 < x <= 4.0 for x in w)
    # mean over non-floored params is ~1.0 before clamping bites; c and d straddle 1
    assert w[2] < w[3]


from match.bfxr_io import ParamSpace
from match.renderer import BfxrRenderer
from invert.observability import param_sensitivity


def test_param_sensitivity_ranks_audible_above_dead():
    space = ParamSpace()
    with BfxrRenderer(jobs=1) as renderer:
        sens = param_sensitivity(space, renderer, n_probes=12, seed=1)
    assert set(sens) == set(space.names)
    # frequency_start audibly changes the sound; flangerSweep barely does.
    assert sens["frequency_start"] > sens["flangerSweep"]
