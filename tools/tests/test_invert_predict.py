import torch

from invert.model import InverseModel
from invert.predict import load_checkpoint, predict_wave
from match.bfxr_io import ParamSpace


def test_predict_topk_from_random_checkpoint(tmp_path):
    space = ParamSpace()
    m = InverseModel(version=1)
    ckpt = {
        "model_state": m.state_dict(),
        "version": 1,
        "wave_types_order": sorted(space.wave_types),
        "space_names": space.names,
    }
    path = tmp_path / "ckpt.pt"
    torch.save(ckpt, path)
    model, meta = load_checkpoint(path, device="cpu")
    w = (torch.randn(8000).numpy() * 0.2).astype("float32")
    guesses = predict_wave(model, meta, w, top_k=3)
    assert len(guesses) == 3
    assert guesses[0]["unit"].shape == (30,)
    assert "wave_type" in guesses[0]
    assert "class_idx" in guesses[0]
    assert "prob" in guesses[0]
    # v1: same unit vector for each top-k (before per-wave-type pinning may differ)
    # after pinning, non-square may rewrite squareDuty/dutySweep — still shape-ok
    assert all(g["unit"].shape == (30,) for g in guesses)


def test_predict_v2_per_class_units(tmp_path):
    space = ParamSpace()
    m = InverseModel(version=2)
    ckpt = {
        "model_state": m.state_dict(),
        "version": 2,
        "wave_types_order": sorted(space.wave_types),
        "space_names": space.names,
    }
    path = tmp_path / "ckpt_v2.pt"
    torch.save(ckpt, path)
    model, meta = load_checkpoint(path, device="cpu")
    assert meta["version"] == 2
    w = (torch.randn(8000).numpy() * 0.2).astype("float32")
    guesses = predict_wave(model, meta, w, top_k=3)
    assert len(guesses) == 3
    assert guesses[0]["unit"].shape == (30,)
    assert 0.0 <= guesses[0]["prob"] <= 1.0
