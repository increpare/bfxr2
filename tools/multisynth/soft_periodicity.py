"""Experimental continuous pitch/periodicity loss; legacy matcher stays frozen."""
import numpy as np
import torch
from match.audio import normalize_peak
from match.objective import MatchObjective, MIN_WAVE_LEN, TAIL_PAD
from match.features import PITCH_FRAME, ACF_N, HOP, frame_count, _LAG_MIN, _LAG_MAX

VERSION='soft-periodicity-v1'
HARD_PITCH=('pitch','voiced_mismatch','pitch_slope','pitch_movement')


class SoftPeriodicityObjective(MatchObjective):
    def __init__(self,target):
        super().__init__(target)
        lags=torch.logspace(np.log10(_LAG_MIN),np.log10(_LAG_MAX-1),96)
        self.lag0=lags.floor().long();self.fraction=lags-self.lag0
        self.target_periodicity=self._periodicity(target)

    def _periodicity(self,wave):
        x=normalize_peak(np.asarray(wave,dtype=np.float32))
        length=max(len(x),MIN_WAVE_LEN)
        padded=torch.zeros(length+TAIL_PAD);padded[:len(x)]=torch.from_numpy(x.copy())
        frames=padded.unfold(0,PITCH_FRAME,HOP)[:frame_count(length)]
        with torch.no_grad():
            spec=torch.fft.rfft(frames*self.extractor.pitch_window,n=ACF_N)
            acf=torch.fft.irfft(spec.abs().square(),n=ACF_N)[:,:_LAG_MAX+2]
            corr=acf/(acf[:,:1]+1e-12)/self.extractor.acf_norm
            corr=corr.clamp(-1,1)
            sampled=corr[:,self.lag0]*(1-self.fraction)+corr[:,self.lag0+1]*self.fraction
            rms=frames.square().mean(1).sqrt()
            rms=rms/rms.max().clamp(min=1e-12)
        return sampled,rms

    def _periodicity_terms(self,wave):
        a,wa=self.target_periodicity;b,wb=self._periodicity(wave)
        n=max(len(a),len(b))
        pad=lambda x:torch.nn.functional.pad(x,(0,0,0,n-len(x)))
        a,b=pad(a),pad(b)
        wa=torch.nn.functional.pad(wa,(0,n-len(wa)));wb=torch.nn.functional.pad(wb,(0,n-len(wb)))
        # Quiet tails cannot dominate through normalized but unreliable correlation.
        weights=torch.maximum(wa,wb)
        level=((a-b).abs().mean(1)*weights).sum()/weights.sum().clamp(min=1e-12)
        mw=torch.minimum(weights[1:],weights[:-1])
        motion=((a.diff(dim=0)-b.diff(dim=0)).abs().mean(1)*mw).sum()/mw.sum().clamp(min=1e-12)
        return dict(periodicity=4*float(level),periodicity_motion=float(motion))

    def _score_valid(self,waves):
        _,components=super()._score_valid(waves)
        for wave,terms in zip(waves,components):
            for key in HARD_PITCH:del terms[key]
            terms.update(self._periodicity_terms(wave))
        return np.array([sum(c.values()) for c in components]),components

    @staticmethod
    def precompute_candidates(*args,**kwargs):
        raise NotImplementedError('Legacy candidate caches omit continuous periodicity')

    def score_candidates(self,cache):
        raise NotImplementedError('Use exact-wave score_batch with this experimental objective')
