"""Controlled absolute-pitch checks, separate from human likeness judgments."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.optimizer import freq_param_from_hz
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from match.audio import normalize_peak
from .predict import load_model
from .evaluate import OriginalBfxr, approximate, pitch_summary, serializable, digest


def probes(renderer):
    cases=[]
    for hz in (220,440,880):
        b=deepcopy(renderer.specs['Bfxr']['defaults'])
        b.update(waveType=2,frequency_start=freq_param_from_hz(hz),attackTime=.03,
                 sustainTime=.35,decayTime=.15,frequency_slide=0.,frequency_acceleration=0.,
                 vibratoDepth=0.,lpFilterCutoff=1.,hpFilterCutoff=0.)
        cases.append(('Bfxr',hz,b))
        t=deepcopy(renderer.specs['Transfxr']['defaults']);pitch=np.log2(hz/40)/7
        t.update(duration=.65,echo=0.,resonance=0.,attack=.015,release=.15,waveType=0,waveTo=-1,
                 pitch={'start':pitch,'end':pitch,'curve':'Linear'},
                 vibrato={'start':0.,'end':0.,'curve':'Linear'},
                 tone={'start':1.,'end':1.,'curve':'Linear'},
                 level={'start':.7,'end':.7,'curve':'Linear'})
        cases.append(('Transfxr',hz,t))
    for hz in (220,440):
        p=deepcopy(renderer.specs['Pluckr']['defaults'])
        p.update(pitch=np.log2(hz/55)/4,strings=1,inharmonic=0.,coupling=0.,strum=0.,
                 vibrato=0.,tremolo=0.,duration=.8)
        cases.append(('Pluckr',hz,p))
    return cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','bfxr-checkpoint','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--budget',type=int,default=128);parser.add_argument('--bfxr-budget',type=int,default=2000)
    args=parser.parse_args();torch.set_num_threads(1)
    if args.output.exists():raise ValueError('Use a fresh tonal output directory')
    args.output.mkdir(parents=True);model,metadata=load_model(args.model);records=[]
    with Renderer() as renderer,BfxrRenderer(jobs=2) as bfxr:
        original=OriginalBfxr(args.bfxr_checkpoint,bfxr)
        for index,(synth,hz,params) in enumerate(probes(renderer)):
            canonical,wave=renderer.render(synth,params,91827+index)
            target_pitch=pitch_summary(wave)
            if target_pitch['medianHz'] is None or target_pitch['voicedFraction']<.6:
                raise ValueError('Unreliable tonal probe '+synth+str(hz))
            calibration=abs(12*np.log2(target_pitch['medianHz']/hz))
            if calibration>.5:raise ValueError('Tonal probe differs from claimed pitch')
            result=approximate(model,metadata,wave,renderer,original,starts=4,budget=args.budget,
                               bfxr_budget=args.bfxr_budget,seed=43270+index*71)
            known=[r for r in result['allRaw'] if r['synth']==synth]
            known=min(known,key=lambda r:r['score']) if known else None
            roles={'knownRaw':known,'unrestrictedRaw':result['raw'],'neuralRefined':result['neural'],
                   'selected':result['selected'],'original':result['original']}
            dest=args.output/f'{index+1:03d}';dest.mkdir()
            sf.write(dest/'target.wav',normalize_peak(wave),44100,subtype='PCM_16')
            record={'sourceSynth':synth,'expectedHz':hz,'targetPitch':target_pitch,
                'calibrationSemitones':calibration,'sourceParams':canonical,'sourceSeed':91827+index,
                'sourceHash':metadata['sourceHash'],'candidates':{}}
            for role,c in roles.items():
                if c is None:record['candidates'][role]=None;continue
                pitch=pitch_summary(c['wave'])
                error=abs(12*np.log2(pitch['medianHz']/target_pitch['medianHz'])) if pitch['medianHz'] and pitch['voicedFraction']>=.6 else None
                record['candidates'][role]={**serializable(c),'pitch':pitch,'absolutePitchErrorSemitones':error}
                sf.write(dest/(role+'.wav'),normalize_peak(c['wave']),44100,subtype='PCM_16')
            records.append(record)
            print(json.dumps({'synth':synth,'hz':hz,'pitchErrors':{
                k:v['absolutePitchErrorSemitones'] if v else None for k,v in record['candidates'].items()}}),flush=True)
    summary={}
    for role in records[0]['candidates']:
        errors=[r['candidates'][role]['absolutePitchErrorSemitones'] if r['candidates'][role] else None for r in records]
        valid=[e for e in errors if e is not None]
        summary[role]={'withinOneSemitone':sum(e<=1 for e in valid),'total':len(errors),
                       'unreliableOrMissing':len(errors)-len(valid),'medianAbsoluteSemitones':float(np.median(valid)) if valid else None}
    report={'metadata':{'modelSha256':digest(args.model),'bfxrCheckpointSha256':digest(args.bfxr_checkpoint),
        'sourceHash':metadata['sourceHash'],'scope':'Controlled stationary tones only; diagnostic pitch tracker, not human likeness.'},
        'summary':summary,'results':records}
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
