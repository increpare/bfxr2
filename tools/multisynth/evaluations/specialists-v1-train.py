"""Freeze unseen native control groups, then train two independent specialists."""
import json
from pathlib import Path
import shutil

import numpy as np
from neural_invert.data import file_hash, verify_dataset_files, _json_write
from neural_invert.schema import ControlSchema
from neural_invert.train import train_model

PLAN = Path('tools/multisynth/evaluations/specialists-v1-plan.json')
ROOT = Path('tools/multisynth/runs/specialists-v1')


def main():
    plan = json.loads(PLAN.read_text())
    output = ROOT/'models'
    fit_root = ROOT/'fit-data'
    if output.exists() or (ROOT/'targets.json').exists() or fit_root.exists():
        raise FileExistsError('Preserve original training attempt')
    for path, checksum in plan['codeHashes'].items():
        assert file_hash(path)==checksum
    targets, datasets = [], {}
    for index, engine in enumerate(plan['engines']):
        data = Path(plan['data']['paths'][engine])
        manifest = json.loads((data/'manifest.json').read_text())
        assert manifest['complete'] and manifest['engines']==[engine]
        verify_dataset_files(data, manifest)
        meta = json.loads((data/(engine+'.json')).read_text())
        assert len(meta['rows'])==plan['data']['rowsPerEngine']
        train = {meta['rows'][i]['parameterHash'] for i in meta['train']}
        assert not train & {meta['rows'][i]['parameterHash'] for i in meta['val']}
        schema = ControlSchema(meta['spec'])
        def controls(row):
            unit, cat = schema.encode(row['params'])
            return (tuple(unit.tolist()), tuple(cat.tolist()))
        train_controls = {controls(meta['rows'][i]) for i in meta['train']}
        assert not train_controls & {controls(meta['rows'][i]) for i in meta['val']}, 'Controls overlap after ignoring random seed'
        seen = set()
        for i in np.random.default_rng(plan['evaluation']['nativeSelectionSeed']+index).permutation(meta['val']):
            row = meta['rows'][int(i)]
            if row['parameterHash'] in seen:
                continue
            seen.add(row['parameterHash'])
            targets.append(dict(id=f'{engine}-specialist-{i:05d}', group='fresh-native-'+engine,
                sourceSynth=engine, sourceParams=row['params'], sourceSeed=row['seed'],
                sourceRow=int(i), parameterHash=row['parameterHash'], sourceAudioHash=row['audioHash']))
            if len(seen)==plan['evaluation']['freshNativeControlsPerEngine']:
                break
        assert len(seen)==16
        # Reserve the whole selected control groups from checkpoint-selection
        # validation too. Preserve the original generated dataset unchanged.
        heldout_controls = {controls(meta['rows'][t['sourceRow']]) for t in targets if t['sourceSynth']==engine}
        test = [i for i in meta['val'] if controls(meta['rows'][i]) in heldout_controls]
        validation = [i for i in meta['val'] if controls(meta['rows'][i]) not in heldout_controls]
        assert len(test)>=16 and len(validation)>1000
        fit = fit_root/engine
        fit.mkdir(parents=True)
        shutil.copyfile(data/(engine+'.npz'),fit/(engine+'.npz'))
        fitted = {**meta, 'val':validation, 'test':test,
            'originalMetadataSha256':file_hash(data/(engine+'.json')),
            'heldoutPolicy':'All selected native control groups removed from both optimization and validation checkpoint selection.',
            'splitScriptSha256':file_hash(__file__)}
        _json_write(fit/(engine+'.json'),fitted)
        fit_manifest = {**manifest, 'originalManifestSha256':file_hash(data/'manifest.json'),
            'splits':{engine:{'train':meta['train'],'val':validation,'test':test}},
            'files':{engine:dict(npzSha256=file_hash(fit/(engine+'.npz')),metadataSha256=file_hash(fit/(engine+'.json')))}}
        _json_write(fit/'manifest.json',fit_manifest)
        verify_dataset_files(fit,fit_manifest)
        datasets[engine] = dict(path=str(fit.resolve()),manifestSha256=file_hash(fit/'manifest.json'),
            originalPath=str(data.resolve()),originalManifestSha256=file_hash(data/'manifest.json'))
    _json_write(ROOT/'targets.json', dict(rows=targets, datasets=datasets, planSha256=file_hash(PLAN),
        scriptSha256=file_hash(__file__), scope='Native test control groups excluded from optimization and checkpoint-selection validation; preset families overlap training. Frozen before fitting.'))
    output.mkdir()
    recipe = plan['training']
    for engine in plan['engines']:
        train_model(datasets[engine]['path'], output/engine, epochs=recipe['epochs'],
            device=recipe['device'], hidden=recipe['hidden'], batch_size=recipe['batchSize'],
            seed=recipe['seeds'][engine], threads=1, learning_rate=recipe['learningRate'],
            head_mode=recipe['headMode'], loss_mode=recipe['lossMode'])
    _json_write(ROOT/'training-receipt.json', dict(complete=True, planSha256=file_hash(PLAN),
        scriptSha256=file_hash(__file__), targetsSha256=file_hash(ROOT/'targets.json'), datasets=datasets,
        models={name:dict(checkpointSha256=file_hash(output/name/'best.pt'),
            trainingSha256=file_hash(output/name/'training.json')) for name in plan['engines']}))


if __name__ == '__main__':
    main()
