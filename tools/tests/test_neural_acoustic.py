import copy
import numpy as np
import pytest
import torch


def spec():
    return {'name':'Test','presets':['a','b'],'defaults':{'pitch':.4,'shape':0,'masterVolume':.5},
            'params':[{'name':'pitch','type':'RANGE','min':0,'max':1},
                      {'name':'shape','type':'BUTTONSELECT','values':[0,1]}]}


def test_acoustic_controls_do_not_depend_on_guessed_generator():
    from neural_invert.model import MultiSynthModel
    model=MultiSynthModel({'Test':spec()},12,hidden=32,head_mode='acoustic')
    x=torch.randn(6,12)
    a=model(x,'Test',torch.zeros(6,dtype=torch.long))
    b=model(x,'Test',torch.ones(6,dtype=torch.long))
    assert torch.equal(a['continuous'],b['continuous'])
    assert all(torch.equal(x,y) for x,y in zip(a['categorical'],b['categorical']))


def test_acoustic_checkpoint_retains_mode_and_old_model_still_loads(tmp_path):
    from neural_invert.model import MultiSynthModel
    from neural_invert.predict import load_model
    from neural_invert.features import DIM,VERSION,FEATURE_HASH,FEATURE_CODE_HASH
    metadata={'engines':['Test'],'specs':{'Test':spec()},'hidden':32,'headMode':'acoustic',
              'featureDim':DIM,'featureVersion':VERSION,'featureHash':FEATURE_HASH,
              'featureCodeHash':FEATURE_CODE_HASH,'normalization':{'mean':[0.]*DIM,'std':[1.]*DIM}}
    model=MultiSynthModel(metadata['specs'],DIM,32,head_mode='acoustic')
    path=tmp_path/'best.pt';torch.save({'model':model.state_dict(),'metadata':metadata},path)
    loaded,info=load_model(path)
    assert loaded.heads['Test'].head_mode=='acoustic' and info['headMode']=='acoustic'
    metadata['headMode']='unrecognized';torch.save({'model':model.state_dict(),'metadata':metadata},path)
    with pytest.raises(ValueError,match='mode'):load_model(path)


def actual(synth):
    from multisynth.renderer import Renderer
    from neural_invert.schema import ControlSchema
    with Renderer() as r:s=r.specs[synth]
    return s,ControlSchema(s)


def pack(s,schema,params):
    unit,cat=schema.encode(params)
    labels={'continuous':torch.tensor(unit)[None],'categorical':torch.tensor(cat)[None],
            'generator':torch.tensor([0])}
    prediction={'continuous':labels['continuous'].clone().requires_grad_(),
                'categorical':[torch.zeros(1,len(c['values']),requires_grad=True) for c in schema.categorical],
                'generator':torch.zeros(1,len(s['presets']),requires_grad=True)}
    return prediction,labels


def test_bfxr_pitch_octave_error_and_square_only_controls_use_audible_loss():
    from neural_invert.acoustic import acoustic_loss
    from match.optimizer import freq_param_from_hz
    s,schema=actual('Bfxr');p=copy.deepcopy(s['defaults']);p.update(waveType=2,frequency_start=freq_param_from_hz(220))
    prediction,labels=pack(s,schema,p)
    base=acoustic_loss(prediction,labels,s)
    names=[c['name'] for c in schema.continuous]
    # Pulse width is inactive for this sine, including both its value and sweep.
    changed={**prediction,'continuous':prediction['continuous'].clone()}
    changed['continuous'][0,names.index('squareDuty')]=.99
    changed['continuous'][0,names.index('dutySweep')]=.99
    assert acoustic_loss(changed,labels,s).item()==pytest.approx(base.item())
    pitched={**prediction,'continuous':prediction['continuous'].clone()}
    pitched['continuous'][0,names.index('frequency_start')]=freq_param_from_hz(440)
    assert acoustic_loss(pitched,labels,s).item()>base.item()+.5
    acoustic_loss(pitched,labels,s).backward()
    assert torch.isfinite(prediction['continuous'].grad).all()


def test_inactive_vibrato_rate_and_static_transition_curves_do_not_create_targets():
    from neural_invert.acoustic import acoustic_loss
    s,schema=actual('Bfxr');p=copy.deepcopy(s['defaults']);p.update(vibratoDepth=0.)
    prediction,labels=pack(s,schema,p);base=acoustic_loss(prediction,labels,s)
    prediction['continuous']=prediction['continuous'].clone()
    names=[c['name'] for c in schema.continuous]
    prediction['continuous'][0,names.index('vibratoSpeed')]=1.
    assert acoustic_loss(prediction,labels,s).item()==pytest.approx(base.item())
    p.update(pitch_jump_amount=0.,pitch_jump_2_amount=0.)
    prediction,labels=pack(s,schema,p);base=acoustic_loss(prediction,labels,s)
    prediction['continuous']=prediction['continuous'].clone()
    prediction['continuous'][0,names.index('pitch_jump_repeat_speed')]=1.
    assert acoustic_loss(prediction,labels,s).item()==pytest.approx(base.item())


def test_pluck_motion_speed_and_single_string_coupling_remain_audible_targets():
    from neural_invert.acoustic import acoustic_loss
    s,schema=actual('Pluckr');p=copy.deepcopy(s['defaults']);p.update(strings=1,tremolo=0.,vibrato=.2,coupling=0.)
    prediction,labels=pack(s,schema,p);base=acoustic_loss(prediction,labels,s)
    names=[c['name'] for c in schema.continuous]
    for name in ('tremoloRate','coupling'):
        changed={**prediction,'continuous':prediction['continuous'].clone()}
        changed['continuous'][0,names.index(name)]=1.
        assert acoustic_loss(changed,labels,s).item()>base.item(),name
    # The same rate becomes inactive only with neither audible modulation.
    p['vibrato']=0.
    prediction,labels=pack(s,schema,p);base=acoustic_loss(prediction,labels,s)
    changed={**prediction,'continuous':prediction['continuous'].clone()}
    for name in ('tremoloRate','strum'):changed['continuous'][0,names.index(name)]=1.
    assert acoustic_loss(changed,labels,s).item()==pytest.approx(base.item())


def test_static_transition_curves_are_not_audible_targets():
    from neural_invert.acoustic import acoustic_loss
    s,schema=actual('Transfxr');p=copy.deepcopy(s['defaults']);p['pitch']={'start':.5,'end':.5,'curve':'Linear'}
    prediction,labels=pack(s,schema,p);base=acoustic_loss(prediction,labels,s)
    i=[c['name'] for c in schema.categorical].index('pitch.curve')
    prediction['categorical'][i]=torch.tensor([[20.]+[0.]*(len(schema.categorical[i]['values'])-1)])
    assert acoustic_loss(prediction,labels,s).item()==pytest.approx(base.item())


def test_acoustic_proposals_use_distinct_discrete_choices():
    from neural_invert.predict import categorical_proposals
    logits=[torch.tensor([[3.,2.,-10.]]),torch.tensor([[2.,1.]])]
    controls=[{'name':'waveType'},{'name':'pitch.curve'}]
    assert categorical_proposals(logits,controls,2)==[[0,0],[1,0]]
    assert categorical_proposals([],[],2)==[[]]


def test_train_acoustic_checkpoint_through_real_dataset(tmp_path):
    from neural_invert.data import generate_dataset
    from neural_invert.train import train_model
    from neural_invert.predict import load_model,predict
    from multisynth.renderer import Renderer
    data=tmp_path/'data';generate_dataset(data,8,1,synths=['Footsteppr'])
    report=train_model(data,tmp_path/'model',epochs=1,hidden=32,threads=1,head_mode='acoustic',loss_mode='acoustic')
    model,metadata=load_model(tmp_path/'model')
    assert metadata['headMode']=='acoustic' and metadata['lossPolicy']['version']=='acoustic-controls-v2'
    with Renderer() as renderer:
        p=renderer.sample('Footsteppr',renderer.specs['Footsteppr']['presets'][0],919)
        _,wave=renderer.render('Footsteppr',p,928)
        rows=predict(model,metadata,wave,renderer,2)
    assert rows and all(r['provenance']['headMode']=='acoustic' for r in rows)
    assert np.isfinite(report['bestValidationLoss'])
