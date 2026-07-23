import torch

from invert.constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
from invert.model import InverseModel
from invert.sampler import wave_type_index_map
from invert.train import invert_loss
from match.bfxr_io import ParamSpace


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


def test_invert_loss_masks_square_only():
    space = ParamSpace()
    id_to_cls, _ = wave_type_index_map(space)
    sq_idx = [space.names.index(n) for n in ("squareDuty", "dutySweep")]
    unit_tgt = torch.rand(2, 30)
    unit_pred = unit_tgt.clone()
    unit_pred[0, sq_idx[0]] += 1.0  # huge error on square-only
    # example 0 = nonsquare, example 1 = square
    wave_types = torch.tensor([9, 0])
    class_idx = torch.tensor([id_to_cls[9], id_to_cls[0]])
    logits = torch.zeros(2, 12)
    logits[range(2), class_idx] = 10.0
    out = {"unit": unit_pred, "wavetype_logits": logits}
    loss, parts = invert_loss(out, unit_tgt, wave_types, class_idx, space, version=1)
    assert torch.isfinite(loss)
    assert parts["unit_mse"] < 0.1


def test_train_step_smoke():
    space = ParamSpace()
    m = InverseModel(version=1)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    x = torch.randn(8, N_CHANNELS, N_FRAMES)
    log_dur = torch.randn(8)
    unit = torch.rand(8, 30)
    wt = torch.tensor([0, 9, 1, 4, 2, 3, 5, 6])
    id_to_cls, _ = wave_type_index_map(space)
    cls = torch.tensor([id_to_cls[int(t)] for t in wt])
    out = m(x, log_dur)
    loss, _ = invert_loss(out, unit, wt, cls, space, version=1)
    loss.backward()
    opt.step()
    assert torch.isfinite(loss)
