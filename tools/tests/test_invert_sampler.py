import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, SQUARE_ONLY_PARAMS
from match.audio import SAMPLE_RATE
from invert.constants import TRAIN_CAP_SECONDS
from invert.sampler import sample_example, wave_type_index_map


def test_wave_type_index_map_bijective():
    space = ParamSpace()
    id_to_cls, cls_to_id = wave_type_index_map(space)
    assert len(id_to_cls) == 12
    for wt, cls in id_to_cls.items():
        assert cls_to_id[cls] == wt


def test_sampler_determinism():
    space = ParamSpace()
    a = sample_example(space, rng=np.random.default_rng(0))
    b = sample_example(space, rng=np.random.default_rng(0))
    assert np.allclose(a["unit"], b["unit"])
    assert a["wave_type"] == b["wave_type"]


def test_sampler_nonsquare_pins_square_only():
    space = ParamSpace()
    rng = np.random.default_rng(1)
    for _ in range(40):
        ex = sample_example(space, rng=rng, force_wave_type=9)  # Bitnoise
        for name in SQUARE_ONLY_PARAMS:
            i = space.names.index(name)
            assert abs(ex["unit"][i] - space.defaults_unit()[i]) < 1e-9


def test_sampler_envelope_under_cap():
    space = ParamSpace()
    rng = np.random.default_rng(2)
    cap = TRAIN_CAP_SECONDS * SAMPLE_RATE
    for _ in range(50):
        ex = sample_example(space, rng=rng)
        params = space.params_dict(ex["unit"], ex["wave_type"])
        total = sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)
        assert total <= cap + 1.0  # float slack
