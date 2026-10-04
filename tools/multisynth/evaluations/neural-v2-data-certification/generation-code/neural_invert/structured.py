"""Append physical pitch/envelope draws while retaining every native example.

All audio comes from the application DSP. Gesture pitches are nominal control
values, not measured pitch labels or evidence of perceptual likeness.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
from match.optimizer import freq_param_from_hz
from multisynth.renderer import Renderer
from .data import _json_write, file_hash, parameter_hash, split_rows, verify_dataset_files
from .features import CONFIG, DIM, FEATURE_CODE_HASH, FEATURE_HASH, VERSION, describe
from .schema import ControlSchema

AUGMENTATION_VERSION = 'physical-gestures-v2'
GENERATION_CODE_FILES = ('neural_invert/structured.py', 'neural_invert/schema.py',
                         'neural_invert/data.py', 'match/optimizer.py',
                         'match/audio.py', 'multisynth/renderer.py', 'render/multisynth_worker.js')
TARGETS = ('Bfxr', 'Transfxr', 'Pluckr')
AUGMENTATION_CONFIG = {
    'targets': list(TARGETS), 'pitchSampling': 'log-uniform',
    'pitchBoundsHz': {'Bfxr': [80, 1600], 'Transfxr': [80, 1600], 'Pluckr': [80, 880]},
    'gestureCycle': ['stationary']*4+['rise', 'fall', 'jump', 'vibrato'],
    'pluckrGestureCycle': ['stationary']*7+['vibrato'],
    'stationarySineEvery': 4, 'validationFraction': .15,
    'generatorLabelPolicy': 'origin auxiliary only; structured draws are not generator ancestry; randomize_params label when present, otherwise index 0',
    'pitchMeaning': 'Nominal DSP control pitch; endpoint is approximate for Bfxr slides and not a measured audio label.',
    'preserveNativeRows': True,
    'codeBinding': {'version': 'relative-file-sha256-v1', 'files': list(GENERATION_CODE_FILES)},
}
ARRAY_DTYPES = {'features': np.float16, 'continuous': np.float32,
                'categorical': np.int16, 'generator': np.int16}


def generation_code_binding():
    """Bind codec, grouped splitting, pitch mapping and renderer bridge bytes.

    Relative names keep the digest independent of checkout location and cwd.
    Feature extraction and actual DSP have their separate existing bindings.
    DSP sourceHash includes multisynth_context.js and its loaded synth sources;
    the worker's request dispatch and float32 serialization are bound here.
    """
    root = Path(__file__).resolve().parents[1]
    files = {}
    for relative in GENERATION_CODE_FILES:
        path = root/relative
        try:
            files[relative] = file_hash(path)
        except OSError as error:
            raise ValueError('Augmentation code dependency missing or unreadable: '+relative) from error
    encoded = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return {'files': files, 'sha256': hashlib.sha256(encoded).hexdigest()}


def _transition(start, end=None, curve='Linear'):
    return {'start': float(start), 'end': float(start if end is None else end), 'curve': curve}


def structured_params(spec, rng, index):
    """Draw canonicalizable real controls from defaults and supported DSP maps."""
    name = spec['name']
    if name not in TARGETS:
        raise ValueError('Unsupported structured synth: '+name)
    params = deepcopy(spec['defaults'])
    lo, hi = AUGMENTATION_CONFIG['pitchBoundsHz'][name]
    hz = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
    kind = AUGMENTATION_CONFIG['gestureCycle'][index % 8]
    if name == 'Pluckr' and kind != 'vibrato':
        kind = 'stationary'
    duration = float(np.exp(rng.uniform(np.log(.22), np.log(1.8))))
    end_hz = hz
    if kind in ('rise', 'fall', 'jump'):
        ratio = float(2**rng.uniform(.2, 1.25))
        if kind == 'fall' or (kind == 'jump' and rng.random() < .5):
            ratio = 1/ratio
        end_hz = float(np.clip(hz*ratio, lo, hi))
    params['masterVolume'] = .5
    if name == 'Bfxr':
        # Bfxr uses squared envelope controls and an eight-times supersampled
        # oscillator. Reuse the optimizer's empirically checked pitch map.
        attack = float(duration*rng.uniform(.005, .2))
        decay = float(duration*rng.uniform(.12, .65))
        sustain = max(.03, duration-attack-decay)
        params.update(waveType=2 if index % 4 == 0 else int(rng.choice([2, 0, 1, 4, 8, 6, 7, 11])),
                      frequency_start=freq_param_from_hz(hz),
                      attackTime=float(np.sqrt(attack*44100/100000)),
                      sustainTime=float(np.sqrt(sustain*44100/100000)),
                      decayTime=float(np.sqrt(decay*44100/100000)),
                      squareDuty=float(rng.uniform(0, .7)), sustainPunch=float(rng.uniform(0, .3)))
        if kind in ('rise', 'fall'):
            # period *= slide once per output sample; slide = 1-control^3*.01.
            slide = (hz/end_hz)**(1/max(1, duration*44100))
            params['frequency_slide'] = float(np.cbrt((1-slide)/.01))
        elif kind == 'jump':
            ratio = end_hz/hz
            params['pitch_jump_amount'] = (float(np.sqrt((1-1/ratio)/.9)) if ratio >= 1
                                           else -float(np.sqrt((1/ratio-1)/10)))
            params['pitch_jump_onset_percent'] = float(rng.uniform(.25, .7))
        elif kind == 'vibrato':
            params['vibratoDepth'] = float(rng.uniform(.015, .12))
            # phase increments speed^2*.01 per output sample.
            params['vibratoSpeed'] = float(np.sqrt(rng.uniform(3, 9)*2*np.pi/(44100*.01)))
    elif name == 'Transfxr':
        pitch = float(np.log2(hz/40)/7)
        curve = 'Steps' if kind == 'jump' else str(rng.choice(['Linear', 'Ease In', 'Ease Out', 'Smooth']))
        # A fixed waveform sine subset covers the whole pitch/envelope range.
        params.update(waveType=0 if index % 4 == 0 else int(rng.choice([0, 1, 2, 3, 4, 5, 6, 8, 11])),
                      waveTo=-1, duration=duration, echo=0., resonance=float(rng.uniform(0, .3)),
                      attack=float(duration*rng.uniform(.005, .22)),
                      release=float(duration*rng.uniform(.08, .5)),
                      pitch=_transition(pitch, np.log2(end_hz/40)/7, curve),
                      vibrato=_transition(rng.uniform(.02, .25) if kind == 'vibrato' else 0),
                      tone=_transition(1. if index % 4 == 0 else rng.uniform(.5, 1)),
                      level=_transition(rng.uniform(.4, .95)))
    else:
        # Root pitch is bounded at 880 Hz by Pluckr's actual 55*2^(pitch*4).
        # It has no ramp/jump control; only its varying delay supports vibrato.
        params.update(pitch=float(np.log2(hz/55)/4), duration=duration,
                      material=int(rng.choice([p for p in spec['params'] if p['name'] == 'material'][0]['values'])),
                      strings=1 if index % 4 == 0 else int(rng.integers(1, 5)),
                      damping=float(rng.uniform(.02, .8)), brightness=float(rng.uniform(.2, .95)),
                      pluck=float(rng.uniform(.08, .85)), coupling=float(rng.uniform(0, .4)),
                      strum=float(rng.uniform(0, .3)), inharmonic=0.,
                      vibrato=float(rng.uniform(.1, .8)) if kind == 'vibrato' else 0.,
                      tremoloRate=float(rng.uniform(2, 9)), tremolo=0.)
    gesture = {'kind': kind, 'nominalStartHz': hz, 'nominalEndHz': end_hz,
               'nominalDurationSeconds': duration, 'pitchMeaning': 'nominal DSP control, not measured pitch'}
    return params, gesture


def _composition(rows, train, val, base_count):
    return {key: {'base': sum(i < base_count for i in ids),
                  'structured': sum(i >= base_count for i in ids),
                  'gestures': dict(Counter(rows[i]['structuredGesture']['kind'] for i in ids if i >= base_count))}
            for key, ids in (('train', train), ('val', val))}


def _build_shard(base, output, name, per_synth, seed, source_hash, config_hash):
    started = time.monotonic()
    base, output = Path(base), Path(output)
    meta = json.loads((base/(name+'.json')).read_text())
    rows = meta['rows']
    base_count = len(rows)
    with np.load(base/(name+'.npz')) as saved:
        arrays = {key: saved[key].copy() for key in ARRAY_DTYPES}
    for key, dtype in ARRAY_DTYPES.items():
        if arrays[key].dtype != np.dtype(dtype) or len(arrays[key]) != base_count:
            raise ValueError('Base dataset arrays incompatible: '+name+'/'+key)
    added = {key: [] for key in ARRAY_DTYPES}
    failures = []
    if name in TARGETS:
        try:
            from threadpoolctl import threadpool_limits
            limiter = threadpool_limits(limits=1)
        except ImportError:
            from contextlib import nullcontext
            limiter = nullcontext()
        with limiter, Renderer() as renderer:
            if renderer.inventory['sourceHash'] != source_hash or renderer.specs[name] != meta['spec']:
                raise ValueError('DSP source or spec changed during structured generation')
            spec = renderer.specs[name]
            schema = ControlSchema(spec)
            generator_index = spec['presets'].index('randomize_params') if 'randomize_params' in spec['presets'] else 0
            rng = np.random.default_rng(seed)
            attempts = 0
            while len(rows) < base_count+per_synth:
                index = len(rows)-base_count
                attempts += 1
                if attempts > per_synth*4:
                    raise RuntimeError('Too many invalid structured draws: '+name)
                sample_seed = int(rng.integers(0, 2**32))
                render_seed = int(rng.integers(0, 2**32))
                params, gesture = structured_params(spec, np.random.default_rng(sample_seed), index)
                try:
                    canonical, wave = renderer.render(name, params, render_seed)
                    if not np.isfinite(wave).all() or not len(wave) or np.max(np.abs(wave)) < 1e-7:
                        raise ValueError('Silent or nonfinite structured draw')
                    feat = describe(wave)
                    unit, cat = schema.encode(canonical)
                except (ValueError, RuntimeError) as error:
                    failures.append({'index': index, 'sampleSeed': sample_seed, 'seed': render_seed, 'error': str(error)})
                    continue
                row = {'synth': name, 'generator': spec['presets'][generator_index], 'generatorIndex': generator_index,
                       'sampleSeed': sample_seed, 'seed': render_seed, 'mode': 'structured', 'origin': 'structured',
                       'structured': True, 'structuredIndex': index, 'structuredGesture': gesture,
                       'sourceHash': source_hash, 'params': canonical, 'audioSamples': len(wave),
                       'audioHash': hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest(),
                       'featureHash': hashlib.sha256(feat.astype('<f4').tobytes()).hexdigest(),
                       'packedFeatureHash': hashlib.sha256(feat.astype('<f2').tobytes()).hexdigest()}
                row['parameterHash'] = parameter_hash(row)
                rows.append(row)
                for key, value in [('features', feat), ('continuous', unit), ('categorical', cat), ('generator', generator_index)]:
                    added[key].append(value)
                if len(added['features']) % 256 == 0:
                    print(json.dumps({'synth': name, 'structuredRows': len(added['features']),
                                      'seconds': round(time.monotonic()-started, 1)}), flush=True)
        for key, dtype in ARRAY_DTYPES.items():
            arrays[key] = np.concatenate([arrays[key], np.asarray(added[key], dtype=dtype)], axis=0)
    train, val = split_rows(rows, seed=seed, fraction=AUGMENTATION_CONFIG['validationFraction'])
    meta.update(rows=rows, train=train, val=val, perSynth=len(rows), baseRows=base_count,
                structuredRows=len(rows)-base_count, structuredIndices=list(range(base_count, len(rows))),
                augmentationVersion=AUGMENTATION_VERSION, augmentationConfigHash=config_hash,
                augmentationSeed=seed, structuredFailures=failures,
                generatorLabelPolicy=AUGMENTATION_CONFIG['generatorLabelPolicy'],
                splitComposition=_composition(rows, train, val, base_count))
    npz = output/(name+'.npz')
    if name in TARGETS:
        temp = npz.with_suffix('.tmp.npz')
        np.savez_compressed(temp, **arrays); temp.replace(npz)
    else:
        shutil.copyfile(base/(name+'.npz'), npz)
    _json_write(output/(name+'.json'), meta)
    return {'synth': name, 'rows': len(rows), 'baseRows': base_count, 'structuredRows': len(rows)-base_count,
            'failures': len(failures), 'splitComposition': meta['splitComposition'],
            'npzSha256': file_hash(npz), 'metadataSha256': file_hash(output/(name+'.json'))}


def augment_dataset(base, output, per_synth=2048, seed=20261005, jobs=3):
    """Preserve frozen base rows/arrays, append structured audio, split by controls."""
    if per_synth < 4 or jobs < 1:
        raise ValueError('At least four structured examples and one job required')
    base, output = Path(base).resolve(), Path(output).resolve()
    if base == output or base in output.parents or output in base.parents:
        raise ValueError('Base and output must be separate dataset directories')
    manifest_path = base/'manifest.json'
    base_manifest_hash = file_hash(manifest_path)
    base_manifest = json.loads(manifest_path.read_text())
    expected = {'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
                'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM}
    if not base_manifest.get('complete') or any(base_manifest.get(k) != v for k, v in expected.items()):
        raise ValueError('Base dataset features or completeness incompatible')
    verify_dataset_files(base, base_manifest)
    engines = base_manifest['engines']
    if any(n not in engines for n in TARGETS):
        raise ValueError('Base dataset must include all structured target engines')
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != base_manifest['sourceHash']:
            raise ValueError('Base dataset DSP source incompatible')
    for name in engines:
        meta = json.loads((base/(name+'.json')).read_text())
        if meta.get('sourceHash') != base_manifest['sourceHash'] or any(meta.get(k) != v for k, v in expected.items()):
            raise ValueError('Base dataset shard provenance incompatible: '+name)
    code_binding = generation_code_binding()
    config = {'version': 2, 'sourceHash': base_manifest['sourceHash'], **expected, 'featureConfig': CONFIG,
              'baseManifestHash': base_manifest_hash, 'baseFiles': base_manifest['files'],
              'engines': engines, 'perSynth': per_synth, 'seed': seed,
              'augmentationVersion': AUGMENTATION_VERSION, 'augmentationConfig': AUGMENTATION_CONFIG,
              'augmentationCodeHash': code_binding['sha256'],
              'augmentationCodeFiles': code_binding['files'],
              'fixedStructureScope': base_manifest['fixedStructureScope']}
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    config['augmentationConfigHash'] = config_hash
    output.mkdir(parents=True, exist_ok=True)
    path = output/'manifest.json'
    completed = {}
    if path.exists():
        old = json.loads(path.read_text())
        if any(old.get(k) != v for k, v in config.items()):
            raise ValueError('Structured dataset manifest incompatible with requested configuration')
        if old.get('complete'):
            verify_dataset_files(output, old)
            return old
        completed = {s['synth']: s for s in old.get('shards', [])}
        if completed:
            verify_dataset_files(output, {**old, 'engines': list(completed)})
    elif any(output.iterdir()):
        raise ValueError('Structured output contains unbound files; use a fresh output directory')
    config.update(complete=False, shards=list(completed.values()),
                  files={name: {k: s[k] for k in ('npzSha256', 'metadataSha256')} for name, s in completed.items()})
    _json_write(path, config)
    tasks = []
    for i, name in enumerate(engines):
        if name in completed:
            continue
        if (output/(name+'.npz')).exists() or (output/(name+'.json')).exists():
            raise ValueError('Structured dataset shard integrity unbound: '+name)
        tasks.append((str(base), str(output), name, per_synth, seed+i*104729,
                      config['sourceHash'], config_hash))

    def record(result):
        name = result['synth']; completed[name] = result
        config['shards'] = [completed[n] for n in engines if n in completed]
        config['files'][name] = {k: result[k] for k in ('npzSha256', 'metadataSha256')}
        _json_write(path, config)
        print(json.dumps({k: result[k] for k in ('synth', 'rows', 'structuredRows')}), flush=True)

    if jobs == 1:
        for task in tasks:
            record(_build_shard(*task))
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(_build_shard, *task) for task in tasks]
            for future in as_completed(futures):
                record(future.result())
    # Check code and base integrity again before declaring the derivative complete.
    if generation_code_binding() != code_binding:
        raise ValueError('Augmentation code dependencies changed during generation')
    if file_hash(manifest_path) != base_manifest_hash:
        raise ValueError('Base manifest changed during augmentation')
    verify_dataset_files(base, base_manifest)
    verify_dataset_files(output, config)
    config.update(complete=True,
                  splits={n: {k: json.loads((output/(n+'.json')).read_text())[k] for k in ('train', 'val')} for n in engines},
                  composition={n: completed[n]['splitComposition'] for n in engines},
                  baseRows=sum(s['baseRows'] for s in completed.values()),
                  structuredRows=sum(s['structuredRows'] for s in completed.values()),
                  totalRows=sum(s['rows'] for s in completed.values()))
    _json_write(path, config)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--per-synth', type=int, default=2048)
    parser.add_argument('--seed', type=int, default=20261005)
    parser.add_argument('--jobs', type=int, default=3)
    args = parser.parse_args()
    augment_dataset(args.base, args.output, args.per_synth, args.seed, args.jobs)


if __name__ == '__main__':
    main()
