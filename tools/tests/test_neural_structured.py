"""Structured draws must stay grounded in actual controls and immutable native data."""
import hashlib
import json

import numpy as np
import pytest

from multisynth.renderer import Renderer
from neural_invert.data import file_hash, generate_dataset, parameter_hash, split_rows
from neural_invert.features import DIM, describe
from neural_invert.schema import ControlSchema


def test_structured_draws_are_deterministic_and_actual_schema_roundtrips():
    from neural_invert.structured import structured_params
    with Renderer() as renderer:
        for name in ('Bfxr', 'Transfxr', 'Pluckr'):
            spec = renderer.specs[name]
            first = np.random.default_rng(178)
            second = np.random.default_rng(178)
            for index in range(24):
                params, gesture = structured_params(spec, first, index)
                assert (params, gesture) == structured_params(spec, second, index)
                assert gesture['kind'] in ('stationary', 'rise', 'fall', 'jump', 'vibrato')
                assert 80 <= gesture['nominalStartHz'] <= (880 if name == 'Pluckr' else 1600)
                canonical, wave = renderer.render(name, params, 883 + index)
                assert len(wave) and np.isfinite(wave).all() and np.max(np.abs(wave)) > 1e-7
                schema = ControlSchema(spec)
                unit, cat = schema.encode(canonical)
                decoded = schema.decode(unit, cat, canonical)
                for control in schema.continuous:
                    assert schema._read(decoded, control['path']) == pytest.approx(schema._read(canonical, control['path']), abs=1e-5)
                for control in schema.categorical:
                    assert schema._read(decoded, control['path']) == schema._read(canonical, control['path'])
                if name == 'Bfxr':
                    from match.optimizer import freq_param_from_hz
                    assert params['frequency_start'] == freq_param_from_hz(gesture['nominalStartHz'])


def test_stationary_sines_cover_pitch_and_envelope_ranges():
    from neural_invert.structured import structured_params
    with Renderer() as renderer:
        for name, sine in [('Bfxr', 2), ('Transfxr', 0)]:
            rng = np.random.default_rng(36)
            draws = [structured_params(renderer.specs[name], rng, i) for i in range(512)]
            tones = [(p, g) for p, g in draws if g['kind'] == 'stationary' and p['waveType'] == sine]
            assert len(tones) >= 64
            assert min(g['nominalStartHz'] for _, g in tones) < 120
            assert max(g['nominalStartHz'] for _, g in tones) > 1200
            envelope = 'sustainTime' if name == 'Bfxr' else 'duration'
            assert max(p[envelope] for p, _ in tones) > min(p[envelope] for p, _ in tones)*2


@pytest.fixture(scope='module')
def augmented(tmp_path_factory):
    from neural_invert.structured import augment_dataset
    path = tmp_path_factory.mktemp('structured')
    base, output = path/'base', path/'output'
    generate_dataset(base, per_synth=8, jobs=1, seed=218, synths=['Bfxr', 'Transfxr', 'Pluckr', 'Footsteppr'])
    # Include exact duplicate controls with a distinct seed: augmentation must
    # group by controls rather than preserving the earlier row-level split.
    meta_path = base/'Bfxr.json'
    meta = json.loads(meta_path.read_text())
    meta['rows'][1] = dict(meta['rows'][0], seed=8991)
    with Renderer() as renderer:
        row = meta['rows'][1]
        _, wave = renderer.render('Bfxr', row['params'], row['seed'])
        feat = describe(wave)
        row.update(audioHash=hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest(),
                   featureHash=hashlib.sha256(feat.astype('<f4').tobytes()).hexdigest(),
                   packedFeatureHash=hashlib.sha256(feat.astype('<f2').tobytes()).hexdigest())
        unit, cat = ControlSchema(meta['spec']).encode(row['params'])
        npz_path = base/'Bfxr.npz'
        with np.load(npz_path) as saved:
            arrays = {key: saved[key].copy() for key in saved.files}
        for key, value in [('features', feat), ('continuous', unit), ('categorical', cat), ('generator', row['generatorIndex'])]:
            arrays[key][1] = value
        np.savez_compressed(npz_path, **arrays)
    meta['train'], meta['val'] = split_rows(meta['rows'], seed=218)
    meta_path.write_text(json.dumps(meta))
    manifest_path = base/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['files']['Bfxr']['metadataSha256'] = file_hash(meta_path)
    manifest['files']['Bfxr']['npzSha256'] = file_hash(base/'Bfxr.npz')
    manifest_path.write_text(json.dumps(manifest))
    frozen = {p.name: file_hash(p) for p in base.iterdir()}
    result = augment_dataset(base, output, per_synth=8, seed=321, jobs=1)
    return base, output, frozen, result


def test_augmentation_keeps_native_rows_and_arrays_and_binds_actual_new_renders(augmented):
    base, output, frozen, result = augmented
    assert result['complete'] and result['engines'] == ['Bfxr', 'Transfxr', 'Pluckr', 'Footsteppr']
    assert result['baseManifestHash'] == frozen['manifest.json']
    assert {p.name: file_hash(p) for p in base.iterdir()} == frozen
    with Renderer() as renderer:
        for name in result['engines']:
            native = json.loads((base/(name+'.json')).read_text())
            shard = json.loads((output/(name+'.json')).read_text())
            added = 0 if name == 'Footsteppr' else 8
            assert shard['rows'][:8] == native['rows']
            assert len(shard['rows']) == 8+added
            assert shard['baseRows'] == 8 and shard['structuredRows'] == added
            assert shard['splitComposition']['train']['base'] + shard['splitComposition']['val']['base'] == 8
            assert shard['splitComposition']['train']['structured'] + shard['splitComposition']['val']['structured'] == added
            with np.load(base/(name+'.npz')) as original, np.load(output/(name+'.npz')) as saved:
                for key in original.files:
                    np.testing.assert_array_equal(saved[key][:8], original[key])
                assert saved['features'].dtype == np.float16
                assert saved['features'].shape == (8+added, DIM)
                assert saved['continuous'].dtype == np.float32
                assert saved['categorical'].dtype == saved['generator'].dtype == np.int16
                for i in range(8, 8+added):
                    row = shard['rows'][i]
                    assert row['origin'] == 'structured' and row['structured']
                    assert row['generator'] == 'randomize_params'
                    assert row['sourceHash'] == result['sourceHash']
                    canonical, wave = renderer.render(name, row['params'], row['seed'])
                    assert canonical == row['params']
                    assert row['parameterHash'] == parameter_hash(row)
                    from neural_invert.structured import structured_params
                    proposed, gesture = structured_params(shard['spec'], np.random.default_rng(row['sampleSeed']), row['structuredIndex'])
                    assert gesture == row['structuredGesture']
                    assert renderer.render(name, proposed, row['seed'])[0] == canonical
                    unit, cat = ControlSchema(shard['spec']).encode(canonical)
                    np.testing.assert_array_equal(saved['continuous'][i], unit)
                    np.testing.assert_array_equal(saved['categorical'][i], cat)
                    assert saved['generator'][i] == row['generatorIndex']
                    assert hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest() == row['audioHash']
                    feat = describe(wave)
                    assert hashlib.sha256(feat.astype('<f4').tobytes()).hexdigest() == row['featureHash']
                    assert hashlib.sha256(saved['features'][i].astype('<f2').tobytes()).hexdigest() == row['packedFeatureHash']
            train = {parameter_hash(shard['rows'][i]) for i in shard['train']}
            val = {parameter_hash(shard['rows'][i]) for i in shard['val']}
            assert not train & val
            assert sorted(shard['train']+shard['val']) == list(range(8+added))
    from neural_invert.train import _load_dataset
    loaded, specs, shards, mean, std = _load_dataset(output)
    assert mean.shape == std.shape == (DIM,)
    assert len(specs) == len(shards) == 4


def test_complete_resume_is_immutable_and_rejects_changed_config_and_corruption(augmented):
    from neural_invert.structured import augment_dataset
    base, output, _, result = augmented
    frozen = {p.name: file_hash(p) for p in output.iterdir()}
    assert augment_dataset(base, output, per_synth=8, seed=321, jobs=2) == result
    assert {p.name: file_hash(p) for p in output.iterdir()} == frozen
    for kwargs in ({'per_synth': 9, 'seed': 321}, {'per_synth': 8, 'seed': 322}):
        with pytest.raises(ValueError, match='incompatible'):
            augment_dataset(base, output, jobs=1, **kwargs)
    path = output/'Pluckr.npz'; original = path.read_bytes()
    try:
        path.write_bytes(original[:-1]+b'X')
        with pytest.raises(ValueError, match='integrity'):
            augment_dataset(base, output, per_synth=8, seed=321, jobs=1)
    finally:
        path.write_bytes(original)
    path = base/'Footsteppr.npz'; original = path.read_bytes()
    try:
        path.write_bytes(original[:-1]+b'X')
        with pytest.raises(ValueError, match='integrity'):
            augment_dataset(base, output, per_synth=8, seed=321, jobs=1)
    finally:
        path.write_bytes(original)


def test_generation_code_binding_reads_actual_dependency_bytes_independent_of_cwd(tmp_path, monkeypatch):
    from pathlib import Path
    from neural_invert.structured import generation_code_binding
    import neural_invert.structured as structured
    root = Path(structured.__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    binding = generation_code_binding()
    assert set(binding['files']) == {'neural_invert/structured.py', 'neural_invert/schema.py',
                                    'neural_invert/data.py', 'match/optimizer.py',
                                    'match/audio.py', 'multisynth/renderer.py', 'render/multisynth_worker.js'}
    for relative, digest in binding['files'].items():
        assert digest == file_hash(root/relative)
    encoded = json.dumps(binding['files'], sort_keys=True, separators=(',', ':')).encode()
    assert binding['sha256'] == hashlib.sha256(encoded).hexdigest()
    monkeypatch.setattr(structured, '__file__', str(tmp_path/'missing'/'neural_invert'/'structured.py'))
    with pytest.raises(ValueError, match='dependency.*missing'):
        generation_code_binding()


@pytest.mark.parametrize('dependency', ['neural_invert/schema.py', 'neural_invert/data.py', 'match/optimizer.py', 'render/multisynth_worker.js'])
def test_resume_rejects_changed_dependency_bytes(augmented, tmp_path, monkeypatch, dependency):
    from pathlib import Path
    import neural_invert.structured as structured
    base, output, _, result = augmented
    assert dependency in result['augmentationCodeFiles']
    assert result['augmentationCodeHash'] == structured.generation_code_binding()['sha256']
    # Copy dependencies under an alternative module path so the test changes
    # real bytes without touching shared production dependencies.
    original_root = Path(structured.__file__).resolve().parents[1]
    copied_root = tmp_path/'tools'
    for relative in result['augmentationCodeFiles']:
        path = copied_root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((original_root/relative).read_bytes())
    monkeypatch.setattr(structured, '__file__', str(copied_root/'neural_invert'/'structured.py'))
    assert structured.augment_dataset(base, output, 8, 321, jobs=1) == result
    path = copied_root/dependency
    path.write_bytes(path.read_bytes()+b'\n# stale dependency bytes\n')
    with pytest.raises(ValueError, match='incompatible'):
        structured.augment_dataset(base, output, 8, 321, jobs=1)


def test_resume_regenerates_worker_shard_interrupted_before_manifest_publication(augmented, tmp_path, monkeypatch):
    import neural_invert.structured as structured
    base, _, _, _ = augmented
    output = tmp_path/'interrupted'
    original_write = structured._json_write

    def interrupt_before_binding(path, value):
        if path.name == 'manifest.json' and value.get('shards'):
            raise RuntimeError('Interrupted before shard binding publication')
        return original_write(path, value)

    with monkeypatch.context() as interrupted:
        interrupted.setattr(structured, '_json_write', interrupt_before_binding)
        with pytest.raises(RuntimeError, match='Interrupted before shard binding'):
            structured.augment_dataset(base, output, 8, 321, jobs=1)
    published = json.loads((output/'manifest.json').read_text())
    assert not published['complete'] and not published['shards'] and not published['files']
    assert (output/'Bfxr.npz').exists() and (output/'Bfxr.json').exists()
    # These valid but unbound worker files still must never be accepted as a
    # completed shard. Deliberately damage them; regeneration must replace them.
    (output/'Bfxr.npz').write_bytes(b'not a valid npz')
    (output/'Bfxr.json').write_text('{"untrusted":true}')
    result = structured.augment_dataset(base, output, 8, 321, jobs=1)
    assert result['complete']
    metadata = json.loads((output/'Bfxr.json').read_text())
    assert len(metadata['rows']) == 16 and metadata['structuredRows'] == 8
    with np.load(output/'Bfxr.npz') as saved:
        assert saved['features'].shape == (16, DIM)


@pytest.mark.parametrize('partial_name', ['Transfxr.npz', 'Transfxr.json', 'Transfxr.tmp.npz', 'Transfxr.json.tmp'])
def test_resume_discards_partial_unbound_files_and_preserves_bound_shards(augmented, tmp_path, partial_name):
    import shutil
    import neural_invert.structured as structured
    base, existing, _, original_result = augmented
    output = tmp_path/'partial'
    shutil.copytree(existing, output)
    manifest_path = output/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update(complete=False, shards=[s for s in manifest['shards'] if s['synth'] != 'Transfxr'])
    del manifest['files']['Transfxr']
    manifest_path.write_text(json.dumps(manifest))
    (output/'Transfxr.npz').unlink()
    (output/'Transfxr.json').unlink()
    (output/partial_name).write_bytes(b'half-written worker file')
    bound = {p.name: file_hash(p) for p in output.iterdir() if p.name != 'manifest.json' and not p.name.startswith('Transfxr.')}
    result = structured.augment_dataset(base, output, 8, 321, jobs=1)
    assert result['complete']
    for name, digest in bound.items():
        assert file_hash(output/name) == digest
    assert file_hash(output/'Transfxr.npz') == file_hash(existing/'Transfxr.npz')
    assert json.loads((output/'Transfxr.json').read_text())['rows'] == json.loads((existing/'Transfxr.json').read_text())['rows']
    assert not (output/'Transfxr.tmp.npz').exists()
    assert not (output/'Transfxr.json.tmp').exists()


@pytest.mark.parametrize('failure', ['changed-config', 'corrupt-bound', 'inconsistent-bindings'])
def test_incomplete_resume_validates_before_discarding_any_unbound_bytes(augmented, tmp_path, failure):
    import shutil
    import neural_invert.structured as structured
    base, existing, _, _ = augmented
    output = tmp_path/'reject'
    shutil.copytree(existing, output)
    path = output/'manifest.json'
    manifest = json.loads(path.read_text())
    manifest.update(complete=False, shards=[s for s in manifest['shards'] if s['synth'] != 'Transfxr'])
    if failure != 'inconsistent-bindings':
        del manifest['files']['Transfxr']
    if failure == 'changed-config':
        manifest['augmentationCodeHash'] = 'stale'
    if failure == 'corrupt-bound':
        (output/'Bfxr.npz').write_bytes(b'corrupted bound shard')
    path.write_text(json.dumps(manifest))
    (output/'Transfxr.npz').write_bytes(b'unbound bytes must be preserved on validation failure')
    frozen = {p.name: file_hash(p) for p in output.iterdir()}
    with pytest.raises(ValueError, match='incompatible|integrity'):
        structured.augment_dataset(base, output, 8, 321, jobs=1)
    assert {p.name: file_hash(p) for p in output.iterdir()} == frozen
