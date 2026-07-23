import torch
from match.bfxr_io import ParamSpace
from invert.surrogate import SurrogateSynth
from invert.train import invert_loss
from invert.constants import N_CHANNELS, N_FRAMES


def test_spectral_term_added_and_backprops_to_unit():
    space = ParamSpace()
    n = len(space.names)
    b = 4
    out = {
        "unit": torch.rand(b, n, requires_grad=True),
        "wavetype_logits": torch.randn(b, 12),
    }
    tgt = torch.rand(b, n)
    wt = torch.zeros(b, dtype=torch.long)
    cls = torch.zeros(b, dtype=torch.long)
    surrogate = SurrogateSynth(width=16).eval()
    for p in surrogate.parameters():
        p.requires_grad_(False)
    norm_feats = torch.rand(b, N_CHANNELS, N_FRAMES)
    log_dur = torch.zeros(b)

    loss_no, parts_no = invert_loss(out, tgt, wt, cls, space)
    assert "spectral" not in parts_no

    loss_sp, parts_sp = invert_loss(
        out, tgt, wt, cls, space,
        surrogate=surrogate, spectral_weight=1.0,
        norm_features=norm_feats, log_duration=log_dur,
    )
    assert "spectral" in parts_sp and parts_sp["spectral"] >= 0.0
    loss_sp.backward()
    assert out["unit"].grad is not None and torch.isfinite(out["unit"].grad).all()


from pathlib import Path
from invert.surrogate import train_surrogate
from invert.dataset import write_shard
from invert.constants import DATASET_VERSION, N_PARAMS
from invert.train import train


def test_train_with_spectral_loss_smoke(tmp_path: Path):
    n = 48
    payload = {
        "features": torch.rand(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.zeros(n),
        "unit": torch.rand(n, N_PARAMS),
        "wave_type": torch.zeros(n, dtype=torch.long),
        "class_idx": torch.zeros(n, dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    data = tmp_path / "data"
    write_shard(data / "shard_0000.pt", payload)
    (data / "manifest.json").write_text('{"n": %d}' % n)
    sur = train_surrogate(data, tmp_path / "sur", epochs=2, batch_size=16, device="cpu")
    best = train(data, tmp_path / "run", epochs=2, batch_size=16,
                 surrogate_path=sur, spectral_weight=1.0, device="cpu")
    assert best.is_file()
