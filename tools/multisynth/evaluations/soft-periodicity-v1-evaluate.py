"""Frozen opt-in objective versus legacy on exact retained judgments."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.preference import training_pairs,score_summary
from multisynth.embedding import family_groups
from multisynth.coverage import verify_archived_audio
from neural_invert.data import file_hash,_json_write
BASE=Path('tools/multisynth');OUTPUT=BASE/'evaluations/soft-periodicity-v1-evaluation.json'

def main():
    if OUTPUT.exists():raise FileExistsError('Preserve original diagnostic')
    torch.set_num_threads(1)
    roots=sorted(p.parent for p in (BASE/'listening_data').glob('*/manifest.json'))
    data=training_pairs(roots);audio={};refs=[]
    for root in roots:
        m=json.loads((root/'manifest.json').read_text())
        for t in m['targets']:
            a=t['referenceAudio'];audio[a['pcmSha256']]=(root,a);refs.append(dict(pcm=a['pcmSha256'],source=t['source']))
        for c in m['candidates']:audio[c['audio']['pcmSha256']]=(root,c['audio'])
    families=dict(zip([r['pcm'] for r in refs],family_groups(refs)))
    groups=np.array([families[r] for r in data.groups]);wave_cache={}
    def read(pcm):
        if pcm not in wave_cache:
            root,a=audio[pcm];verify_archived_audio(root,a)
            x,sr=sf.read(root/a['file'],dtype='float32');assert sr==44100
            wave_cache[pcm]=x
        return wave_cache[pcm]
    components={};objectives={};observations=[]
    for i,o in enumerate(data.observations):
        r=o['referencePcmSha256']
        if r not in objectives:objectives[r]={'legacy':MatchObjective(read(r)),'soft':SoftPeriodicityObjective(read(r))}
        for pcm in [o['candidatePcmSha256A'],o['candidatePcmSha256B']]:
            key=(r,pcm)
            if key not in components:components[key]={k:obj.score_components(read(pcm)) for k,obj in objectives[r].items()}
        a,b=[components[(r,o[k])] for k in ['candidatePcmSha256A','candidatePcmSha256B']]
        pred={k:sum(a[k].values())-sum(b[k].values()) for k in objectives[r]}
        observations.append({**o,'family':families[r],'componentsA':a,'componentsB':b,'predictions':pred})
    scores={k:score_summary(np.array([o['predictions'][k] for o in observations]),data.y,groups) for k in ['legacy','soft']}
    subsets={}
    for label,mask in [('historical',np.array([o['archive']!='2026-10-05-cue-calibration-quick-01' for o in observations])),('calibration',np.array([o['archive']=='2026-10-05-cue-calibration-quick-01' for o in observations]))]:
        subsets[label]={k:score_summary(np.array([o['predictions'][k] for o in observations])[mask],data.y[mask],groups[mask]) for k in scores}
    passed=scores['soft']['pairAccuracy']>=scores['legacy']['pairAccuracy']
    result=dict(complete=True,scriptSha256=file_hash(__file__),objectiveSha256=file_hash(BASE/'soft_periodicity.py'),
        legacyCodeHashes={str(p):file_hash(p) for p in [Path('tools/match/objective.py'),Path('tools/match/features.py')]},
        archives=data.archives,scores=scores,subsets=subsets,observations=observations,
        gate=dict(historicalNonRegression=passed),
        interpretation='Development diagnostic with fixed weights, not independent validation or proof of adequate synth output. Calibration edits are not synth examples.')
    _json_write(OUTPUT,result);print(json.dumps(dict(scores=scores,subsets=subsets,gate=result['gate']),indent=2),flush=True)
if __name__=='__main__':main()
