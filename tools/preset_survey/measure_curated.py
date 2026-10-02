#!/usr/bin/env python3
"""Measure the curated palette and verify the traits requested by the listener."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from analyze import extract_features,read_audio,normalize,distances,FEATURE_NAMES
from runtime_provenance import require_current_runtime,runtime_fingerprint

def wobble(pcm,rate):
    n=2048;hop=256
    frames=np.lib.stride_tricks.sliding_window_view(pcm,n)[::hop]
    spec=abs(np.fft.rfft(frames*np.hanning(n),axis=1))**2+1e-20
    spec[:,:3]=0;peak=spec.argmax(axis=1);peak=np.clip(peak,1,spec.shape[1]-2)
    rows=np.arange(len(spec));logs=np.log(spec+1e-20);left,center,right=logs[rows,peak-1],logs[rows,peak],logs[rows,peak+1]
    offset=np.clip(.5*(left-right)/(left-2*center+right-1e-20),-.5,.5)
    track=np.log2((peak+offset)*rate/n)
    # Remove the slow journey; what remains should quiver near eight Hz.
    t=np.arange(len(track))*hop/rate
    track-=np.polyval(np.polyfit(t,track,2),t)
    motion=abs(np.fft.rfft(track*np.hanning(len(track))))**2
    freq=np.fft.rfftfreq(len(track),hop/rate);keep=(freq>=5)&(freq<=12)
    at=np.flatnonzero(keep)[np.argmax(motion[keep])]
    return {'wobble_hz':float(freq[at]),'wobble_rms_octaves':float(np.sqrt(np.mean(track**2)))}

def traits(sound,family):
    p=sound['params'];f=sound['features'];id=family['id'];errors=[]
    def require(check,message):
        if not check:errors.append(message)
    require(sound['rms']>=.004,'inaudible');require(sound['peak']<1,'clipped')
    if id in ['grainy_taps','fuzzy_chirps','soft_pips','sand_sprays','arcade_zaps','bubble_pops','rubber_clicks','static_flecks']:
        max_duration={'grainy_taps':.18,'fuzzy_chirps':.28,'soft_pips':.22,'sand_sprays':.45,'arcade_zaps':.28,'bubble_pops':.29,'rubber_clicks':.26,'static_flecks':.33}[id]
        require(sound['duration']<=max_duration,'long rendered tail');require(p['echo']==0,'echo on a dry sound')
    if id=='wavering_calls':
        require(p['vibrato']['start']>=.65 and p['vibrato']['end']>=.65,'wobble absent')
        require(6.4<=f['wobble_hz']<=9.7 and f['wobble_rms_octaves']>=.035,'weak or irregular measured wobble')
    if id=='soft_pips':
        require(p['waveType']==0 and p['noise']['start']<=.03 and p['noise']['end']<=.03,'rough pip voice')
        require(p['attack']>=.012 and sound['peak']<=.22,'hard or loud pip onset')
        require(f['centroid_hz']<800,'bright pip spectrum')
    if id=='fuzzy_chirps':require(min(p['noise']['start'],p['noise']['end'])>=.18,'chirp has no fuzzy edge')
    if id=='sand_sprays':
        require(min(p['noise']['start'],p['noise']['end'])>=.9,'pitched sand outlier')
        require(f['centroid_hz']>1000,'sand is too dark')
    if id=='air_currents':
        require(p['duration']>=.85 and p['attack']>=.18,'short or abrupt air')
        require(min(p['noise']['start'],p['noise']['end'])>=.9,'air lost its breath')
        require(f['centroid_hz']<1000,'air too close to bright sand')
    if id=='bubble_swells':require(f['peak_time']>.6,'swell does not peak late')
    return errors

def measure(directory,sample_directory=None):
    directory=Path(directory);report=json.loads((directory/'curated.json').read_text())
    require_current_runtime(report)
    sounds=report['sounds'];groups=report['groups']
    def analyze(sound,base):
        pcm,rate=read_audio(base/sound['audio']);sound['features']=extract_features(pcm,rate)
        if groups[sound['cluster']]['id']=='wavering_calls':sound['features'].update(wobble(pcm,rate))
        return pcm
    failures=[];envelopes={}
    for sound in sounds:
        pcm=analyze(sound,directory);parts=np.array_split(pcm[:int(sound['features']['active_duration']*44100)],32)
        env=np.array([np.sqrt(np.mean(part**2)) if len(part) else 0 for part in parts]);envelopes[sound['id']]=env/max(1e-12,env.max())
        failures.extend({'id':sound['id'],'family':groups[sound['cluster']]['name'],'reason':e} for e in traits(sound,groups[sound['cluster']]))
    matrix=np.array([[s['features'][n] for n in FEATURE_NAMES] for s in sounds]);x,scaler=normalize(matrix)
    for group in groups:
        members=np.array([i for i,s in enumerate(sounds) if s['cluster']==group['index']]);center=x[members].mean(axis=0)
        ds=np.sqrt(distances(x[members],center[None,:])[:,0]);order=members[np.argsort(ds)]
        group['exemplars']=[sounds[i]['id'] for i in order]
        group['summary']={n:float(np.median([sounds[i]['features'][n] for i in members])) for n in FEATURE_NAMES+['active_duration','pitch_hz','centroid_hz']}
        group['profile']=np.median([envelopes[sounds[i]['id']] for i in members],axis=0).round(4).tolist()
        for i,d in zip(members,ds):sounds[i]['distance']=float(d)
    bank_path=Path(__file__).resolve().parents[2]/'js/synths/TransfxrPresets.js'
    bank_sha256=hashlib.sha256(bank_path.read_bytes()).hexdigest()
    checks={'revision':2,'bank_sha256':bank_sha256,'runtime_sha256':runtime_fingerprint(),'exemplar_count':len(sounds),'count':0,'failures':failures,'families':[]}
    if sample_directory:
        sample_directory=Path(sample_directory);samples=json.loads((sample_directory/'samples.json').read_text())
        require_current_runtime(samples)
        if samples['bank_sha256']!=bank_sha256:raise ValueError('Fresh samples belong to a different bank')
        checks.update(seed=samples['seed'],count=samples['count'],minimum_rms=min(s['rms'] for s in samples['sounds']),maximum_peak=max(s['peak'] for s in samples['sounds']))
        for sound in samples['sounds']:
            analyze(sound,sample_directory)
            # Fresh manifests do not store duration; read the actual WAV frame count.
            sound['duration']=len(read_audio(sample_directory/sound['audio'])[0])/44100
            failures.extend({'id':sound['id'],'family':groups[sound['cluster']]['name'],'reason':e} for e in traits(sound,groups[sound['cluster']]))
        for group in groups:
            members=[s for s in samples['sounds'] if s['cluster']==group['index']]
            checks['families'].append({'name':group['name'],'count':len(members),'max_rendered_duration':max(s['duration'] for s in members),
                'median_centroid_hz':float(np.median([s['features']['centroid_hz'] for s in members]))})
    checks['failures']=failures
    report['validation']=checks
    (directory/'curated.json').write_text(json.dumps(report,indent=2)+'\n')
    (directory/'curated-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2),flush=True)
    if failures:raise ValueError(f'{len(failures)} family-trait failures; inspect curated-validation.json')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('samples',nargs='?');args=parser.parse_args();measure(args.directory,args.samples)
