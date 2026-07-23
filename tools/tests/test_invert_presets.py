from invert.presets import harvest_preset_params
from invert.sampler import finalize_example
from match.bfxr_io import ParamSpace


def test_harvest_is_deterministic_and_convertible():
    rows_a = harvest_preset_params(16, seed=5)
    rows_b = harvest_preset_params(16, seed=5)
    assert len(rows_a) == 16
    assert rows_a == rows_b
    space = ParamSpace()
    for row in rows_a:
        unit, wt = space.unit_from_params(row["params"])
        ex = finalize_example(space, unit, wt)
        assert ex["wave_type"] == wt
        assert 0.0 <= ex["unit"].min() and ex["unit"].max() <= 1.0
