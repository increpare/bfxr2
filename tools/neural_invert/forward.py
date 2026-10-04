"""Independent differentiable numeric-control forward descriptor pilot.

Descriptors are normalized per engine using training rows only. This predicts
audio evidence, not a waveform; unobserved render RNG anchors remain a limitation.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from multisynth.renderer import Renderer
from .data import _json_write, file_hash, verify_dataset_files
from .features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
from .schema import ControlSchema
from .train import choose_device


ENGINES = ('Bfxr', 'Transfxr', 'Pluckr')
FEATURE_GROUPS = {
    'relativeSpectrum': ((0, 2304),), 'absoluteSpectrum': ((2304, 3840),),
    'relativeEnvelope': ((3840, 3888),), 'absoluteEnvelope': ((3984, 4016),),
    'relativePitch': ((3888, 3936),), 'absolutePitch': ((4016, 4048),),
    'combinedVoicing': ((3936, 3984), (4048, 4080)),
    'duration': ((4080, 4081),), 'rms': ((4082, 4083),),
}
GATE_GROUPS = ('relativeEnvelope', 'absoluteEnvelope', 'relativePitch', 'absolutePitch', 'combinedVoicing')
LOSS_POLICY = {'version': 'forward-equal-groups-v1', 'groups': {name: [list(r) for r in ranges] for name, ranges in FEATURE_GROUPS.items()},
               'groupWeight': 1/9, 'ignoredIndices': [4081], 'normalizationStdFloor': .025}
MODEL_POLICY = {'version': 'forward-mlp-v1', 'hiddenLayers': 2, 'activation': 'GELU',
                'outputDim': DIM, 'categories': 'one-hot-or-softmax-logits', 'input': 'canonical-unit-controls'}
GATE_POLICY = {'totalBaselineRatio': .8, 'groupsAtMostBaseline': list(GATE_GROUPS), 'absoluteTolerance': 1e-8,
               'meaning': 'held-out descriptor prediction only; no waveform or perceptual likeness claim'}


def _hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _code_hash(name):
    return file_hash(Path(__file__).with_name(name))


def _schema(spec):
    schema = ControlSchema(spec)
    if schema.fixed_text:
        raise ValueError('Forward pilot does not support TEXT controls')
    if spec.get('name') not in ENGINES:
        raise ValueError('Unsupported forward pilot engine')
    if not schema.continuous or any(not c['values'] for c in schema.categorical):
        raise ValueError('Invalid forward control schema')
    return schema


def encode_controls(unit, categories, spec):
    """Concatenate unit controls and hard one-hots or softmax(logits).

    A list of one tensor per category denotes logits, so gradients remain intact.
    Integer tensors denote already chosen category indices. Leading dimensions
    are preserved, supporting both individual control vectors and batches.
    """
    schema = _schema(spec)
    if not isinstance(unit, torch.Tensor) or not unit.is_floating_point() or unit.ndim < 1 or unit.shape[-1] != len(schema.continuous):
        raise ValueError('Continuous control dimensions or dtype are invalid')
    if not torch.isfinite(unit).all() or torch.any((unit < 0) | (unit > 1)):
        raise ValueError('Continuous controls must be finite unit values')
    pieces = [unit]
    if isinstance(categories, list):
        if len(categories) != len(schema.categorical):
            raise ValueError('Categorical logits dimensions are invalid')
        for logits, control in zip(categories, schema.categorical):
            if not isinstance(logits, torch.Tensor) or not logits.is_floating_point() or logits.shape != (*unit.shape[:-1], len(control['values'])):
                raise ValueError('Categorical logits dimensions or dtype are invalid')
            if logits.device != unit.device or not torch.isfinite(logits).all():
                raise ValueError('Categorical logits device or values are invalid')
            pieces.append(logits.softmax(-1).to(unit.dtype))
    else:
        if not isinstance(categories, torch.Tensor) or categories.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8) or categories.shape != (*unit.shape[:-1], len(schema.categorical)):
            raise ValueError('Categorical control dimensions or integer dtype are invalid')
        if categories.device != unit.device:
            raise ValueError('Categorical control device is invalid')
        for i, control in enumerate(schema.categorical):
            column = categories[..., i]
            if torch.any((column < 0) | (column >= len(control['values']))):
                raise ValueError('Categorical control outside schema bounds')
            pieces.append(F.one_hot(column.long(), len(control['values'])).to(unit.dtype))
    return torch.cat(pieces, dim=-1)


class ForwardModel(nn.Module):
    def __init__(self, spec, hidden=256):
        super().__init__()
        schema = _schema(spec)
        if not isinstance(hidden, int) or hidden < 1:
            raise ValueError('Forward hidden width must be positive')
        self.spec = deepcopy(spec)
        dimension = len(schema.continuous) + sum(len(c['values']) for c in schema.categorical)
        self.network = nn.Sequential(nn.Linear(dimension, hidden), nn.GELU(),
                                     nn.Linear(hidden, hidden), nn.GELU(), nn.Linear(hidden, DIM))

    def forward(self, unit, categories):
        return self.network(encode_controls(unit, categories, self.spec))


def feature_loss(prediction, target):
    """Equal mean of nine disjoint normalized descriptor-group MSEs."""
    if prediction.shape != target.shape or prediction.ndim < 1 or prediction.shape[-1] != DIM:
        raise ValueError('Forward feature dimensions are invalid')
    if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
        raise ValueError('Forward features must be finite')
    groups = {name: torch.cat([(prediction[..., start:stop]-target[..., start:stop]) for start, stop in ranges], dim=-1).square().mean()
              for name, ranges in FEATURE_GROUPS.items()}
    return torch.stack(list(groups.values())).mean(), groups


def _load_data(path, engines):
    manifest = json.loads((path/'manifest.json').read_text())
    expected = {'featureVersion': VERSION, 'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM}
    if not manifest.get('complete') or any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError('Dataset completion or feature provenance is incompatible')
    if any(name not in manifest['engines'] for name in engines):
        raise ValueError('Requested forward engine is absent from dataset')
    verify_dataset_files(path, manifest)
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != manifest.get('sourceHash'):
            raise ValueError('Dataset DSP source is incompatible')
        current_specs = {name: renderer.specs[name] for name in engines}
    result = {}
    for name in engines:
        metadata = json.loads((path/(name+'.json')).read_text())
        if metadata.get('sourceHash') != manifest['sourceHash'] or any(metadata.get(key) != value for key, value in expected.items()):
            raise ValueError('Dataset shard provenance is incompatible')
        spec = metadata['spec']; schema = _schema(spec)
        if spec != current_specs[name] or spec.get('name') != name:
            raise ValueError('Dataset control schema is incompatible')
        with np.load(path/(name+'.npz'), allow_pickle=False) as saved:
            features = saved['features'].astype(np.float32)
            unit = saved['continuous'].astype(np.float32)
            categories = saved['categorical'].copy()
        count = len(features)
        if features.shape != (count, DIM) or unit.shape != (count, len(schema.continuous)) or categories.shape != (count, len(schema.categorical)):
            raise ValueError('Dataset array dimensions are invalid')
        if not np.isfinite(features).all() or not np.isfinite(unit).all() or categories.dtype.kind not in 'iu':
            raise ValueError('Dataset arrays must be finite with integer categories')
        arrays = {'features': torch.from_numpy(features), 'continuous': torch.from_numpy(unit),
                  'categorical': torch.from_numpy(categories.astype(np.int64))}
        encode_controls(arrays['continuous'], arrays['categorical'], spec)
        splits = {key: metadata[key] for key in ('train', 'val')}
        for ids in splits.values():
            if not ids or any(type(i) is not int or i < 0 or i >= count for i in ids) or len(ids) != len(set(ids)):
                raise ValueError('Dataset split indices must be nonempty and valid')
        if set(splits['train']) & set(splits['val']) or set(splits['train']+splits['val']) != set(range(count)):
            raise ValueError('Dataset splits must cover rows without overlap')
        if manifest.get('splits', {}).get(name) != splits:
            raise ValueError('Dataset manifest and shard splits disagree')
        # Dataset grouping hashes exclude RNG: duplicated controls cannot leak.
        rows = metadata.get('rows', [])
        if len(rows) != count or {rows[i]['parameterHash'] for i in splits['train']} & {rows[i]['parameterHash'] for i in splits['val']}:
            raise ValueError('Dataset canonical row grouping is invalid')
        training = features[splits['train']].astype(np.float64)
        mean = training.mean(0).astype(np.float32)
        std = np.maximum(training.std(0), .025).astype(np.float32)
        arrays.update({key: torch.tensor(ids, dtype=torch.long) for key, ids in splits.items()})
        result[name] = (spec, arrays, mean, std)
    return manifest, result


def _evaluate(model, shard, ids, mean, std, batch_size, device, baseline=False):
    totals = {'total': 0., 'groups': {name: 0. for name in FEATURE_GROUPS}}
    with torch.no_grad():
        for batch in ids.split(batch_size):
            target = (shard['features'][batch].to(device)-mean)/std
            prediction = torch.zeros_like(target) if baseline else model(shard['continuous'][batch].to(device), shard['categorical'][batch].to(device))
            total, groups = feature_loss(prediction, target)
            totals['total'] += float(total)*len(batch)
            for name, loss in groups.items():
                totals['groups'][name] += float(loss)*len(batch)
    return {'total': totals['total']/len(ids), 'groups': {name: value/len(ids) for name, value in totals['groups'].items()}}


def _gate(validation, baseline):
    tolerance = GATE_POLICY['absoluteTolerance']
    total_pass = validation['total'] <= .8*baseline['total'] + tolerance
    group_pass = {name: validation['groups'][name] <= baseline['groups'][name]+tolerance for name in GATE_GROUPS}
    return {'passed': total_pass and all(group_pass.values()), 'totalPassed': total_pass, 'groupPassed': group_pass,
            'policy': deepcopy(GATE_POLICY)}


def _training_recipe(epochs, batch_size, hidden, seed, threads, learning_rate):
    for name, value in (('epochs', epochs), ('batchSize', batch_size), ('hidden', hidden), ('threads', threads)):
        if type(value) is not int or value < 1:
            raise ValueError(name+' must be a positive integer')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('seed must be an integer in [0, 2**32)')
    if not isinstance(learning_rate, (int, float)) or not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError('Forward learning rate must be positive and finite')
    return {'epochs': epochs, 'batchSize': batch_size, 'hidden': hidden, 'seed': seed,
            'threads': threads, 'learningRate': learning_rate,
            'optimizer': {'name': 'AdamW', 'weightDecay': .0001, 'scheduler': 'cosine', 'minimumLearningRate': learning_rate*.1}}


def train_forward(data, output, engines, epochs=40, device=None, hidden=256, batch_size=128, seed=20261007, threads=1, learning_rate=.001):
    """Train independent engines; select epochs solely by validation group loss."""
    output, data = Path(output), Path(data)
    if output.exists():
        raise FileExistsError('Forward pilot output must be fresh: '+str(output))
    engines = list(engines)
    if not engines or len(engines) != len(set(engines)) or any(name not in ENGINES for name in engines):
        raise ValueError('Unsupported or empty forward pilot engines')
    recipe = _training_recipe(epochs, batch_size, hidden, seed, threads, learning_rate)
    manifest, datasets = _load_data(data, engines)
    torch.set_num_threads(threads); torch.manual_seed(seed); np.random.seed(seed)
    device = choose_device(device)
    output.mkdir(parents=True, exist_ok=False)
    report = {'version': 1, 'device': str(device), 'engines': engines, 'epochs': epochs,
              'batchSize': batch_size, 'threads': threads, 'seed': seed, 'learningRate': learning_rate,
              'optimizer': deepcopy(recipe['optimizer']), 'trainingRecipe': recipe,
              'dataManifestHash': file_hash(data/'manifest.json'), 'perEngine': {},
              'limitations': ['Render RNG and seed/instrumentSeed anchors are unobserved inputs; noise/string realizations cannot be predicted exactly.',
                              'Validation measures normalized descriptor prediction, not waveform synthesis or real-SFX likeness.',
                              'This predictive gate is a prerequisite for a separate actual-DSP gradient experiment.']}
    for name in engines:
        spec, shard, mean, std = datasets[name]
        engine_path = output/name; engine_path.mkdir()
        normalization = {'mean': mean.tolist(), 'std': std.tolist(), 'scope': 'engine-training-rows-only',
                         'stdFloor': .025, 'trainRows': len(shard['train']), 'trainingIndicesHash': _hash_json(shard['train'].tolist())}
        metadata = {'version': 1, 'engine': name, 'spec': spec, 'schemaHash': _hash_json(spec), 'hidden': hidden,
                    'trainingRecipe': deepcopy(recipe), 'trainingRecipeHash': _hash_json(recipe),
                    'sourceHash': manifest['sourceHash'], 'featureVersion': VERSION, 'featureDim': DIM,
                    'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH,
                    'forwardCodeHash': _code_hash('forward.py'), 'schemaCodeHash': _code_hash('schema.py'),
                    'datasetCodeHash': _code_hash('data.py'), 'originalTrainingCodeHash': _code_hash('train.py'),
                    'modelPolicy': deepcopy(MODEL_POLICY), 'lossPolicy': deepcopy(LOSS_POLICY),
                    'gatePolicy': deepcopy(GATE_POLICY), 'normalization': normalization, 'normalizationHash': _hash_json(normalization),
                    'seed': seed, 'dataManifestHash': report['dataManifestHash'], 'datasetFiles': manifest['files'][name],
                    'splitHash': _hash_json({key: shard[key].tolist() for key in ('train', 'val')}),
                    'fixedRandomness': ControlSchema(spec).fixed_randomness, 'ignorePeakGain': True}
        model = ForwardModel(spec, hidden).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=.0001)
        schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs, eta_min=learning_rate*.1)
        mean_t, std_t = torch.from_numpy(mean).to(device), torch.from_numpy(std).to(device)
        baseline = _evaluate(model, shard, shard['val'], mean_t, std_t, batch_size, device, baseline=True)
        metadata['baseline'] = baseline
        engine_report = {'metadata': metadata, 'trainingRecipe': deepcopy(recipe), 'baseline': baseline, 'history': [], 'bestValidation': None,
                         'bestEpoch': None, 'trainRows': len(shard['train']), 'validationRows': len(shard['val']),
                         'parameters': sum(p.numel() for p in model.parameters())}
        started = time.monotonic()
        for epoch in range(epochs):
            model.train(); order = shard['train'][torch.randperm(len(shard['train']))]
            train_total, train_groups, count = 0., {group: 0. for group in FEATURE_GROUPS}, 0
            for ids in order.split(batch_size):
                target = (shard['features'][ids].to(device)-mean_t)/std_t
                optimizer.zero_grad(set_to_none=True)
                loss, groups = feature_loss(model(shard['continuous'][ids].to(device), shard['categorical'][ids].to(device)), target)
                loss.backward(); optimizer.step()
                train_total += float(loss.detach())*len(ids); count += len(ids)
                for group, value in groups.items():
                    train_groups[group] += float(value.detach())*len(ids)
            model.eval()
            validation = _evaluate(model, shard, shard['val'], mean_t, std_t, batch_size, device)
            row = {'epoch': epoch+1, 'train': {'total': train_total/count, 'groups': {g: v/count for g, v in train_groups.items()}},
                   'validation': validation, 'trainRows': count, 'validationRows': len(shard['val']),
                   'learningRate': optimizer.param_groups[0]['lr'], 'elapsedSeconds': time.monotonic()-started}
            engine_report['history'].append(row); schedule.step()
            if engine_report['bestValidation'] is None or validation['total'] < engine_report['bestValidation']['total']:
                engine_report.update(bestValidation=validation, bestEpoch=epoch+1)
                torch.save({'model': {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                            'metadata': metadata, 'epoch': epoch+1, 'validation': validation}, engine_path/'best.pt')
            engine_report['checkpointHash'] = file_hash(engine_path/'best.pt')
            engine_report['predictiveGate'] = _gate(engine_report['bestValidation'], baseline)
            _json_write(engine_path/'training.json', engine_report)
            report['perEngine'][name] = engine_report
            report['predictiveGatePassed'] = len(report['perEngine']) == len(engines) and all(r['predictiveGate']['passed'] for r in report['perEngine'].values())
            _json_write(output/'training.json', report)
            print(json.dumps({'engine': name, 'epoch': epoch+1, 'trainLoss': row['train']['total'],
                              'validationLoss': validation['total'], 'device': str(device)}), flush=True)
    return report


def load_forward(path):
    """Load an engine directory or best.pt, enforcing report/code/DSP bindings."""
    path = Path(path)
    if path.is_dir():
        path = path/'best.pt'
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    metadata = checkpoint['metadata']
    report_path = path.parent/'training.json'
    if not report_path.exists():
        raise ValueError('Forward checkpoint report binding is incompatible')
    report = json.loads(report_path.read_text())
    if report.get('checkpointHash') != file_hash(path) or report.get('metadata') != metadata or report.get('bestEpoch') != checkpoint.get('epoch') or report.get('bestValidation') != checkpoint.get('validation'):
        raise ValueError('Forward checkpoint report binding is incompatible')
    if report.get('baseline') != metadata.get('baseline') or report.get('predictiveGate') != _gate(checkpoint['validation'], metadata['baseline']):
        raise ValueError('Forward validation baseline or gate binding is incompatible')
    recipe = metadata.get('trainingRecipe', {})
    expected_recipe = _training_recipe(recipe.get('epochs'), recipe.get('batchSize'), recipe.get('hidden'),
                                       recipe.get('seed'), recipe.get('threads'), recipe.get('learningRate'))
    if recipe != expected_recipe or report.get('trainingRecipe') != recipe or metadata.get('trainingRecipeHash') != _hash_json(recipe):
        raise ValueError('Forward training recipe binding is incompatible')
    if metadata.get('hidden') != recipe['hidden'] or metadata.get('seed') != recipe['seed'] or not 1 <= checkpoint['epoch'] <= recipe['epochs']:
        raise ValueError('Forward training recipe and checkpoint settings disagree')
    expected = {'version': 1, 'featureVersion': VERSION, 'featureDim': DIM, 'featureHash': FEATURE_HASH,
                'featureCodeHash': FEATURE_CODE_HASH, 'schemaCodeHash': _code_hash('schema.py'),
                'forwardCodeHash': _code_hash('forward.py'), 'datasetCodeHash': _code_hash('data.py'),
                'modelPolicy': MODEL_POLICY, 'lossPolicy': LOSS_POLICY, 'gatePolicy': GATE_POLICY, 'ignorePeakGain': True}
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError('Forward feature/schema/model policy or code is incompatible')
    spec = metadata.get('spec', {})
    _schema(spec)
    if metadata.get('engine') != spec.get('name') or metadata.get('schemaHash') != _hash_json(spec):
        raise ValueError('Forward schema metadata is incompatible')
    normalization = metadata.get('normalization', {})
    for key in ('mean', 'std'):
        vector = np.asarray(normalization.get(key, []))
        if vector.shape != (DIM,) or not np.isfinite(vector).all() or (key == 'std' and np.any(vector < .025-1e-8)):
            raise ValueError('Forward feature normalization is invalid')
    if normalization.get('scope') != 'engine-training-rows-only' or normalization.get('stdFloor') != .025 or metadata.get('normalizationHash') != _hash_json(normalization):
        raise ValueError('Forward normalization binding is incompatible')
    for key in ('dataManifestHash', 'splitHash', 'originalTrainingCodeHash'):
        if not isinstance(metadata.get(key), str) or len(metadata[key]) != 64:
            raise ValueError('Forward dataset/code binding is incompatible')
    if not metadata.get('datasetFiles') or any(not metadata['datasetFiles'].get(key) for key in ('npzSha256', 'metadataSha256')):
        raise ValueError('Forward dataset file binding is incompatible')
    with Renderer() as renderer:
        if metadata.get('sourceHash') != renderer.inventory['sourceHash'] or spec != renderer.specs[metadata['engine']]:
            raise ValueError('Forward DSP source or current control schema is incompatible')
    model = ForwardModel(spec, metadata['hidden'])
    model.load_state_dict(checkpoint['model'], strict=True); model.eval()
    if any(not torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError('Forward model weights are invalid')
    return model, dict(metadata, checkpointHash=file_hash(path), checkpointEpoch=checkpoint['epoch'],
                       baseline=report['baseline'], predictiveGate=report['predictiveGate'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--engines', nargs='+', choices=ENGINES, default=list(ENGINES))
    parser.add_argument('--epochs', type=int, default=40); parser.add_argument('--device')
    parser.add_argument('--hidden', type=int, default=256); parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--seed', type=int, default=20261007); parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--learning-rate', type=float, default=.001)
    args = parser.parse_args()
    train_forward(args.data, args.output, args.engines, args.epochs, args.device, args.hidden,
                  args.batch_size, args.seed, args.threads, args.learning_rate)


if __name__ == '__main__':
    main()
