from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import torch
import torchaudio

from match.audio import SAMPLE_RATE, normalize_peak, trim_silence
from match.features import ENV_FLOOR_DB, FeatureExtractor, frame_count
from match.objective import LOG_EPS, LOG_FLOOR, SCALES, TAIL_PAD

from .constants import (
    CHANNEL_MEAN,
    CHANNEL_STD,
    FEATURES_MEL_SCALE_IDX,
    INVERT_CONTOUR_FRAME,
    INVERT_CONTOUR_HOP,
    N_CHANNELS,
    N_FRAMES,
    N_MELS,
)


_extractor: FeatureExtractor | None = None
_mel_transform = None
_channel_mean: torch.Tensor | None = None
_channel_std: torch.Tensor | None = None


def _ensure_backends():
    global _extractor, _mel_transform, _channel_mean, _channel_std
    if _extractor is None:
        # Invert-local finer hop; matcher keeps its own default extractor.
        _extractor = FeatureExtractor(frame=INVERT_CONTOUR_FRAME, hop=INVERT_CONTOUR_HOP)
        n_fft, hop, n_mels = SCALES[FEATURES_MEL_SCALE_IDX]
        assert n_mels == N_MELS
        assert hop == INVERT_CONTOUR_HOP, "contour hop must match mel hop for alignment"
        _mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=SAMPLE_RATE,
            n_fft=n_fft,
            hop_length=hop,
            n_mels=n_mels,
            f_min=30.0,
            f_max=18000.0,
            power=2.0,
        )
        # No mel blur for invert (matcher still blurs in its objective).
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


def _pad_or_crop_1d(x: torch.Tensor, t: int, pad_value: float) -> torch.Tensor:
    """x: (C, T_native) → (C, t). Crop onset-preserving; right-pad if short."""
    assert x.ndim == 2
    c, tn = x.shape
    if tn >= t:
        return x[:, :t]
    out = torch.full((c, t), pad_value, dtype=x.dtype)
    out[:, :tn] = x
    return out


@torch.no_grad()
def pack_features(wave: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (channels, N_FRAMES) float32 + scalar log_duration.

    v4: finer hop, pad/crop (no stretch-up), t_abs replaces active, no mel blur.
    Silence-trims like prepare_target so train/inference duration contours match.
    """
    _ensure_backends()
    assert _extractor is not None and _mel_transform is not None

    w = normalize_peak(trim_silence(np.asarray(wave, dtype=np.float32)))
    duration_s = max(len(w), 1) / SAMPLE_RATE
    log_duration = float(np.log(duration_s + 1e-4))

    # Only pad to one contour frame — do NOT use matcher MIN_WAVE_LEN (4096),
    # which would invent silent "real" frames with nonzero t_abs.
    target_len = max(len(w), INVERT_CONTOUR_FRAME)
    batch = torch.zeros(1, target_len + TAIL_PAD)
    batch[0, : len(w)] = torch.from_numpy(w)

    if len(w) >= INVERT_CONTOUR_FRAME:
        n_native = frame_count(len(w), frame=INVERT_CONTOUR_FRAME, hop=INVERT_CONTOUR_HOP)
    else:
        n_native = 1
    feats = _extractor.extract(batch).slice(0, n_native)

    f0 = feats.f0_log2.clone()
    f0 = torch.where(feats.voiced, f0, torch.zeros_like(f0))

    # Absolute time in seconds for real frames (0 on pad after pad_or_crop).
    t_abs = torch.arange(n_native, dtype=torch.float32) * (INVERT_CONTOUR_HOP / SAMPLE_RATE)
    t_abs = t_abs.unsqueeze(0)  # (1, T)

    contours = torch.stack(
        [
            feats.env_db,
            f0,
            feats.voiced.float(),
            t_abs,
            feats.centroid_log2,
            feats.noisiness,
        ],
        dim=1,
    )[0]  # (6, T)

    hop = SCALES[FEATURES_MEL_SCALE_IDX][1]
    mel = torch.log(_mel_transform(batch)[0] + LOG_EPS)  # (64, Tm) — unblurred

    # Align mel length to contour length (same hop) then pad/crop together.
    t_c = contours.shape[1]
    if mel.shape[1] > t_c:
        mel = mel[:, :t_c]
    elif mel.shape[1] < t_c:
        mel = torch.nn.functional.pad(mel, (0, t_c - mel.shape[1]), value=LOG_FLOOR)

    n_keep = min(t_c, N_FRAMES)
    contours = _pad_or_crop_1d(contours, N_FRAMES, pad_value=0.0)
    # env pad should be floor, not 0
    if n_keep < N_FRAMES:
        contours[0, n_keep:] = ENV_FLOOR_DB
    mel = _pad_or_crop_1d(mel, N_FRAMES, pad_value=LOG_FLOOR)

    x = torch.cat([contours, mel], dim=0).numpy().astype(np.float32)
    return x, log_duration
