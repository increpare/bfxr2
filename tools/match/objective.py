"""Matching objective: perceptual contour features + a low-weight
multi-scale log-mel term.

The score is dominated by explicit per-frame contours — volume envelope,
pitch (with voiced/noise classification), pitch slope, spectral
centroid/flatness — because a raw spectrogram distance cannot rank
structural errors (a rising and a falling sweep are equally far from a
rising target in mel space). The blurred mel term stays as a detail
tiebreaker. Loudness is normalized away (peak). Optional relaxations:
  allow_pitch_shift  — pitch contour compared up to a global transposition;
                       mel term min'd over mel-bin shifts
  allow_time_stretch — mel term min'd over uniform stretch factors
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torchaudio

from .audio import SAMPLE_RATE, normalize_peak
from .features import (
    FeatureExtractor,
    Features,
    FeatureWeights,
    feature_distance,
    frame_count,
)

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


@dataclass
class CandidateCache:
    """Per-candidate mels + contour features, reusable across targets."""
    lengths: list[int]
    mels: list[list[torch.Tensor]]  # [i][scale] -> (n_mels, T_i)
    features: list[Features]


def _mel_bank() -> tuple[list, list[torch.Tensor]]:
    transforms = [
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
    blurs = [
        _blur_matrix(n_mels, MEL_BLUR_SIGMA * n_mels / 128)
        for _, _, n_mels in SCALES
    ]
    return transforms, blurs


class MatchObjective:
    def __init__(
        self,
        target: np.ndarray,
        allow_pitch_shift: bool = False,
        allow_time_stretch: bool = False,
        weights: FeatureWeights | None = None,
    ):
        self.allow_pitch_shift = allow_pitch_shift
        self.allow_time_stretch = allow_time_stretch
        self.weights = weights or FeatureWeights()
        self.extractor = FeatureExtractor()
        self.transforms, self.blurs = _mel_bank()
        target = normalize_peak(np.asarray(target, dtype=np.float32))
        self.target_len = max(len(target), MIN_WAVE_LEN)
        self.target_mels = []
        with torch.no_grad():
            wave = torch.zeros(1, self.target_len + TAIL_PAD)
            wave[0, : len(target)] = torch.from_numpy(target)
            for (_, hop, _), t, blur in zip(SCALES, self.transforms, self.blurs):
                mel = blur @ torch.log(t(wave)[0] + LOG_EPS)
                self.target_mels.append(mel[:, : self.target_len // hop + 1])
            self.target_features = self.extractor.extract(wave).slice(
                0, frame_count(self.target_len)
            )

    @staticmethod
    def precompute_candidates(
        waves: list[np.ndarray], chunk: int = 64
    ) -> CandidateCache:
        """Analyze library waves once; reuse via score_candidates()."""
        extractor = FeatureExtractor()
        transforms, blurs = _mel_bank()
        lengths: list[int] = []
        mels: list[list[torch.Tensor]] = []
        features: list[Features] = []
        with torch.no_grad():
            for i in range(0, len(waves), chunk):
                batch_waves = waves[i : i + chunk]
                batch_lengths = [max(len(w), MIN_WAVE_LEN) for w in batch_waves]
                batch_len = max(batch_lengths) + TAIL_PAD
                batch = torch.zeros(len(batch_waves), batch_len)
                for row, w in enumerate(batch_waves):
                    batch[row, : len(w)] = torch.from_numpy(
                        normalize_peak(np.asarray(w, dtype=np.float32)).copy()
                    )
                scale_mels = []
                for scale_idx, ((_, hop, _), transform) in enumerate(
                    zip(SCALES, transforms)
                ):
                    logged = blurs[scale_idx] @ torch.log(transform(batch) + LOG_EPS)
                    scale_mels.append(
                        [
                            logged[row, :, : length // hop + 1].contiguous()
                            for row, length in enumerate(batch_lengths)
                        ]
                    )
                batch_features = extractor.extract(batch)
                for row, length in enumerate(batch_lengths):
                    lengths.append(length)
                    mels.append([scale_mels[s][row] for s in range(len(SCALES))])
                    features.append(batch_features.slice(row, frame_count(length)))
                done = min(i + chunk, len(waves))
                if (i // chunk) % 20 == 0 or done == len(waves):
                    print(f"  current analyze {done}/{len(waves)}", flush=True)
        return CandidateCache(lengths=lengths, mels=mels, features=features)

    def score_candidates(self, cache: CandidateCache) -> np.ndarray:
        """Score precomputed candidates against this target (no re-analysis)."""
        n = len(cache.lengths)
        totals = np.zeros(n, dtype=np.float64)
        for row in range(n):
            mel_total = 0.0
            for scale_idx, (_, _, n_mels) in enumerate(SCALES):
                target_mel = self.target_mels[scale_idx]
                shift_bins = (
                    round(PITCH_SHIFT_BINS * n_mels / 128)
                    if self.allow_pitch_shift else 0
                )
                mel_total += self._pair_distance(
                    cache.mels[row][scale_idx],
                    target_mel,
                    target_mel.shape[1],
                    shift_bins,
                )
            terms = feature_distance(
                self.target_features, cache.features[row], self.weights,
                allow_pitch_shift=self.allow_pitch_shift,
                allow_time_stretch=self.allow_time_stretch,
            )
            terms["mel"] = self.weights.mel * mel_total / len(SCALES) / 3.0
            totals[row] = sum(terms.values())
        return totals

    def score(self, wave: np.ndarray | None) -> float:
        return float(self.score_batch([wave])[0])

    def score_components(self, wave: np.ndarray) -> dict[str, float]:
        """Score one candidate, returning the per-term breakdown."""
        _, components = self._score_valid([wave])
        return components[0]

    def score_batch(self, waves: list[np.ndarray | None]) -> np.ndarray:
        scores = np.full(len(waves), FAILED_SCORE)
        valid_idx = [i for i, w in enumerate(waves)
                     if w is not None and len(w) > 0]
        if not valid_idx:
            return scores
        totals, _ = self._score_valid([waves[i] for i in valid_idx])
        for i, total in zip(valid_idx, totals):
            scores[i] = total
        return scores

    def _score_valid(
        self, waves: list[np.ndarray]
    ) -> tuple[np.ndarray, list[dict[str, float]]]:
        lengths = [max(len(w), MIN_WAVE_LEN) for w in waves]
        batch_len = max(self.target_len, max(lengths)) + TAIL_PAD
        batch = torch.zeros(len(waves), batch_len)
        for row, w in enumerate(waves):
            batch[row, : len(w)] = torch.from_numpy(normalize_peak(w).copy())

        mel_totals = np.zeros(len(waves))
        with torch.no_grad():
            for scale_idx, ((n_fft, hop, n_mels), transform) in enumerate(
                zip(SCALES, self.transforms)
            ):
                mels = self.blurs[scale_idx] @ torch.log(transform(batch) + LOG_EPS)
                target_mel = self.target_mels[scale_idx]
                t_target = target_mel.shape[1]
                shift_bins = (
                    round(PITCH_SHIFT_BINS * n_mels / 128)
                    if self.allow_pitch_shift else 0
                )
                for row, length in enumerate(lengths):
                    t_cand = length // hop + 1
                    cand_mel = mels[row, :, :t_cand]
                    mel_totals[row] += self._pair_distance(
                        cand_mel, target_mel, t_target, shift_bins
                    )
            batch_features = self.extractor.extract(batch)

        totals = np.zeros(len(waves))
        components: list[dict[str, float]] = []
        for row, length in enumerate(lengths):
            cand_features = batch_features.slice(row, frame_count(length))
            terms = feature_distance(
                self.target_features, cand_features, self.weights,
                allow_pitch_shift=self.allow_pitch_shift,
                allow_time_stretch=self.allow_time_stretch,
            )
            # typical mel L1 magnitudes are ~1-3; bring to unit-ish scale
            terms["mel"] = self.weights.mel * mel_totals[row] / len(SCALES) / 3.0
            totals[row] = sum(terms.values())
            components.append(terms)
        return totals, components

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
