from __future__ import annotations

import numpy as np

from match.audio import SAMPLE_RATE
from match.bfxr_io import ParamSpace
from match.optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, SQUARE_ONLY_PARAMS

from .constants import TRAIN_CAP_SECONDS


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


def sample_unit(space: ParamSpace, rng: np.random.Generator, *, fully_uniform: bool) -> np.ndarray:
    if fully_uniform:
        return rng.random(space.dim)
    unit = space.defaults_unit().copy()
    mask = rng.random(space.dim) > 0.5
    unit[mask] = rng.random(int(mask.sum()))
    return unit


def sample_example(
    space: ParamSpace,
    rng: np.random.Generator,
    *,
    force_wave_type: int | None = None,
    uniform_frac: float = 0.2,
) -> dict:
    """Return {unit, wave_type, class_idx} with labels in search-reachable space."""
    fully_uniform = bool(rng.random() < uniform_frac)
    unit = sample_unit(space, rng, fully_uniform=fully_uniform)
    if force_wave_type is None:
        wave_type = int(rng.choice(space.wave_types))
    else:
        wave_type = int(force_wave_type)

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
        "wave_type": wave_type,
        "class_idx": id_to_cls[wave_type],
    }
