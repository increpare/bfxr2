"""Target/candidate audio preprocessing."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio

SAMPLE_RATE = 44100
TARGET_RMS = 0.1
SILENCE_DB = -60.0
FRAME_MS = 10


def load_audio(path: Path | str) -> np.ndarray:
    """Load any soundfile-readable file as float32 mono at 44100 Hz."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if sr != SAMPLE_RATE:
        wave = torch.from_numpy(mono).unsqueeze(0)
        mono = torchaudio.functional.resample(wave, sr, SAMPLE_RATE).squeeze(0).numpy()
    return mono.astype(np.float32)


def trim_silence(x: np.ndarray, threshold_db: float = SILENCE_DB) -> np.ndarray:
    """Trim leading/trailing frames below threshold (relative to peak),
    keeping one frame of padding on each side."""
    peak = np.abs(x).max()
    if peak == 0:
        return x
    frame = int(SAMPLE_RATE * FRAME_MS / 1000)
    n_frames = int(np.ceil(len(x) / frame))
    padded = np.zeros(n_frames * frame, dtype=x.dtype)
    padded[: len(x)] = x
    rms = np.sqrt((padded.reshape(n_frames, frame) ** 2).mean(axis=1))
    threshold = peak * 10 ** (threshold_db / 20)
    loud = np.flatnonzero(rms > threshold)
    if len(loud) == 0:
        return x
    start = max(0, (loud[0] - 1) * frame)
    end = min(len(x), (loud[-1] + 2) * frame)
    return x[start:end]


def normalize_peak(x: np.ndarray, target_peak: float = 0.5) -> np.ndarray:
    """Peak normalization. RMS normalization is wrong for one-shot sfx: a
    long quiet reverb tail drags RMS down and inflates the attack."""
    peak = np.abs(x).max()
    if peak < 1e-8:
        return x
    return (x * (target_peak / peak)).astype(np.float32)


def prepare_target(path: Path | str) -> np.ndarray:
    return normalize_peak(trim_silence(load_audio(path)))
