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
