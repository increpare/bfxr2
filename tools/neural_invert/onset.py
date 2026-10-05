"""Fine onset evidence alongside frozen whole-sound descriptors.

An experimental input ablation. Parameter accuracy is not perceptual adequacy.
"""
from functools import lru_cache

import numpy as np
import torch
import torchaudio

FEATURE_POLICY = {'version': 'onset-mel-v1', 'rate': 44100, 'fft': 512,
                  'hop': 128, 'frames': 128, 'bands': 64, 'fmin': 30.,
                  'fmax': 18000., 'floorDb': -72., 'trim': 'peak-relative-1e-4',
                  'padding': 'zero', 'melScale': 'htk', 'normalization': 'onset-maximum'}


@lru_cache(maxsize=1)
def _mel():
    return torchaudio.transforms.MelSpectrogram(
        sample_rate=44100, n_fft=512, hop_length=128, n_mels=64,
        f_min=30., f_max=18000., power=2., center=True, pad_mode='constant')


def onset_features(wave):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Audio must be finite nonempty mono')
    peak = float(np.max(np.abs(wave)))
    if peak < 1e-8:
        return np.full((64, 128), -1., np.float32)
    active = np.flatnonzero(np.abs(wave) > peak*1e-4)
    wave = wave[active[0]:active[-1]+1]/peak
    # Keep sufficient right context for the last centred frame, never rescale time.
    size = 127*128+256
    padded = np.zeros(size, np.float32)
    padded[:min(size, len(wave))] = wave[:size]
    with torch.no_grad():
        power = _mel()(torch.from_numpy(padded))[:, :128]
        power = power.clamp_min(1e-20)
        db = 10*power.log10()
        return ((db-db.max())/72).clamp(-1, 0).numpy().astype(np.float32)
