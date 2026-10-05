import numpy as np
import pytest
import torch


def test_curve_formulas_and_order():
    from neural_invert.gesture import curve_bank, CURVES
    t=torch.tensor([0.,.25,.5,.75,1.])
    x=curve_bank(t,CURVES)
    torch.testing.assert_close(x[0],t)
    torch.testing.assert_close(x[1],t*t)
    torch.testing.assert_close(x[4],torch.tensor([0.,.5,1.,.5,0.]))
    torch.testing.assert_close(x[7],torch.tensor([0.,.25,.5,.75,1.]))
    assert x.shape==(8,5) and torch.isfinite(x).all()
    with pytest.raises(ValueError):curve_bank(t,['Unknown'])


def test_expected_gesture_error_penalizes_wrong_curve_and_has_gradients():
    from neural_invert.gesture import gesture_energy
    from neural_invert.schema import ControlSchema
    from multisynth.renderer import Renderer
    with Renderer() as renderer:spec=renderer.specs['Transfxr']
    schema=ControlSchema(spec)
    params=spec['defaults'].copy()
    params.update(pitch=dict(start=.7,end=.3,curve='Linear'),vibrato=dict(start=0.,end=0.,curve='Linear'))
    unit,cats=schema.encode(params)
    labels=dict(continuous=torch.tensor(unit[None]),categorical=torch.tensor(cats[None]))
    logits=[torch.full((1,1,len(c['values'])),-20.) for c in schema.categorical]
    for i,k in enumerate(cats):logits[i][0,0,k]=20.
    numeric=torch.tensor(unit[None,None],requires_grad=True)
    pred=dict(continuous=numeric,categorical=logits)
    assert gesture_energy(pred,labels,spec).item()<1e-10
    pitch_cat=next(i for i,c in enumerate(schema.categorical) if c['name']=='pitch.curve')
    logits[pitch_cat]=torch.zeros_like(logits[pitch_cat],requires_grad=True)
    loss=gesture_energy(pred,labels,spec).sum()
    assert loss.item()>.1
    loss.backward()
    assert torch.isfinite(numeric.grad).all() and numeric.grad.abs().sum()>0
    assert logits[pitch_cat].grad[0,0,cats[pitch_cat]]<0
    # Two opposing endpoint errors have a correct mean, but neither is correct.
    wrong=numeric.detach().clone()
    pitch_start=next(i for i,c in enumerate(schema.continuous) if c['name']=='pitch.start')
    wrong[:,:,pitch_start]+=.1
    other=numeric.detach().clone();other[:,:,pitch_start]-=.1
    exact_logits=[torch.full_like(x,-20.) for x in logits]
    for i,k in enumerate(cats):exact_logits[i][0,0,k]=20.
    a=gesture_energy(dict(continuous=wrong,categorical=exact_logits),labels,spec)
    b=gesture_energy(dict(continuous=other,categorical=exact_logits),labels,spec)
    assert a.item()>.1 and b.item()>.1


def test_fixed_epoch_training_reloads_and_reproduces_loss(tmp_path):
    from neural_invert.gesture_train import fit, epoch
    from neural_invert.temporal import TemporalExpert
    from neural_invert.schema import ControlSchema
    from multisynth.renderer import Renderer
    with Renderer() as renderer:spec=renderer.specs['Transfxr']
    schema=ControlSchema(spec);unit,cats=schema.encode(spec['defaults'])
    shard=dict(features=torch.randn(8,4083),continuous=torch.tensor(np.stack([unit]*8)),
               categorical=torch.tensor(np.stack([cats]*8)),train=torch.arange(6),val=torch.arange(6,8))
    model=TemporalExpert(spec,1,'flat')
    weights=dict(train=torch.ones(8),val=torch.ones(8))
    normalization=dict(mean=[0.]*4083,std=[1.]*4083)
    report=fit(model,shard,weights,normalization,tmp_path,dict(testOnly=True),1.,epochs=2,batch_size=4,device='cpu')
    saved=torch.load(tmp_path/'last.pt',weights_only=True)
    model.load_state_dict(saved['model'])
    result=epoch(model,shard,shard['val'],weights['val'],torch.zeros(4083),torch.ones(4083),4,'cpu',1.)
    assert report['complete'] and saved['epoch']==2
    assert result['total']==pytest.approx(saved['validation']['total'],abs=1e-7)


def test_long_sound_vibrato_cannot_alias_to_zero():
    from neural_invert.gesture import gesture_energy
    from neural_invert.schema import ControlSchema
    from multisynth.renderer import Renderer
    with Renderer() as renderer:spec=renderer.specs['Transfxr']
    schema=ControlSchema(spec);params=spec['defaults'].copy()
    params.update(duration=3.9375,pitch=dict(start=.5,end=.5,curve='Linear'),vibrato=dict(start=1.,end=1.,curve='Linear'))
    unit,cats=schema.encode(params)
    labels=dict(continuous=torch.tensor(unit[None]),categorical=torch.tensor(cats[None]))
    pred_unit=torch.tensor(unit[None,None])
    for i,c in enumerate(schema.continuous):
        if c['name'].startswith('vibrato.'):pred_unit[:,:,i]=0.
    logits=[torch.full((1,1,len(c['values'])),-20.) for c in schema.categorical]
    for i,k in enumerate(cats):logits[i][0,0,k]=20.
    loss=gesture_energy(dict(continuous=pred_unit,categorical=logits),labels,spec)
    assert loss.item()==pytest.approx(.16**2/2,rel=.01)


def test_render_gate_rejects_missing_cases_and_gesture_regressions():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('gesture_evaluation',Path(__file__).parents[1]/'multisynth/evaluations/gesture-v2-evaluate.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    control=dict(targets=32,missing=0,meanObjective=4.,failures=0,silence=0,
        staticPass=8,reliablePitch=24,movingDirectionPass=10,movingContourCoverage=.5)
    good={**control,'meanObjective':3.7}
    assert module.gate(control,good)['passed']
    for key,value in dict(missing=1,silence=1,staticPass=7,reliablePitch=23,
                          movingDirectionPass=9,movingContourCoverage=.49).items():
        assert not module.gate(control,{**good,key:value})['passed']
    assert not module.gate({**control,'missing':1},good)['passed']
