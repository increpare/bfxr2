"""Contracts for surrogate-only continuous refinement and actual-DSP checks."""
from copy import deepcopy
import json

import numpy as np
import pytest
import soundfile as sf
import torch


def fixture_model():
    spec = {'name': 'Bfxr', 'defaults': {'pitch': .123456789, 'shape': 1, 'seed': 11,
        'instrumentSeed': 19, 'masterVolume': .5}, 'params': [
        {'name': 'pitch', 'type': 'RANGE', 'min': 0, 'max': 1},
        {'name': 'shape', 'type': 'BUTTONSELECT', 'values': [0, 1]},
        {'name': 'seed', 'type': 'RANGE', 'min': 0, 'max': 100},
        {'name': 'instrumentSeed', 'type': 'RANGE', 'min': 0, 'max': 100}]}

    class LinearForward(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.spec = deepcopy(spec)
            self.scale = torch.nn.Parameter(torch.tensor(2.))
        def forward(self, unit, categories):
            return (unit[:, :1] * self.scale).expand(-1, 4083)

    model = LinearForward()
    # Raw descriptors are 10 + 2 * normalized descriptors.
    metadata = {'spec': spec, 'normalization': {'mean': [10.]*4083, 'std': [2.]*4083}}
    return model, metadata, deepcopy(spec['defaults'])


def test_refinement_uses_train_normalization_and_only_continuous_gradients():
    from neural_invert.forward_probe import refine_controls
    model, metadata, params = fixture_model()
    original_weight = model.scale.detach().clone()
    result = refine_controls(model, metadata, params, np.full(4083, 13., np.float32), steps=30, learning_rate=.03)
    assert result['bestLoss'] < result['initialLoss'] / 10
    assert result['params']['pitch'] > params['pitch'] + .3
    assert len(result['trace']) == 31
    assert result['initialLoss'] == pytest.approx((2*params['pitch'] - 1.5)**2, rel=1e-6)
    assert result['bestLoss'] == min(result['trace'])
    assert result['finalLoss'] == result['trace'][-1]
    assert result['maximumGradientNorm'] > 0
    assert torch.equal(model.scale, original_weight)
    assert not model.scale.requires_grad and model.scale.grad is None
    assert not model.training
    for name in ('shape', 'seed', 'instrumentSeed', 'masterVolume'):
        assert result['params'][name] == params[name]
    assert params == metadata['spec']['defaults']


def test_best_state_includes_initial_without_control_roundtrip():
    from neural_invert.forward_probe import refine_controls
    model, metadata, params = fixture_model()
    # A very large step overshoots the target; retain the exact original float.
    target = np.full(4083, 10 + 2*(2*params['pitch'] + .001), np.float32)
    result = refine_controls(model, metadata, params, target, steps=1, learning_rate=1.)
    assert result['bestStep'] == 0
    assert result['bestLoss'] == result['initialLoss'] < result['finalLoss']
    assert result['params'] == params
    assert result['params']['pitch'] == .123456789


@pytest.mark.parametrize('steps,rate', [(0, .01), (-1, .01), (True, .01), (1.5, .01),
    (1, 0), (1, -1), (1, float('nan')), (1, float('inf')), (1, True)])
def test_invalid_optimizer_settings_fail(steps, rate):
    from neural_invert.forward_probe import refine_controls
    model, metadata, params = fixture_model()
    with pytest.raises(ValueError):
        refine_controls(model, metadata, params, np.zeros(4083), steps=steps, learning_rate=rate)


def test_existing_output_is_untouched(tmp_path):
    from neural_invert.forward_probe import run_probe
    output = tmp_path/'output'; output.mkdir(); (output/'keep').write_text('unchanged')
    with pytest.raises(FileExistsError):
        run_probe(tmp_path/'missing.json', tmp_path/'models', output)
    assert (output/'keep').read_text() == 'unchanged'


def test_every_model_gate_is_checked_before_output_or_optimization(tmp_path, monkeypatch):
    import neural_invert.forward_probe as probe
    loaded = []
    def load(path):
        name = path.name
        loaded.append(name)
        model, metadata, _ = fixture_model()
        return model, dict(metadata, engine=name, predictiveGate={'passed': name != 'Pluckr'})
    monkeypatch.setattr(probe, 'load_forward', load)
    monkeypatch.setattr(probe, 'refine_controls', lambda *a, **k: pytest.fail('optimization before predictive gate'))
    with pytest.raises(ValueError, match='predictive gate'):
        probe.run_probe(tmp_path/'absent.json', tmp_path/'models', tmp_path/'output')
    assert loaded == ['Bfxr', 'Transfxr', 'Pluckr']
    assert not (tmp_path/'output').exists()


def test_actual_gate_requires_improvement_count_mean_and_pitch_preservation():
    from neural_invert.forward_probe import summarize
    rows = [{'id': str(i), 'family': 'static', 'sourceSynth': 'Bfxr',
        'target': {'pitch': {'reliable': True}},
        'before': {'featureLoss': {'total': 2.}, 'pitch': {'reliable': True}},
        'after': {'featureLoss': {'total': 1. if i < 15 else 2.}, 'pitch': {'reliable': True}},
        'surrogate': {'initialLoss': 2., 'bestLoss': 1.}} for i in range(20)]
    summary = summarize(rows)
    assert summary['actualGate']['passed'] and summary['actualGate']['improved'] == 15
    rows[0]['after']['pitch']['reliable'] = False
    assert not summarize(rows)['actualGate']['passed']
    rows[0]['after']['pitch']['reliable'] = True
    rows[0]['after']['featureLoss']['total'] = 100.
    assert not summarize(rows)['actualGate']['passed']
    assert not summarize(rows[:19])['actualGate']['passed']


@pytest.mark.parametrize('corruption', ['complete', 'source', 'feature', 'model', 'arm', 'count', 'wav'])
def test_benchmark_provenance_fails_before_output_and_optimization(tmp_path, monkeypatch, corruption):
    import neural_invert.forward_probe as probe
    from neural_invert.data import file_hash
    from neural_invert.forward import _hash_json
    from neural_invert.features import VERSION, FEATURE_HASH, FEATURE_CODE_HASH
    source = 'c'*64
    data = tmp_path/'data'; data.mkdir()
    for name in probe.ENGINES:
        (data/(name+'.npz')).write_bytes(b'bound shard')
        (data/(name+'.json')).write_text(json.dumps({'train': [0], 'val': [1]}))
    manifest = {'complete': True, 'sourceHash': source, 'engines': list(probe.ENGINES),
        'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
        'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': 4083,
        'splits': {name: {'train': [0], 'val': [1]} for name in probe.ENGINES},
        'files': {name: {'npzSha256': file_hash(data/(name+'.npz')),
            'metadataSha256': file_hash(data/(name+'.json'))} for name in probe.ENGINES}}
    if corruption == 'feature':
        manifest['featureCodeHash'] = 'changed'
    (data/'manifest.json').write_text(json.dumps(manifest))
    inverse = tmp_path/'inverse.pt'
    torch.save({'metadata': {'dataManifestHash': file_hash(data/'manifest.json')}}, inverse)
    pcm = tmp_path/'original.wav'; pcm.write_bytes(b'bound PCM')
    rows = []
    for i, family in enumerate(['native']*3 + ['static']*9 + ['moving']*8):
        before = {'waveFile': str(pcm), 'waveFileSha256': file_hash(pcm),
            'provenance': {'checkpointHash': file_hash(inverse)}}
        rows.append({'id': str(i), 'family': family, 'sourceSynth': 'Bfxr',
            'waveFile': str(pcm), 'waveFileSha256': file_hash(pcm),
            'arms': {'acoustic': {'checkpointSha256': file_hash(inverse),
                'candidates': {'knownRaw': before}}}})
    config = {'complete': True, 'sourceHash': source,
        'benchmarkCodeSha256': file_hash(probe.Path(probe.__file__).with_name('benchmark.py')),
        'models': {'acoustic': str(inverse)}, 'modelHashes': {'acoustic': file_hash(inverse)},
        'datasets': [{'path': str(data), 'manifestSha256': file_hash(data/'manifest.json')}]}
    if corruption == 'complete':
        config['complete'] = False
    elif corruption == 'source':
        config['sourceHash'] = 'changed'
    elif corruption == 'model':
        config['modelHashes']['acoustic'] = 'changed'
    elif corruption == 'arm':
        rows[0]['arms']['acoustic']['checkpointSha256'] = 'changed'
    elif corruption == 'count':
        rows.pop()
    elif corruption == 'wav':
        rows[0]['waveFileSha256'] = 'changed'
    benchmark = tmp_path/'benchmark.json'
    benchmark.write_text(json.dumps({'metadata': config, 'results': rows}))
    def load(path):
        model, metadata, _ = fixture_model()
        return model, dict(metadata, predictiveGate={'passed': True},
            dataManifestHash=file_hash(data/'manifest.json'), datasetFiles=manifest['files'][path.name],
            splitHash=_hash_json({'train': [0], 'val': [1]}))
    class Inventory:
        inventory = {'sourceHash': source}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(probe, 'load_forward', load)
    monkeypatch.setattr(probe, 'Renderer', Inventory)
    monkeypatch.setattr(probe, 'refine_controls', lambda *a, **k: pytest.fail('optimization before provenance checks'))
    with pytest.raises(ValueError):
        probe.run_probe(benchmark, tmp_path/'models', tmp_path/'output')
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('corruption', ['none', 'dataset', 'files', 'split'])
def test_forward_training_is_bound_to_exact_acoustic_dataset(tmp_path, corruption):
    import neural_invert.forward_probe as probe
    from neural_invert.forward import _hash_json
    from neural_invert.data import file_hash
    from neural_invert.features import VERSION, FEATURE_HASH, FEATURE_CODE_HASH
    source = 'c'*64
    datasets, manifests = [], []
    for version in ('v1', 'v2'):
        path = tmp_path/version; path.mkdir()
        files = {}
        for name in probe.ENGINES:
            (path/(name+'.npz')).write_bytes((name+version).encode())
            (path/(name+'.json')).write_text(json.dumps({'train': [0, 1], 'val': [2]}))
            files[name] = {'npzSha256': file_hash(path/(name+'.npz')),
                'metadataSha256': file_hash(path/(name+'.json'))}
        manifest = {'complete': True, 'sourceHash': source, 'engines': list(probe.ENGINES),
            'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
            'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': 4083,
            'splits': {name: {'train': [0, 1], 'val': [2]} for name in probe.ENGINES}, 'files': files}
        (path/'manifest.json').write_text(json.dumps(manifest))
        datasets.append({'path': str(path), 'manifestSha256': file_hash(path/'manifest.json')})
        manifests.append(manifest)
    inverse = tmp_path/'inverse.pt'
    torch.save({'metadata': {'dataManifestHash': datasets[1]['manifestSha256']}}, inverse)
    wave = tmp_path/'wave'; wave.write_bytes(b'bound PCM')
    rows = [{'id': str(i), 'family': family, 'sourceSynth': 'Bfxr',
        'waveFile': str(wave), 'waveFileSha256': file_hash(wave),
        'arms': {'acoustic': {'checkpointSha256': file_hash(inverse), 'candidates': {'knownRaw': {
            'waveFile': str(wave), 'waveFileSha256': file_hash(wave),
            'provenance': {'checkpointHash': file_hash(inverse)}}}}}}
        for i, family in enumerate(['native']*3+['static']*9+['moving']*8)]
    config = {'complete': True, 'sourceHash': source, 'datasets': datasets,
        'benchmarkCodeSha256': file_hash(probe.Path(probe.__file__).with_name('benchmark.py')),
        'models': {'acoustic': str(inverse)}, 'modelHashes': {'acoustic': file_hash(inverse)}}
    path = tmp_path/'benchmark.json'
    path.write_text(json.dumps({'metadata': config, 'results': rows}))
    loaded = {name: (None, {'dataManifestHash': datasets[1]['manifestSha256'],
        'datasetFiles': manifests[1]['files'][name], 'splitHash': _hash_json({'train': [0, 1], 'val': [2]})})
        for name in probe.ENGINES}
    if corruption == 'dataset':
        loaded['Bfxr'][1]['dataManifestHash'] = datasets[0]['manifestSha256']
    elif corruption == 'files':
        loaded['Bfxr'][1]['datasetFiles'] = manifests[0]['files']['Bfxr']
    elif corruption == 'split':
        loaded['Bfxr'][1]['splitHash'] = _hash_json({'train': [0, 2], 'val': [1]})
    renderer = type('Inventory', (), {'inventory': {'sourceHash': source}})()
    if corruption == 'none':
        selected, bindings = probe._benchmark_inputs(path, loaded, renderer)
        assert len(selected) == 20 and str(inverse.resolve()) in bindings
        return
    with pytest.raises(ValueError, match='training|dataset|split'):
        probe._benchmark_inputs(path, loaded, renderer)


def test_completion_checks_fresh_dsp_inventory(monkeypatch):
    import neural_invert.forward_probe as probe
    class ChangedInventory:
        inventory = {'sourceHash': 'changed-on-disk'}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(probe, 'Renderer', ChangedInventory)
    with pytest.raises(ValueError, match='source'):
        probe._verify_completion({}, 'initial-source', 20)


def test_one_actual_case_replays_controls_and_float_wav(tmp_path):
    from multisynth.renderer import Renderer
    from neural_invert.benchmark import audio_hash
    from neural_invert.data import file_hash
    from neural_invert.forward import ForwardModel
    from neural_invert.forward_probe import probe_case
    with Renderer() as renderer:
        spec = renderer.specs['Pluckr']
        target_params, target_wave = renderer.render('Pluckr', spec['defaults'], 123)
        before_params, before_wave = renderer.render('Pluckr', spec['defaults'], 127)
        target_path, before_path = tmp_path/'target.wav', tmp_path/'before.wav'
        sf.write(target_path, target_wave, 44100, subtype='FLOAT')
        sf.write(before_path, before_wave, 44100, subtype='FLOAT')
        source = renderer.inventory['sourceHash']
        row = {'id': 'test-Pluckr-native', 'family': 'native', 'sourceSynth': 'Pluckr',
            'sourceParams': target_params, 'sourceSeed': 123, 'sourceHash': source,
            'waveFile': str(target_path), 'waveFileSha256': file_hash(target_path),
            'audioHash': audio_hash(target_wave), 'audioSamples': len(target_wave),
            'sourceReplay': {'exact': True, 'canonicalParamsEqual': True,
                'audioHash': audio_hash(target_wave), 'seed': 123, 'backend': 'actual-multisynth'},
            'arms': {'acoustic': {'candidates': {'knownRaw': {
                'synth': 'Pluckr', 'params': before_params, 'seed': 127, 'sourceHash': source,
                'waveFile': str(before_path), 'waveFileSha256': file_hash(before_path),
                'audioHash': audio_hash(before_wave), 'audioSamples': len(before_wave)}}}}}
        torch.manual_seed(3)
        model = ForwardModel(spec, hidden=4)
        metadata = {'spec': spec, 'engine': 'Pluckr', 'sourceHash': source,
            'normalization': {'mean': [0.]*4083, 'std': [1.]*4083},
            'checkpointHash': 'a'*64, 'normalizationHash': 'b'*64}
        result = probe_case(row, model, metadata, renderer, tmp_path/'case', steps=1)
        assert result['before']['params'] == before_params
        assert result['before']['audioHash'] == row['arms']['acoustic']['candidates']['knownRaw']['audioHash']
        for name in ('target', 'before', 'after'):
            record = result[name]
            saved, rate = sf.read(record['waveFile'], dtype='float32')
            assert rate == 44100 and sf.info(record['waveFile']).subtype == 'FLOAT'
            assert file_hash(record['waveFile']) == record['waveFileSha256']
            assert audio_hash(saved) == record['audioHash']
            assert record['sourceReplay']['exact']
            assert set(record['featureLoss']['groups']) == {
                'relativeSpectrum', 'absoluteSpectrum', 'relativeEnvelope', 'absoluteEnvelope',
                'relativePitch', 'absolutePitch', 'combinedVoicing', 'duration', 'rms'}
        replay_params, replay_wave = renderer.render('Pluckr', result['after']['params'], 127)
        assert replay_params == result['after']['params']
        assert audio_hash(replay_wave) == result['after']['audioHash']
        for anchor in ('seed', 'instrumentSeed'):
            if anchor in before_params:
                assert before_params[anchor] == result['after']['params'][anchor]
        assert result['after']['seed'] == result['before']['seed'] == 127
        assert np.isfinite(result['surrogate']['canonicalLoss'])
        assert json.loads((tmp_path/'case'/'report.json').read_text()) == result
