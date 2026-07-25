from invert.presets import harvest_preset_params
from invert.sampler import finalize_example
from match.bfxr_io import ParamSpace


def test_harvest_rows_are_records_wrapping_a_params_dict():
    """Pins the shape every consumer unwraps: {"preset", "seed", "params"}.

    Callers that hand a row straight to the renderer get the default sound --
    unknown keys are merged over the defaults and silently ignored. This is
    the real-shape counterpart to the fakes in test_headroom_presets.py.
    """
    rows = harvest_preset_params(2, seed=5)
    for row in rows:
        assert set(row) >= {"preset", "seed", "params"}
        assert isinstance(row["params"], dict)
        assert "waveType" in row["params"]


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
