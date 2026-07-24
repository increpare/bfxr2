import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, SQUARE_ONLY_PARAMS
from match.audio import SAMPLE_RATE
from invert.constants import TRAIN_CAP_SECONDS
from invert.sampler import (
    TONAL_WAVE_TYPES,
    _structured_unit,
    sample_example,
    sample_unit,
    wave_type_index_map,
)


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


def test_kknob_moves_few_params():
    space = ParamSpace()
    rng = np.random.default_rng(3)
    for _ in range(20):
        unit = sample_unit(space, rng, mode="kknob")
        moved = int((unit != space.defaults_unit()).sum())
        assert 1 <= moved <= 6


def _idx(space, name):
    return space.names.index(name)


def test_structured_unit_sets_a_pitch_jump_and_audible_envelope():
    space = ParamSpace()
    rng = np.random.default_rng(0)
    u = _structured_unit(space, rng)
    assert u.shape == (space.dim,)
    assert np.all((u >= 0.0) & (u <= 1.0))
    # at least the first jump is non-default (default pitch_jump_amount unit = 0.5)
    assert abs(u[_idx(space, "pitch_jump_amount")] - 0.5) > 1e-6
    # onset ordered when a second jump is present
    a2 = u[_idx(space, "pitch_jump_2_amount")]
    if abs(a2 - 0.5) > 1e-6:
        assert u[_idx(space, "pitch_jump_onset2_percent")] >= u[_idx(space, "pitch_jump_onset_percent")]
    # envelope has real sustain (audible), not the degenerate near-zero
    assert u[_idx(space, "sustainTime")] > 0.2


def test_structured_unit_is_deterministic_under_seed():
    space = ParamSpace()
    a = _structured_unit(space, np.random.default_rng(7))
    b = _structured_unit(space, np.random.default_rng(7))
    assert np.array_equal(a, b)


def test_sample_unit_structured_mode_dispatches():
    space = ParamSpace()
    u = sample_unit(space, np.random.default_rng(1), mode="structured")
    assert u.shape == (space.dim,)
    assert abs(u[_idx(space, "pitch_jump_amount")] - 0.5) > 1e-6


def test_tonal_wave_types_exclude_noise():
    assert 3 not in TONAL_WAVE_TYPES and 9 not in TONAL_WAVE_TYPES
    assert 0 in TONAL_WAVE_TYPES
