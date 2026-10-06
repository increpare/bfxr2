"""Full-context optimization must not regress to scoring isolated source crops."""
from copy import deepcopy
import json
import numpy as np
from multisynth.joint_timeline import refine

class Timeline:
    def __init__(self): self.inputs=[]
    def render(self, params):
        self.inputs.append(deepcopy(params))
        layers=json.loads(params['layers'])
        # The second, immutable source overlaps every sample of the first.
        audio=np.full(32,sum(l['params']['tone'] for l in layers),np.float32)
        return deepcopy(params),audio

class Objective:
    def __init__(self): self.seen=[]
    def score_batch(self,waves):
        self.seen.extend(np.array(w,copy=True) for w in waves)
        return np.array([float(np.mean((w-5)**2)) for w in waves])

def setup():
    params={'seed':.5,'masterVolume':.5,'spacing':1,'layers':json.dumps([
        {'synth':'Variable','params':{'tone':.2,'seed':.5},'start':0.,'gain':.5,'pitch':0.},
        {'synth':'Fixed','params':{'tone':4.,'seed':.5},'start':.15,'gain':.5,'pitch':0.}])}
    specs={'Variable':{'params':[{'name':'tone','type':'KNOB','min':0,'max':2}]},'Fixed':{'params':[]}}
    return params,specs

def test_joint_uses_complete_overlap_and_preserves_input():
    params,specs=setup();before=deepcopy(params);renderer=Timeline();objective=Objective()
    result=refine(params,renderer,specs,objective,budget=128,seed=37,joint=True)
    assert params==before
    assert result['score']<result['trace'][0]*.05
    assert result['accepted']['source']>0
    assert np.all(np.diff(result['trace'])<=0) and len(result['trace'])==129
    assert all(w.shape==(32,) and w.min()>=4 for w in objective.seen)
    assert json.loads(result['params']['layers'])[0]['params']['seed']==.5
    assert json.loads(result['params']['layers'])[1]['params']=={'tone':4.,'seed':.5}
    assert json.loads(result['params']['layers'])[0]['start']==0
    assert np.array_equal(result['wave'],renderer.render(result['params'])[1])

def test_locked_arm_cannot_change_source_controls():
    params,specs=setup();renderer=Timeline()
    result=refine(params,renderer,specs,Objective(),budget=64,seed=37,joint=False)
    originals=[l['params'] for l in json.loads(params['layers'])]
    assert all([l['params'] for l in json.loads(p['layers'])]==originals for p in renderer.inputs)
    assert result['accepted']['source']==0 and result['attempted']=={'source':0,'timeline':64}
    assert result['score']==result['trace'][0]
