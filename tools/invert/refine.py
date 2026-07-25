"""Inference-time Adam refine of predicted unit through frozen SurrogateSynth.

    See docs/superpowers/specs/2026-07-25-inverse-model-test-time-refine-design.md
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

from match.bfxr_io import ParamSpace

from .constants import N_WAVETYPES, SQUARE_ONLY


def _pin_square_only(unit: np.ndarray, wave_type: int, space: ParamSpace) -> np.ndarray:
    out = np.asarray(unit, dtype=np.float64).copy()
    if wave_type != 0:
        defaults = space.defaults_unit()
        for name in SQUARE_ONLY:
            j = space.names.index(name)
            out[j] = float(defaults[j])
    return out


def refine_unit(
    unit: np.ndarray,
    wave_type: int,
    target_features_norm: torch.Tensor,
    log_duration: torch.Tensor,
    surrogate: torch.nn.Module,
    *,
    steps: int,
    lr: float,
    device: torch.device,
) -> np.ndarray:
    """Optimize `unit` to match `target_features_norm` under frozen surrogate.

    `target_features_norm` and `log_duration` must already be on `device` (or
    will be moved). Wavetype is fixed (hard one-hot). Returns a pinned numpy
    unit in [0, 1]. When steps <= 0, only pins and returns.
    """
    space = ParamSpace()
    unit_np = _pin_square_only(unit, wave_type, space)
    if steps <= 0:
        return unit_np

    surrogate = surrogate.to(device)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    x = target_features_norm.to(device).float()
    if x.dim() == 2:
        x = x.unsqueeze(0)
    log_dur = log_duration.to(device).float().reshape(-1)

    onehot = F.one_hot(
        torch.tensor([int(wave_type)], device=device), N_WAVETYPES
    ).float()

    u = torch.tensor(unit_np, dtype=torch.float32, device=device).unsqueeze(0)
    u = u.detach().clone().requires_grad_(True)
    opt = torch.optim.Adam([u], lr=lr)

    for _ in range(int(steps)):
        opt.zero_grad(set_to_none=True)
        pred = surrogate(u, onehot, log_dur)
        loss = F.mse_loss(pred, x)
        loss.backward()
        opt.step()
        with torch.no_grad():
            u.clamp_(0.0, 1.0)

    out = u.detach().cpu().numpy().reshape(-1).astype(np.float64)
    return _pin_square_only(out, wave_type, space)
