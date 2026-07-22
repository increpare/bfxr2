import numpy as np
import pytest

from match.bfxr_io import ParamSpace, param_info
from match.renderer import BfxrRenderer

MIN_SAMPLES = int(0.18 * 44100)


@pytest.fixture(scope="module")
def renderer():
    with BfxrRenderer() as r:
        yield r


@pytest.fixture(scope="module")
def space():
    return ParamSpace()


def test_param_info_shape():
    info = param_info()
    ranges = [p for p in info["params"] if p["type"] == "RANGE"]
    assert len(ranges) == 31
    assert len(info["waveTypes"]) == 12
    assert info["sampleRate"] == 44100
    assert "masterVolume" in info["permalocked"]


def test_param_space(space):
    assert space.dim == 30  # masterVolume excluded
    assert sorted(space.wave_types) == list(range(12))
    unit = space.defaults_unit()
    assert np.all(unit >= 0) and np.all(unit <= 1)
    params = space.params_dict(unit, wave_type=3)
    assert params["waveType"] == 3
    assert params["masterVolume"] == 0.5
    round_trip, wt = space.unit_from_params(params)
    assert wt == 3
    np.testing.assert_allclose(round_trip, unit, atol=1e-12)


def test_render_defaults_nonsilent(renderer):
    buf = renderer.render({}, seed=1)
    assert buf is not None
    assert len(buf) >= MIN_SAMPLES
    assert np.sqrt(np.mean(buf**2)) > 0.01


def test_render_deterministic_same_seed(renderer):
    p = {"waveType": 3, "frequency_start": 0.4}
    a = renderer.render(p, seed=42)
    b = renderer.render(p, seed=42)
    np.testing.assert_array_equal(a, b)


def test_render_differs_across_seeds_for_noise(renderer):
    p = {"waveType": 3, "frequency_start": 0.4}
    a = renderer.render(p, seed=1)
    b = renderer.render(p, seed=2)
    assert len(a) != len(b) or not np.array_equal(a, b)


def test_render_batch_order_and_count(renderer, space):
    rng = np.random.default_rng(0)
    batch = [space.params_dict(rng.random(space.dim), wave_type=wt) for wt in range(12)]
    results = renderer.render_batch(batch, seeds=1)
    assert len(results) == 12
    # order preserved: re-render one entry individually and compare
    again = renderer.render(batch[5], seed=1)
    if results[5] is None:
        assert again is None
    else:
        np.testing.assert_array_equal(results[5], again)


def test_render_large_batch(renderer, space):
    """Batch big enough to exercise pipe backpressure in both directions."""
    rng = np.random.default_rng(7)
    batch = [space.params_dict(rng.random(space.dim), wave_type=int(rng.integers(0, 12)))
             for _ in range(200)]
    results = renderer.render_batch(batch, seeds=3)
    assert len(results) == 200
    ok = [r for r in results if r is not None]
    assert len(ok) > 150  # most random params should render fine
