"""Measure the retained original Bfxr network before its expensive optimizer.

Four native-DSP proposals per reference. Different training data, objective and
renderer make this a historical comparator, not an input-only ablation.
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from invert.predict import load_checkpoint, predict_wave
from match.bfxr_io import ParamSpace
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import _json_write,file_hash
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.temporal_gallery import backend_provenance

ROOT=Path('tools/multisynth/runs/onset-v1/original-raw')
CHECKPOINT=Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
LISTS=[Path('tools/multisynth/evaluations')/n for n in ('onset-v1-targets.json','onset-v1-probe-targets.json')]
if ROOT.exists():raise FileExistsError('Fresh original baseline directory required')
torch.set_num_threads(1)
assert file_hash(CHECKPOINT)=='47f2b5ff6bfdd4abc503810a3a0b9b0c8fed2398a66b3b75b18dcaf0b87f8d98'
model,metadata=load_checkpoint(CHECKPOINT)
space=ParamSpace()
ROOT.mkdir()
report={'complete':False,'scriptSha256':file_hash(__file__),'checkpointSha256':file_hash(CHECKPOINT),
        'targetsSha256':{str(p):file_hash(p) for p in LISTS},'candidateBudget':4,'seed':1234,
        'scope':__doc__,'rows':[]}
with Renderer() as target_renderer, BfxrRenderer(jobs=1) as native:
    report['backend']=backend_provenance(native)
    for target in [r for p in LISTS for r in json.loads(p.read_text())['rows']]:
        assert target['sourceHash']==target_renderer.inventory['sourceHash']
        params,wave=target_renderer.render(target['sourceSynth'],target['sourceParams'],target['sourceSeed'])
        assert params==target['sourceParams'] and audio_hash(wave)==target['audioHash']
        objective=MatchObjective(wave)
        pitch=descriptor_pitch(wave)
        path=ROOT/target['id'];path.mkdir()
        guesses=predict_wave(model,metadata,wave,top_k=4)
        candidates=[]
        for i,guess in enumerate(guesses):
            controls=space.params_dict(guess['unit'],guess['wave_type'])
            candidate={'params':controls,'seed':1234,'probability':guess['prob'],'waveType':guess['wave_type'],'rank':i}
            rendered=native.render(controls,seed=1234)
            if rendered is None:
                candidate['failure']='native render failed'
            else:
                dest=path/f'{i}.wav';sf.write(dest,rendered,44100,subtype='FLOAT')
                candidate.update(waveFile=str(dest.resolve()),waveFileSha256=file_hash(dest),audioHash=audio_hash(rendered))
                if not len(rendered) or np.max(np.abs(rendered))<1e-6:
                    candidate['failure']='silent prediction'
                else:
                    score=float(objective.score_batch([rendered])[0])
                    assert np.isfinite(score)
                    candidate.update(score=score,pitchComparison=compare_descriptor_pitch(pitch,descriptor_pitch(rendered)))
            candidates.append(candidate)
        valid=[c for c in candidates if 'score' in c]
        row={**target,'candidates':candidates,'selected':min(valid,key=lambda c:c['score']) if valid else None}
        report['rows'].append(row)
        _json_write(ROOT/'results.json',report)
        print(json.dumps({'target':target['id'],'score':row['selected']['score'] if row['selected'] else None}),flush=True)
report['complete']=True
_json_write(ROOT/'results.json',report)
