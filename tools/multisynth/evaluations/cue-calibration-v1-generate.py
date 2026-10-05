"""Five fixed contrasts for local likeness evidence, not synth reproduction."""
import json, hashlib, importlib.metadata
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt
import librosa

BASE=Path('tools/multisynth');OUT=BASE/'runs/cue-calibration-v1-listening'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def process(x,params):
    op=params['operation']
    if op=='lowpass':
        y=sosfiltfilt(butter(4,params['hz'],fs=44100,output='sos'),x)
    elif op=='time-stretch':
        y=librosa.effects.time_stretch(x,rate=params['rate'],n_fft=1024,hop_length=256)
    elif op=='pitch-shift':
        y=librosa.effects.pitch_shift(x,sr=44100,n_steps=params['semitones'],n_fft=1024,hop_length=256,res_type='soxr_hq')
    elif op=='attack-fade':
        start=int(np.flatnonzero(np.abs(x)>=.01*np.max(np.abs(x)))[0])
        count=min(round(params['seconds']*44100),len(x)-start)
        y=x.copy();y[:start]=0;y[start:start+count]*=.5-.5*np.cos(np.linspace(0,np.pi,count))
    elif op=='tail-fade':
        start=int(params['startFraction']*len(x))
        env=np.ones(len(x));env[start:]=10**(np.linspace(0,params['endDb'],len(x)-start)/20)
        y=x*env
    else:raise ValueError(op)
    y=np.asarray(y,np.float64)
    gain=float(np.sqrt(np.mean(x.astype(float)**2)/np.mean(y*y)))
    cap=.8/(np.max(np.abs(y))*gain)
    capped=bool(cap<1);gain*=min(1.,cap)
    pcm=np.clip(np.rint(y*gain*32768),-32768,32767).astype(np.int16)
    assert np.isfinite(y).all() and len(pcm)>0 and np.max(np.abs(pcm.astype(int)))<32767
    return pcm,dict(gain=gain,peakCapApplied=capped,outputSamples=len(pcm))


def main():
    if OUT.exists():raise FileExistsError('Preserve diagnostic gallery')
    latest=BASE/'listening_data/2026-10-05-tagged-coverage-quick-01'
    charm=BASE/'listening_data/2026-10-05-pitch-calibration-quick-01'
    plans=[(latest,'footstep/footstep_wood_000.ogg',[dict(operation='attack-fade',seconds=.03),dict(operation='lowpass',hz=2500)]),
        (latest,'explode/Break Brick.wav',[dict(operation='time-stretch',rate=.8),dict(operation='lowpass',hz=2500)]),
        (charm,'die/charm2.wav',[dict(operation='pitch-shift',semitones=2),dict(operation='lowpass',hz=2500)]),
        (latest,'clothes/cloth3.ogg',[dict(operation='time-stretch',rate=.8),dict(operation='lowpass',hz=1800)]),
        (latest,'laser/Lasers.wav',[dict(operation='pitch-shift',semitones=2),dict(operation='tail-fade',startFraction=.6,endDb=-18)])]
    rows=[]
    for root,name,ops in plans:
        m=json.loads((root/'manifest.json').read_text());t=next(t for t in m['targets'] if t['source']['name']==name)
        rows.append(dict(archive=str(root),manifestSha256=digest(root/'manifest.json'),source=t['source'],reference=t['referenceAudio'],operations=ops))
    protocol=dict(scriptSha256=digest(__file__),planSha256=digest('docs/superpowers/plans/2026-10-05-perceptual-cue-calibration.md'),
        packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','librosa','soxr','soundfile']},
        purpose='Controlled local likeness calibration; edited originals, not synth output or model improvement',rows=rows)
    write(BASE/'evaluations/cue-calibration-v1-protocol.json',protocol)
    OUT.mkdir()
    records=[]
    for i,row in enumerate(rows):
        folder=OUT/f'{i+1:03d}';folder.mkdir()
        path=Path(row['archive'])/row['reference']['file']
        pcm,sr=sf.read(path,dtype='int16',always_2d=True)
        ph=hashlib.sha256(str((sr,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()
        assert sr==44100 and pcm.shape[1]==1 and ph==row['reference']['pcmSha256']
        sf.write(folder/'target.wav',pcm,44100,subtype='PCM_16')
        x=pcm[:,0].astype(np.float32)/32768
        record=dict(folder=folder.name,source=row['source'],candidates=[],note='Deliberately edited originals. Choose the version that stays closest to the reference, then how close it feels.')
        hashes={digest(folder/'target.wav')}
        for j,op in enumerate(row['operations']):
            y,levels=process(x,op);again,again_levels=process(x,op)
            assert np.array_equal(y,again) and levels==again_levels
            if op['operation']=='time-stretch':assert len(y)==round(len(x)/op['rate'])
            else:assert len(y)==len(x)
            filename=f'option-{j+1}.wav';sf.write(folder/filename,y,44100,subtype='PCM_16')
            sha=digest(folder/filename);assert sha not in hashes;hashes.add(sha)
            record['candidates'].append(dict(role='selected' if j==0 else 'alternative',label='Edited comparison option',
                synth='Controlled audio edit',params=op,seed=0,sourceHash=protocol['scriptSha256'],file=filename,
                provenance=dict(method='controlled-reference-edit',scriptSha256=protocol['scriptSha256'],
                    protocolSha256=digest(BASE/'evaluations/cue-calibration-v1-protocol.json'),
                    referencePcmSha256=ph,referenceArchive=row['archive'],transform=op,**levels,
                    auditionWavSha256=sha,repeatRenderIdentical=True,notSynthReproduction=True)))
        records.append(record)
    write(OUT/'generation.json',dict(protocol=protocol,records=records))
    print('Generated five references and ten deterministic variants',flush=True)

if __name__=='__main__':main()
