#!/usr/bin/env python3
"""Measure rendered audio and discover reproducible families. Requires NumPy only."""
import argparse
import json
import math
from pathlib import Path
import wave
import numpy as np

FEATURE_GROUPS = {
    'time': ['active_duration_log2', 'energy_spread', 'peak_time', 'late_energy', 'attack_rise'],
    'timbre': ['centroid_log2', 'flatness_db', 'tonal_concentration', 'spectral_entropy'] + ['band_'+str(i) for i in range(8)],
    'motion': ['centroid_range_octaves', 'centroid_slope_octaves', 'flux', 'envelope_variation'],
    'pitch': ['pitch_log2', 'pitch_slope_octaves', 'pitch_range_octaves', 'voiced_fraction'],
}
FEATURE_NAMES = sum(FEATURE_GROUPS.values(), [])

def read_audio(path):
    with wave.open(str(path), 'rb') as wav:
        assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
        return np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float)/32768, wav.getframerate()

def extract_features(pcm, rate=44100):
    pcm = np.asarray(pcm, dtype=float)
    if len(pcm) < 2 or not np.all(np.isfinite(pcm)):
        raise ValueError('Audio must contain finite samples')
    n, hop = 2048, 512
    padded = np.pad(pcm, (0, max(0,n-len(pcm))))
    frames = np.lib.stride_tricks.sliding_window_view(padded,n)[::hop]
    env = np.sqrt(np.mean(frames**2,axis=1))
    peak = max(float(env.max()),1e-12)
    active = np.flatnonzero(env > max(peak*0.008,0.00004))
    if not len(active): raise ValueError('Silent audio')
    first,last = active[0],active[-1]
    duration = min(len(pcm)/rate, (last*hop+n)/rate)
    env = env[:last+1]
    frames = frames[:last+1]
    power = abs(np.fft.rfft(frames*np.hanning(n),axis=1))**2 + 1e-20
    freq = np.fft.rfftfreq(n,1/rate)
    keep = env > peak*0.07
    if not np.any(keep): keep[:] = True
    spec = power[keep]
    total = spec.sum(axis=1)
    probability = spec/total[:,None]
    centroid = (spec@freq)/total
    logcentroid = np.log2(np.maximum(centroid,30))
    flatness = np.exp(np.mean(np.log(spec),axis=1))/np.mean(spec,axis=1)
    concentration = np.partition(probability,-8,axis=1)[:,-8:].sum(axis=1)
    entropy = -(probability*np.log(probability+1e-20)).sum(axis=1)/np.log(spec.shape[1])
    normalized = np.sqrt(probability)
    flux = np.sqrt(np.sum(np.diff(normalized,axis=0)**2,axis=1))
    edges=[0,160,320,640,1280,2560,5120,10000,rate/2+1]
    bands = np.array([np.mean(probability[:,(freq>=a)&(freq<b)].sum(axis=1)) for a,b in zip(edges[:-1],edges[1:])])
    # Dominant peak is useful for tonal effects; noise is marked unvoiced instead
    # of treating its strongest random Fourier bin as a musical fundamental.
    voice = concentration > 0.5
    spectrum = spec.copy(); spectrum[:,freq<40] = 0; spectrum[:,freq>6000] = 0
    indices = np.argmax(spectrum,axis=1)
    indices = np.clip(indices,1,spectrum.shape[1]-2)
    rows = np.arange(len(spectrum)); logs=np.log(spectrum+1e-20)
    left,center,right=logs[rows,indices-1],logs[rows,indices],logs[rows,indices+1]
    correction=np.clip(0.5*(left-right)/(left-2*center+right-1e-20),-0.5,0.5)
    pitches=np.log2(np.maximum(40,(indices+correction)*rate/n))
    vp=pitches[voice]
    validpos=np.flatnonzero(voice)
    split=max(1,len(pitches)//3)
    beginning=pitches[voice & (np.arange(len(pitches))<split)]
    ending=pitches[voice & (np.arange(len(pitches))>=len(pitches)-split)]
    slope=float(np.median(ending)-np.median(beginning)) if len(beginning) and len(ending) else 0.0
    weights=env**2;cum=np.cumsum(weights)/(weights.sum()+1e-20)
    q=lambda value: float(np.searchsorted(cum,value)/max(1,len(env)-1))
    attack=float(np.argmax(env)/max(1,len(env)-1))
    envnorm=env/peak
    result={
        'active_duration_log2':math.log2(max(0.02,duration)),
        'energy_spread':q(.9)-q(.1),'peak_time':attack,
        'late_energy':float(weights[int(len(weights)*.75):].sum()/weights.sum()),
        'attack_rise':float(np.max(np.diff(envnorm))) if len(env)>1 else 0.,
        'centroid_log2':float(np.median(logcentroid)),
        'flatness_db':float(np.mean(10*np.log10(np.maximum(flatness,1e-12)))),
        'tonal_concentration':float(np.median(concentration)),
        'spectral_entropy':float(np.mean(entropy)),
        'centroid_range_octaves':float(np.quantile(logcentroid,.9)-np.quantile(logcentroid,.1)),
        'centroid_slope_octaves':float(np.median(logcentroid[-split:])-np.median(logcentroid[:split])),
        'flux':float(np.mean(flux)) if len(flux) else 0.,
        'envelope_variation':float(np.std(np.diff(envnorm))) if len(env)>1 else 0.,
        'pitch_log2':float(np.median(vp)) if len(vp) else 0.,
        'pitch_slope_octaves':slope,'pitch_range_octaves':float(np.quantile(vp,.9)-np.quantile(vp,.1)) if len(vp) else 0.,
        'voiced_fraction':float(np.mean(voice)),
        'active_duration':duration,'centroid_hz':float(2**np.median(logcentroid)),
        'pitch_hz':float(2**np.median(vp)) if len(vp) else 0.,
    }
    result.update({'band_'+str(i):float(np.log10(max(value,1e-8))) for i,value in enumerate(bands)})
    return result

def normalize(matrix):
    median=np.median(matrix,axis=0)
    spread=np.maximum((np.quantile(matrix,.85,axis=0)-np.quantile(matrix,.15,axis=0))/2,0.08)
    weights=np.concatenate([np.full(len(group),1/math.sqrt(len(group))) for group in FEATURE_GROUPS.values()])
    x=np.clip((matrix-median)/spread,-4,4)*weights
    return x,{'feature_names':FEATURE_NAMES,'median':median.tolist(),'spread':spread.tolist(),'weights':weights.tolist(),'clip':4}

def transform(matrix,scaler):
    return np.clip((matrix-np.array(scaler['median']))/np.array(scaler['spread']),-scaler['clip'],scaler['clip'])*np.array(scaler['weights'])

def distances(a,b):
    return np.maximum(0,(a*a).sum(axis=1)[:,None]+(b*b).sum(axis=1)[None,:]-2*a@b.T)

def cluster(x,k,seed=20261002,restarts=12):
    best=None
    for attempt in range(restarts):
        random=np.random.default_rng(seed+attempt)
        centers=[x[random.integers(len(x))]]
        for _ in range(1,k):
            d=distances(x,np.array(centers)).min(axis=1)
            centers.append(x[random.choice(len(x),p=d/d.sum())] if d.sum()>0 else x[random.integers(len(x))])
        centers=np.array(centers)
        previous=None
        for _ in range(150):
            d=distances(x,centers);labels=d.argmin(axis=1)
            if previous is not None and np.array_equal(labels,previous): break
            previous=labels.copy()
            for j in range(k):
                members=x[labels==j]
                centers[j]=members.mean(axis=0) if len(members) else x[np.argmax(d.min(axis=1))]
        loss=float(distances(x,centers)[np.arange(len(x)),labels].sum())
        if best is None or loss<best[0]: best=(loss,labels.copy(),centers.copy())
    return best[1],best[2]

def silhouette(x,labels):
    d=np.sqrt(distances(x,x));scores=[]
    for i in range(len(x)):
        own=(labels==labels[i]);own[i]=False
        if not np.any(own): scores.append(0);continue
        a=d[i,own].mean();b=min(d[i,labels==j].mean() for j in np.unique(labels) if j!=labels[i])
        scores.append((b-a)/max(a,b,1e-12))
    return float(np.mean(scores))

def diverse_representatives(x,members,center,limit=24):
    # Central example first, then farthest-first coverage inside the main 92%.
    distances_to_center=np.sqrt(distances(x[members],center[None,:])[:,0])
    central=members[np.argmin(distances_to_center)]
    pool=members[distances_to_center<=np.quantile(distances_to_center,.92)]
    selected=[int(central)]
    target=min(limit,len(pool))
    pool=pool[pool!=central]
    while len(selected)<target:
        d=distances(x[pool],x[selected]).min(axis=1)
        selected.append(int(pool[np.argmax(d)]))
        pool=pool[~np.isin(pool,selected)]
        if not len(pool):break
    return selected

def analyze(directory):
    directory=Path(directory);corpus=json.loads((directory/'corpus.json').read_text())
    for i,sound in enumerate(corpus['sounds']):
        pcm,rate=read_audio(directory/sound['audio']);sound['features']=extract_features(pcm,rate)
        if (i+1)%64==0: print('Measured',i+1,flush=True)
    matrix=np.array([[s['features'][n] for n in FEATURE_NAMES] for s in corpus['sounds']])
    x,scaler=normalize(matrix)
    trials=[];models={}
    for k in [8,10,12,14,16]:
        labels,centers=cluster(x,k)
        score=silhouette(x,labels);counts=np.bincount(labels,minlength=k)
        trials.append({'k':k,'silhouette':score,'min_size':int(counts.min()),'max_size':int(counts.max())})
        models[k]=(labels,centers);print(trials[-1],flush=True)
    # Prefer expressive granularity with viable membership; silhouette is evidence,
    # not a substitute for the usefulness of the resulting named categories.
    eligible=[t for t in trials if t['min_size']>=12]
    peak=max(t['silhouette'] for t in eligible or trials)
    chosen=max((t for t in eligible or trials if t['silhouette']>=peak-.04),key=lambda t:t['k'])
    labels,centers=models[chosen['k']]
    groups=[]
    for j in range(chosen['k']):
        members=np.flatnonzero(labels==j)
        examples=diverse_representatives(x,members,centers[j])
        summary={n:float(np.median([corpus['sounds'][i]['features'][n] for i in members])) for n in corpus['sounds'][0]['features']}
        param_summary={n:float(np.median([corpus['sounds'][i]['params'][n] for i in members])) for n in ['duration','attack','release','resonance','echo']}
        groups.append({'index':j,'count':len(members),'members':[corpus['sounds'][i]['id'] for i in members],
            'exemplars':[corpus['sounds'][i]['id'] for i in examples], 'center':centers[j].tolist(),
            'summary':summary,'param_summary':param_summary})
        for i in members:
            corpus['sounds'][i]['cluster']=j
            corpus['sounds'][i]['distance']=float(np.sqrt(distances(x[i:i+1],centers[j:j+1])[0,0]))
    report={'synth':corpus['synth'],'seed':corpus['seed'],'count':corpus['count'],'trials':trials,
        'chosen_k':chosen['k'],'scaler':scaler,'groups':groups,'sounds':corpus['sounds']}
    (directory/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Wrote',directory/'analysis.json',flush=True)
    for g in groups:
        s=g['summary'];print(f"{g['index']:2}: {g['count']:3} sounds; active {s['active_duration']:.2f}s; pitch {s['pitch_hz']:.0f}Hz; slope {s['pitch_slope_octaves']:+.2f}oct; centroid {s['centroid_hz']:.0f}Hz; tonal {s['tonal_concentration']:.2f}; peak time {s['peak_time']:.2f}; example {g['exemplars'][0]}")
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');args=parser.parse_args();analyze(args.directory)
