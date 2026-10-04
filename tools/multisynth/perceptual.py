"""Waveform-structure-v1: auditory-v1 prefix plus short-window event/texture cues.

The extra blocks are comparisons to a reference, never a generic transient
penalty. Five-millisecond envelope samples precede relative-time pooling;
physical-time autocorrelation and subband modulation retain repetition rate.
Synthetic ordering/seed diagnostics establish behavior, not perceptual validity.
"""
from functools import lru_cache

import numpy as np
from match.audio import SAMPLE_RATE
from . import features

VERSION = 'waveform-structure-v1'
EXTRA_BLOCKS = [('fine_envelope',128), ('absolute_fine_envelope',128),
                ('event_sequence',128), ('attack_shape',16), ('gap_structure',32),
                ('repetition',32), ('subband_envelope',192), ('subband_modulation',96),
                ('cross_band_correlation',15), ('texture_statistics',48)]
DIM = features.DIM + sum(n for _, n in EXTRA_BLOCKS)
HOP = 220
WINDOW = 512


def _resize(rows, count):
    rows = np.atleast_2d(rows)
    return np.asarray([np.interp(np.linspace(0,1,count),np.linspace(0,1,len(row)),row)
                       for row in rows])


def _pool(rows, count):
    # Average rather than select frames so brief events survive downsampling.
    rows = np.atleast_2d(rows)
    if rows.shape[1] <= count:
        return _resize(rows,count)
    edges = np.linspace(0,rows.shape[1],count+1).astype(int)
    sums = np.pad(np.cumsum(rows,axis=1),((0,0),(1,0)))
    return (sums[:,edges[1:]]-sums[:,edges[:-1]])/np.diff(edges)


@lru_cache(maxsize=1)
def _bank():
    hz = np.fft.rfftfreq(WINDOW,1/SAMPLE_RATE)
    edges = [0,250,650,1500,3500,8000,SAMPLE_RATE/2+1]
    return np.asarray([(hz >= a)&(hz < b) for a,b in zip(edges[:-1],edges[1:])],float), np.hanning(WINDOW)


def _extra(wave):
    wave = features.prepare(wave)
    padded = np.pad(wave,(0,WINDOW))
    frames = np.lib.stride_tricks.sliding_window_view(padded,WINDOW)[::HOP]
    env = np.sqrt(np.mean(frames**2,axis=1))
    # Three-frame smoothing suppresses carrier phase and random grain peaks.
    env = np.convolve(np.pad(env,(1,1),mode='edge'),np.ones(3)/3,mode='valid')
    env /= max(env.max(),1e-9)
    times = np.arange(len(env))*HOP/SAMPLE_RATE
    fine = _pool(env,128).ravel()
    absolute = np.interp(np.arange(128)/32,times,env,left=env[0],right=0)
    rise = np.maximum(np.diff(env,prepend=0),0)
    event = _pool(rise,128).ravel()
    cdf = np.cumsum(env**2); cdf /= max(cdf[-1],1e-9)
    attack = np.r_[np.interp(np.arange(8)*.01,times,env,right=0),
                   [np.searchsorted(cdf,q)/max(1,len(env)-1) for q in np.linspace(.05,.95,8)]]
    gap = _pool((env < .12).astype(float),32).ravel()
    centered = env-env.mean()
    variance = np.mean(centered**2)
    # Fixed physical lags separate rate changes from total-length changes.
    lags = np.maximum(1,np.rint(np.geomspace(.015,.5,32)*SAMPLE_RATE/HOP).astype(int))
    repetition = np.asarray([np.mean(centered[:-lag]*centered[lag:])/(variance+1e-8)
                             if lag < len(env) else 0 for lag in lags])
    bank,window = _bank()
    power = np.abs(np.fft.rfft(frames*window,axis=1))**2
    bands = np.sqrt(bank @ power.T)
    # Normalize global level, retaining relative band strengths; local smoothing
    # and coarse pooling make these statistics tolerant of noise realization.
    bands = (np.pad(bands,((0,0),(1,1)),mode='edge')[:,:-2] + bands +
             np.pad(bands,((0,0),(1,1)),mode='edge')[:,2:])/3
    bands /= max(np.max(bands),1e-9)
    band_env = _pool(bands,32).ravel()
    centered_bands = bands-bands.mean(axis=1,keepdims=True)
    # Modulation energy is pooled into fixed Hz bins, with DC excluded.
    mod = np.abs(np.fft.rfft(centered_bands,axis=1))**2
    hz = np.fft.rfftfreq(bands.shape[1],HOP/SAMPLE_RATE)
    edges = np.r_[0,np.geomspace(2,90,16)]
    modulation = np.asarray([mod[:,(hz > a)&(hz <= b)].sum(axis=1)
                             for a,b in zip(edges[:-1],edges[1:])]).T
    modulation = np.sqrt(modulation/(mod.sum(axis=1,keepdims=True)+1e-9))
    norm = np.sqrt(np.sum(centered_bands**2,axis=1))
    corr = centered_bands @ centered_bands.T / (norm[:,None]*norm[None,:]+1e-9)
    correlation = corr[np.triu_indices(6,1)]
    # Local normalized fluctuations distinguish steady beds and granular bursts.
    residual = np.abs(np.diff(bands,axis=1,prepend=bands[:,:1]))
    texture = _pool(residual,8).ravel()
    return np.concatenate([fine,absolute,event,attack,gap,repetition,band_env,
                           modulation.ravel(),correlation,texture]).astype(np.float32)


def describe(wave):
    result = np.r_[features.describe(wave),_extra(wave)].astype(np.float32)
    if result.shape != (DIM,) or not np.isfinite(result).all():
        raise ValueError('Invalid waveform-structure descriptor')
    return result


def extra_components(target,candidates):
    target = np.asarray(target)
    candidates = np.atleast_2d(np.asarray(candidates))
    if (target.shape != (DIM,) or candidates.ndim != 2 or candidates.shape[1] != DIM
            or not np.isfinite(target).all() or not np.isfinite(candidates).all()):
        raise ValueError('Expected finite waveform-structure descriptors')
    result,offset = {},features.DIM
    for name,length in EXTRA_BLOCKS:
        result[name] = np.mean(np.abs(candidates[:,offset:offset+length]-target[offset:offset+length]),axis=1)
        offset += length
    return result
