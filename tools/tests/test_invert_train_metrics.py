# tools/tests/test_invert_train_metrics.py
import torch

from invert.train import per_param_r2, select_unit_pred, wavetype_topk_accuracy
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
