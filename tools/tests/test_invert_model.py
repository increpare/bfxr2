import torch

from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
from invert.model import InverseModel


def test_v1_forward_shapes():
    m = InverseModel(version=1)
    x = torch.randn(2, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(2)
    out = m(x, log_dur)
    assert out["unit"].shape == (2, N_PARAMS)
    assert out["wavetype_logits"].shape == (2, N_WAVETYPES)
    # unit in [0,1] via sigmoid
    assert float(out["unit"].min()) >= 0.0
    assert float(out["unit"].max()) <= 1.0


def test_v2_forward_shapes():
    m = InverseModel(version=2)
    x = torch.randn(3, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(3)
    out = m(x, log_dur)
    assert out["unit_per_class"].shape == (3, N_WAVETYPES, N_PARAMS)
    assert out["wavetype_logits"].shape == (3, N_WAVETYPES)
