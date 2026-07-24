from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest
import torch

from invert.constants import N_CHANNELS, N_FRAMES
from invert.real_audio import (
    RealAudioFeatureDataset,
    build_manifest,
    iter_audio_files,
)


def _write_tone_wav(path: Path, *, n: int = 4000, hz: float = 440.0, sr: int = 44100) -> None:
    t = np.arange(n) / sr
    x = (0.4 * np.sin(2 * np.pi * hz * t)).astype(np.float32)
    # 16-bit PCM via stdlib wave
    pcm = np.clip(x * 32767.0, -32768, 32767).astype(np.int16)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def test_iter_audio_files_finds_wav(tmp_path: Path):
    _write_tone_wav(tmp_path / "a.wav")
    _write_tone_wav(tmp_path / "sub" / "b.WAV")
    (tmp_path / "ignore.txt").write_text("x")
    found = iter_audio_files(tmp_path)
    assert len(found) == 2


def test_build_manifest_splits_and_caps(tmp_path: Path):
    pack = tmp_path / "minecraft_legends_units"
    for i in range(12):
        _write_tone_wav(pack / f"u{i}.wav", hz=200 + i)
    tags = tmp_path / "tags" / "jump"
    for i in range(5):
        _write_tone_wav(tags / f"j{i}.wav", hz=300 + i)

    out = tmp_path / "manifest.json"
    build_manifest(
        [tmp_path],
        out_json=out,
        seed=0,
        holdout_frac=0.25,
        caps={"minecraft_legends_units": 4},
    )
    rows = json.loads(out.read_text())
    packs = {r["pack"] for r in rows}
    assert "minecraft_legends_units" in packs
    mc = [r for r in rows if r["pack"] == "minecraft_legends_units"]
    assert len(mc) == 4
    assert any(r["split"] == "train" for r in rows)
    assert any(r["split"] == "holdout" for r in rows)


def test_dataset_yields_features_shape(tmp_path: Path):
    d = tmp_path / "tags" / "hit"
    _write_tone_wav(d / "a.wav")
    _write_tone_wav(d / "b.wav")
    out = tmp_path / "m.json"
    build_manifest([tmp_path / "tags"], out_json=out, seed=1, holdout_frac=0.5, caps={})
    rows = json.loads(out.read_text())
    # Force both splits present for dataset construction
    rows[0]["split"] = "train"
    rows[1]["split"] = "holdout"
    ds = RealAudioFeatureDataset(rows, split="train")
    item = ds[0]
    assert item["features"].shape == (N_CHANNELS, N_FRAMES)
    assert item["log_duration"].ndim == 0
    assert torch.isfinite(item["features"]).all()


def test_build_manifest_excludes_roots(tmp_path: Path):
    keep = tmp_path / "keep"
    drop = tmp_path / "targets"
    _write_tone_wav(keep / "a.wav")
    _write_tone_wav(drop / "b.wav")
    out = tmp_path / "m.json"
    build_manifest(
        [tmp_path],
        out_json=out,
        exclude_roots=[drop],
        caps={},
    )
    rows = json.loads(out.read_text())
    paths = [r["path"] for r in rows]
    assert any("keep" in p for p in paths)
    assert not any("/targets/" in p or p.endswith("/targets/b.wav") for p in paths)
