from pathlib import Path

import json

import numpy as np
import pytest
import torch

from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES
from invert.dataset import (
    InvertShardDataset,
    _is_acceptable_wave,
    generate_shards,
    read_shard,
    write_shard,
)


def _shard_payload(n: int = 2, *, dataset_version: str = DATASET_VERSION) -> dict:
    return {
        "features": torch.randn(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.randn(n),
        "unit": torch.rand(n, 30),
        "wave_type": torch.zeros(n, dtype=torch.long),
        "class_idx": torch.zeros(n, dtype=torch.long),
        "meta": {"dataset_version": dataset_version, "n": n},
    }


def test_shard_round_trip(tmp_path: Path):
    n = 4
    payload = {
        "features": torch.randn(n, N_CHANNELS, N_FRAMES).half(),
        "log_duration": torch.randn(n),
        "unit": torch.rand(n, 30),
        "wave_type": torch.tensor([0, 9, 1, 4], dtype=torch.long),
        "class_idx": torch.tensor([2, 9, 3, 0], dtype=torch.long),
        "meta": {"dataset_version": DATASET_VERSION, "n": n},
    }
    path = tmp_path / "shard_0000.pt"
    write_shard(path, payload)
    loaded = read_shard(path)
    assert loaded["meta"]["dataset_version"] == DATASET_VERSION
    assert torch.equal(loaded["wave_type"], payload["wave_type"])
    assert torch.allclose(loaded["features"].float(), payload["features"].float())
    assert torch.allclose(loaded["unit"], payload["unit"])


def test_generate_tiny_shard(tmp_path: Path):
    generate_shards(tmp_path, n=8, seed=0, jobs=1, shard_size=8, augment_p=0.5)
    shards = sorted(tmp_path.glob("shard_*.pt"))
    assert len(shards) == 1
    data = read_shard(shards[0])
    assert data["features"].shape[0] == 8
    assert data["features"].shape[1:] == (N_CHANNELS, N_FRAMES)


def test_generate_clears_stale_shards(tmp_path: Path):
    write_shard(tmp_path / "shard_0000.pt", _shard_payload(4))
    write_shard(tmp_path / "shard_0001.pt", _shard_payload(4))
    (tmp_path / "manifest.json").write_text(json.dumps({"n": 8, "dataset_version": DATASET_VERSION}))

    generate_shards(tmp_path, n=4, seed=0, jobs=1, shard_size=4, augment_p=0.0)
    shards = sorted(tmp_path.glob("shard_*.pt"))
    assert len(shards) == 1
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    ds = InvertShardDataset(tmp_path)
    assert len(ds) == manifest["n"] == 4


def test_is_acceptable_wave_rejects_nonfinite():
    ok = np.ones(100, dtype=np.float32) * 0.2
    assert _is_acceptable_wave(ok)
    assert not _is_acceptable_wave(None)
    assert not _is_acceptable_wave(np.zeros(10, dtype=np.float32))
    nan = ok.copy()
    nan[3] = np.nan
    assert not _is_acceptable_wave(nan)
    inf = ok.copy()
    inf[5] = np.inf
    assert not _is_acceptable_wave(inf)


def test_dataset_version_mismatch_raises(tmp_path: Path):
    write_shard(tmp_path / "shard_0000.pt", _shard_payload(2, dataset_version="not-v1"))
    with pytest.raises(ValueError, match="dataset_version"):
        InvertShardDataset(tmp_path)
