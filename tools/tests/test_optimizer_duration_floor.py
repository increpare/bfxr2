from types import SimpleNamespace

from match.audio import SAMPLE_RATE
from match.bfxr_io import ParamSpace
from match.optimizer import (
    ENVELOPE_PARAMS,
    ENVELOPE_SAMPLES_PER_UNIT,
    OptimizeSettings,
    StagedOptimizer,
)


def _opt(duration_floor: float, target_seconds: float) -> StagedOptimizer:
    space = ParamSpace()
    obj = SimpleNamespace(target_len=int(target_seconds * SAMPLE_RATE))
    return StagedOptimizer(
        space, None, obj, OptimizeSettings(duration_floor=duration_floor)
    )


def _env_samples(params: dict) -> float:
    return sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)


def test_floor_off_leaves_tiny_envelope_untouched():
    opt = _opt(0.0, target_seconds=2.0)
    params = {n: 0.02 for n in ENVELOPE_PARAMS}
    before = _env_samples(params)
    opt._project_envelope(params)
    assert _env_samples(params) == before  # unchanged when floor disabled


def test_floor_extends_short_envelope_to_target_fraction():
    opt = _opt(0.5, target_seconds=2.0)
    params = {n: 0.02 for n in ENVELOPE_PARAMS}
    opt._project_envelope(params)
    total = _env_samples(params)
    # filled to ~0.5 * 2.0s (via the decay tail), attack/sustain preserved
    assert total >= 0.5 * 2.0 * SAMPLE_RATE * 0.98
    assert params["attackTime"] == 0.02 and params["sustainTime"] == 0.02


def test_floor_does_not_shorten_already_long_envelope():
    opt = _opt(0.5, target_seconds=2.0)
    params = {"attackTime": 0.0, "sustainTime": 0.9, "decayTime": 0.0}
    before = _env_samples(params)
    opt._project_envelope(params)
    # already above the 0.5x floor -> decay not reduced by the floor branch
    assert params["decayTime"] == 0.0
    assert _env_samples(params) == before


def test_floor_skipped_for_very_short_targets():
    # target under 0.1s: floor disabled so genuinely short sounds stay free
    opt = _opt(0.5, target_seconds=0.05)
    assert opt.floor_samples == 0.0
    params = {n: 0.02 for n in ENVELOPE_PARAMS}
    before = _env_samples(params)
    opt._project_envelope(params)
    assert _env_samples(params) == before
