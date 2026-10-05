"""Stage exact real-reference proposals; does not publish a listening page."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import _json_write,file_hash
from neural_invert.evaluate import serializable
from neural_invert.onset_train import load,predict
from neural_invert.temporal import load_temporal,predict_temporal

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--engine',choices=['Bfxr','Transfxr'],required=True)
args=parser.parse_args()
root=Path('tools/multisynth')
previous=root/'runs/pitch-calibration-listening-v1'
output=root/'runs/onset-v1/real-proposals'/args.engine
if output.exists():raise FileExistsError('Use fresh proposal output')
prior=json.loads((previous/'results.json').read_text())
assert len(prior['results'])==5
experts={arm:load(root/'runs/onset-v1/models'/args.engine/arm) for arm in ('control','onset')}
old=load_temporal(root/'runs/temporal-v3/hybrid-experts'/args.engine)
torch.set_num_threads(1)
output.mkdir(parents=True)
report={'complete':False,'engine':args.engine,'scriptSha256':file_hash(__file__),
        'referenceReportSha256':file_hash(previous/'results.json'),
        'checkpointHashes':{a:m['checkpointSha256'] for a,(_,m) in experts.items()},
        'frozenCheckpointHash':old[1]['checkpointHash'],
        'scope':'Private raw proposal generation on five development references rejected by the user; no new quality claim.',
        'rows':[]}
with Renderer() as renderer:
    for record in prior['results']:
        source=previous/record['folder']/'target.wav'
        target,rate=sf.read(source,dtype='float32')
        assert rate==44100
        objective=MatchObjective(target)
        folder=output/record['folder'];folder.mkdir()
        row={'source':record['source'],'referenceWavSha256':file_hash(source),
             'referenceFloatPcmSha256':audio_hash(target),'folder':record['folder'],'arms':{}}
        for arm in ('control','onset','frozen-v3'):
            proposals=(predict_temporal(*old,target,renderer,count=4) if arm=='frozen-v3'
                       else predict(*experts[arm],target,renderer,count=4))
            candidates=[]
            for i,p in enumerate(proposals):
                candidate={**p,'rank':i}
                try:
                    params,wave=renderer.render(p['synth'],p['params'],p['seed'])
                    path=folder/f'{arm}-{i}.wav';sf.write(path,wave,44100,subtype='FLOAT')
                    candidate.update(params=params,waveFile=str(path.resolve()),waveFileSha256=file_hash(path),audioHash=audio_hash(wave))
                    if len(wave)==0 or np.max(np.abs(wave))<1e-6:
                        candidate['failure']='silent prediction'
                    else:
                        score=float(objective.score_batch([wave])[0])
                        assert np.isfinite(score)
                        candidate['score']=score
                except (ValueError,RuntimeError) as exc:
                    candidate['failure']=str(exc)
                candidates.append(candidate)
            valid=[c for c in candidates if 'score' in c]
            row['arms'][arm]={'candidates':candidates,'selected':min(valid,key=lambda c:c['score']) if valid else None,
                              'expectedProposals':4,'actualProposals':len(proposals)}
        report['rows'].append(row)
        _json_write(output/'results.json',report)
        print(json.dumps({'name':record['source']['name'],'scores':{a:r['selected']['score'] if r['selected'] else None for a,r in row['arms'].items()}}),flush=True)
report['complete']=True
_json_write(output/'results.json',report)
