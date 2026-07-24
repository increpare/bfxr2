import warnings
from pathlib import Path

import pytest
import torch
from invert import constants
from invert.surrogate import SurrogateSynth, load_surrogate, train_surrogate
from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
from invert.dataset import write_shard


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


def test_train_surrogate_writes_checkpoint(tmp_path: Path):
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
    out = train_surrogate(data, tmp_path / "sur", epochs=3, batch_size=16, device="cpu")
    assert out.is_file()
    ck = torch.load(out, weights_only=False)
    assert ck["width"] == 128 and "model_state" in ck


def _tiny_checkpoint(path: Path, *, channel_mean, channel_std) -> None:
    model = SurrogateSynth(width=4)
    torch.save(
        {
            "model_state": model.state_dict(),
            "width": 4,
            "channel_mean": list(channel_mean),
            "channel_std": list(channel_std),
        },
        path,
    )


def test_load_surrogate_warns_on_channel_stats_mismatch(tmp_path: Path):
    path = tmp_path / "surrogate_mismatch.pt"
    mismatched_mean = [m + 1.0 for m in constants.CHANNEL_MEAN]
    _tiny_checkpoint(path, channel_mean=mismatched_mean, channel_std=constants.CHANNEL_STD)

    with pytest.warns(UserWarning):
        load_surrogate(path, torch.device("cpu"))


def test_load_surrogate_no_warning_when_channel_stats_match(tmp_path: Path):
    path = tmp_path / "surrogate_match.pt"
    _tiny_checkpoint(
        path, channel_mean=constants.CHANNEL_MEAN, channel_std=constants.CHANNEL_STD
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_surrogate(path, torch.device("cpu"))
    assert len(caught) == 0
