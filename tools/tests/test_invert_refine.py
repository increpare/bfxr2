import numpy as np
import torch
import torch.nn.functional as F

from invert.constants import N_PARAMS, N_WAVETYPES, SQUARE_ONLY
from invert.surrogate import SurrogateSynth
from match.bfxr_io import ParamSpace


def _mse(surrogate, unit, onehot, log_dur, target_feat):
    with torch.no_grad():
        pred = surrogate(unit, onehot, log_dur)
        return float(F.mse_loss(pred, target_feat))


def test_refine_unit_reduces_surrogate_mse():
    from invert.refine import refine_unit

    torch.manual_seed(0)
    surrogate = SurrogateSynth(width=16)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    unit_true = torch.rand(1, N_PARAMS)
    # non-square so square-only pin is exercised later
    wave_type = 2
    onehot = F.one_hot(torch.tensor([wave_type]), N_WAVETYPES).float()
    log_dur = torch.zeros(1)
    target_feat = surrogate(unit_true, onehot, log_dur).detach()

    noise = 0.15 * torch.randn_like(unit_true)
    unit0 = (unit_true + noise).clamp(0, 1).numpy().astype(np.float64).reshape(-1)

    u0 = torch.tensor(unit0, dtype=torch.float32).unsqueeze(0)
    mse0 = _mse(surrogate, u0, onehot, log_dur, target_feat)

    refined = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=80, lr=5e-2, device=torch.device("cpu"),
    )
    assert refined.shape == (N_PARAMS,)
    assert np.all(refined >= 0.0) and np.all(refined <= 1.0)

    u1 = torch.tensor(refined, dtype=torch.float32).unsqueeze(0)
    # rebuild onehot the same way refine does (wave_type fixed)
    mse1 = _mse(surrogate, u1, onehot, log_dur, target_feat)
    assert mse1 < mse0


def test_refine_pins_square_only_for_non_square():
    from invert.refine import refine_unit

    torch.manual_seed(1)
    surrogate = SurrogateSynth(width=8)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)

    space = ParamSpace()
    wave_type = 2  # not square
    unit0 = np.random.default_rng(0).random(N_PARAMS).astype(np.float64)
    # force square-only dims away from defaults so pin is visible
    for name in SQUARE_ONLY:
        unit0[space.names.index(name)] = 0.9

    onehot = F.one_hot(torch.tensor([wave_type]), N_WAVETYPES).float()
    log_dur = torch.zeros(1)
    target_feat = surrogate(
        torch.tensor(unit0, dtype=torch.float32).unsqueeze(0), onehot, log_dur
    ).detach()

    refined = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=5, lr=1e-2, device=torch.device("cpu"),
    )
    defaults = space.defaults_unit()
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        assert abs(refined[j] - float(defaults[j])) < 1e-6


def test_refine_steps_zero_returns_pinned_copy():
    from invert.refine import refine_unit

    space = ParamSpace()
    wave_type = 2
    unit0 = np.linspace(0.1, 0.9, N_PARAMS).astype(np.float64)
    for name in SQUARE_ONLY:
        unit0[space.names.index(name)] = 0.77

    # dummy tensors unused when steps=0
    target_feat = torch.zeros(1, 70, 128)
    log_dur = torch.zeros(1)
    surrogate = SurrogateSynth(width=4)

    out = refine_unit(
        unit0, wave_type, target_feat, log_dur, surrogate,
        steps=0, lr=1e-2, device=torch.device("cpu"),
    )
    defaults = space.defaults_unit()
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        assert abs(out[j] - float(defaults[j])) < 1e-6
    # other dims unchanged
    for j, name in enumerate(space.names):
        if name in SQUARE_ONLY:
            continue
        assert abs(out[j] - unit0[j]) < 1e-9
