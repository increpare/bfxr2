import importlib.util
import numpy as np
import pytest


def module():
    assert importlib.util.find_spec('neural_invert.onset') is not None, 'onset feature/model module is missing'
    from neural_invert import onset
    return onset


def test_onset_retains_event_time_without_stretching():
    m = module()
    a = np.zeros(22050, np.float32)
    a[0] = 1
    a[2205] = 1
    b = np.pad(a, (0, 22050))
    x = m.onset_features(a)
    assert x.shape == (64, 128)
    np.testing.assert_allclose(x, m.onset_features(b), atol=1e-6)
    power = (x + 1).mean(0)
    assert abs(np.argmax(power[10:]) + 10 - 2205 / 128) <= 2
    assert np.all(x[:, 25:] == -1)


def test_onset_gain_silence_and_invalid_audio():
    m = module()
    wave = np.sin(2*np.pi*1100*np.arange(12000)/44100).astype(np.float32)
    np.testing.assert_allclose(m.onset_features(wave), m.onset_features(wave*.13), atol=1e-5)
    assert np.all(m.onset_features(np.zeros(100)) == -1)
    for x in ([], [np.nan], [np.inf], np.zeros((2, 30))):
        with pytest.raises(ValueError):
            m.onset_features(x)


def test_onset_ablation_masks_only_extra_input_and_has_gradients():
    import torch
    from multisynth.renderer import Renderer
    assert importlib.util.find_spec('neural_invert.onset_inverse') is not None, 'onset inverse module is missing'
    from neural_invert.onset_inverse import OnsetExpert
    with Renderer() as renderer:
        spec = renderer.specs['Transfxr']
    torch.manual_seed(7)
    control = OnsetExpert(spec, use_onset=False)
    treatment = OnsetExpert(spec, use_onset=True)
    treatment.load_state_dict(control.state_dict())
    coarse = torch.randn(2, 4083)
    onset = torch.randn(2, 64, 128, requires_grad=True)
    a = control(coarse, onset)
    b = control(coarse, torch.zeros_like(onset))
    torch.testing.assert_close(a['continuous'], b['continuous'])
    for x,y in zip(a['categorical'],b['categorical']):
        torch.testing.assert_close(x,y)
    t = treatment(coarse,onset)
    assert not torch.allclose(t['continuous'],a['continuous'])
    t['continuous'].sum().backward()
    assert onset.grad.abs().sum()>0 and torch.isfinite(onset.grad).all()
    assert t['continuous'].shape[:2] == (2,1)


def test_fitting_saves_best_epoch_and_can_reproduce_validation(tmp_path):
    import torch
    from multisynth.renderer import Renderer
    from neural_invert import onset_inverse
    assert hasattr(onset_inverse, 'fit'), 'onset fitting loop is missing'
    with Renderer() as renderer:
        spec = renderer.specs['Bfxr']
    from neural_invert.schema import ControlSchema
    unit, cats = ControlSchema(spec).encode(spec['defaults'])
    torch.manual_seed(42)
    shard = {'features':torch.randn(8,4083),
             'continuous':torch.tensor(np.stack([unit]*8)),
             'categorical':torch.tensor(np.stack([cats]*8)),
             'train':torch.arange(6), 'val':torch.arange(6,8)}
    onset = torch.rand(8,64,128)-1
    model=onset_inverse.OnsetExpert(spec)
    weights={'train':torch.ones(8),'val':torch.ones(8)}
    report=onset_inverse.fit(model,shard,onset,torch.zeros(4083),torch.ones(4083),weights,
                             tmp_path,{'testOnly':True},epochs=2,batch_size=4,device='cpu')
    saved=torch.load(tmp_path/'best.pt',weights_only=True)
    model.load_state_dict(saved['model'])
    loss=onset_inverse.epoch(model,shard,onset,shard['val'],weights['val'],torch.zeros(4083),
                              torch.ones(4083),4,'cpu')
    assert loss == pytest.approx(saved['validation'], abs=1e-7)
    assert saved['validation'] == min(x['validation'] for x in report['history'])
    assert report['complete'] and len(report['history'])==2


def test_render_gate_cannot_hide_missing_outputs_or_pitch_regression():
    assert importlib.util.find_spec('neural_invert.onset_eval') is not None, 'onset evaluation module is missing'
    from neural_invert.onset_eval import gate
    a={'meanObjective':2.,'missing':0,'failedRenders':0,'staticPass':8,'targets':32}
    b={**a,'meanObjective':1.8}
    assert gate(a,b)['passed']
    assert not gate(a,{**b,'missing':1})['passed']
    assert not gate(a,{**b,'staticPass':7})['passed']
    assert not gate(a,{**b,'failedRenders':1})['passed']
    assert not gate(a,{**b,'meanObjective':1.95})['passed']


def test_derived_features_require_exact_actual_dsp_pcm():
    from multisynth.renderer import Renderer
    from neural_invert.benchmark import audio_hash
    from neural_invert.onset_data import replay_chunk
    with Renderer() as renderer:
        params,wave=renderer.render('Bfxr',renderer.specs['Bfxr']['defaults'],42)
        source_hash=renderer.inventory['sourceHash']
    row={'params':params,'seed':42,'audioHash':audio_hash(wave),'parameterHash':'test'}
    derived=replay_chunk('Bfxr',[row],source_hash)
    np.testing.assert_array_equal(derived[0],module().onset_features(wave).astype('<f2'))
    with pytest.raises(ValueError,match='replay mismatch'):
        replay_chunk('Bfxr',[{**row,'audioHash':'incorrect'}],source_hash)
