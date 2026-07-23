from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import torch

from match.audio import SAMPLE_RATE, normalize_peak, trim_silence
from match.features import FeatureExtractor, stretch_to, frame_count
from match.objective import (
    LOG_EPS,
    MIN_WAVE_LEN,
    SCALES,
    TAIL_PAD,
    _blur_matrix,
    MEL_BLUR_SIGMA,
)
import torchaudio

from .constants import (
    CHANNEL_MEAN,
    CHANNEL_STD,
    FEATURES_MEL_SCALE_IDX,
    N_CHANNELS,
    N_FRAMES,
    N_MELS,
)


_extractor: FeatureExtractor | None = None
_mel_transform = None
_mel_blur: torch.Tensor | None = None
_channel_mean: torch.Tensor | None = None
_channel_std: torch.Tensor | None = None


def _ensure_backends():
    global _extractor, _mel_transform, _mel_blur, _channel_mean, _channel_std
    if _extractor is None:
        _extractor = FeatureExtractor()
        n_fft, hop, n_mels = SCALES[FEATURES_MEL_SCALE_IDX]
        assert n_mels == N_MELS
        _mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            hop_length=hop,
            n_mels=n_mels,
            f_min=30.0,
            f_max=18000.0,
            power=2.0,
        )
        _mel_blur = _blur_matrix(n_mels, MEL_BLUR_SIGMA * n_mels / 128)
        assert len(CHANNEL_MEAN) == N_CHANNELS and len(CHANNEL_STD) == N_CHANNELS
        _channel_mean = torch.tensor(CHANNEL_MEAN, dtype=torch.float32).view(N_CHANNELS, 1)
        _channel_std = torch.tensor(CHANNEL_STD, dtype=torch.float32).view(N_CHANNELS, 1)


def normalize_channels(
    x: torch.Tensor,
    mean: Sequence[float] | None = None,
    std: Sequence[float] | None = None,
) -> torch.Tensor:
    """Z-score each input channel. x: (..., C, T) float32.

    Pass checkpoint-stored mean/std at inference so old models stay aligned
    if constants.py is re-estimated later. Defaults to CHANNEL_MEAN/STD.
    """
    _ensure_backends()
    if mean is None or std is None:
        assert _channel_mean is not None and _channel_std is not None
        mean_t = _channel_mean
        std_t = _channel_std
    else:
        if len(mean) != N_CHANNELS or len(std) != N_CHANNELS:
            raise ValueError(
                f"channel mean/std must have length {N_CHANNELS}, "
                f"got {len(mean)}/{len(std)}"
            )
        mean_t = torch.as_tensor(mean, dtype=torch.float32).view(N_CHANNELS, 1)
        std_t = torch.as_tensor(std, dtype=torch.float32).view(N_CHANNELS, 1)
    mean_t = mean_t.to(device=x.device, dtype=x.dtype)
    std_t = std_t.to(device=x.device, dtype=x.dtype)
    while mean_t.ndim < x.ndim:
        mean_t = mean_t.unsqueeze(0)
        std_t = std_t.unsqueeze(0)
    return (x - mean_t) / std_t


@torch.no_grad()
def pack_features(wave: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (channels, N_FRAMES) float32 + scalar log_duration.

    Silence-trims like prepare_target so train/inference duration contours match.
    """
    _ensure_backends()
    assert _extractor is not None and _mel_transform is not None and _mel_blur is not None

    w = normalize_peak(trim_silence(np.asarray(wave, dtype=np.float32)))
    duration_s = max(len(w), 1) / SAMPLE_RATE
    log_duration = float(np.log(duration_s + 1e-4))

    target_len = max(len(w), MIN_WAVE_LEN)
    batch = torch.zeros(1, target_len + TAIL_PAD)
    batch[0, : len(w)] = torch.from_numpy(w)

    feats = _extractor.extract(batch).slice(0, frame_count(target_len))
    feats = stretch_to(feats, N_FRAMES)

    f0 = feats.f0_log2.clone()
    f0 = torch.where(feats.voiced, f0, torch.zeros_like(f0))

    contours = torch.stack(
        [
            feats.env_db,
            f0,
            feats.voiced.float(),
            feats.active.float(),
            feats.centroid_log2,
            feats.noisiness,
        ],
        dim=1,
    )[
        0
    ]  # (6, T)

    n_fft, hop, _ = SCALES[FEATURES_MEL_SCALE_IDX]
    mel = _mel_blur @ torch.log(_mel_transform(batch)[0] + LOG_EPS)
    mel = mel[:, : target_len // hop + 1]  # (64, Tm)
    mel_t = torch.nn.functional.interpolate(
        mel.unsqueeze(0), size=N_FRAMES, mode="linear", align_corners=False
    ).squeeze(0)

    x = torch.cat([contours, mel_t], dim=0).numpy().astype(np.float32)
    return x, log_duration
