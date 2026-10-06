"""Recover a post-fit verification failure without changing any search decision.

The frozen runner accidentally passed exported PCM through audition_pcm again
in its verification assertion. PCM16 normalization is not idempotent. Search
already scored exactly one export; verify with bare MatchObjective instead.
Completed fits are reused; the interrupted deterministic fit must reproduce its
already written WAV exactly. Independent remaining arms run in three workers.
"""
import importlib.util
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.timeline import TimelineRenderer
from multisynth.renderer import Renderer
from multisynth.joint_timeline import refine
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/joint-events-v1'
ARCHIVE=BASE/'listening_data/2026-10-06-learned-events-v1-quick-01'
RECEIPT=BASE/'evaluations/joint-events-v1-recovery.json'

def frozen():
    spec=importlib.util.spec_from_file_location('frozen_joint_events',BASE/'evaluations/joint-events-v1.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def arm_job(task):
    i,arm=task;mod=frozen();p=mod.checked();entry=p['rows'][i];dest=ROOT/f'{i+1:03d}'
    dest.mkdir(exist_ok=True);torch.set_num_threads(1)
    reference,rate=sf.read(ARCHIVE/entry['target']['referenceAudio']['file'],dtype='float32');assert rate==44100
    objective=mod.Objective(reference);bare=MatchObjective(reference);started=time.monotonic()
    with Renderer() as source,TimelineRenderer() as timeline:
        assert timeline.inventory==p['inventory'] and source.inventory['sourceHash']==timeline.inventory['baseSourceHash']
        original_render=timeline.render;calls=0
        def progress(*args,**kwargs):
            nonlocal calls
            out=original_render(*args,**kwargs);calls+=1
            if calls%256==0:print(json.dumps(dict(target=i+1,arm=arm,renders=calls)),flush=True)
            return out
        timeline.render=progress
        result=refine(entry['initial']['params'],timeline,source.specs,objective,p['budget'],entry['seed'],joint=arm=='joint')
        # Persist source controls before verification so a failed check is recoverable.
        provisional={k:v for k,v in result.items() if k!='wave'}
        _json_write(dest/(arm+'-fit-recovery.json'),provisional)
        canonical,native=timeline.render(result['params'],uncached=True);pcm=audition_pcm(native)
        assert canonical==result['params'] and np.array_equal(native,result['wave'])
        assert abs(result['score']-bare.score(pcm))<1e-6
        path=dest/(arm+'.wav')
        if path.exists():
            previous,rate=sf.read(path,dtype='float32');assert rate==44100 and np.array_equal(previous,pcm),'Interrupted fit failed exact deterministic replay'
        else:sf.write(path,pcm,44100,subtype='PCM_16')
        option=provisional|dict(role=arm,synth='Stackr',seed=0,sourceHash=timeline.inventory['sourceHash'],
            nativeHash=audio_hash(native),auditionHash=audio_hash(pcm),wavSha256=file_hash(path),seconds=time.monotonic()-started,
            recoveryScriptSha256=file_hash(__file__))
        _json_write(dest/(arm+'.json'),option)
        print(json.dumps(dict(done=i+1,arm=arm,score=result['score'],seconds=option['seconds'])),flush=True)
    return i,arm

def main():
    mod=frozen();p=mod.checked()
    if (ROOT/'results.json').exists() or RECEIPT.exists():raise FileExistsError('Preserve recovery')
    preserved={str(f):file_hash(f) for f in sorted(ROOT.glob('*/*')) if f.is_file()}
    jobs=[(i,arm) for i in range(4) for arm in p['arms'] if not (ROOT/f'{i+1:03d}'/(arm+'.json')).exists()]
    receipt=dict(complete=False,scriptSha256=file_hash(__file__),protocolSha256=file_hash(ROOT/'protocol.json'),
        reason='Post-fit verifier normalized already exported PCM a second time. Search itself uses one export. Use bare MatchObjective for verification.',
        evidence=dict(path=str(ROOT/'002/joint.wav'),samples=455464,peak=.499969482421875,changedSamplesOnSecondNormalization=21260,
            singleScore=1.1733049921601075,doubleScore=1.330623099725773,maxSampleDifference=1/32768),
        preservedFiles=preserved,recomputedJobs=jobs,workers=3,
        scope='Same exact frozen seeds, initial controls, budgets and search code. Parallel execution changes timing only. Interrupted footstep joint fit repeats2048 identical attempts and must reproduce saved PCM; disclose duplicate compute.')
    _json_write(RECEIPT,receipt)
    with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(arm_job,jobs))
    rows=[]
    for i,entry in enumerate(p['rows']):
        dest=ROOT/f'{i+1:03d}';options=[json.loads((dest/(arm+'.json')).read_text()) for arm in p['arms']]
        row=dict(entry=entry,options=options)
        if (dest/'result.json').exists():assert json.loads((dest/'result.json').read_text())==row
        else:_json_write(dest/'result.json',row)
        rows.append(row)
    assert all(file_hash(f)==h for f,h in preserved.items())
    assert mod.checked()==p
    receipt['complete']=True;receipt['exactInterruptedReplayVerified']=True;_json_write(RECEIPT,receipt)
    report=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),rows=rows,recoverySha256=file_hash(RECEIPT))
    _json_write(ROOT/'results.json',report);_json_write(BASE/'evaluations/joint-events-v1-evaluation.json',report)

if __name__=='__main__':main()
