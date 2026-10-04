"""Contracts for the bounded controls-to-descriptor forward pilot."""
import hashlib
import json

import numpy as np
import pytest
import torch


def numeric_spec():
    return {'name': 'Bfxr', 'presets': ['a'], 'defaults': {}, 'params': [
        {'name': 'pitch', 'type': 'RANGE', 'min': 0, 'max': 1},
        {'name': 'shape', 'type': 'BUTTONSELECT', 'values': [0, 1, 2]}]}


def test_hard_categories_and_confident_soft_logits_agree():
    from neural_invert.forward import encode_controls
    unit = torch.tensor([[.2], [.8]])
    hard = encode_controls(unit, torch.tensor([[0], [2]]), numeric_spec())
    soft = encode_controls(unit, [torch.tensor([[40., -40., -40.], [-40., -40., 40.]])], numeric_spec())
    assert torch.allclose(hard, soft, atol=1e-7)


def test_forward_keeps_numeric_and_soft_categorical_gradients():
    from neural_invert.forward import ForwardModel, feature_loss
    torch.manual_seed(4)
    model = ForwardModel(numeric_spec(), hidden=16)
    unit = torch.tensor([[.4]], requires_grad=True)
    logits = torch.tensor([[.2, -.3, .7]], requires_grad=True)
    total, groups = feature_loss(model(unit, [logits]), torch.zeros(1, 4083))
    total.backward()
    assert len(groups) == 9
    for gradient in (unit.grad, logits.grad):
        assert torch.isfinite(gradient).all() and gradient.abs().sum() > 0


def test_feature_groups_cover_all_except_peak_and_receive_equal_weight():
    from neural_invert.forward import FEATURE_GROUPS, feature_loss
    covered = [i for ranges in FEATURE_GROUPS.values() for start, stop in ranges for i in range(start, stop)]
    assert len(FEATURE_GROUPS) == 9
    assert len(covered) == len(set(covered)) == 4082
    assert set(covered) == set(range(4083)) - {4081}
    prediction, target = torch.zeros(2, 4083), torch.zeros(2, 4083)
    target[:, 4081] = 999.
    total, groups = feature_loss(prediction, target)
    assert total == 0 and all(value == 0 for value in groups.values())
    target[:, 4080] = 3.
    total, groups = feature_loss(prediction, target)
    assert groups['duration'] == 9 and total == 1


@pytest.mark.parametrize('case', ['text', 'unsupported', 'category', 'fractional', 'nonfinite', 'dimension'])
def test_invalid_controls_are_rejected(case):
    from neural_invert.forward import ForwardModel, encode_controls
    spec = numeric_spec()
    unit, categories = torch.tensor([[.2]]), torch.tensor([[0]])
    if case == 'text':
        spec['params'].append({'name': 'phrase', 'type': 'TEXT'})
        with pytest.raises(ValueError, match='TEXT'):
            ForwardModel(spec)
        return
    if case == 'unsupported':
        spec['name'] = 'Clonkr'
    if case == 'category':
        categories[0, 0] = 3
    if case == 'fractional':
        categories = torch.tensor([[.5]])
    if case == 'nonfinite':
        unit[0, 0] = float('nan')
    if case == 'dimension':
        unit = torch.zeros(1, 2)
    with pytest.raises(ValueError):
        encode_controls(unit, categories, spec)


@pytest.fixture
def tiny_dataset(tmp_path):
    from neural_invert.data import generate_dataset, file_hash
    data = tmp_path/'data'
    manifest = generate_dataset(data, per_synth=4, jobs=1, synths=['Bfxr', 'Pluckr'])
    # Make validation distinctive so a leaked normalization has a visible error.
    for name in manifest['engines']:
        meta = json.loads((data/(name+'.json')).read_text())
        with np.load(data/(name+'.npz')) as saved:
            arrays = {key: saved[key].copy() for key in saved.files}
        arrays['features'][meta['val']] += np.float16(2.)
        np.savez_compressed(data/(name+'.npz'), **arrays)
        manifest['files'][name]['npzSha256'] = file_hash(data/(name+'.npz'))
    (data/'manifest.json').write_text(json.dumps(manifest))
    return data


def test_real_format_training_normalizes_each_train_split_and_reloads(tiny_dataset, tmp_path):
    from neural_invert.forward import train_forward, load_forward, feature_loss
    report = train_forward(tiny_dataset, tmp_path/'model', ['Bfxr', 'Pluckr'], epochs=2, hidden=16, batch_size=2, device='cpu')
    assert set(report['perEngine']) == {'Bfxr', 'Pluckr'}
    for name in report['perEngine']:
        model, metadata = load_forward(tmp_path/'model'/name)
        shard_meta = json.loads((tiny_dataset/(name+'.json')).read_text())
        with np.load(tiny_dataset/(name+'.npz')) as saved:
            train = saved['features'][shard_meta['train']].astype(np.float64)
            val = saved['features'][shard_meta['val']].astype(np.float32)
            expected_mean = train.mean(0)
            expected_std = np.maximum(train.std(0), .025)
            unit = torch.from_numpy(saved['continuous'][shard_meta['val']])
            categories = torch.from_numpy(saved['categorical'][shard_meta['val']].astype(np.int64))
        np.testing.assert_allclose(metadata['normalization']['mean'], expected_mean, atol=1e-6)
        np.testing.assert_allclose(metadata['normalization']['std'], expected_std, atol=1e-6)
        target = torch.tensor((val - expected_mean)/expected_std, dtype=torch.float32)
        baseline, groups = feature_loss(torch.zeros_like(target), target)
        engine = report['perEngine'][name]
        assert engine['baseline']['total'] == pytest.approx(float(baseline), rel=1e-6)
        assert set(engine['baseline']['groups']) == set(groups)
        assert all(row['trainRows'] == len(train) and row['validationRows'] == len(val) for row in engine['history'])
        assert engine['bestEpoch'] in (1, 2)
        loss, _ = feature_loss(model(unit, categories), target)
        assert float(loss.detach()) == pytest.approx(engine['bestValidation']['total'], rel=1e-6)
        assert metadata['checkpointHash'] == engine['checkpointHash']
        assert metadata['trainingRecipe'] == engine['trainingRecipe'] == {
            'epochs': 2, 'batchSize': 2, 'hidden': 16, 'seed': 20261007,
            'threads': 1, 'learningRate': .001,
            'optimizer': {'name': 'AdamW', 'weightDecay': .0001, 'scheduler': 'cosine', 'minimumLearningRate': .0001}}
        assert engine['predictiveGate']['passed'] == (engine['bestValidation']['total'] <= .8*engine['baseline']['total'] + 1e-8 and all(
            engine['bestValidation']['groups'][g] <= engine['baseline']['groups'][g] + 1e-8
            for g in ('relativeEnvelope', 'absoluteEnvelope', 'relativePitch', 'absolutePitch', 'combinedVoicing')))


def test_existing_output_is_rejected_without_modification(tmp_path):
    from neural_invert.forward import train_forward
    output = tmp_path/'existing'; output.mkdir(); (output/'keep').write_text('preserve')
    with pytest.raises(FileExistsError):
        train_forward(tmp_path/'absent', output, ['Bfxr'], epochs=1)
    assert (output/'keep').read_text() == 'preserve'


@pytest.mark.parametrize('setting,value', [('hidden', 0), ('hidden', 1.5), ('epochs', 1.5),
    ('batch_size', 1.5), ('threads', 1.5), ('seed', 1.5), ('seed', -1), ('epochs', True)])
def test_invalid_integer_training_settings_leave_no_output(tmp_path, setting, value):
    from neural_invert.forward import train_forward
    with pytest.raises(ValueError, match='integer'):
        train_forward(tmp_path/'absent', tmp_path/'model', ['Bfxr'], **{setting: value})
    assert not (tmp_path/'model').exists()


@pytest.mark.parametrize('location', ['report', 'checkpoint'])
def test_reload_rejects_altered_training_recipe(tiny_dataset, tmp_path, location):
    from neural_invert.forward import train_forward, load_forward
    train_forward(tiny_dataset, tmp_path/'model', ['Bfxr'], epochs=1, hidden=8, device='cpu')
    path = tmp_path/'model'/'Bfxr'/'best.pt'
    report_path = path.parent/'training.json'
    report = json.loads(report_path.read_text())
    if location == 'report':
        report['trainingRecipe']['epochs'] += 1
    else:
        checkpoint = torch.load(path, weights_only=True)
        checkpoint['metadata']['trainingRecipe']['epochs'] += 1
        torch.save(checkpoint, path)
        report['metadata'] = checkpoint['metadata']
        report['trainingRecipe'] = checkpoint['metadata']['trainingRecipe']
        report['checkpointHash'] = hashlib.sha256(path.read_bytes()).hexdigest()
    report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='recipe|binding'):
        load_forward(path)


@pytest.mark.parametrize('case', ['empty', 'overlap', 'category', 'nonfinite'])
def test_training_rejects_invalid_shard_semantics(tiny_dataset, tmp_path, case):
    from neural_invert.forward import train_forward
    from neural_invert.data import file_hash
    path = tiny_dataset/'Bfxr.json'
    meta = json.loads(path.read_text())
    manifest = json.loads((tiny_dataset/'manifest.json').read_text())
    if case == 'empty':
        meta['train'] = []
    elif case == 'overlap':
        meta['val'] = meta['train'][:1]
    else:
        with np.load(tiny_dataset/'Bfxr.npz') as saved:
            arrays = {key: saved[key].copy() for key in saved.files}
        if case == 'category':
            arrays['categorical'][0, 0] = 999
        else:
            arrays['features'][0, 0] = np.nan
        np.savez_compressed(tiny_dataset/'Bfxr.npz', **arrays)
        manifest['files']['Bfxr']['npzSha256'] = file_hash(tiny_dataset/'Bfxr.npz')
    path.write_text(json.dumps(meta))
    manifest['files']['Bfxr']['metadataSha256'] = file_hash(path)
    manifest['splits']['Bfxr'] = {key: meta[key] for key in ('train', 'val')}
    (tiny_dataset/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        train_forward(tiny_dataset, tmp_path/'model', ['Bfxr'], epochs=1, hidden=8)
    assert not (tmp_path/'model').exists()


@pytest.mark.parametrize('field', ['checkpointHash', 'baseline', 'predictiveGate'])
def test_reload_rejects_altered_training_report(tiny_dataset, tmp_path, field):
    from neural_invert.forward import train_forward, load_forward
    train_forward(tiny_dataset, tmp_path/'model', ['Bfxr'], epochs=1, hidden=8, device='cpu')
    path = tmp_path/'model'/'Bfxr'/'training.json'
    report = json.loads(path.read_text())
    if field == 'checkpointHash':
        report[field] = 'changed'
    elif field == 'baseline':
        report[field]['total'] += 1.
    else:
        report[field]['passed'] = not report[field]['passed']
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='binding|incompatible'):
        load_forward(path.parent)


@pytest.mark.parametrize('field', ['featureCodeHash', 'schemaCodeHash', 'forwardCodeHash', 'sourceHash', 'lossPolicy', 'normalization'])
def test_reload_rejects_incompatible_metadata(tiny_dataset, tmp_path, field):
    from neural_invert.forward import train_forward, load_forward
    train_forward(tiny_dataset, tmp_path/'model', ['Bfxr'], epochs=1, hidden=8, device='cpu')
    path = tmp_path/'model'/'Bfxr'/'best.pt'
    checkpoint = torch.load(path, weights_only=True)
    checkpoint['metadata'][field] = {'mean': [0.]*4083, 'std': [0.]*4083} if field == 'normalization' else 'incompatible'
    torch.save(checkpoint, path)
    # Rebind the file hash so this exercises metadata compatibility too.
    report_path = path.parent/'training.json'
    report = json.loads(report_path.read_text()); report['checkpointHash'] = hashlib.sha256(path.read_bytes()).hexdigest()
    report['metadata'] = checkpoint['metadata']; report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match='incompatible|invalid'):
        load_forward(path)
