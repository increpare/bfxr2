"""Pair training normalization, global validation, and artifact bindings."""
from copy import deepcopy
import json

import numpy as np
import pytest
import torch


def test_normalization_uses_train_rows_and_suppresses_peak():
    from neural_invert.pair_train import normalization
    features = torch.zeros(5, 4083)
    features[0] = 1; features[1] = 3; features[2:] = 1000
    result = normalization(features, torch.tensor([0, 1]))
    assert result['scope'] == 'training-rows-only'
    assert result['mean'][0] == 2 and result['std'][0] == 1
    assert result['mean'][4081] == 0 and result['std'][4081] == 1e9
    constant = normalization(features, torch.tensor([0]))
    assert constant['std'][0] == pytest.approx(.025)


def test_validation_routing_is_global_and_independent_of_batch_size(monkeypatch):
    from neural_invert import pair_train as training
    from neural_invert.temporal import mixture_loss

    class Fixed(torch.nn.Module):
        codec = None
        modes = 4

        def forward(self, x):
            # Every minibatch of two picks one mode; global routing is balanced.
            winner = x[:, 0].long()
            energy = torch.full((len(x), 4), 8.)
            energy.scatter_(1, winner[:, None], 0.)
            return {'energy': energy, 'mode_logits': torch.zeros(len(x), 4)}

    monkeypatch.setattr(training, 'pair_energy', lambda pred, *_: pred['energy'])
    features = torch.zeros(8, 4083); features[:, 0] = torch.arange(4).repeat_interleave(2)
    shard = dict(features=features, continuous=torch.zeros(8, 1), categorical=torch.zeros(8, 1, dtype=torch.long))
    norm = dict(mean=[0.]*4083, std=[1.]*4083)
    a = training.validation(Fixed(), shard, torch.arange(8), norm, torch.device('cpu'), batch_size=2)
    b = training.validation(Fixed(), shard, torch.arange(8), norm, torch.device('cpu'), batch_size=5)
    prediction = Fixed()(features)
    expected, _ = mixture_loss(prediction['energy'], prediction['mode_logits'])
    assert a['total'] == pytest.approx(float(expected), abs=1e-7)
    assert a == b and a['routingKL'] == pytest.approx(0, abs=1e-7)


@pytest.fixture
def mini_data(tmp_path, monkeypatch):
    from neural_invert import pair_train as training
    from neural_invert import pair_data as data
    from neural_invert.pair_model import PairCodec
    from neural_invert.data import _json_write, file_hash
    from neural_invert.benchmark import audio_hash
    from multisynth.renderer import Renderer
    from multisynth.composition import CompositionRenderer
    import soundfile as sf
    root = tmp_path/'data'; root.mkdir(); (root/'bank').mkdir()
    with Renderer() as renderer:
        specs = {n: renderer.specs[n] for n in data.ENGINES}
    with CompositionRenderer() as renderer:
        inventory = renderer.inventory
    counts = {split: (2, 1, 1) for split in ('train', 'val', 'test')}
    monkeypatch.setattr(training, 'COUNTS', counts)
    monkeypatch.setattr(training, 'POOL', {s: 1 for s in counts})
    bank = {}
    for name in data.ENGINES:
        for split in counts:
            for i in range(1000):
                params = deepcopy(specs[name]['defaults'])
                params['duration'] = .2+i*.001
                source = dict(synth=name, name=name, params=params, renderSeed=.5)
                key = data.component_id(source)
                if data.split_for_id(key) == split: break
            path = root/'bank'/(key+'.wav')
            wave = np.full(4410, .01, np.float32); sf.write(path, wave, 44100, subtype='FLOAT')
            bank[key] = dict(id=key, source=source, split=split, file=str(path), fileSha256=file_hash(path),
                             audioHash=audio_hash(wave), samples=len(wave))
    rows = []
    for split, quantities in counts.items():
        ids = [next(k for k, v in bank.items() if v['split'] == split and v['source']['synth'] == name) for name in data.ENGINES]
        for kind, count in zip(('both', 'Boomr', 'Transfxr'), quantities):
            for i in range(count):
                keys = [key if kind in ('both', name) else None for key, name in zip(ids, data.ENGINES)]
                rows.append(dict(id=f'{split}-{kind}-{i}', split=split, kind=kind, componentIds=keys,
                                 params=dict(sources=json.dumps([bank[k]['source'] if k else None for k in keys]),
                                             balance=.4 if kind == 'both' else .5, seed=.5, masterVolume=.5)))
    codec = PairCodec(specs)
    labels = [codec.encode(row['params']) for row in rows]
    features = np.random.default_rng(2).normal(size=(len(rows), 4083)).astype(np.float32)
    features[4:] += 100
    np.savez_compressed(root/'data.npz', features=features,
                        continuous=np.stack([v[0] for v in labels]), categorical=np.stack([v[1] for v in labels]))
    _json_write(root/'rows.json', rows); _json_write(root/'frozen-rows.json', rows)
    bankdoc = dict(complete=True, inventory=inventory, specs=specs, bank=bank,
                   codeBindings=data.code_bindings(), seed=data.SEED, poolSizes=training.POOL,
                   exampleCounts=counts, featureHash=training.FEATURE_HASH, featureCodeHash=training.FEATURE_CODE_HASH)
    _json_write(root/'bank.json', bankdoc)
    manifest = dict(complete=True, examples=len(rows), specs=specs, inventory=inventory,
                    codeBindings=data.code_bindings(), seed=data.SEED,
                    bankSha256=file_hash(root/'bank.json'), dataSha256=file_hash(root/'data.npz'),
                    rowsSha256=file_hash(root/'rows.json'), frozenRowsSha256=file_hash(root/'frozen-rows.json'),
                    featureHash=training.FEATURE_HASH, featureCodeHash=training.FEATURE_CODE_HASH,
                    splits={s: [i for i, row in enumerate(rows) if row['split'] == s] for s in counts})
    _json_write(root/'manifest.json', manifest)
    return root, manifest, rows


def test_data_bindings_and_exact_label_validation(mini_data):
    from neural_invert.pair_train import read_data
    root, manifest, _ = mini_data
    loaded, bank, rows, shard, codec = read_data(root)
    assert loaded == manifest and len(rows) == 12 and len(bank['bank']) == 6
    assert shard['features'].shape == (12, 4083) and codec.n_continuous == 28
    (root/'rows.json').write_text('[]')
    with pytest.raises(ValueError, match='binding|integrity'): read_data(root)


def test_read_data_rejects_semantically_altered_labels_even_with_new_file_hash(mini_data):
    from neural_invert.pair_train import read_data
    from neural_invert.data import file_hash, _json_write
    root, manifest, _ = mini_data
    with np.load(root/'data.npz') as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    arrays['continuous'][0, 0] += .01
    np.savez_compressed(root/'data.npz', **arrays)
    manifest['dataSha256'] = file_hash(root/'data.npz')
    _json_write(root/'manifest.json', manifest)
    with pytest.raises(ValueError, match='encoded labels'): read_data(root)


def test_one_epoch_checkpoint_reproduces_validation_and_rejects_tampering(mini_data, monkeypatch, tmp_path):
    from neural_invert import pair_train as training
    root, _, _ = mini_data
    monkeypatch.setattr(training, 'RECIPE', dict(training.RECIPE, epochs=1, batchSize=3))
    output = tmp_path/'model'
    report = training.train(output, data=root, device='cpu')
    assert report['complete'] and report['bestEpoch'] == 1
    assert report['validationReplay']['reproduced']
    model, meta = training.load(output)
    assert meta['normalization']['mean'][0] < 2
    assert len(training.predict(model, meta, np.full(4410, .01, np.float32))) == 4
    with pytest.raises(ValueError, match='finite'):
        training.predict(model, meta, np.full(4410, np.nan, np.float32))
    path = output/'training.json'; saved = json.loads(path.read_text())
    saved['history'][0]['validation']['total'] += .1
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match='best|history|validation'): training.load(output)
