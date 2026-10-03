"""Compact auditory descriptors. Heuristic similarity, not a human preference model.

Compare spectral evolution on relative time and envelopes on both relative and
absolute time. This tolerates small timing differences without erasing duration,
attack or event order. Noise phase and overall playback gain are irrelevant.
"""
from functools import lru_cache

import numpy as np
import torch
from match.audio import SAMPLE_RATE
from match.features import FeatureExtractor

VERSION = 'auditory-v1'
FRAMES = 32
BANDS = 40
# Each block contributes its mean absolute error times this weight.
BLOCKS = [('spectrum', BANDS*FRAMES, 3.0), ('envelope', FRAMES, .7),
          ('absolute_envelope', 64, .7), ('pitch', FRAMES, .65),
          ('voicing', FRAMES, .45), ('noisiness', FRAMES, .5),
          ('duration', 1, .35), ('motion', 2, .2)]
DIM = sum(n for _, n, _ in BLOCKS)


def prepare(wave):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Audio must be a nonempty finite mono array')
    peak = float(np.max(np.abs(wave)))
    if peak < 1e-7:
        raise ValueError('Silent audio')
    wave = wave / peak
    # Sample-level onset alignment avoids the old frame-grid sensitivity.
    active = np.flatnonzero(np.abs(wave) > .001)
    return wave[active[0]:active[-1]+1].copy()


def _resize(values, count=FRAMES):
    values = np.atleast_2d(values)
    return np.array([np.interp(np.linspace(0, 1, count),
                             np.linspace(0, 1, len(row)), row) for row in values])


@lru_cache(maxsize=1)
def _backends():
    n = 2048
    hz = np.fft.rfftfreq(n, 1/SAMPLE_RATE)
    mel = lambda f: 2595*np.log10(1+f/700)
    edges = 700*(10**(np.linspace(mel(30), mel(18000), BANDS+2)/2595)-1)
    bank = np.maximum(0, np.minimum((hz[None]-edges[:-2,None])/(edges[1:-1]-edges[:-2])[:,None],
                                   (edges[2:,None]-hz[None])/(edges[2:]-edges[1:-1])[:,None]))
    bank /= np.maximum(bank.sum(axis=1, keepdims=True), 1e-9)
    return bank, np.hanning(n), FeatureExtractor()


def describe(wave):
    wave = prepare(wave)
    duration = len(wave)/SAMPLE_RATE
    bank, window, extractor = _backends()
    padded = np.pad(wave, (0, max(2048-len(wave), 0)+2048))
    frames = np.lib.stride_tricks.sliding_window_view(padded, 2048)[::512]
    # Include a final zero-tail window so short transients retain their decay.
    power = np.abs(np.fft.rfft(frames*window, axis=1))**2
    mel = bank @ power.T
    mel_db = 10*np.log10(np.maximum(mel, 1e-12))
    mel_db = np.clip((mel_db-mel_db.max())/60, -1, 0)
    env = np.sqrt(np.mean(frames**2, axis=1))
    env = env/max(env.max(), 1e-9)
    absolute = np.interp(np.arange(64)*.0625, np.arange(len(env))*512/SAMPLE_RATE,
                         env, left=env[0], right=0)
    with torch.no_grad():
        f = extractor.extract(torch.from_numpy(padded[None]))
    voiced = f.voiced.numpy()[0].astype(float)
    pitch = (f.f0_log2.numpy()[0]-np.log2(90))/6 * voiced
    noise = f.noisiness.numpy()[0]
    result = np.concatenate([
        _resize(mel_db).ravel(), _resize(env).ravel(), absolute,
        _resize(pitch).ravel(), _resize(voiced).ravel(), _resize(noise).ravel(),
        [np.log2(max(.01, duration))],
        [np.abs(np.diff(env)).mean() if len(env)>1 else 0,
         np.abs(np.diff(mel_db, axis=1)).mean() if mel_db.shape[1]>1 else 0],
    ]).astype(np.float32)
    if result.shape != (DIM,) or not np.isfinite(result).all():
        raise ValueError('Invalid descriptor')
    return result


def components(target, candidates):
    candidates = np.atleast_2d(candidates)
    offset, result = 0, {}
    for name, length, weight in BLOCKS:
        result[name] = np.mean(np.abs(candidates[:, offset:offset+length]-target[offset:offset+length]), axis=1)*weight
        offset += length
    return result


def distances(target, candidates):
    return sum(components(target, candidates).values())
