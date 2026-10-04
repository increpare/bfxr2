import json
import numpy as np
import pytest
import torch


def specimen(name='Test'):
    return {'name': name, 'presets': ['low', 'high'], 'defaults': {'masterVolume': .5, 'pitch': 10., 'shape': 3, 'bend': {'start': 0., 'end': 1., 'curve': 'Linear'}, 'phrase': 'c4'}, 'params': [
        {'name': 'masterVolume', 'type': 'RANGE', 'min': 0, 'max': 1, 'default': .5},
        {'name': 'pitch', 'type': 'RANGE', 'min': 10, 'max': 100, 'default': 10},
        {'name': 'shape', 'type': 'BUTTONSELECT', 'values': [0, 3, 8], 'default': 3},
        {'name': 'bend', 'type': 'KNOB_TRANSITION', 'min': 0, 'max': 1, 'values': ['Linear', 'Steps'], 'default': {'start': 0, 'end': 1, 'curve': 'Linear'}},
        {'name': 'phrase', 'type': 'TEXT', 'default': 'c4'}]}


def test_schema_roundtrip_discrete_and_global_ranges():
    from neural_invert.schema import ControlSchema
    schema = ControlSchema(specimen())
    anchor = specimen()['defaults']
    p = dict(anchor, pitch=97, shape=8, bend={'start': .8, 'end': .1, 'curve': 'Steps'})
    unit, cat = schema.encode(p)
    result = schema.decode(unit, cat, anchor)
    assert result['pitch'] == pytest.approx(97)
    assert result['shape'] == 8
    assert result['bend']['curve'] == 'Steps'
    assert result['phrase'] == 'c4'
    assert schema.decode(np.ones_like(unit), cat, anchor)['pitch'] == 100
    assert schema.fixed_text == ['phrase']


def test_features_keep_late_pitch_and_duration():
    from neural_invert.features import describe, DIM
    sr = 44100
    t = np.arange(sr) / sr
    a = np.sin(2*np.pi*440*t).astype('float32')
    b = a.copy(); b[sr//2:] = np.sin(2*np.pi*880*t[sr//2:])
    fa, fb = describe(a), describe(b)
    assert fa.shape == (DIM,)
    assert np.linalg.norm(fa-fb) > 1
    assert np.linalg.norm(describe(a)-describe(a[:sr//2])) > 1
    assert np.isfinite(describe(np.zeros(100))).all()


def test_parameter_duplicates_never_cross_split():
    from neural_invert.data import split_rows
    rows = [{'synth': 'X', 'params': {'pitch': i//2}, 'seed': i} for i in range(30)]
    train, val = split_rows(rows, seed=9)
    assert train and val
    tr = {json.dumps(rows[i]['params'], sort_keys=True) for i in train}
    va = {json.dumps(rows[i]['params'], sort_keys=True) for i in val}
    assert not tr & va
    assert sorted(train+val) == list(range(len(rows)))


def test_model_has_distinct_variable_heads_and_learns():
    from neural_invert.model import MultiSynthModel, supervised_loss
    from neural_invert.schema import ControlSchema
    a, b = specimen('A'), specimen('B'); b['params'] = b['params'][:3]
    specs = {'A': a, 'B': b}
    model = MultiSynthModel(specs, input_dim=12, hidden=32)
    assert model.heads['A'] is not model.heads['B']
    x = torch.randn(8, 12)
    out = model(x, 'A', torch.zeros(8, dtype=torch.long))
    assert out['continuous'].shape == (8, len(ControlSchema(a).continuous))
    assert len(out['categorical']) == 2
    labels = {'continuous': torch.full_like(out['continuous'], .8), 'categorical': torch.zeros(8, 2, dtype=torch.long), 'generator': torch.zeros(8, dtype=torch.long)}
    initial = supervised_loss(out, labels).item()
    optimizer = torch.optim.Adam(model.parameters(), lr=.02)
    for _ in range(20):
        optimizer.zero_grad(); loss = supervised_loss(model(x, 'A', labels['generator']), labels); loss.backward(); optimizer.step()
    assert loss.item() < initial*.5


def test_checkpoint_roundtrip_and_invalid_feature_version(tmp_path):
    from neural_invert.model import MultiSynthModel
    from neural_invert.predict import load_model
    from neural_invert.features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
    model = MultiSynthModel({'A': specimen('A')}, input_dim=DIM, hidden=32)
    meta = {'specs': {'A': specimen('A')}, 'engines': ['A'], 'featureDim': DIM, 'featureVersion': VERSION, 'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH, 'hidden': 32, 'normalization': {'mean': [0.]*DIM, 'std': [1.]*DIM}}
    path = tmp_path/'best.pt'; torch.save({'model': model.state_dict(), 'metadata': meta}, path)
    loaded, info = load_model(path)
    assert info['engines'] == ['A']
    assert loaded.heads['A'].continuous.out_features == 3
    meta['featureVersion'] = 'wrong'; torch.save({'model': model.state_dict(), 'metadata': meta}, path)
    with pytest.raises(ValueError, match='feature'):
        load_model(path)


def test_predictions_override_generator_numeric_and_categorical_controls():
    from neural_invert.model import MultiSynthModel
    from neural_invert.predict import predict
    from neural_invert.features import DIM, VERSION
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        spec = renderer.specs['Clonkr']
        model = MultiSynthModel({'Clonkr': spec}, DIM, hidden=32)
        with torch.no_grad():
            model.heads['Clonkr'].continuous.weight.zero_()
            model.heads['Clonkr'].continuous.bias.fill_(9.)
            for head in model.heads['Clonkr'].categorical:
                head.weight.zero_(); head.bias.fill_(-9.); head.bias[-1] = 9.
        meta = {'engines': ['Clonkr'], 'specs': {'Clonkr': spec}, 'featureVersion': VERSION,
                'normalization': {'mean': np.zeros(DIM), 'std': np.ones(DIM)}}
        _, wave = renderer.render('Clonkr', renderer.sample('Clonkr', spec['presets'][0], 15), 16)
        rows = predict(model, meta, wave, renderer, per_synth=2)
        assert len(rows) == 2
        numeric = next(p for p in spec['params'] if p['type']=='RANGE' and p['name'] not in ('masterVolume','seed','instrumentSeed'))
        assert rows[0]['params'][numeric['name']] > numeric['min']+.99*(numeric['max']-numeric['min'])
        for row in rows:
            for control in spec['params']:
                if control['type'] == 'BUTTONSELECT':
                    assert row['params'][control['name']] == control['values'][-1]
            assert row['provenance']['method'] == 'neural-global-controls'
            assert 'renderError' not in row['provenance']


def test_real_data_resume_preserves_rows_and_rejects_changed_configuration(tmp_path):
    from neural_invert.data import generate_dataset
    from neural_invert.train import train_model
    from neural_invert.predict import load_model
    manifest = generate_dataset(tmp_path/'data', per_synth=8, jobs=1, synths=['Footsteppr'])
    assert manifest['complete'] and len(manifest['engines']) == 1
    shard = json.loads((tmp_path/'data'/'Footsteppr.json').read_text())
    before = (tmp_path/'data'/'Footsteppr.npz').read_bytes()
    resumed = generate_dataset(tmp_path/'data', per_synth=8, jobs=1, synths=['Footsteppr'])
    assert resumed['shards'][0]['resumed']
    assert (tmp_path/'data'/'Footsteppr.npz').read_bytes() == before
    with pytest.raises(ValueError, match='incompatible'):
        generate_dataset(tmp_path/'data', per_synth=9, jobs=1, synths=['Footsteppr'])
    report = train_model(tmp_path/'data', tmp_path/'model', epochs=1, hidden=32, threads=1)
    model, meta = load_model(tmp_path/'model')
    with np.load(tmp_path/'data'/'Footsteppr.npz') as saved:
        expected = saved['features'][shard['train']].astype(np.float64).mean(0)
    np.testing.assert_allclose(meta['normalization']['mean'], expected, atol=1e-6)
    assert report['history'][0]['perEngine']['Footsteppr']['validationRows'] == len(shard['val'])
    assert model.heads['Footsteppr'].categorical[0].out_features == 5


def test_all_active_engine_schemas_roundtrip_actual_canonical_controls():
    from neural_invert.schema import ControlSchema
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        active = [spec for spec in renderer.specs.values() if spec['collectionCompatible']]
        assert len(active) == 22
        for spec in active:
            schema = ControlSchema(spec)
            params = renderer.sample(spec['name'], spec['presets'][0], 21)
            unit, categorical = schema.encode(params)
            decoded = schema.decode(unit, categorical, params)
            for c in schema.continuous:
                assert schema._read(decoded, c['path']) == pytest.approx(schema._read(params, c['path']), abs=1e-4)
            for c in schema.categorical:
                assert schema._read(decoded, c['path']) == schema._read(params, c['path'])
            assert all(c['name'] not in ('seed','instrumentSeed') for c in schema.continuous)


@pytest.mark.parametrize('location,field', [('manifest','featureCodeHash'), ('manifest','featureHash'), ('Footsteppr','featureCodeHash'), ('Footsteppr','featureHash'), ('Footsteppr','featureVersion')])
def test_dataset_rejects_changed_feature_provenance_before_training_or_resume(tmp_path, location, field):
    from neural_invert.data import generate_dataset
    from neural_invert.train import _load_dataset
    path = tmp_path/'data'
    generate_dataset(path, per_synth=4, jobs=1, synths=['Footsteppr'])
    metadata_path = path/(location+'.json')
    metadata = json.loads(metadata_path.read_text())
    metadata[field] = 'different-feature-implementation'
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='incompatible|disagree'):
        _load_dataset(path)
    with pytest.raises(ValueError, match='incompatible'):
        generate_dataset(path, per_synth=4, jobs=1, synths=['Footsteppr'])


@pytest.mark.parametrize('field', ['featureHash','featureCodeHash'])
def test_checkpoint_requires_recorded_feature_hashes(tmp_path, field):
    from neural_invert.model import MultiSynthModel
    from neural_invert.predict import load_model
    from neural_invert.features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
    model = MultiSynthModel({'A': specimen('A')}, DIM, hidden=32)
    metadata = {'specs': {'A': specimen('A')}, 'engines': ['A'], 'featureDim': DIM, 'featureVersion': VERSION,
                'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH, 'hidden': 32,
                'normalization': {'mean': [0.]*DIM, 'std': [1.]*DIM}}
    del metadata[field]
    path = tmp_path/'best.pt'; torch.save({'model': model.state_dict(), 'metadata': metadata}, path)
    with pytest.raises(ValueError, match='feature'):
        load_model(path)


@pytest.mark.parametrize('corrupt', ['arrays','canonicalRows'])
def test_dataset_file_binding_rejects_array_or_canonical_row_edits(tmp_path, corrupt):
    import hashlib
    from neural_invert.data import generate_dataset
    from neural_invert.train import _load_dataset
    path = tmp_path/'data'
    manifest = generate_dataset(path, per_synth=4, jobs=1, synths=['Footsteppr'])
    shard_path = path/'Footsteppr.json'
    shard = json.loads(shard_path.read_text())
    with np.load(path/'Footsteppr.npz') as saved:
        for i, row in enumerate(shard['rows']):
            assert row['packedFeatureHash'] == hashlib.sha256(saved['features'][i].astype('<f2').tobytes()).hexdigest()
    assert manifest['files']['Footsteppr']['metadataSha256'] == hashlib.sha256(shard_path.read_bytes()).hexdigest()
    if corrupt == 'arrays':
        file = path/'Footsteppr.npz'; damaged = bytearray(file.read_bytes()); damaged[-20] ^= 1; file.write_bytes(damaged)
    else:
        shard['rows'][0]['params']['heel'] = .123456
        shard_path.write_text(json.dumps(shard))
    with pytest.raises(ValueError, match='integrity'):
        _load_dataset(path)
    with pytest.raises(ValueError, match='integrity'):
        generate_dataset(path, per_synth=4, jobs=1, synths=['Footsteppr'])
