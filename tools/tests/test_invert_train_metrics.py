# tools/tests/test_invert_train_metrics.py
from pathlib import Path

import torch

from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES, N_PARAMS
from invert.dataset import write_shard
from invert.train import (
    curriculum_weights,
    invert_loss,
    per_param_r2,
    select_unit_pred,
    train,
    wavetype_topk_accuracy,
)
from match.bfxr_io import ParamSpace


def test_per_param_r2_perfect_prediction_is_one():
    tgt = torch.rand(200, 30)
    names = list(ParamSpace().names)
    r2 = per_param_r2(tgt, tgt, names)
    assert set(r2) == set(names)
    assert all(v > 0.999 for v in r2.values())


def test_per_param_r2_mean_prediction_is_zero():
    tgt = torch.rand(500, 30)
    pred = tgt.mean(dim=0, keepdim=True).expand_as(tgt)
    r2 = per_param_r2(pred, tgt, list(ParamSpace().names))
    assert all(abs(v) < 0.02 for v in r2.values())


def test_wavetype_topk_accuracy():
    # logits rank class 0 first, class 1 second for every row
    logits = torch.tensor([[3.0, 2.0, 1.0]] * 4)
    cls = torch.tensor([0, 1, 1, 2])
    assert wavetype_topk_accuracy(logits, cls, 1) == 0.25
    assert wavetype_topk_accuracy(logits, cls, 2) == 0.75


def test_select_unit_pred_versions():
    out_v1 = {"unit": torch.rand(4, 30)}
    assert torch.equal(select_unit_pred(out_v1, torch.zeros(4).long(), 1), out_v1["unit"])
    per_class = torch.rand(4, 12, 30)
    cls = torch.tensor([0, 3, 7, 11])
    got = select_unit_pred({"unit_per_class": per_class}, cls, 2)
    for b in range(4):
        assert torch.equal(got[b], per_class[b, cls[b]])


def test_invert_loss_weighted_sum_and_raw_parts():
    from invert.train import invert_loss

    space = ParamSpace()
    out = {"unit": torch.rand(8, 30), "wavetype_logits": torch.randn(8, 12)}
    tgt = torch.rand(8, 30)
    wt = torch.zeros(8).long()
    cls = torch.zeros(8).long()
    loss, parts = invert_loss(
        out,
        tgt,
        wt,
        cls,
        space,
        version=1,
        unit_weight=10.0,
        ce_weight=0.5,
    )
    expected = 10.0 * parts["unit_mse"] + 0.5 * parts["ce"]
    assert abs(float(loss) - expected) < 1e-5


def _fake_out(space, batch=4):
    n = len(space.names)
    return {
        "unit": torch.rand(batch, n, requires_grad=True),
        "wavetype_logits": torch.randn(batch, 12, requires_grad=True),
    }


def test_invert_loss_weights_scale_reported_mse_is_unweighted():
    space = ParamSpace()
    n = len(space.names)
    torch.manual_seed(0)
    out = _fake_out(space)
    tgt = torch.rand(4, n)
    wt = torch.zeros(4, dtype=torch.long)   # square, so no square-only masking
    cls = torch.zeros(4, dtype=torch.long)

    w_uniform = torch.ones(n)
    w_skew = torch.ones(n)
    w_skew[0] = 4.0  # up-weight param 0

    loss_u, parts_u = invert_loss(out, tgt, wt, cls, space, unit_loss_weights=w_uniform)
    loss_s, parts_s = invert_loss(out, tgt, wt, cls, space, unit_loss_weights=w_skew)

    # reported unit_mse is the plain masked MSE — identical regardless of weights
    assert abs(parts_u["unit_mse"] - parts_s["unit_mse"]) < 1e-6
    # the training loss does change when weights change
    assert abs(float(loss_u) - float(loss_s)) > 1e-6


def test_curriculum_ramps_hard_params_only():
    base = torch.tensor([2.0, 2.0, 1.0, 1.0])
    easy = torch.tensor([1.0, 1.0, 0.0, 0.0])  # first two are "easy"
    # epoch 1 of 4: hard params at 0.25 * base; easy unchanged
    w1 = curriculum_weights(base, easy, epoch=1, curriculum_epochs=4)
    assert torch.allclose(w1, torch.tensor([2.0, 2.0, 0.25, 0.25]))
    # at/after curriculum end: full base weights
    w4 = curriculum_weights(base, easy, epoch=4, curriculum_epochs=4)
    assert torch.allclose(w4, base)
    # disabled: returns base unchanged
    w0 = curriculum_weights(base, easy, epoch=1, curriculum_epochs=0)
    assert torch.allclose(w0, base)


def test_train_smoke_with_curriculum(tmp_path: Path):
    n = 32
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
    best = train(data, tmp_path / "run", epochs=2, batch_size=16,
                 curriculum_epochs=2, device="cpu")
    assert best.is_file()
