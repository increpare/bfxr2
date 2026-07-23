from pathlib import Path

import numpy as np
import torch

from invert.constants import DATASET_VERSION, N_CHANNELS, N_FRAMES
from invert.dataset import write_shard, read_shard


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
    from invert.dataset import generate_shards, read_shard

    generate_shards(tmp_path, n=8, seed=0, jobs=1, shard_size=8, augment_p=0.5)
    shards = sorted(tmp_path.glob("shard_*.pt"))
    assert len(shards) == 1
    data = read_shard(shards[0])
    assert data["features"].shape[0] == 8
    assert data["features"].shape[1:] == (N_CHANNELS, N_FRAMES)
