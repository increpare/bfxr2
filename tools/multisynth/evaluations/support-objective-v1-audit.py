"""Verify appended-zero invariance on retained external recordings, with no fitting."""
from pathlib import Path
import json
import numpy as np
import soundfile as sf
import torch
from multisynth.support_objective import SupportObjective,POLICY,analysis_support
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');A=BASE/'listening_data/2026-10-06-learned-events-v1-quick-01';out=Path(__file__).with_suffix('.json')
if out.exists():raise FileExistsError('Preserve audit')
torch.set_num_threads(1);m=json.loads((A/'manifest.json').read_text());cs={c['id']:c for c in m['candidates']};rows=[]
for t in m['targets']:
    ref,rate=sf.read(A/t['referenceAudio']['file'],dtype='float32');assert rate==44100
    c=cs[t['choice']['preferredCandidateIds'][0]];w,rate=sf.read(A/c['audio']['file'],dtype='float32');assert rate==44100
    obj=SupportObjective(ref);score=obj.score(w);checks=[]
    for seconds in (1,4):
        padded=np.pad(w,(0,seconds*44100));padded_ref=np.pad(ref,(0,seconds*44100))
        assert np.array_equal(analysis_support(w),analysis_support(padded))
        assert np.array_equal(analysis_support(ref),analysis_support(padded_ref))
        same=obj.score(padded);same_ref=SupportObjective(padded_ref).score(w)
        assert abs(score-same)<1e-7 and abs(score-same_ref)<1e-7
        checks.append(dict(paddedSeconds=seconds,candidateScore=same,targetScore=same_ref))
    rows.append(dict(name=t['source']['name'],score=score,checks=checks,fullSamples=len(w),analysisSamples=len(analysis_support(w))))
_json_write(out,dict(complete=True,scriptSha256=file_hash(__file__),codeSha256=file_hash('tools/multisynth/support_objective.py'),
    manifestSha256=file_hash(A/'manifest.json'),policy=POLICY,rows=rows,interpretation='Zero-padding invariance verified. No claim of improved human ranking; threshold remains experimental.'))
print(json.dumps(dict(complete=True,externalReferences=len(rows),invarianceChecks=20)))
