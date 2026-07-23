import torch
from invert.surrogate import SurrogateSynth
from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES


def test_surrogate_shapes_and_backward():
    m = SurrogateSynth(width=32)
    b = 5
    unit = torch.rand(b, N_PARAMS, requires_grad=True)
    onehot = torch.nn.functional.one_hot(
        torch.zeros(b, dtype=torch.long), N_WAVETYPES
    ).float()
    log_dur = torch.zeros(b)
    out = m(unit, onehot, log_dur)
    assert out.shape == (b, N_CHANNELS, N_FRAMES)
    out.sum().backward()
    assert unit.grad is not None and torch.isfinite(unit.grad).all()
