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
    sq_j = space.names.index("squareDuty")

    unit_tgt = torch.zeros(1, 30)
    unit_pred = unit_tgt.clone()
    unit_pred[0, sq_j] = 1.0  # huge error only on square-only dim

    # Nonsquare: square-only dim must be masked → unit_mse ≈ 0
    wt_ns = torch.tensor([9])
    cls_ns = torch.tensor([id_to_cls[9]])
    logits_ns = torch.zeros(1, 12)
    logits_ns[0, cls_ns[0]] = 10.0
    loss_ns, parts_ns = invert_loss(
        {"unit": unit_pred, "wavetype_logits": logits_ns},
        unit_tgt,
        wt_ns,
        cls_ns,
        space,
        version=1,
    )
    assert torch.isfinite(loss_ns)
    assert torch.isfinite(torch.tensor(parts_ns["ce"]))
    assert parts_ns["unit_mse"] < 1e-6

    # Square: same error must contribute → unit_mse clearly larger
    wt_sq = torch.tensor([0])
    cls_sq = torch.tensor([id_to_cls[0]])
    logits_sq = torch.zeros(1, 12)
    logits_sq[0, cls_sq[0]] = 10.0
    loss_sq, parts_sq = invert_loss(
        {"unit": unit_pred, "wavetype_logits": logits_sq},
        unit_tgt,
        wt_sq,
        cls_sq,
        space,
        version=1,
    )
    assert torch.isfinite(loss_sq)
    assert torch.isfinite(torch.tensor(parts_sq["ce"]))
    assert parts_sq["unit_mse"] > 0.01


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


def test_train_step_on_float16_shard_payload():
    """Shards store float16 features; training must cast before the CNN."""
    import numpy as np

    from invert.dataset import _pack_shard_payload
    from invert.features_pack import normalize_channels

    space = ParamSpace()
    id_to_cls, _ = wave_type_index_map(space)
    rng = np.random.default_rng(0)
    n = 4
    examples = [
        {
            "unit": rng.random(30).astype(np.float64),
            "wave_type": wt,
            "class_idx": id_to_cls[wt],
        }
        for wt in (0, 9, 1, 4)
    ]
    waves = [rng.standard_normal(8000).astype(np.float32) * 0.2 for _ in range(n)]
    payload = _pack_shard_payload(examples, waves, rng, augment_p=0.0)
    assert payload["features"].dtype == torch.float16

    # Mimic InvertShardDataset.__getitem__ + _run_epoch casting/norm
    x = normalize_channels(payload["features"].float())
    log_dur = payload["log_duration"].float()
    unit = payload["unit"].float()
    wt = payload["wave_type"]
    cls = payload["class_idx"]

    m = InverseModel(version=1)
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    out = m(x, log_dur)
    loss, parts = invert_loss(out, unit, wt, cls, space, version=1)
    loss.backward()
    opt.step()
    assert torch.isfinite(loss)
    assert parts["ce"] > 1.0  # near ln(12)≈2.48 at init, not collapsed
