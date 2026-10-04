"""Balanced synthetic supervised data from actual DSP, resumable by engine."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import time
import numpy as np
from multisynth.renderer import Renderer
from .features import describe, DIM, VERSION, CONFIG, FEATURE_HASH, FEATURE_CODE_HASH
from .schema import ControlSchema


def parameter_hash(row):
    # Render randomness is deliberately absent: identical controls are one group.
    content = {'synth': row['synth'], 'params': row['params']}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def split_rows(rows, seed=20261004, fraction=.15):
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(parameter_hash(row), []).append(i)
    keys = list(groups)
    rng = np.random.default_rng(seed); rng.shuffle(keys)
    count = min(len(keys)-1, max(1, int(len(keys)*fraction)))
    if count < 1:
        raise ValueError('Need at least two distinct parameter groups for validation')
    validation = set(keys[:count])
    train = [i for key, ids in groups.items() if key not in validation for i in ids]
    val = [i for key, ids in groups.items() if key in validation for i in ids]
    return sorted(train), sorted(val)


def _json_write(path, value):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); temp.replace(path)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_dataset_files(path, manifest):
    path = Path(path)
    files = manifest.get('files', {})
    for name in manifest['engines']:
        binding = files.get(name, {})
        for extension, key in (('.npz', 'npzSha256'), ('.json', 'metadataSha256')):
            file = path/(name+extension)
            if not binding.get(key) or not file.exists() or file_hash(file) != binding[key]:
                raise ValueError('Dataset shard integrity incompatible: '+name+extension)


def _generate_engine(output, name, per_synth, seed, source_hash):
    # Limit BLAS threads in subprocesses; four workers otherwise oversubscribe.
    try:
        from threadpoolctl import threadpool_limits
        limiter = threadpool_limits(limits=1)
    except ImportError:
        from contextlib import nullcontext
        limiter = nullcontext()
    with limiter, Renderer() as renderer:
        if renderer.inventory['sourceHash'] != source_hash:
            raise ValueError('DSP source changed during data generation')
        spec = renderer.specs[name]
        schema = ControlSchema(spec)
        output = Path(output); npz = output/(name+'.npz'); jsonpath = output/(name+'.json')
        metadata = {'synth': name, 'spec': spec, 'sourceHash': source_hash, 'featureVersion': VERSION,
                    'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM, 'seed': seed, 'perSynth': per_synth,
                    'sampling': {'original': .5, 'sparseGlobal': .3, 'broadGlobal': .2},
                    'fixedText': schema.fixed_text, 'fixedRandomness': schema.fixed_randomness,
                    'featureHashMeaning': 'row featureHash hashes the prequantization float32 descriptor; packedFeatureHash hashes persisted little-endian float16 bytes.'}
        if npz.exists() and jsonpath.exists():
            previous = json.loads(jsonpath.read_text())
            if all(previous.get(k) == metadata[k] for k in ('sourceHash','featureVersion','featureHash','featureCodeHash','featureDim','seed','perSynth')):
                with np.load(npz) as saved:
                    if saved['features'].shape == (per_synth, DIM):
                        return {'synth': name, 'rows': per_synth, 'resumed': True}
            raise ValueError('Existing dataset shard is incompatible: '+str(jsonpath))
        rng = np.random.default_rng(seed)
        features, continuous, categorical, generators, rows = [], [], [], [], []
        failures = []; attempts = 0; started = time.monotonic()
        while len(rows) < per_synth:
            if attempts > per_synth*4:
                raise RuntimeError('Too many invalid draws for '+name)
            i = len(rows); attempts += 1
            generator_index = i % len(spec['presets'])
            generator = spec['presets'][generator_index]
            sample_seed = int(rng.integers(0, 2**32)); render_seed = int(rng.integers(0, 2**32))
            r = rng.random(); mode = 'original' if r < .5 else 'sparse' if r < .8 else 'broad'
            try:
                params = renderer.sample(name, generator, sample_seed)
                params = schema.mutate(params, rng, mode)
                canonical, wave = renderer.render(name, params, render_seed)
                # Silent controls have no inverse; keep silence descriptors supported
                # for inference, but do not give these ambiguous examples labels.
                if float(np.max(np.abs(wave))) < 1e-7:
                    raise ValueError('Silent draw')
                feat = describe(wave)
                unit, cat = schema.encode(canonical)
            except (ValueError, RuntimeError) as error:
                failures.append({'attempt': attempts, 'generator': generator, 'sampleSeed': sample_seed,
                                 'renderSeed': render_seed, 'error': str(error)})
                continue
            features.append(feat); continuous.append(unit); categorical.append(cat); generators.append(generator_index)
            row = {'synth': name, 'generator': generator, 'generatorIndex': generator_index,
                   'sampleSeed': sample_seed, 'seed': render_seed, 'mode': mode, 'params': canonical,
                   'audioSamples': len(wave), 'audioHash': hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest(),
                   'featureHash': hashlib.sha256(feat.astype('<f4').tobytes()).hexdigest(),
                   'packedFeatureHash': hashlib.sha256(feat.astype('<f2').tobytes()).hexdigest()}
            row['parameterHash'] = parameter_hash(row); rows.append(row)
            if len(rows)%256 == 0:
                print(json.dumps({'synth': name, 'rows': len(rows), 'seconds': round(time.monotonic()-started, 1)}), flush=True)
        train, val = split_rows(rows, seed=seed)
        metadata.update(rows=rows, train=train, val=val, failures=failures, attempts=attempts,
                        elapsedSeconds=time.monotonic()-started)
        temp = npz.with_suffix('.tmp.npz')
        np.savez_compressed(temp, features=np.asarray(features, dtype=np.float16),
                            continuous=np.asarray(continuous, dtype=np.float32),
                            categorical=np.asarray(categorical, dtype=np.int16),
                            generator=np.asarray(generators, dtype=np.int16))
        temp.replace(npz); _json_write(jsonpath, metadata)
        return {'synth': name, 'rows': len(rows), 'failures': len(failures), 'seconds': metadata['elapsedSeconds']}


def generate_dataset(output, per_synth=2048, jobs=4, seed=20261004, synths=None):
    if per_synth < 4 or jobs < 1:
        raise ValueError('At least four examples and one job required')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with Renderer() as renderer:
        inventory = renderer.inventory
        available = [s['name'] for s in inventory['synths'] if s.get('collectionCompatible')]
        engines = available if synths is None else list(synths)
        if not engines or any(name not in available for name in engines):
            raise ValueError('Requested engine is not active and collection compatible')
    config = {'version': 1, 'sourceHash': inventory['sourceHash'], 'featureVersion': VERSION,
              'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM, 'featureConfig': CONFIG,
              'perSynth': per_synth, 'seed': seed, 'engines': engines,
              'fixedStructureScope': 'TEXT phrase comes from the predicted generator; random seed controls are held at generator anchors.'}
    manifest = output/'manifest.json'
    if manifest.exists():
        old = json.loads(manifest.read_text())
        if any(old.get(k) != config[k] for k in ('sourceHash','featureVersion','featureHash','featureCodeHash','featureDim','seed','engines','perSynth')):
            raise ValueError('Dataset manifest is incompatible with requested configuration')
        if old.get('complete'):
            verify_dataset_files(output, old)
    config['complete'] = False; _json_write(manifest, config)
    tasks = [(str(output), name, per_synth, seed+i*104729, inventory['sourceHash']) for i,name in enumerate(engines)]
    if jobs == 1:
        results = [_generate_engine(*task) for task in tasks]
    else:
        results = []
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(_generate_engine, *task) for task in tasks]
            for future in as_completed(futures):
                result = future.result(); results.append(result); print(json.dumps(result), flush=True)
    config['shards'] = results
    config['splits'] = {name: {key: json.loads((output/(name+'.json')).read_text())[key] for key in ('train','val')} for name in engines}
    config['files'] = {name: {'npzSha256': file_hash(output/(name+'.npz')),
                              'metadataSha256': file_hash(output/(name+'.json'))} for name in engines}
    config['complete'] = True; _json_write(manifest, config)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True); parser.add_argument('--per-synth', type=int, default=2048)
    parser.add_argument('--jobs', type=int, default=4); parser.add_argument('--seed', type=int, default=20261004)
    parser.add_argument('--synths', nargs='+')
    args = parser.parse_args(); generate_dataset(args.output, args.per_synth, args.jobs, args.seed, args.synths)


if __name__ == '__main__':
    main()
