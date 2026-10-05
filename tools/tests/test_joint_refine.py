import copy
import json
import numpy as np
import pytest
from multisynth.joint_refine import MixSpace, optimize

SPECS={'Tone':{'name':'Tone','params':[
    {'name':'x','type':'KNOB','min':0.,'max':1.},
    {'name':'kind','type':'BUTTONSELECT','values':[0,1,2]},
    {'name':'seed','type':'KNOB','min':0.,'max':1.}]}}

def patch(n=2):
    s={'synth':'Tone','params':{'x':.5,'kind':0,'seed':.7},'renderSeed':.3}
    return {'sources':json.dumps([s,s if n==2 else None]),'balance':.5,'seed':.5,'masterVolume':.5}

def test_mutation_both_slots_fixed_identity_and_bounds():
    p=patch();old=copy.deepcopy(p);space=MixSpace(SPECS);rng=np.random.default_rng(37)
    changed=[False,False];balances=[]
    for _ in range(100):
        q=space.mutate(p,rng,.6);src=json.loads(q['sources'])
        for i,s in enumerate(src):
            assert s['synth']=='Tone' and s['renderSeed']==.3 and s['params']['seed']==.7
            assert 0<=s['params']['x']<=1 and s['params']['kind'] in [0,1,2]
            changed[i]|=s['params']['x']!=.5
        assert .1<=q['balance']<=.9
        balances.append(q['balance'])
        assert q['masterVolume']==.5 and q['seed']==.5
    assert all(changed) and len(set(balances))>1 and p==old

def test_single_and_deterministic_mutation():
    space=MixSpace(SPECS);p=patch(1)
    a=space.mutate(p,np.random.default_rng(1),.1)
    b=space.mutate(p,np.random.default_rng(1),.1)
    assert a==b and json.loads(a['sources'])[1] is None and a['balance']==.5
    with pytest.raises(ValueError):space.mutate({**p,'sources':'[]'},np.random.default_rng(1),.1)

def test_budget_incumbent_and_reproducible_search():
    calls=[]
    def evaluate(p):
        calls.append(p)
        return p, abs(json.loads(p['sources'])[0]['params']['x']-.12)
    a=optimize([patch(1)],MixSpace(SPECS),evaluate,budget=60,seed=5)
    assert len(calls)==61 and a['attempts']==60 and a['failures']==0
    assert a['score']<a['initialScore'] and np.all(np.diff(a['trace'])<=0)
    b=optimize([patch(1)],MixSpace(SPECS),evaluate,budget=60,seed=5)
    assert a==b

def test_failed_and_nonfinite_proposals_do_not_replace_incumbent():
    calls=[0]
    def evaluate(p):
        calls[0]+=1
        if calls[0]==1:return p,1.
        if calls[0]%2:raise ValueError('bad render')
        return p,float('nan')
    a=optimize([patch(1)],MixSpace(SPECS),evaluate,budget=10,seed=5)
    assert a['score']==1 and a['failures']==10 and len(a['trace'])==11
    with pytest.raises(ValueError):optimize([],MixSpace(SPECS),evaluate,budget=1,seed=5)


def test_frozen_protocol_rejects_changed_search_budget(tmp_path,monkeypatch):
    import importlib.util
    from pathlib import Path
    path=Path(__file__).parents[1]/'multisynth/evaluations/mixr-joint-v1.py'
    spec=importlib.util.spec_from_file_location('joint_experiment',path)
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    # The original digest is supplied independently of the subsequently changed file.
    original={'budgetPerArm':512}
    protocol=tmp_path/'protocol.json';protocol.write_text(json.dumps(original))
    receipt=tmp_path/'evaluations';receipt.mkdir()
    (receipt/'mixr-joint-v1-protocol.json').write_text(json.dumps({'protocolSha256':experiment.file_hash(protocol)}))
    protocol.write_text(json.dumps({'budgetPerArm':1}))
    monkeypatch.setattr(experiment,'ROOT',tmp_path);monkeypatch.setattr(experiment,'BASE',tmp_path)
    with pytest.raises(AssertionError):experiment.verify({'budgetPerArm':1})
