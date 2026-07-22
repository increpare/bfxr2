"""Per-frame perceptual features: volume contour, pitch contour + voicedness,
and timbre contour (spectral centroid/flatness).

These drive the matching objective. A raw spectrogram distance can't rank
"rising sweep" above "falling sweep" against a rising target (both overlap
the target almost nowhere), while contour features make those errors explicit
and smooth.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch

from .audio import SAMPLE_RATE

FRAME = 2048
HOP = 512
# pitch uses shorter frames: a 46ms window smears sweeps into useless
# autocorrelations, 23ms tracks game-sfx chirps fine
PITCH_FRAME = 1024
ACF_N = 2048  # zero-padded FFT size for linear autocorrelation
F0_MIN = 90.0  # PITCH_FRAME needs ~2 periods
F0_MAX = 4000.0
ENV_FLOOR_DB = -80.0
ACTIVE_DB = -60.0  # frames quieter than this (rel. peak) are "silent"
CLARITY_THRESHOLD = 0.55  # autocorrelation peak height for "pitched"

_LAG_MIN = int(SAMPLE_RATE / F0_MAX)
_LAG_MAX = min(int(SAMPLE_RATE / F0_MIN), PITCH_FRAME // 2)


@dataclass
class Features:
    env_db: torch.Tensor    # (B, T) envelope, dB relative to each sound's peak
    f0_log2: torch.Tensor   # (B, T) log2 of f0 in Hz (garbage where unvoiced)
    voiced: torch.Tensor    # (B, T) bool
    active: torch.Tensor    # (B, T) bool, louder than ACTIVE_DB
    centroid_log2: torch.Tensor  # (B, T) log2 spectral centroid Hz
    noisiness: torch.Tensor      # (B, T) in [0,1]: 1 = noise, 0 = tonal

    def slice(self, row: int, t: int) -> "Features":
        return Features(*(getattr(self, f.name)[row : row + 1, :t]
                          for f in self.__dataclass_fields__.values()))


def frame_count(n_samples: int) -> int:
    return max(1, (n_samples - FRAME) // HOP + 1)


class FeatureExtractor:
    def __init__(self):
        self.window = torch.hann_window(FRAME)
        self.pitch_window = torch.hann_window(PITCH_FRAME)
        self.freqs = torch.fft.rfftfreq(FRAME, 1.0 / SAMPLE_RATE)
        # the window's own autocorrelation tapers the signal ACF, biasing
        # peaks ~7% toward shorter lags; divide it out
        wspec = torch.fft.rfft(self.pitch_window, n=ACF_N)
        wacf = torch.fft.irfft(wspec.real**2 + wspec.imag**2, n=ACF_N)
        wacf = wacf[: _LAG_MAX + 2]
        self.acf_norm = (wacf / wacf[0]).clamp(min=1e-3)

    @torch.no_grad()
    def extract(self, batch: torch.Tensor) -> Features:
        """batch: (B, L) float32, L >= FRAME."""
        frames = batch.unfold(1, FRAME, HOP)  # (B, T, FRAME)
        n_t = frames.shape[1]

        energy = (frames**2).mean(dim=2)  # (B, T)
        env_db = 10.0 * torch.log10(energy + 1e-12)
        env_db = (env_db - env_db.amax(dim=1, keepdim=True)).clamp(min=ENV_FLOOR_DB)
        active = env_db > ACTIVE_DB

        spec = torch.fft.rfft(frames * self.window)
        power = spec.real**2 + spec.imag**2  # (B, T, F)

        psum = power.sum(dim=2) + 1e-12
        centroid = (power * self.freqs).sum(dim=2) / psum
        centroid_log2 = torch.log2(centroid.clamp(min=20.0))
        flatness = torch.exp(torch.log(power + 1e-12).mean(dim=2)) / (
            power.mean(dim=2) + 1e-12
        )
        flatness_db = 10.0 * torch.log10(flatness + 1e-12)
        # squash to a noise-vs-tonal axis: raw flatness differences between
        # two tonal sounds (-35 vs -60 dB) are aliasing/harmonic-grid noise,
        # while noise vs tone (-10 vs -40 dB) is the distinction that matters
        noisiness = torch.sigmoid((flatness_db + 20.0) / 5.0)

        f0_log2, clarity = self._track_pitch(batch, n_t)
        voiced = (clarity > CLARITY_THRESHOLD) & active
        return Features(
            env_db=env_db,
            f0_log2=f0_log2,
            voiced=voiced,
            active=active,
            centroid_log2=centroid_log2,
            noisiness=noisiness,
        )

    def _track_pitch(
        self, batch: torch.Tensor, n_t: int
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Autocorrelation pitch track on short frames, sliced/padded to the
        spectral frame count n_t."""
        frames = batch.unfold(1, PITCH_FRAME, HOP)  # (B, T2, PITCH_FRAME)
        spec = torch.fft.rfft(frames * self.pitch_window, n=ACF_N)
        power = spec.real**2 + spec.imag**2
        acf = torch.fft.irfft(power, n=ACF_N)[..., : _LAG_MAX + 2]
        acf = acf / (acf[..., :1] + 1e-12)
        acf = acf / self.acf_norm  # remove window-taper bias
        seg = acf[..., _LAG_MIN:_LAG_MAX]

        # Octave-error guard: the ACF peaks at the period and all its
        # multiples with similar height. Take the SMALLEST lag that is a
        # LOCAL max within 90% of the global peak — local, because the ACF's
        # near-zero-lag shoulder is high for any signal but is never a peak.
        local_max = (seg[..., 1:-1] > seg[..., :-2]) & (seg[..., 1:-1] >= seg[..., 2:])
        local_max = torch.nn.functional.pad(local_max, (1, 1), value=False)
        max_val = seg.amax(dim=2, keepdim=True)
        near = local_max & (seg >= 0.9 * max_val)
        has_peak = near.any(dim=2)
        best = torch.where(
            has_peak, near.float().argmax(dim=2), seg.argmax(dim=2)
        )
        clarity = seg.gather(2, best.unsqueeze(2)).squeeze(2).clamp(max=1.0)
        lag = best + _LAG_MIN

        # parabolic interpolation around the peak for sub-sample lag
        idx = lag.unsqueeze(2)
        y0 = acf.gather(2, idx - 1).squeeze(2)
        y1 = acf.gather(2, idx).squeeze(2)
        y2 = acf.gather(2, idx + 1).squeeze(2)
        denom = y0 - 2 * y1 + y2
        shift = torch.where(
            denom.abs() > 1e-9, 0.5 * (y0 - y2) / denom, torch.zeros_like(denom)
        ).clamp(-0.5, 0.5)
        f0 = SAMPLE_RATE / (lag.float() + shift)
        f0_log2 = torch.log2(f0.clamp(min=1.0))

        # 3-frame median filter: single-frame tracker glitches (e.g. at pitch
        # jumps) otherwise dominate the slope term
        padded = torch.nn.functional.pad(f0_log2, (1, 1), mode="replicate")
        stacked = torch.stack(
            [padded[:, :-2], padded[:, 1:-1], padded[:, 2:]], dim=2
        )
        f0_log2 = stacked.median(dim=2).values

        # align to spectral frame count
        f0_log2 = _fit_frames(f0_log2, n_t)
        clarity = _fit_frames(clarity, n_t)
        return f0_log2, clarity


@dataclass
class FeatureWeights:
    env: float = 1.0
    pitch: float = 1.5
    voiced_mismatch: float = 1.0
    pitch_slope: float = 1.0
    timbre: float = 1.0
    mel: float = 0.35


def _fit_frames(x: torch.Tensor, t: int) -> torch.Tensor:
    """Slice or replicate-pad along dim 1 to exactly t frames."""
    if x.shape[1] >= t:
        return x[:, :t]
    return torch.nn.functional.pad(x, (0, t - x.shape[1]), mode="replicate")


def _resample(x: torch.Tensor, t: int, is_mask: bool = False) -> torch.Tensor:
    if is_mask:
        out = torch.nn.functional.interpolate(
            x.float().unsqueeze(1), size=t, mode="nearest")
        return out.squeeze(1) > 0.5
    return torch.nn.functional.interpolate(
        x.unsqueeze(1), size=t, mode="linear", align_corners=False
    ).squeeze(1)


def stretch_to(f: Features, t: int) -> Features:
    """Uniformly time-stretch feature tracks to t frames."""
    return Features(
        env_db=_resample(f.env_db, t),
        f0_log2=_resample(f.f0_log2, t),
        voiced=_resample(f.voiced, t, is_mask=True),
        active=_resample(f.active, t, is_mask=True),
        centroid_log2=_resample(f.centroid_log2, t),
        noisiness=_resample(f.noisiness, t),
    )


def feature_distance(
    a: Features,
    b: Features,
    w: FeatureWeights,
    allow_pitch_shift: bool = False,
    allow_time_stretch: bool = False,
) -> dict[str, float]:
    """Distance components between two single-row Features (shape (1, T))."""
    if allow_time_stretch and b.env_db.shape[1] != a.env_db.shape[1]:
        b = stretch_to(b, a.env_db.shape[1])
    ta, tb = a.env_db.shape[1], b.env_db.shape[1]
    t = max(ta, tb)

    def pad(x: torch.Tensor, value: float) -> torch.Tensor:
        return torch.nn.functional.pad(x, (0, t - x.shape[1]), value=value)

    env_a, env_b = pad(a.env_db, ENV_FLOOR_DB), pad(b.env_db, ENV_FLOOR_DB)
    env_term = float((env_a - env_b).abs().mean()) / 20.0

    voiced_a, voiced_b = pad(a.voiced.float(), 0), pad(b.voiced.float(), 0)
    active_either = (pad(a.active.float(), 0) + pad(b.active.float(), 0)) > 0
    n_either = int(active_either.sum())
    if n_either > 0:
        voiced_mm = float(
            ((voiced_a - voiced_b).abs() * active_either).sum()
        ) / n_either
    else:
        voiced_mm = 0.0

    f0_a, f0_b = pad(a.f0_log2, 0), pad(b.f0_log2, 0)
    both_voiced = (voiced_a * voiced_b) > 0
    n_both = int(both_voiced.sum())
    pitch_term = 0.0
    slope_term = 0.0
    if n_both > 0:
        diff = f0_a - f0_b  # octaves
        if allow_pitch_shift:
            diff = diff - diff[both_voiced].median()
        pitch_term = float((diff.abs() * both_voiced).sum()) / n_both

        # frame-to-frame pitch slope: distinguishes glides from jumps and
        # rising from falling
        da, db = f0_a[:, 1:] - f0_a[:, :-1], f0_b[:, 1:] - f0_b[:, :-1]
        both2 = both_voiced[:, 1:] & both_voiced[:, :-1]
        n2 = int(both2.sum())
        if n2 > 0:
            # zero deltas across unvoiced boundaries, then smooth over 3
            # frames: a pitch jump landing one frame off must cost less
            # than omitting the jump entirely
            da = torch.nn.functional.avg_pool1d(
                (da * both2).unsqueeze(1), 3, stride=1, padding=1
            ).squeeze(1)
            db = torch.nn.functional.avg_pool1d(
                (db * both2).unsqueeze(1), 3, stride=1, padding=1
            ).squeeze(1)
            slope_diff = (da - db).abs().clamp(max=0.5)
            slope_term = float(slope_diff.sum()) / n2 * 8.0

    cen_a, cen_b = pad(a.centroid_log2, 0), pad(b.centroid_log2, 0)
    ns_a, ns_b = pad(a.noisiness, 0), pad(b.noisiness, 0)
    both_active = (pad(a.active.float(), 0) * pad(b.active.float(), 0)) > 0
    n_act = int(both_active.sum())
    timbre_term = 0.0
    if n_act > 0:
        timbre_term = (
            float(((cen_a - cen_b).abs() * both_active).sum()) / n_act / 2.0
            + float(((ns_a - ns_b).abs() * both_active).sum()) / n_act
        )

    return {
        "env": w.env * env_term,
        "pitch": w.pitch * pitch_term,
        "voiced_mismatch": w.voiced_mismatch * voiced_mm,
        "pitch_slope": w.pitch_slope * slope_term,
        "timbre": w.timbre * timbre_term,
    }
