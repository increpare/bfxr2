"""Multi-scale log-mel spectrogram distance between a target and candidates.

Strict by default: timing, pitch contour, and duration all count (loudness is
normalized away). Optional relaxations:
  allow_pitch_shift  — min over integer mel-bin shifts of the candidate
  allow_time_stretch — min over uniform time-stretch factors of the candidate
"""
from __future__ import annotations

import numpy as np
import torch
import torchaudio

from .audio import SAMPLE_RATE, normalize_rms

# (n_fft, hop, n_mels)
SCALES = [(2048, 512, 128), (1024, 256, 96), (512, 128, 64), (256, 64, 32)]
LOG_EPS = 1e-5
LOG_FLOOR = float(np.log(LOG_EPS))
STRETCH_FACTORS = [0.75, 0.85, 1.0, 1.18, 1.33]
PITCH_SHIFT_BINS = 8  # on the 128-band scale
FAILED_SCORE = 1e6
# Gaussian blur (in mel bins, on the 128-band scale) applied along the
# frequency axis of both spectrograms. Without it the distance is a needle:
# a tone one mel bin off scores nearly as badly as silence, leaving black-box
# search no slope to descend. ~2 bins ≈ a third of a semitone of tolerance.
MEL_BLUR_SIGMA = 2.0

# reflect-padding in the mel transform needs len > n_fft // 2
MIN_WAVE_LEN = 4096
# every waveform gets this much zero tail before the mel transform, so the
# frames near a sound's end always see zeros — otherwise the transform's
# reflect-padding kicks in only for whichever candidate happens to be the
# longest in its batch, and the same sound scores differently alone vs
# batched
TAIL_PAD = 2048


class MelObjective:
    def __init__(
        self,
        target: np.ndarray,
        allow_pitch_shift: bool = False,
        allow_time_stretch: bool = False,
    ):
        self.allow_pitch_shift = allow_pitch_shift
        self.allow_time_stretch = allow_time_stretch
        self.transforms = [
            torchaudio.transforms.MelSpectrogram(
                sample_rate=SAMPLE_RATE,
                n_fft=n_fft,
                hop_length=hop,
                n_mels=n_mels,
                f_min=30.0,
                f_max=18000.0,
                power=2.0,
            )
            for n_fft, hop, n_mels in SCALES
        ]
        self.blurs = [
            _blur_matrix(n_mels, MEL_BLUR_SIGMA * n_mels / 128)
            for _, _, n_mels in SCALES
        ]
        target = normalize_rms(np.asarray(target, dtype=np.float32))
        self.target_len = max(len(target), MIN_WAVE_LEN)
        self.target_mels = []
        with torch.no_grad():
            wave = torch.zeros(1, self.target_len + TAIL_PAD)
            wave[0, : len(target)] = torch.from_numpy(target)
            for (_, hop, _), t, blur in zip(SCALES, self.transforms, self.blurs):
                mel = blur @ torch.log(t(wave)[0] + LOG_EPS)
                self.target_mels.append(mel[:, : self.target_len // hop + 1])

    def score(self, wave: np.ndarray | None) -> float:
        return float(self.score_batch([wave])[0])

    def score_batch(self, waves: list[np.ndarray | None]) -> np.ndarray:
        scores = np.full(len(waves), FAILED_SCORE)
        valid = [(i, w) for i, w in enumerate(waves) if w is not None and len(w) > 0]
        if not valid:
            return scores

        lengths = [max(len(w), MIN_WAVE_LEN) for _, w in valid]
        batch_len = max(self.target_len, max(lengths)) + TAIL_PAD
        batch = torch.zeros(len(valid), batch_len)
        for row, (_, w) in enumerate(valid):
            batch[row, : len(w)] = torch.from_numpy(normalize_rms(w).copy())

        totals = np.zeros(len(valid))
        with torch.no_grad():
            for scale_idx, ((n_fft, hop, n_mels), transform) in enumerate(
                zip(SCALES, self.transforms)
            ):
                mels = self.blurs[scale_idx] @ torch.log(transform(batch) + LOG_EPS)  # (B, M, T_batch)
                target_mel = self.target_mels[scale_idx]
                t_target = target_mel.shape[1]
                shift_bins = (
                    round(PITCH_SHIFT_BINS * n_mels / 128)
                    if self.allow_pitch_shift else 0
                )
                for row, length in enumerate(lengths):
                    t_cand = length // hop + 1
                    cand_mel = mels[row, :, :t_cand]
                    totals[row] += self._pair_distance(
                        cand_mel, target_mel, t_target, shift_bins
                    )
        for (i, _), total in zip(valid, totals):
            scores[i] = total / len(SCALES)
        return scores

    def _pair_distance(
        self,
        cand_mel: torch.Tensor,  # (M, T_c)
        target_mel: torch.Tensor,  # (M, T_t)
        t_target: int,
        shift_bins: int,
    ) -> float:
        factors = STRETCH_FACTORS if self.allow_time_stretch else [1.0]
        best = None
        for factor in factors:
            if factor == 1.0:
                stretched = cand_mel
            else:
                t_new = max(2, round(cand_mel.shape[1] * factor))
                stretched = torch.nn.functional.interpolate(
                    cand_mel.unsqueeze(0), size=t_new, mode="linear",
                    align_corners=False,
                )[0]
            t_common = max(stretched.shape[1], t_target)
            a = _pad_frames(stretched, t_common)
            b = _pad_frames(target_mel, t_common)
            n = a.shape[0] * t_common
            for k in range(-shift_bins, shift_bins + 1):
                d = float((_shift_mel(a, k) - b).abs().sum()) / n
                if best is None or d < best:
                    best = d
        return best


def _pad_frames(mel: torch.Tensor, t: int) -> torch.Tensor:
    if mel.shape[1] >= t:
        return mel
    return torch.nn.functional.pad(
        mel, (0, t - mel.shape[1]), value=LOG_FLOOR
    )


def _blur_matrix(n_mels: int, sigma: float) -> torch.Tensor:
    """Row-normalized Gaussian smoothing matrix along the mel axis."""
    sigma = max(sigma, 0.5)
    idx = torch.arange(n_mels, dtype=torch.float32)
    kernel = torch.exp(-((idx[None, :] - idx[:, None]) ** 2) / (2 * sigma**2))
    return kernel / kernel.sum(dim=1, keepdim=True)


def _shift_mel(mel: torch.Tensor, k: int) -> torch.Tensor:
    """Shift along the mel axis, filling with the log floor."""
    if k == 0:
        return mel
    shifted = torch.full_like(mel, LOG_FLOOR)
    if k > 0:
        shifted[k:] = mel[:-k]
    else:
        shifted[:k] = mel[-k:]
    return shifted
