"""Actual Mixr codec and masked joint parameter reconstruction contracts."""
from copy import deepcopy
import json

import numpy as np
import pytest
import torch


@pytest.fixture(scope='module')
def specs():
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        return {name: deepcopy(renderer.specs[name]) for name in ('Boomr', 'Transfxr')}


@pytest.fixture
def codec(specs):
    from neural_invert.pair_model import PairCodec
    return PairCodec(specs)


def patch(specs, structure=2):
    sources = [dict(synth=name, name=name, params=deepcopy(specs[name]['defaults']), renderSeed=.5)
               if structure in (i, 2) else None for i, name in enumerate(('Boomr', 'Transfxr'))]
    return dict(sources=json.dumps(sources), balance=.37 if structure == 2 else float(structure),
                seed=.5, masterVolume=.5)


@pytest.mark.parametrize('structure', [0, 1, 2])
def test_codec_roundtrips_actual_mixr_canonical_controls(codec, specs, structure):
    from multisynth.composition import CompositionRenderer
    with CompositionRenderer() as renderer:
        canonical, _ = renderer.render(patch(specs, structure))
        unit, categories = codec.encode(canonical)
        assert unit.dtype == np.float32 and categories.dtype == np.int64
        assert categories[codec.structure_index] == structure
        decoded = codec.decode(unit, categories)
        replay, wave = renderer.render(decoded, uncached=True)
    again, again_categories = codec.encode(replay)
    np.testing.assert_allclose(again, unit, atol=1e-7)
    np.testing.assert_array_equal(again_categories, categories)
    assert np.isfinite(wave).all() and len(wave)
    assert decoded['seed'] == decoded['masterVolume'] == .5
    sources = json.loads(decoded['sources'])
    for i, source in enumerate(sources):
        assert (source is not None) == (structure in (i, 2))
        if source:
            assert source['renderSeed'] == source['params']['masterVolume'] == .5
            for key in codec.schemas[source['synth']].fixed_randomness:
                assert source['params'][key] == .5


def prediction(codec, params, modes=4):
    unit, cat = codec.encode(params)
    true, categories = torch.tensor(unit)[None], torch.tensor(cat)[None]
    pred = dict(continuous=true[:, None].repeat(1, modes, 1),
                categorical=[torch.zeros(1, modes, size) for size in codec.cat_sizes],
                mode_logits=torch.zeros(1, modes))
    return pred, true, categories


@pytest.mark.parametrize('structure', [0, 1])
def test_absent_source_and_singleton_balance_have_zero_loss_and_gradient(codec, specs, structure):
    from neural_invert.pair_model import pair_energy
    pred, true, cat = prediction(codec, patch(specs, structure))
    base = pair_energy(pred, true, cat, codec)
    absent = ('Boomr', 'Transfxr')[1-structure]
    ns, cs = codec.continuous_slices[absent], codec.categorical_slices[absent]
    pred['continuous'][:, :, ns] = .99
    pred['continuous'][:, :, codec.balance_index] = .88
    for i in range(cs.start, cs.stop):
        pred['categorical'][i][:, :, 0] = 20
    assert torch.equal(base, pair_energy(pred, true, cat, codec))
    pred['continuous'].requires_grad_()
    pair_energy(pred, true, cat, codec).sum().backward()
    assert torch.count_nonzero(pred['continuous'].grad[:, :, ns]) == 0
    assert torch.count_nonzero(pred['continuous'].grad[:, :, codec.balance_index]) == 0


def test_disabled_morph_and_equal_endpoint_curve_are_masked(codec, specs):
    from neural_invert.pair_model import pair_energy
    params = patch(specs)
    sources = json.loads(params['sources'])
    sources[1]['params']['tone'].update(start=.4, end=.4)
    params['sources'] = json.dumps(sources)
    pred, true, cat = prediction(codec, params)
    base = pair_energy(pred, true, cat, codec)
    ns, cs = codec.continuous_slices['Transfxr'], codec.categorical_slices['Transfxr']
    for i, control in enumerate(codec.schemas['Transfxr'].continuous):
        if control['name'].startswith('morph.'):
            pred['continuous'][:, :, ns.start+i] = .74
    for i, control in enumerate(codec.schemas['Transfxr'].categorical):
        if control['name'] in ('morph.curve', 'tone.curve'):
            pred['categorical'][cs.start+i][:, :, 0] = 30
    assert torch.equal(base, pair_energy(pred, true, cat, codec))
    pred['continuous'][:, :, codec.balance_index] += .1
    torch.testing.assert_close(pair_energy(pred, true, cat, codec)-base, torch.full((1, 4), .04))


def test_loss_normalizes_each_source_then_averages_only_present_sources(codec, specs):
    from neural_invert.pair_model import pair_energy
    # Boomr has 12 numeric controls: duration weight 2, the other 11 weight 1.
    pressure = [c['name'] for c in codec.schemas['Boomr'].continuous].index('pressure')
    for structure, expected in ((0, 8*.1**2/13), (2, 8*.1**2/13/2)):
        pred, true, cat = prediction(codec, patch(specs, structure))
        baseline = pair_energy(pred, true, cat, codec)
        pred['continuous'][:, :, pressure] += .1
        torch.testing.assert_close(pair_energy(pred, true, cat, codec)-baseline,
                                   torch.full((1, 4), expected))


def test_enabled_morph_and_nonconstant_curve_receive_gradients(codec, specs):
    from neural_invert.pair_model import pair_energy
    params = patch(specs)
    sources = json.loads(params['sources']); sources[1]['params']['waveTo'] = 1
    params['sources'] = json.dumps(sources)
    pred, true, cat = prediction(codec, params)
    ns, cs = codec.continuous_slices['Transfxr'], codec.categorical_slices['Transfxr']
    start = ns.start+[c['name'] for c in codec.schemas['Transfxr'].continuous].index('morph.start')
    curve = cs.start+[c['name'] for c in codec.schemas['Transfxr'].categorical].index('morph.curve')
    pred['continuous'][:, :, start] = .25
    pred['continuous'].requires_grad_()
    for logits in pred['categorical']: logits.requires_grad_()
    pair_energy(pred, true, cat, codec).sum().backward()
    assert torch.count_nonzero(pred['continuous'].grad[:, :, start]) == 4
    assert torch.count_nonzero(pred['categorical'][curve].grad) > 0


def test_pair_model_shapes_order_peak_invariance_and_finite_backprop(codec, specs):
    from neural_invert.pair_model import PairInverse, pair_energy
    from neural_invert.temporal import mixture_loss
    torch.manual_seed(42)
    model = PairInverse(codec)
    x = torch.randn(3, 4083)
    pred = model(x)
    assert pred['continuous'].shape == (3, 4, codec.n_continuous)
    assert pred['mode_logits'].shape == (3, 4)
    assert [p.shape for p in pred['categorical']] == [(3, 4, n) for n in codec.cat_sizes]
    changed = x.clone(); changed[:, 4081] += 99
    assert torch.equal(pred['continuous'], model(changed)['continuous'])
    changed[:, :2304] = x[:, :2304].reshape(3, 48, 48).flip(-1).flatten(1)
    assert not torch.allclose(pred['continuous'], model(changed)['continuous'])
    labels = [codec.encode(patch(specs, structure)) for structure in range(3)]
    true, cat = (torch.tensor(np.stack(v)) for v in zip(*labels))
    energy = pair_energy(pred, true, cat, codec)
    assert energy.shape == (3, 4) and torch.isfinite(energy).all()
    loss, _ = mixture_loss(energy, pred['mode_logits'])
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())


def test_codec_rejects_invalid_categories_nonfinite_and_source_order(codec, specs):
    unit, cat = codec.encode(patch(specs))
    for bad in (np.full_like(unit, np.nan), unit[:-1]):
        with pytest.raises(ValueError): codec.decode(bad, cat)
    for bad in (cat.astype(float)+.5, np.full_like(cat, -1), cat[:-1]):
        with pytest.raises(ValueError): codec.decode(unit, bad)
    for sources in ([None, None], list(reversed(json.loads(patch(specs)['sources'])))):
        with pytest.raises(ValueError): codec.encode(dict(patch(specs), sources=json.dumps(sources)))
    bad = patch(specs); bad['balance'] = float('nan')
    with pytest.raises(ValueError): codec.encode(bad)
    sources = json.loads(patch(specs)['sources']); sources[0]['params']['pressure'] = float('inf')
    with pytest.raises(ValueError): codec.encode(dict(patch(specs), sources=json.dumps(sources)))


def test_model_and_energy_reject_nonfinite_and_invalid_shapes(codec, specs):
    from neural_invert.pair_model import PairInverse, pair_energy
    model = PairInverse(codec)
    with pytest.raises(ValueError): model(torch.full((1, 4083), float('nan')))
    with pytest.raises(ValueError): model(torch.zeros(1, 12))
    pred, true, cat = prediction(codec, patch(specs))
    bad = deepcopy(pred); bad['categorical'][0][0, 0, 0] = float('inf')
    with pytest.raises(ValueError): pair_energy(bad, true, cat, codec)
    with pytest.raises(ValueError): pair_energy(pred, true[:, :-1], cat, codec)
    bad_cat = cat.clone(); bad_cat[:, codec.structure_index] = 3
    with pytest.raises(ValueError): pair_energy(pred, true, bad_cat, codec)
