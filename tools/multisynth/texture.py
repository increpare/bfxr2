"""Experimental auditory-envelope texture statistics, not a perceptual standard.

Motivated by McDermott & Simoncelli (2011). This compact implementation is not
their validated model; ordered event/pitch representations remain necessary.
"""
from functools import lru_cache
import numpy as np
from .features import prepare

VERSION='erb-envelope-texture-v1'
RATE=44100
BANDS=24
HOP=100
PAD=2048
COMPRESSION=.3
ERB_EDGES=np.linspace(21.4*np.log10(1+.00437*50),21.4*np.log10(1+.00437*18000),BANDS+2)
BAND_CENTERS=(10**(ERB_EDGES[1:-1]/21.4)-1)/.00437
MOD_EDGES=np.array([0.,2.,4.,8.,16.,32.,64.,128.,RATE/HOP/2])
NAMES=('spectrum','variation','skew','kurtosis','correlation','modulation')
SIZES=(24,24,24,24,276,192)
CONFIG=dict(version=VERSION,bands=BANDS,rate=RATE,hop=HOP,pad=PAD,compression=COMPRESSION,
            bandCenters=BAND_CENTERS.tolist(),modulationEdges=MOD_EDGES.tolist(),
            varianceFloor=.05,presenceAmplitudeRatio=.05,compressedLogSpectrumFloor=-3.,alignment='auditory-v1 prepare; entire non-silent extent')


@lru_cache(maxsize=8)
def _frequency_axis(n):
    return 21.4*np.log10(1+.00437*np.fft.rfftfreq(n,1/RATE))


def describe(wave):
    w=prepare(wave).astype(np.float64)
    n=1<<(len(w)+2*PAD-1).bit_length()
    padded=np.zeros(n);padded[PAD:PAD+len(w)]=w
    spectrum=np.fft.rfft(padded);erb=_frequency_axis(n)
    means=[];envelopes=[]
    for center in ERB_EDGES[1:-1]:
        position=(erb-center)/(ERB_EDGES[1]-ERB_EDGES[0])
        band=np.cos(np.clip(position,-1,1)*np.pi/2);band[abs(position)>=1]=0
        positive=np.zeros(n,dtype=complex);positive[:len(spectrum)]=2*spectrum*band
        envelope=np.abs(np.fft.ifft(positive)[PAD:PAD+len(w)])
        means.append(float(envelope.mean()))
        compressed=envelope**COMPRESSION
        compressed=np.pad(compressed,(0,(-len(compressed))%HOP),mode='edge')
        envelopes.append(compressed.reshape(-1,HOP).mean(1))
    env=np.array(envelopes);mean=env.mean(1);centered=env-mean[:,None]
    variance=(centered**2).mean(1);std=np.sqrt(variance)
    regular=np.maximum(std,np.maximum(mean*.05,1e-12))
    presence=np.clip(np.array(means)/max(max(means)*.05,1e-12),0,1)
    correlation=(centered@centered.T/max(1,env.shape[1]))/(regular[:,None]*regular[None,:])
    correlation*=presence[:,None]*presence[None,:]
    frames=max(8,env.shape[1]);fft_len=1<<(frames-1).bit_length()
    window=np.hanning(env.shape[1]) if env.shape[1]>2 else np.ones(env.shape[1])
    power=abs(np.fft.rfft(centered*window,n=fft_len,axis=1))**2
    power*=2/(max(float((window**2).sum()),1e-12)*fft_len)
    freq=np.fft.rfftfreq(fft_len,HOP/RATE)
    modulation=np.column_stack([power[:,(freq>lo)&(freq<=hi)].sum(1) for lo,hi in zip(MOD_EDGES,MOD_EDGES[1:])])
    modulation=np.log1p(modulation/np.maximum(mean[:,None]**2,1e-12))*presence[:,None]
    result=dict(
        # Below this floor, float32 quantization of nominally absent bands can
        # dominate log differences after compression (a gain-invariance failure).
        spectrum=np.clip(np.log(np.maximum(mean,1e-12)/max(float(mean.max()),1e-12)),-3,0),
        variation=np.log1p(std/np.maximum(mean,1e-12))*presence,
        skew=np.arcsinh(np.clip((centered**3).mean(1)/regular**3,-20,20))/3*presence,
        kurtosis=np.log1p(np.minimum((centered**4).mean(1)/regular**4,100))*presence,
        correlation=np.clip(correlation[np.triu_indices(BANDS,1)],-1,1),
        modulation=modulation.ravel())
    result={k:v.astype(np.float32) for k,v in result.items()}
    if any(v.shape!=(size,) or not np.isfinite(v).all() for v,size in zip(result.values(),SIZES)):
        raise ValueError('Nonfinite or malformed texture descriptor')
    return result


def components(target,candidate):
    if tuple(target)!=NAMES or tuple(candidate)!=NAMES:raise ValueError('Texture block mismatch')
    result=[]
    for key,size in zip(NAMES,SIZES):
        a,b=np.asarray(target[key]),np.asarray(candidate[key])
        if a.shape!=(size,) or b.shape!=(size,) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Invalid texture block')
        result.append(float(np.mean(abs(a-b))))
    return np.array(result)
