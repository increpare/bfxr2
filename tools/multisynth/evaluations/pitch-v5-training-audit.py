"""Independently compare data/architecture bindings and recompute validation."""
import json
from pathlib import Path
import numpy as np
import torch
from neural_invert.temporal import load_temporal as load_old, acoustic_energy, mixture_loss, balanced_weights
from neural_invert.pitch_v5_temporal import load_temporal
from neural_invert.pitch_v5_data import load_dataset, UNCHANGED
from neural_invert.pitch_v5_features import describe
from neural_invert.data import file_hash
from neural_invert.benchmark import audio_hash
from multisynth.renderer import Renderer


def main():
    torch.set_num_threads(1)
    root = Path('tools/multisynth/runs/pitch-v5')
    old_root = Path('tools/multisynth/runs/temporal-v3')
    manifest, specs, shards, metas, normalization, splits = load_dataset(root/'data')
    source = json.loads((old_root/'data/manifest.json').read_text())
    assert manifest['sourceDataset']['manifestSha256'] == file_hash(old_root/'data/manifest.json')
    assert manifest['splits'] == source['splits']
    data_rows = []
    with Renderer() as renderer:
        for name in manifest['engines']:
            meta = metas[name]
            with np.load(old_root/'data'/(name+'.npz')) as before, np.load(root/'data'/(name+'.npz')) as after:
                for key in before.files:
                    old = before[key][:, UNCHANGED] if key == 'features' else before[key]
                    new = after[key][:, UNCHANGED] if key == 'features' else after[key]
                    assert old.dtype == new.dtype and old.shape == new.shape and old.tobytes() == new.tobytes(), (name, key)
                sample_ids = sorted(set(np.linspace(0, len(meta['rows'])-1, 9).astype(int)))
                for i in sample_ids:
                    row = meta['rows'][i]
                    canonical, wave = renderer.render(name, row['params'], row['seed'])
                    assert canonical == row['params'] and audio_hash(wave) == row['audioHash']
                    feature = describe(wave)
                    assert audio_hash(feature) == row['featureHash']
                    assert feature.astype('<f2').tobytes() == after['features'][i].tobytes()
            data_rows.append({'engine': name, 'rows': len(meta['rows']), 'train': len(splits[name]['train']),
                'validation': len(splits[name]['val']), 'replayedRows': [int(i) for i in sample_ids],
                'unchangedColumnsLabelsSplits': True})
    records = []
    for name in ('Bfxr', 'Transfxr', 'Pluckr'):
        path = root/'experts'/name
        model, metadata = load_temporal(path)
        old_model, old_meta = load_old(old_root/'hybrid-experts'/name)
        assert metadata['trainingRecipe'] == old_meta['trainingRecipe']
        assert metadata['engineSeed'] == old_meta['engineSeed']
        assert metadata['spec'] == old_meta['spec']
        assert {k: tuple(v.shape) for k,v in model.state_dict().items()} == {k: tuple(v.shape) for k,v in old_model.state_dict().items()}
        for key in ('mean','std'):
            assert np.array_equal(np.asarray(metadata['normalization'][key])[UNCHANGED], np.asarray(old_meta['normalization'][key])[UNCHANGED])
        shard = shards[name]; ids = shard['val']
        weights = balanced_weights(metas[name]['rows'], splits[name]['val'])
        mean, std = [torch.tensor(metadata['normalization'][key]) for key in ('mean','std')]
        total = 0.
        batch_size = metadata['trainingRecipe']['batchSize']
        with torch.no_grad():
            for offset in range(0, len(ids), batch_size):
                batch = ids[offset:offset+batch_size]
                prediction = model((shard['features'][batch]-mean)/std)
                labels = {key: shard[key][batch] for key in ('continuous','categorical')}
                loss, _ = mixture_loss(acoustic_energy(prediction, labels, metadata['spec']), prediction['mode_logits'], weights[offset:offset+batch_size])
                total += float(loss)*len(batch)
        actual = total/len(ids)
        report = json.loads((path/'training.json').read_text())
        expected = report['bestValidation']['total']
        assert abs(actual-expected) <= 3e-5, (name, actual, expected)
        records.append({'engine': name, 'checkpointSha256': metadata['checkpointHash'], 'baselineCheckpointSha256': old_meta['checkpointHash'],
            'checkpointEpoch': metadata['checkpointEpoch'], 'reportSha256': file_hash(path/'training.json'),
            'validationRows': len(ids), 'recomputedLoss': actual, 'reportedLoss': expected,
            'difference': abs(actual-expected), 'allEpochs': len(report['history']),
            'baselineControlLoss': json.loads((old_root/'hybrid-experts'/name/'training.json').read_text())['bestValidation']['total'],
            'architectureRecipeSeedMatched': True, 'nonpitchNormalizationUnchanged': True})
        print(name, metadata['checkpointEpoch'], actual, flush=True)
    result = {'complete': True, 'dataManifestSha256': file_hash(root/'data/manifest.json'),
        'sourceDataManifestSha256': file_hash(old_root/'data/manifest.json'), 'auditScriptSha256': file_hash(__file__),
        'data': data_rows, 'models': records, 'cpuValidationRecomputed': True, 'absoluteTolerance': 3e-5,
        'scope': 'Dataset preservation and controlled recipe/checkpoint validation; control loss does not establish audible likeness.'}
    Path('tools/multisynth/evaluations/pitch-v5-training-audit.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
