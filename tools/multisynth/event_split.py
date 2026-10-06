"""Conservative waveform-only boundaries for a native timeline capability pilot.

These are analysis hypotheses, not labeled perceptual event boundaries.
"""
import numpy as np

POLICY={'rate':44100,'fft':1024,'hop':256,'minimumSpacingSeconds':.06,
        'maximumInteriorBoundaries':2,'relativePeakThreshold':.25,
        'minimumNovelty':.08,'spectrumBands':24}

def split_events(wave):
    wave=np.asarray(wave,dtype=np.float64)
    if wave.ndim!=1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Expected finite nonempty mono audio')
    peak=np.max(np.abs(wave)); n=len(wave); rate=POLICY['rate']
    if peak<1e-8 or n<rate*.12:return [0,n]
    wave=wave/peak; fft=POLICY['fft'];hop=POLICY['hop']
    frames=np.lib.stride_tricks.sliding_window_view(np.pad(wave,(fft//2,fft//2)),fft)[::hop]
    power=np.abs(np.fft.rfft(frames*np.hanning(fft),axis=1))**2
    # Coarse magnitude distributions and amplitude onsets, with short smoothing.
    edges=np.unique(np.geomspace(1,power.shape[1],POLICY['spectrumBands']+1).astype(int))
    bands=np.array([power[:,a:b].sum(axis=1) for a,b in zip(edges[:-1],edges[1:])]).T
    bands=np.sqrt(bands);bands/=np.maximum(bands.sum(axis=1,keepdims=True),1e-12)
    env=np.sqrt(np.mean(frames**2,axis=1));env/=max(env.max(),1e-12)
    change=np.maximum(np.diff(bands,axis=0),0).sum(axis=1)*env[1:]
    novelty=np.r_[0,change+np.maximum(np.diff(env),0)]
    novelty=np.convolve(novelty,[.25,.5,.25],mode='same')
    threshold=max(POLICY['minimumNovelty'],float(novelty.max())*.25)
    indices=np.flatnonzero((novelty[1:-1]>novelty[:-2]) &
                           (novelty[1:-1]>=novelty[2:]) &
                           (novelty[1:-1]>=threshold))+1
    eligible=[int(i) for i in indices if .06*rate<=i*hop<=n-.06*rate]
    selected=[]
    for i in sorted(eligible,key=lambda i:(-novelty[i],i)):
        if all(abs(i-j)*hop>=.06*rate for j in selected):selected.append(i)
        if len(selected)==2:break
    return [0,*[i*hop for i in sorted(selected)],n]
