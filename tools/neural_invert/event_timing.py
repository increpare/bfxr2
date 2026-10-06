"""Small experimental native-sequence timing model; not a synth-control inverse."""
from functools import lru_cache
import numpy as np
import torch
from torch import nn

RATE=44100
HOP=256
FRAMES=256
POLICY={'version':'stackr-event-timing-v1','rate':RATE,'fft':1024,'hop':HOP,
        'frames':FRAMES,'bands':24,'maxSamples':HOP*FRAMES,'peakThreshold':.5,
        'edgeSeconds':.06,'minimumGapSeconds':.06,'maximumInterior':2,'matchToleranceSeconds':.025}

@lru_cache(maxsize=1)
def _bank():
    hz=np.fft.rfftfreq(1024,1/RATE);edge=np.geomspace(40,18000,26)
    bank=np.maximum(0,np.minimum((hz[None]-edge[:-2,None])/(edge[1:-1]-edge[:-2])[:,None],
                    (edge[2:,None]-hz[None])/(edge[2:]-edge[1:-1])[:,None]))
    bank/=np.maximum(bank.sum(axis=1,keepdims=True),1e-12)
    return bank

def features(wave):
    wave=np.asarray(wave,dtype=np.float64)
    if wave.ndim!=1 or not wave.size or len(wave)>POLICY['maxSamples'] or not np.isfinite(wave).all():
        raise ValueError('Expected finite mono audio within fixed analysis horizon')
    peak=np.max(np.abs(wave))
    if peak<1e-8:return np.r_[np.full((24,FRAMES),-1.),np.zeros((1,FRAMES))].astype(np.float32)
    wave=wave/peak
    padded=np.pad(wave,(512,POLICY['maxSamples']-len(wave)+512))
    frames=np.lib.stride_tricks.sliding_window_view(padded,1024)[::HOP][:FRAMES]
    power=np.abs(np.fft.rfft(frames*np.hanning(1024),axis=1))**2
    power=power@_bank().T;db=10*np.log10(np.maximum(power,1e-15))
    spec=np.clip((db-db.max())/60,-1,0).T
    envelope=np.sqrt(np.mean(frames**2,axis=1));envelope/=max(envelope.max(),1e-12)
    return np.r_[spec,envelope[None]].astype(np.float32)

def targets(starts):
    starts=np.asarray(starts,dtype=float)
    if starts.ndim!=1 or not len(starts) or starts[0]!=0 or not np.isfinite(starts).all() or np.any(np.diff(starts)<=0):
        raise ValueError('Expected strictly ordered starts beginning at zero')
    if len(starts)>3 or starts[-1]>=POLICY['maxSamples']/RATE:raise ValueError('Starts exceed model scope')
    output=np.zeros(FRAMES)
    for start in starts[1:]:output=np.maximum(output,np.exp(-.5*(np.arange(FRAMES)-start*RATE/HOP)**2))
    return output.astype(np.float32)

def decode(probabilities,samples):
    p=np.asarray(probabilities,dtype=float)
    if p.shape!=(FRAMES,) or not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not 0<samples<=POLICY['maxSamples']:
        raise ValueError('Invalid probabilities or sample count')
    peaks=np.flatnonzero((p[1:-1]>p[:-2])&(p[1:-1]>=p[2:])&(p[1:-1]>=POLICY['peakThreshold']))+1
    eligible=[int(i) for i in peaks if .06*RATE<=i*HOP<=samples-.06*RATE]
    selected=[]
    for i in sorted(eligible,key=lambda i:(-p[i],i)):
        if all(abs(i-j)*HOP>=.06*RATE for j in selected):selected.append(i)
        if len(selected)==2:break
    return [0,*[i*HOP for i in sorted(selected)],int(samples)]

class TimingNet(nn.Module):
    def __init__(self):
        super().__init__()
        layers=[nn.Conv1d(25,32,1),nn.GELU()]
        for d in (1,2,4,8):layers.extend([nn.Conv1d(32,32,3,padding=d,dilation=d),nn.GELU()])
        layers.append(nn.Conv1d(32,1,1));self.network=nn.Sequential(*layers)
    def forward(self,x):
        return self.network(x).squeeze(1)

def match_events(truth,predicted,tolerance=.025):
    a,b=sorted(truth),sorted(predicted);i=j=tp=0
    while i<len(a) and j<len(b):
        if abs(a[i]-b[j])<=tolerance+1e-12:tp+=1;i+=1;j+=1
        elif b[j]<a[i]:j+=1
        else:i+=1
    return dict(tp=tp,fp=len(b)-tp,fn=len(a)-tp)
