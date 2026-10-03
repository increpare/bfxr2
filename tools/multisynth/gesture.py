"""Multi-scale event-shape distance over frozen auditory-v1 frame features.

This deliberately keeps the old feature extractor/library intact. It changes
how temporal structure, timbre and movement are represented and compared.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from .features import BLOCKS, DIM, VERSION as BASE_VERSION

VERSION = 'gesture-v2'
NAMES = ('envelope_shape', 'attack_release', 'pulse_structure', 'spectral_motion',
         'timbre', 'texture', 'pitch_motion', 'pitch_register', 'duration')
PRIOR = np.array([.21, .11, .12, .13, .22, .09, .07, .025, .025])


def _pool(x, frames):
    return x.reshape(*x.shape[:-1], frames, 32//frames).mean(axis=-1)


def representation(descriptors):
    data = np.atleast_2d(descriptors)
    if data.shape[1] != DIM or not np.isfinite(data).all():
        raise ValueError('Gesture distance requires finite auditory-v1 descriptors')
    blocks, offset = {}, 0
    for name, size, _ in BLOCKS:
        blocks[name] = data[:, offset:offset+size]
        offset += size
    env = np.maximum(blocks['envelope'], 0)
    env /= np.maximum(env.max(axis=1, keepdims=True), 1e-8)
    weight = env/(env.sum(axis=1, keepdims=True)+1e-8)
    # Per-frame spectral distribution removes amplitude from the timbre path.
    power = 10**(blocks['spectrum'].reshape(-1,40,32)*4)
    power /= np.maximum(power.sum(axis=1,keepdims=True), 1e-8)
    centroid = (power*np.linspace(0,1,40)[None,:,None]).sum(axis=1)
    center = (centroid*weight).sum(axis=1,keepdims=True)
    coarse = power.reshape(-1,10,4,32).sum(axis=2)
    timbre = (coarse*weight[:,None,:]).sum(axis=2)**.5
    voiced = np.clip(blocks['voicing'], 0, 1)
    vweight = weight*voiced
    pitch = blocks['pitch']
    register = (pitch*vweight).sum(axis=1,keepdims=True)/(vweight.sum(axis=1,keepdims=True)+1e-8)
    motion = (pitch-register)*voiced
    cdf = np.cumsum(weight, axis=1)
    quantiles = np.stack([(cdf >= q).argmax(axis=1)/31 for q in (.1,.5,.9)],axis=1)
    # Positive envelope change and autocorrelation distinguish bursts from beds.
    diff = np.diff(env, axis=1)
    rising = np.maximum(diff,0)
    centered_env = env-env.mean(axis=1,keepdims=True)
    variance = np.mean(centered_env**2,axis=1)+1e-8
    autocorr = np.stack([np.mean(centered_env[:,:-lag]*centered_env[:,lag:],axis=1)/variance
                         for lag in (1,2,4,8)],axis=1)
    peaks = ((env[:,1:-1] > env[:,:-2]+.04) & (env[:,1:-1] >= env[:,2:]) &
             (env[:,1:-1] > .2)).sum(axis=1)/8
    return {
        'envelope_shape': np.concatenate([_pool(env**.6,n) for n in (4,8,16)],axis=1),
        'attack_release': np.column_stack([quantiles, env.argmax(axis=1)/31]),
        'pulse_structure': np.column_stack([rising.sum(axis=1)/4, peaks, autocorr*.5]),
        'spectral_motion': _pool((centroid-center)*env**.3,8)*3,
        'timbre': timbre,
        'texture': np.concatenate([_pool(blocks['noisiness'],4), _pool(voiced,4)],axis=1),
        'pitch_motion': _pool(motion,8)*2,
        'pitch_register': register,
        'duration': blocks['duration']/3,
    }


class GestureMetric:
    names = NAMES
    version = VERSION

    def __init__(self, weights=None):
        self.weights = np.array(PRIOR if weights is None else weights,dtype=float)
        if (self.weights.shape != (len(NAMES),) or not np.isfinite(self.weights).all()
                or np.any(self.weights < 0) or self.weights.sum() <= 0):
            raise ValueError('Gesture weights must be finite, nonnegative and nonempty')
        self.weights /= self.weights.sum()

    def raw_components(self, target, candidates):
        a, b = representation(target), representation(candidates)
        return np.column_stack([np.mean(np.abs(a[k]-b[k]),axis=1) for k in NAMES])

    def distances(self, target, candidates):
        return self.raw_components(target,candidates) @ self.weights

    def components(self, target, candidates):
        values = self.raw_components(target,candidates)*self.weights
        return {key:values[:,i] for i,key in enumerate(NAMES)}

    def save(self, path, training=None):
        payload = {'objectiveVersion': VERSION, 'baseFeatureVersion': BASE_VERSION,
                   'components': list(NAMES), 'weights': self.weights.tolist(),
                   'training': training or {}}
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        Path(path).write_text(json.dumps(payload,indent=2)+'\n')

    @classmethod
    def load(cls,path):
        payload = json.loads(Path(path).read_text())
        if (payload.get('objectiveVersion') != VERSION or payload.get('baseFeatureVersion') != BASE_VERSION
                or payload.get('components') != list(NAMES)):
            raise ValueError('Incompatible gesture model')
        return cls(payload['weights'])


def model_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
