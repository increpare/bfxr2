"""Experimental analysis support for MatchObjective; no audition audio changes.

The historical metric averages envelope/mel errors over the longest waveform.
Quiet allocated buffers can dilute errors. Analyze only through the final sample
above -60dB relative peak, plus20ms context. Leading silence and later audible
events remain. This is a declared analysis policy, not a human audibility model.
"""
import numpy as np
from match.objective import MatchObjective

POLICY={'version':'support-v1','sampleRate':44100,'relativeAmplitudeFloor':.001,'guardSamples':882,
        'leadingSilence':'preserve','auditionWaveform':'unchanged'}

def analysis_support(wave):
    x=np.asarray(wave,dtype=np.float32)
    if x.ndim!=1 or not x.size or not np.isfinite(x).all():raise ValueError('Finite nonempty mono waveform required')
    peak=float(np.max(np.abs(x)))
    if peak<1e-8:return np.zeros(1,np.float32)
    active=np.flatnonzero(np.abs(x)>peak*POLICY['relativeAmplitudeFloor'])
    end=int(active[-1])+1+POLICY['guardSamples']
    result=np.zeros(end,np.float32);n=min(end,len(x));result[:n]=x[:n]
    return result

class SupportObjective(MatchObjective):
    def __init__(self,target,**kwargs):
        super().__init__(analysis_support(target),**kwargs)
    def score_batch(self,waves):
        return super().score_batch([analysis_support(w) if w is not None and len(w) else w for w in waves])
    def score_components(self,wave):
        return super().score_components(analysis_support(wave))
    def score_candidates(self,cache):
        raise NotImplementedError('Cached historical features do not apply the support policy; rescore waveforms')
