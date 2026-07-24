from __future__ import annotations

import numpy as np

from match.audio import SAMPLE_RATE
from match.bfxr_io import ParamSpace
from match.optimizer import (
    ENVELOPE_PARAMS,
    ENVELOPE_SAMPLES_PER_UNIT,
    SQUARE_ONLY_PARAMS,
    freq_param_from_hz,
)
from match.notes import pitch_jump_param_from_ratio

from .constants import TRAIN_CAP_SECONDS

TONAL_WAVE_TYPES = (0, 1, 2, 4, 5, 6, 7, 8, 10, 11)


def _to_unit(space: ParamSpace, name: str, value: float) -> float:
    i = space.names.index(name)
    lo, hi = float(space.mins[i]), float(space.maxs[i])
    span = hi - lo
    return float(np.clip((value - lo) / span, 0.0, 1.0)) if span else 0.0


def _structured_unit(space: ParamSpace, rng: np.random.Generator) -> np.ndarray:
    """A coherent arpeggio: 1-2 pitch jumps at musical intervals with an
    envelope sized so every note is audible, plus optional repeat / vibrato /
    filter-sweep variants. Returns a unit vector; wave type is chosen by the
    caller (tonal). Non-overridden params keep their defaults (e.g. no slide)."""
    unit = space.defaults_unit().copy()

    base_hz = float(np.exp(rng.uniform(np.log(200.0), np.log(2000.0))))
    fs = freq_param_from_hz(base_hz)
    unit[space.names.index("frequency_start")] = _to_unit(
        space, "frequency_start", fs if fs is not None else 0.3)

    def _ratio() -> float:
        semis = int(rng.integers(2, 25)) * (1 if rng.random() < 0.5 else -1)
        return float(2.0 ** (semis / 12.0))

    on1 = float(rng.uniform(0.2, 0.5))
    unit[space.names.index("pitch_jump_amount")] = _to_unit(
        space, "pitch_jump_amount", pitch_jump_param_from_ratio(_ratio()))
    unit[space.names.index("pitch_jump_onset_percent")] = _to_unit(
        space, "pitch_jump_onset_percent", on1)
    if rng.random() < 0.6:  # second jump most of the time
        unit[space.names.index("pitch_jump_2_amount")] = _to_unit(
            space, "pitch_jump_2_amount", pitch_jump_param_from_ratio(_ratio()))
        unit[space.names.index("pitch_jump_onset2_percent")] = _to_unit(
            space, "pitch_jump_onset2_percent", float(rng.uniform(on1 + 0.15, 0.9)))

    unit[space.names.index("attackTime")] = _to_unit(
        space, "attackTime", float(rng.uniform(0.0, 0.05)))
    unit[space.names.index("sustainTime")] = _to_unit(
        space, "sustainTime", float(rng.uniform(0.25, 0.6)))
    unit[space.names.index("decayTime")] = _to_unit(
        space, "decayTime", float(rng.uniform(0.15, 0.5)))

    if rng.random() < 0.25:  # repeating motif
        unit[space.names.index("pitch_jump_repeat_speed")] = _to_unit(
            space, "pitch_jump_repeat_speed", float(rng.uniform(0.1, 0.6)))
    if rng.random() < 0.25:  # vibrato
        unit[space.names.index("vibratoDepth")] = _to_unit(
            space, "vibratoDepth", float(rng.uniform(0.1, 0.5)))
        unit[space.names.index("vibratoSpeed")] = _to_unit(
            space, "vibratoSpeed", float(rng.uniform(0.2, 0.7)))
    if rng.random() < 0.25:  # filter sweep
        unit[space.names.index("lpFilterCutoffSweep")] = _to_unit(
            space, "lpFilterCutoffSweep", float(rng.uniform(-0.5, 0.5)))

    return np.clip(unit, 0.0, 1.0)



def wave_type_index_map(space: ParamSpace) -> tuple[dict[int, int], dict[int, int]]:
    ordered = sorted(space.wave_types)
    id_to_cls = {wt: i for i, wt in enumerate(ordered)}
    cls_to_id = {i: wt for wt, i in id_to_cls.items()}
    return id_to_cls, cls_to_id


def _project_envelope(params: dict, cap_samples: float) -> None:
    total = sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)
    if total > cap_samples:
        scale = float(np.sqrt(cap_samples / total))
        for n in ENVELOPE_PARAMS:
            params[n] *= scale


def sample_unit(
    space: ParamSpace,
    rng: np.random.Generator,
    *,
    mode: str = "biased",
    fully_uniform: bool | None = None,
) -> np.ndarray:
    if fully_uniform is not None:
        mode = "uniform" if fully_uniform else "biased"
    if mode == "uniform":
        return rng.random(space.dim)
    if mode == "kknob":
        unit = space.defaults_unit().copy()
        k = int(rng.integers(1, 7))
        idx = rng.choice(space.dim, size=k, replace=False)
        unit[idx] = rng.random(k)
        return unit
    if mode == "biased":
        unit = space.defaults_unit().copy()
        mask = rng.random(space.dim) > 0.5
        unit[mask] = rng.random(int(mask.sum()))
        return unit
    if mode == "structured":
        return _structured_unit(space, rng)
    raise ValueError(mode)


def finalize_example(space: ParamSpace, unit: np.ndarray, wave_type: int) -> dict:
    """Pin square-only params, cap the envelope, round-trip through params
    so labels live in exactly the space search explores."""
    unit = np.asarray(unit, dtype=np.float64).copy()
    if wave_type != 0:
        du = space.defaults_unit()
        for name in SQUARE_ONLY_PARAMS:
            unit[space.names.index(name)] = float(du[space.names.index(name)])

    cap = TRAIN_CAP_SECONDS * SAMPLE_RATE
    params = space.params_dict(unit, wave_type)
    _project_envelope(params, cap)
    unit, _ = space.unit_from_params(params)

    id_to_cls, _ = wave_type_index_map(space)
    return {
        "unit": unit.astype(np.float64),
        "wave_type": int(wave_type),
        "class_idx": id_to_cls[int(wave_type)],
    }


def sample_example(
    space: ParamSpace,
    rng: np.random.Generator,
    *,
    force_wave_type: int | None = None,
    uniform_frac: float = 0.2,
    mode: str | None = None,
) -> dict:
    """Return {unit, wave_type, class_idx} with labels in search-reachable space."""
    if mode is None:
        mode = "uniform" if rng.random() < uniform_frac else "biased"
    unit = sample_unit(space, rng, mode=mode)
    if force_wave_type is None:
        wave_type = int(rng.choice(space.wave_types))
    else:
        wave_type = int(force_wave_type)
    return finalize_example(space, unit, wave_type)
