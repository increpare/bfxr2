"""Diagnostic only: a sound should not become a better match by adding zeros."""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from neural_invert.experiment import audition_pcm
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');A=BASE/'listening_data/2026-10-06-learned-events-v1-quick-01'
out=Path(__file__).with_suffix('.json')
if out.exists():raise FileExistsError('Preserve probe')
torch.set_num_threads(1);m=json.loads((A/'manifest.json').read_text());cs={c['id']:c for c in m['candidates']};rows=[]
for t in m['targets']:
    ref,rate=sf.read(A/t['referenceAudio']['file'],dtype='float32');assert rate==44100
    c=cs[t['choice']['preferredCandidateIds'][0]];w,rate=sf.read(A/c['audio']['file'],dtype='float32');assert rate==44100
    obj=MatchObjective(ref);scores={str(s):obj.score(np.pad(w,(0,s*44100))) for s in (0,1,4)}
    rows.append(dict(name=t['source']['name'],candidateId=c['id'],audioSha256=file_hash(A/c['audio']['file']),scoresByAppendedZeroSeconds=scores))
path=BASE/'runs/joint-events-v1/002/joint.wav';w,rate=sf.read(path,dtype='float32');assert rate==44100
ref,rate=sf.read(A/m['targets'][1]['referenceAudio']['file'],dtype='float32');assert rate==44100
obj=MatchObjective(ref);again=audition_pcm(w)
components={name:obj.score_components(x) for name,x in [('once',w),('twice',again)]}
result=dict(complete=True,scriptSha256=file_hash(__file__),manifestSha256=file_hash(A/'manifest.json'),
    rows=rows,interruptedWave=dict(path=str(path),sha256=file_hash(path),seconds=len(w)/44100,
        supportAboveOneThousandthPeakSeconds=(int(np.flatnonzero(abs(w)>.001*abs(w).max())[-1])+1)/44100,
        changedSamples=int(np.sum(w!=again)),maximumSampleDifference=float(abs(w-again).max()),components=components),
    scope='Unchanged heard signals with appended digital silence. This is an objective-invariance diagnostic, not fresh human labels or evidence of audible improvement.')
_json_write(out,result);print(json.dumps(result),flush=True)
