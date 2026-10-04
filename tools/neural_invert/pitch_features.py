"""Pitch-only replacement for the frozen full-sound descriptor.

Native-rate, window-corrected autocorrelation supports roughly 55–8000 Hz.
The spectral, amplitude and scalar evidence is copied from the frozen module.
"""
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np

from . import features as frozen

VERSION = 'neural-pitch-v4'
DIM = frozen.DIM
SAMPLE_RATE = frozen.SAMPLE_RATE
FFT = 2048
OVERSAMPLE = 4
MIN_HZ = 55.
MAX_HZ = 8000.
MIN_VOICE = .6
PEAK_RATIO = .9
FROZEN_FEATURE_CODE_HASH = frozen.FEATURE_CODE_HASH
CONFIG = {'version': VERSION, 'sampleRate': SAMPLE_RATE, 'fft': FFT,
          'autocorrelationOversample': OVERSAMPLE,
          'minHz': MIN_HZ, 'maxHz': MAX_HZ, 'minVoice': MIN_VOICE,
          'lowFrequencyLagGuard': 3,
          'dcRemoval': 'hann-weighted-frame-mean',
          'peakRatio': PEAK_RATIO, 'window': 'hann-autocorrelation-corrected',
          'relative': frozen.RELATIVE, 'absolute': frozen.ABSOLUTE,
          'absoluteSeconds': frozen.ABS_SECONDS, 'maxAnalysisFrames': 512,
          'frozenFeatureHash': frozen.FEATURE_HASH,
          'frozenFeatureCodeHash': FROZEN_FEATURE_CODE_HASH}
FEATURE_CODE_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FEATURE_HASH = hashlib.sha256(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()


def _audio(wave):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Audio must be finite nonempty mono')
    return wave


@lru_cache(maxsize=1)
def _window():
    window = np.hanning(FFT)
    ac = _autocorrelation(window)
    return window, ac/ac[0]


def _autocorrelation(frames):
    """Band-limited interpolation of linear ACF, including Nyquist splitting."""
    power = np.abs(np.fft.rfft(frames, n=2*FFT, axis=-1))**2
    # In the longer transform the old Nyquist bin has distinct positive and
    # negative partners. Each must contain half the original coefficient.
    power[..., -1] *= .5
    return np.fft.irfft(power, n=2*FFT*OVERSAMPLE, axis=-1)*OVERSAMPLE


def _contours(wave):
    peak = float(np.max(np.abs(wave)))
    if peak < 1e-8:
        return np.array([0.]), np.zeros((2, 1)), len(wave)/SAMPLE_RATE
    active = np.flatnonzero(np.abs(wave) > peak*1e-4)
    wave = wave[active[0]:active[-1]+1]/peak
    duration = len(wave)/SAMPLE_RATE
    # Match the frozen descriptor's downsampled frame times exactly, including
    # its capped frame schedule, while keeping the audio at its native rate.
    down_length = (len(wave)+1)//2
    starts = np.arange(0, down_length, 256)
    if len(starts) > 512:
        starts = np.unique(np.linspace(0, down_length-1, 512).astype(int))
    padded = np.pad(wave, (FFT//2, FFT//2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, FFT)[starts*2]
    window, window_ac = _window()
    centered = frames-(frames @ window/window.sum())[:, None]
    ac = _autocorrelation(centered*window)
    # Extra neighbours allow true local-maximum tests at BOTH range endpoints.
    # A three-sample low-frequency guard accommodates the phase-dependent peak
    # shift of harmonic tones when only 2.5 periods fit in the window.
    lags = np.arange(int(np.floor(SAMPLE_RATE/MAX_HZ*OVERSAMPLE)),
                     int(np.ceil(SAMPLE_RATE/MIN_HZ*OVERSAMPLE))+3*OVERSAMPLE+1)
    corr = ac[:, lags[0]-1:lags[-1]+2]/np.maximum(ac[:, :1], 1e-12)
    corr /= window_ac[lags[0]-1:lags[-1]+2]
    left, middle, right = corr[:, :-2], corr[:, 1:-1], corr[:, 2:]
    maxima = (middle > left) & (middle >= right)
    curvature = left-2*middle+right
    offset = np.divide(.5*(left-right), curvature, out=np.zeros_like(middle),
                       where=maxima & (curvature < -1e-12))
    offset = np.clip(offset, -.5, .5)
    height = middle-.25*(left-right)*offset
    # Compare interpolated peak heights; raw integer-lag peaks penalize high
    # pitches whose true periods fall halfway between samples.
    eligible = np.where(maxima, height, -np.inf)
    best = eligible.max(axis=1, keepdims=True)
    strong = maxima & (height >= MIN_VOICE) & (height >= PEAK_RATIO*best)
    voiced = strong.any(axis=1)
    chosen = strong.argmax(axis=1)
    row = np.arange(len(frames))
    hz = SAMPLE_RATE*OVERSAMPLE/(lags[chosen]+offset[row, chosen])
    voice = np.where(voiced, np.clip(height[row, chosen], 0., 1.), 0.)
    pitch = np.where(voiced, np.log2(hz/55.)/7., 0.)
    return starts/frozen.RATE, np.stack([pitch, voice]), duration


def pitch_track(wave, positions):
    """Return (Hz, confidence) at seconds relative to the trimmed active sound.

    Unvoiced frames and positions after the final analysis frame return zero.
    Interpolation uses the descriptor's logarithmic pitch encoding. As in the
    frozen descriptor, transitions between voiced/unvoiced frames are linearly
    interpolated, so diagnostic accuracy should be assessed inside voiced spans.
    """
    wave = _audio(wave)
    positions = np.asarray(positions, dtype=np.float64)
    if positions.ndim != 1 or not np.isfinite(positions).all():
        raise ValueError('Positions must be finite one-dimensional seconds')
    times, contours, _ = _contours(wave)
    pitch, voice = frozen._sample(contours, times, positions, 0.)
    hz = np.where(voice > 0, 55.*np.exp2(7.*pitch), 0.).astype(np.float32)
    return hz, voice


def describe(wave):
    """Return 4083 float32 values, replacing only pitch and voicing evidence."""
    wave = _audio(wave)
    result = frozen.describe(wave)
    times, contours, duration = _contours(wave)
    result[3888:3984] = frozen._sample(
        contours, times, np.linspace(0, duration, frozen.RELATIVE), 0.).ravel()
    result[4016:4080] = frozen._sample(
        contours, times, np.linspace(0, frozen.ABS_SECONDS, frozen.ABSOLUTE), 0.).ravel()
    return result
