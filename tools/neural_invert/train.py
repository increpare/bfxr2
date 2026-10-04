"""Train shared encoder and separate synth experts on canonical synthetic labels."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from .data import _json_write, verify_dataset_files
from .features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
from .model import MultiSynthModel, supervised_loss
from .schema import ControlSchema


def choose_device(requested=None):
    if requested:
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device('cuda')
    if torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def _load_dataset(path):
    manifest = json.loads((path/'manifest.json').read_text())
    if not manifest.get('complete'):
        raise ValueError('Dataset generation is incomplete')
    expected_features = {'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
                         'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM}
    if any(manifest.get(key) != value for key, value in expected_features.items()):
        raise ValueError('Dataset features or feature code provenance are incompatible')
    verify_dataset_files(path, manifest)
    specs, shards = {}, {}
    sums, squared, count = np.zeros(DIM, dtype=np.float64), np.zeros(DIM, dtype=np.float64), 0
    for name in manifest['engines']:
        meta = json.loads((path/(name+'.json')).read_text())
        if meta.get('sourceHash') != manifest['sourceHash']:
            raise ValueError('Dataset DSP hashes disagree')
        if any(meta.get(key) != manifest[key] for key in expected_features):
            raise ValueError('Dataset shard features or feature code provenance disagree')
        specs[name] = meta['spec']
        with np.load(path/(name+'.npz')) as saved:
            shard = {key: torch.from_numpy(saved[key].astype(np.float32 if key in ('features','continuous') else np.int64)) for key in saved.files}
        shard['train'] = torch.tensor(meta['train'], dtype=torch.long)
        shard['val'] = torch.tensor(meta['val'], dtype=torch.long)
        tr = shard['features'][shard['train']].numpy().astype(np.float64)
        sums += tr.sum(axis=0); squared += (tr*tr).sum(axis=0); count += len(tr)
        shards[name] = shard
    mean = sums/count; std = np.maximum(np.sqrt(np.maximum(0, squared/count-mean*mean)), .025)
    return manifest, specs, shards, mean.astype(np.float32), std.astype(np.float32)


def train_model(data, output, epochs=30, device=None, hidden=256, batch_size=128, seed=20261004, threads=4, learning_rate=.001):
    if epochs < 1:
        raise ValueError('At least one training epoch required')
    torch.set_num_threads(threads); torch.manual_seed(seed); np.random.seed(seed)
    dataset_path, output = Path(data), Path(output); output.mkdir(parents=True, exist_ok=True)
    manifest, specs, shards, mean, std = _load_dataset(dataset_path)
    device = choose_device(device)
    model = MultiSynthModel(specs, DIM, hidden).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=.0001)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, epochs, eta_min=learning_rate*.1)
    metadata = {'version': 1, 'specs': specs, 'engines': manifest['engines'], 'sourceHash': manifest['sourceHash'],
                'featureVersion': VERSION, 'featureHash': FEATURE_HASH, 'featureCodeHash': manifest['featureCodeHash'], 'ignorePeakGain': True, 'featureDim': DIM, 'hidden': hidden,
                'normalization': {'mean': mean.tolist(), 'std': std.tolist()},
                'seed': seed, 'fixedStructureScope': manifest['fixedStructureScope'],
                'fixedControls': {name: {'text': ControlSchema(spec).fixed_text,
                                          'randomness': ControlSchema(spec).fixed_randomness} for name,spec in specs.items()},
                'dataManifestHash': hashlib.sha256((dataset_path/'manifest.json').read_bytes()).hexdigest()}
    mean_t, std_t = torch.from_numpy(mean).to(device), torch.from_numpy(std).to(device)
    history, best, started = [], float('inf'), time.monotonic()
    for epoch in range(epochs):
        model.train(); tasks = []
        for name, shard in shards.items():
            order = shard['train'][torch.randperm(len(shard['train']))]
            tasks.extend((name, ids) for ids in order.split(batch_size))
        # Round-robin randomization gives every synth equal data weight.
        permutation = np.random.permutation(len(tasks)); train_sum, train_count = 0., 0
        for task in permutation:
            name, ids = tasks[task]; shard = shards[name]
            x = (shard['features'][ids].to(device)-mean_t)/std_t
            x[:, -2] = 0
            labels = {key: shard[key][ids].to(device) for key in ('continuous','categorical','generator')}
            optimizer.zero_grad(set_to_none=True)
            loss = supervised_loss(model(x, name, labels['generator']), labels)
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
            optimizer.step(); train_sum += float(loss.detach())*len(ids); train_count += len(ids)
        model.eval(); val_sum, val_count, per_engine = 0., 0, {}
        with torch.no_grad():
            for name, shard in shards.items():
                total, n, squared_error, correct_gen, correct_cat, cat_count = 0., 0, 0., 0, 0, 0
                for ids in shard['val'].split(batch_size):
                    x = (shard['features'][ids].to(device)-mean_t)/std_t
                    x[:, -2] = 0
                    labels = {key: shard[key][ids].to(device) for key in ('continuous','categorical','generator')}
                    # Validate using inferred generator, as during deployment.
                    prediction = model(x, name)
                    loss = supervised_loss(prediction, labels)
                    total += float(loss)*len(ids); n += len(ids)
                    squared_error += float(torch.mean((prediction['continuous']-labels['continuous'])**2))*len(ids)
                    correct_gen += int((prediction['generator'].argmax(1)==labels['generator']).sum())
                    for i, logits in enumerate(prediction['categorical']):
                        correct_cat += int((logits.argmax(1)==labels['categorical'][:,i]).sum()); cat_count += len(ids)
                per_engine[name] = {'loss': total/n, 'unitMSE': squared_error/n, 'generatorAccuracy': correct_gen/n,
                                    'categoricalAccuracy': correct_cat/cat_count if cat_count else None, 'validationRows': n}
                val_sum += total; val_count += n
        val_loss = val_sum/val_count
        row = {'epoch': epoch+1, 'trainLoss': train_sum/train_count, 'validationLoss': val_loss,
               'perEngine': per_engine, 'elapsedSeconds': time.monotonic()-started, 'learningRate': optimizer.param_groups[0]['lr']}
        history.append(row); schedule.step()
        if val_loss < best:
            best = val_loss
            cpu_state = {k: v.detach().cpu().clone() for k,v in model.state_dict().items()}
            torch.save({'model': cpu_state, 'metadata': metadata, 'epoch': epoch+1, 'validationLoss': best}, output/'best.pt')
        report = {'device': str(device), 'threads': threads, 'epochs': epochs, 'batchSize': batch_size,
                  'learningRate': learning_rate, 'parameters': sum(p.numel() for p in model.parameters()),
                  'metadata': metadata, 'history': history, 'bestValidationLoss': best,
                  'limitations': ['Validation excludes exact saved-control duplicates; generator-family holdout is separate.',
                                  'Numeric loss measures control errors; rendered audio reconstruction is assessed separately.',
                                  'TEXT source structures and randomness codes are generator anchors.'],
                  'checkpointHash': hashlib.sha256((output/'best.pt').read_bytes()).hexdigest()}
        _json_write(output/'training.json', report)
        print(json.dumps({'epoch': epoch+1, 'trainLoss': row['trainLoss'], 'validationLoss': val_loss,
                          'seconds': round(row['elapsedSeconds'], 2), 'device': str(device)}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--epochs', type=int, default=30); parser.add_argument('--device')
    parser.add_argument('--hidden', type=int, default=256); parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--threads', type=int, default=4); parser.add_argument('--seed', type=int, default=20261004)
    args = parser.parse_args(); train_model(args.data, args.output, args.epochs, args.device, args.hidden, args.batch_size, args.seed, args.threads)


if __name__ == '__main__':
    main()
