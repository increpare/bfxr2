"""Frozen-recipe training and strict loading of the joint native Mixr inverse."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf
import torch

from multisynth.composition import CompositionRenderer
from multisynth.renderer import Renderer
from . import pair_data
from .benchmark import audio_hash
from .data import _json_write, file_hash
from .experiment import audition_pcm
from .features import DIM, FEATURE_HASH, FEATURE_CODE_HASH, describe
from .pair_model import PairCodec, PairInverse, pair_energy, MODEL_POLICY, LOSS_POLICY
from .temporal import mixture_loss
from .train import choose_device

COUNTS, POOL = deepcopy(pair_data.COUNTS), deepcopy(pair_data.POOL)
RECIPE = dict(epochs=60, batchSize=128, learningRate=.001, minimumLearningRate=.0001,
              weightDecay=.0001, clipNorm=5., seed=20261020, threads=1, modes=4,
              optimizer='AdamW', scheduler='cosine', selection='minimum-full-validation-mixture-loss',
              normalizationStdFloor=.025, ignoredPeakIndex=4081)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _read(path):
    value = json.loads(Path(path).read_text())
    try:
        _hash(value)
    except (ValueError, TypeError) as error:
        raise ValueError('Artifact JSON contains nonfinite values') from error
    return value


def code_bindings():
    return {**pair_data.code_bindings(),
            'tools/multisynth/composition.py': file_hash('tools/multisynth/composition.py'),
            **{str(Path(__file__).with_name(name)): file_hash(Path(__file__).with_name(name))
               for name in ('pair_train.py', 'train.py')}}


def read_data(path):
    """Validate persisted files, exact encoded labels, split groups and live DSP."""
    path = Path(path)
    manifest = _read(path/'manifest.json')
    if (not manifest.get('complete') or manifest.get('seed') != RECIPE['seed']
            or manifest.get('featureHash') != FEATURE_HASH or manifest.get('featureCodeHash') != FEATURE_CODE_HASH
            or manifest.get('codeBindings') != pair_data.code_bindings()):
        raise ValueError('Dataset feature/code/recipe binding is incompatible')
    for filename, key in (('data.npz', 'dataSha256'), ('rows.json', 'rowsSha256'),
                          ('bank.json', 'bankSha256'), ('frozen-rows.json', 'frozenRowsSha256')):
        if not (path/filename).is_file() or file_hash(path/filename) != manifest.get(key):
            raise ValueError('Dataset file integrity binding differs: '+filename)
    bankdoc, rows, frozen = (_read(path/name) for name in ('bank.json', 'rows.json', 'frozen-rows.json'))
    if (not bankdoc.get('complete') or bankdoc.get('inventory') != manifest.get('inventory')
            or bankdoc.get('specs') != manifest.get('specs')
            or bankdoc.get('codeBindings') != manifest['codeBindings']):
        raise ValueError('Dataset bank binding differs')
    with CompositionRenderer() as renderer:
        if renderer.inventory != manifest['inventory']:
            raise ValueError('Dataset DSP inventory differs')
    with Renderer() as renderer:
        if any(renderer.specs.get(name) != manifest['specs'].get(name) for name in pair_data.ENGINES):
            raise ValueError('Dataset source schemas differ')
    codec = PairCodec(manifest['specs'])
    bank = bankdoc['bank']
    sizes = Counter()
    for key, component in bank.items():
        source = component['source']
        if (key != component.get('id') or key != pair_data.component_id(source)
                or component['split'] != pair_data.split_for_id(key)
                or source['synth'] not in pair_data.ENGINES
                or source.get('renderSeed') != .5 or source['params'].get('masterVolume') != .5
                or any(source['params'].get(k) != .5 for k in codec.schemas[source['synth']].fixed_randomness)):
            raise ValueError('Dataset component identity or fixed seed differs')
        file = Path(component['file'])
        if not file.is_file() or file_hash(file) != component['fileSha256']:
            raise ValueError('Dataset bank PCM file binding differs')
        wave, rate = sf.read(file, dtype='float32')
        if (rate != 44100 or wave.ndim != 1 or len(wave) != component['samples']
                or not np.isfinite(wave).all() or audio_hash(wave) != component['audioHash']):
            raise ValueError('Dataset bank PCM identity differs')
        sizes[(source['synth'], component['split'])] += 1
    expected_sizes = Counter({(name, split): count for name in pair_data.ENGINES for split, count in POOL.items()})
    if sizes != expected_sizes:
        raise ValueError('Dataset component pool counts differ')
    if len(rows) != manifest.get('examples') or len(frozen) != len(rows) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Dataset row identities differ')
    if len(rows) != sum(sum(counts) for counts in COUNTS.values()):
        raise ValueError('Dataset example counts differ')
    expected_splits = {split: [i for i, row in enumerate(rows) if row['split'] == split] for split in COUNTS}
    if manifest.get('splits') != expected_splits or sum(map(len, expected_splits.values())) != len(rows):
        raise ValueError('Dataset splits do not partition rows')
    for split, counts in COUNTS.items():
        if Counter(rows[i]['kind'] for i in expected_splits[split]) != Counter(dict(zip(('both', *pair_data.ENGINES), counts))):
            raise ValueError('Dataset structure counts differ')
    pair_data.check_component_splits(bank, rows)
    for row, original in zip(rows, frozen):
        if any(row[key] != original[key] for key in ('id', 'split', 'kind', 'componentIds')):
            raise ValueError('Dataset frozen row binding differs')
        sources = json.loads(row['params']['sources'])
        if len(sources) != 2 or any(source != (bank[key]['source'] if key else None)
                                    for source, key in zip(sources, row['componentIds'])):
            raise ValueError('Dataset row source controls differ from bank')
        if row['params'].get('seed') != .5 or row['params'].get('masterVolume') != .5:
            raise ValueError('Dataset Mixr fixed seed or volume differs')
        expected_kind = 'both' if all(sources) else pair_data.ENGINES[int(sources[0] is None)]
        if row['kind'] != expected_kind:
            raise ValueError('Dataset row structure differs from sources')
    with np.load(path/'data.npz', allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in ('features', 'continuous', 'categorical')}
    shapes = dict(features=(len(rows), DIM), continuous=(len(rows), codec.n_continuous),
                  categorical=(len(rows), len(codec.cat_sizes)))
    for key, values in arrays.items():
        if (values.shape != shapes[key] or not np.isfinite(values).all()
                or values.dtype != (np.int64 if key == 'categorical' else np.float32)):
            raise ValueError('Dataset typed arrays are invalid')
    for i, row in enumerate(rows):
        unit, cat = codec.encode(row['params'])
        if not np.array_equal(unit, arrays['continuous'][i]) or not np.array_equal(cat, arrays['categorical'][i]):
            raise ValueError('Dataset encoded labels differ from exact native controls')
    shard = {key: torch.from_numpy(values) for key, values in arrays.items()}
    shard.update({split: torch.tensor(ids, dtype=torch.long) for split, ids in expected_splits.items()})
    return manifest, bankdoc, rows, shard, codec


def normalization(features, train_indices):
    values = features[train_indices].numpy().astype(np.float64)
    if not len(values) or not np.isfinite(values).all():
        raise ValueError('Training features must be finite and nonempty')
    mean = values.mean(0).astype(np.float32)
    std = np.maximum(values.std(0), RECIPE['normalizationStdFloor']).astype(np.float32)
    mean[4081], std[4081] = 0., 1e9
    return dict(mean=mean.tolist(), std=std.tolist(), scope='training-rows-only',
                stdFloor=RECIPE['normalizationStdFloor'], ignoredIndices=[4081],
                trainingIndicesHash=_hash(train_indices.tolist()), trainingRows=len(train_indices))


def validation(model, shard, indices, norm, device, batch_size=128):
    """Apply mixture_loss once to the entire split, including its routing KL."""
    model.eval()
    mean, std = (torch.tensor(norm[key], device=device) for key in ('mean', 'std'))
    energies, logits = [], []
    with torch.no_grad():
        for batch in indices.split(batch_size):
            pred = model((shard['features'][batch].to(device)-mean)/std)
            energy = pair_energy(pred, shard['continuous'][batch].to(device),
                                 shard['categorical'][batch].to(device), model.codec)
            energies.append(energy.cpu()); logits.append(pred['mode_logits'].cpu())
    if not energies:
        raise ValueError('Validation requires nonempty indices')
    loss, info = mixture_loss(torch.cat(energies), torch.cat(logits))
    return dict(total=float(loss), energy=float(info['energy']), routingKL=float(info['routingKL']),
                utilization=info['utilization'].tolist(), rows=len(indices))


def _epoch(model, shard, indices, norm, device, optimizer):
    model.train()
    mean, std = (torch.tensor(norm[key], device=device) for key in ('mean', 'std'))
    total = 0.
    for batch in indices[torch.randperm(len(indices))].split(RECIPE['batchSize']):
        pred = model((shard['features'][batch].to(device)-mean)/std)
        energy = pair_energy(pred, shard['continuous'][batch].to(device),
                             shard['categorical'][batch].to(device), model.codec)
        loss, _ = mixture_loss(energy, pred['mode_logits'])
        if not torch.isfinite(loss):
            raise ValueError('Nonfinite pair training loss')
        optimizer.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), RECIPE['clipNorm'], error_if_nonfinite=True)
        optimizer.step()
        total += float(loss.detach())*len(batch)
    return dict(total=total/len(indices), rows=len(indices), reduction='row-weighted-mean-minibatch-training-loss')


def train(output, data=pair_data.ROOT, device=None):
    """Run the fixed recipe; destination must be fresh. Default device is MPS."""
    output, data = Path(output), Path(data).resolve()
    if output.exists():
        raise FileExistsError('Preserve prior pair training run')
    manifest, _, _, shard, codec = read_data(data)
    torch.set_num_threads(RECIPE['threads']); torch.manual_seed(RECIPE['seed']); np.random.seed(RECIPE['seed'])
    device = choose_device(device or 'mps')
    norm = normalization(shard['features'], shard['train'])
    model = PairInverse(codec, RECIPE['modes']).to(device)
    metadata = dict(version=1, trainingRecipe=deepcopy(RECIPE), modelPolicy=deepcopy(MODEL_POLICY),
                    lossPolicy=deepcopy(LOSS_POLICY), codeBindings=code_bindings(),
                    datasetPath=str(data), dataManifestHash=file_hash(data/'manifest.json'), datasetManifest=manifest,
                    specs=codec.specs, normalization=norm, normalizationHash=_hash(norm), modes=RECIPE['modes'],
                    featureHash=FEATURE_HASH, featureCodeHash=FEATURE_CODE_HASH,
                    sourceHash=manifest['inventory']['sourceHash'], inventory=manifest['inventory'],
                    device=str(device), torchVersion=str(torch.__version__), numpyVersion=np.__version__,
                    soundfileVersion=sf.__version__, libsndfileVersion=sf.__libsndfile_version__)
    output.mkdir(parents=True)
    report = dict(complete=False, metadata=metadata, history=[], bestEpoch=None, bestValidation=None)
    _json_write(output/'training.json', report)
    optimizer = torch.optim.AdamW(model.parameters(), lr=RECIPE['learningRate'], weight_decay=RECIPE['weightDecay'])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, RECIPE['epochs'], eta_min=RECIPE['minimumLearningRate'])
    start = time.monotonic()
    for epoch in range(1, RECIPE['epochs']+1):
        rate = optimizer.param_groups[0]['lr']
        training = _epoch(model, shard, shard['train'], norm, device, optimizer)
        values = validation(model, shard, shard['val'], norm, device, RECIPE['batchSize'])
        record = dict(epoch=epoch, training=training, validation=values, learningRate=rate, seconds=time.monotonic()-start)
        report['history'].append(record)
        if report['bestValidation'] is None or values['total'] < report['bestValidation']['total']:
            report.update(bestEpoch=epoch, bestValidation=values)
            torch.save(dict(model={key: value.detach().cpu().clone() for key, value in model.state_dict().items()},
                            metadata=metadata, epoch=epoch, validation=values), output/'best.pt')
        scheduler.step()
        report['checkpointHash'] = file_hash(output/'best.pt')
        _json_write(output/'training.json', report)
        print(json.dumps(record), flush=True)
    checkpoint = torch.load(output/'best.pt', map_location='cpu', weights_only=True)
    restored = PairInverse(codec, RECIPE['modes']).to(device)
    restored.load_state_dict(checkpoint['model'], strict=True)
    replay = validation(restored, shard, shard['val'], norm, device, RECIPE['batchSize'])
    difference = abs(replay['total']-report['bestValidation']['total'])
    if not np.isfinite(difference) or difference > 1e-6:
        raise ValueError('Reloaded best checkpoint failed validation replay')
    if metadata['codeBindings'] != code_bindings() or metadata['dataManifestHash'] != file_hash(data/'manifest.json'):
        raise ValueError('Frozen training inputs changed during run')
    report.update(complete=True, validationReplay=dict(reproduced=True, absoluteDifference=difference, validation=replay))
    _json_write(output/'training.json', report)
    return report


def load(path):
    """Load only complete runs bound to their dataset, current code and DSP."""
    path = Path(path)
    if path.is_dir():
        path = path/'best.pt'
    report = _read(path.parent/'training.json')
    if not report.get('complete') or report.get('checkpointHash') != file_hash(path):
        raise ValueError('Incomplete or altered pair checkpoint binding')
    saved = torch.load(path, map_location='cpu', weights_only=True)
    meta = saved['metadata']
    if (meta != report.get('metadata') or meta.get('trainingRecipe') != RECIPE
            or meta.get('modelPolicy') != MODEL_POLICY or meta.get('lossPolicy') != LOSS_POLICY
            or meta.get('codeBindings') != code_bindings()
            or meta.get('featureHash') != FEATURE_HASH or meta.get('featureCodeHash') != FEATURE_CODE_HASH
            or meta.get('modes') != RECIPE['modes']):
        raise ValueError('Pair model/code/recipe binding differs')
    history = report.get('history', [])
    if [row.get('epoch') for row in history] != list(range(1, RECIPE['epochs']+1)):
        raise ValueError('Pair training history is incomplete')
    best = min(history, key=lambda row: row['validation']['total'])
    if (best['epoch'] != saved.get('epoch') or best['epoch'] != report.get('bestEpoch')
            or best['validation'] != saved.get('validation') or best['validation'] != report.get('bestValidation')):
        raise ValueError('Pair best validation/history binding differs')
    replay = report.get('validationReplay', {})
    if (not replay.get('reproduced') or replay.get('absoluteDifference', float('inf')) > 1e-6
            or abs(replay.get('validation', {}).get('total', float('inf'))-best['validation']['total']) > 1e-6):
        raise ValueError('Pair validation replay binding differs')
    data = Path(meta['datasetPath'])
    if file_hash(data/'manifest.json') != meta.get('dataManifestHash'):
        raise ValueError('Pair dataset manifest binding differs')
    manifest, _, _, shard, codec = read_data(data)
    if (manifest != meta.get('datasetManifest') or codec.specs != meta.get('specs')
            or manifest['inventory'] != meta.get('inventory') or manifest['inventory']['sourceHash'] != meta.get('sourceHash')):
        raise ValueError('Pair dataset/schema/DSP binding differs')
    norm = normalization(shard['features'], shard['train'])
    if norm != meta.get('normalization') or _hash(norm) != meta.get('normalizationHash'):
        raise ValueError('Pair training normalization binding differs')
    for row in history:
        if row['training']['rows'] != len(shard['train']) or row['validation']['rows'] != len(shard['val']):
            raise ValueError('Pair history processed row counts differ')
    model = PairInverse(codec, RECIPE['modes'])
    model.load_state_dict(saved['model'], strict=True)
    if any(not torch.isfinite(value).all() for value in model.parameters()):
        raise ValueError('Pair checkpoint has nonfinite model weights')
    return model.eval(), dict(meta, checkpointHash=file_hash(path), checkpointEpoch=saved['epoch'])


def predict(model, metadata, wave):
    """Four native Mixr parameter dictionaries, ordered by mode probability."""
    if model.codec.specs != metadata['specs'] or model.modes != metadata['modes']:
        raise ValueError('Pair model metadata differs')
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Prediction audio must be finite nonempty mono')
    device = next(model.parameters()).device
    mean, std = (np.asarray(metadata['normalization'][key], dtype=np.float32) for key in ('mean', 'std'))
    features = torch.from_numpy((describe(audition_pcm(wave))-mean)/std)[None].to(device)
    model.eval()
    with torch.no_grad():
        pred = model(features)
    if not torch.isfinite(pred['mode_logits']).all():
        raise ValueError('Nonfinite pair mode predictions')
    proposals = []
    for mode in pred['mode_logits'][0].argsort(descending=True).tolist():
        cat = np.array([int(logits[0, mode].argmax()) for logits in pred['categorical']], dtype=np.int64)
        proposals.append(model.codec.decode(pred['continuous'][0, mode].cpu().numpy(), cat))
    return proposals


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--data', default=str(pair_data.ROOT))
    parser.add_argument('--device', default='mps')
    args = parser.parse_args()
    train(args.output, data=args.data, device=args.device)
