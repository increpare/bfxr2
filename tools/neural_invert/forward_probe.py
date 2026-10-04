"""Bounded surrogate gradients, checked against frozen actual-DSP benchmark PCM.

Actual rendering supplies measurements only after surrogate optimization. The
gate is an architectural prerequisite and cannot establish perceptual likeness.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import RATE, audio_hash, pitch_diagnostic, compare_pitch
from .data import _json_write, file_hash, verify_dataset_files
from .features import describe, DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
from .forward import ENGINES, LOSS_POLICY, feature_loss, load_forward, _hash_json
from .schema import ControlSchema


ACTUAL_GATE_POLICY = {'cases': 20, 'minimumStrictImprovements': 15,
    'meanActualLossMustDecrease': True, 'maximumReliablePitchLosses': 0,
    'meaning': 'actual-DSP descriptor gradient prerequisite; no perceptual likeness claim'}


def _settings(steps, learning_rate):
    if type(steps) is not int or steps < 1:
        raise ValueError('steps must be a positive integer')
    if type(learning_rate) not in (float, int) or not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError('learning_rate must be positive and finite')


def _normalization(metadata, device):
    result = []
    for key in ('mean', 'std'):
        vector = np.asarray(metadata['normalization'][key], dtype=np.float32)
        if vector.shape != (DIM,) or not np.isfinite(vector).all() or (key == 'std' and np.any(vector < .025-1e-8)):
            raise ValueError('Forward normalization is invalid')
        result.append(torch.tensor(vector, device=device))
    return result


def _fixed_controls(schema, before, after):
    _, before_cat = schema.encode(before)
    _, after_cat = schema.encode(after)
    if not np.array_equal(before_cat, after_cat):
        raise ValueError('Refinement changed categorical controls')
    names = schema.fixed_text + schema.fixed_randomness + ['masterVolume']
    if any(before.get(name, schema.spec['defaults'].get(name)) != after.get(name, schema.spec['defaults'].get(name)) for name in names):
        raise ValueError('Refinement changed fixed controls or random anchors')


def refine_controls(model, metadata, params, target_features, steps=100, learning_rate=.01):
    """Freeze weights; optimize unit continuous controls against raw descriptors.

    Best state includes step zero. If it wins, preserve the exact original
    controls instead of losing precision in an encode/decode roundtrip.
    """
    _settings(steps, learning_rate)
    if model.spec != metadata['spec']:
        raise ValueError('Forward model schema differs from metadata')
    schema = ControlSchema(metadata['spec'])
    merged = deepcopy(schema.spec['defaults']); merged.update(deepcopy(params))
    for control in schema.continuous:
        value = schema._read(merged, control['path'])
        if not isinstance(value, (int, float)) or not np.isfinite(value) or not control['min'] <= value <= control['max']:
            raise ValueError('Continuous control outside schema bounds')
    encoded, categories = schema.encode(params)
    device = next(model.parameters()).device
    mean, std = _normalization(metadata, device)
    target = torch.as_tensor(np.asarray(target_features, dtype=np.float32), device=device)
    if target.shape != (DIM,) or not torch.isfinite(target).all():
        raise ValueError('Target descriptor must be finite with the full feature dimension')
    target = ((target-mean)/std).unsqueeze(0)
    model.eval()
    for weight in model.parameters():
        weight.requires_grad_(False); weight.grad = None
    unit = torch.tensor(encoded[None], device=device, requires_grad=True)
    categorical = torch.tensor(categories[None], dtype=torch.long, device=device)
    optimizer = torch.optim.Adam([unit], lr=learning_rate)
    loss, _ = feature_loss(model(unit, categorical), target)
    trace = [float(loss.detach())]
    best_loss, best_step, best_unit = trace[0], 0, unit.detach().clone()
    maximum_gradient = 0.
    for step in range(1, steps+1):
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if unit.grad is None or not torch.isfinite(unit.grad).all():
            raise ValueError('Surrogate continuous gradient is invalid')
        maximum_gradient = max(maximum_gradient, float(unit.grad.norm()))
        optimizer.step()
        with torch.no_grad():
            unit.clamp_(0, 1)
        loss, _ = feature_loss(model(unit, categorical), target)
        value = float(loss.detach()); trace.append(value)
        if value < best_loss:
            best_loss, best_step, best_unit = value, step, unit.detach().clone()
    result_params = deepcopy(params)
    if best_step:
        # Write only optimized paths; preserve every other original field.
        for control, value in zip(schema.continuous, best_unit[0].cpu().numpy()):
            schema._write(result_params, control['path'], float(control['min'] + float(value)*(control['max']-control['min'])))
    _fixed_controls(schema, params, result_params)
    return {'params': result_params, 'initialLoss': trace[0], 'finalLoss': trace[-1],
        'bestLoss': best_loss, 'bestStep': best_step, 'trace': trace,
        'maximumGradientNorm': maximum_gradient, 'steps': steps, 'learningRate': learning_rate,
        'optimizer': 'Adam', 'optimizedControls': [c['name'] for c in schema.continuous],
        'fixedCategorical': categories.tolist(), 'scope': 'surrogate-only; no actual-DSP feedback'}


def _read_pcm(row):
    path = Path(row['waveFile'])
    if file_hash(path) != row.get('waveFileSha256'):
        raise ValueError('Frozen WAV file hash changed: '+str(path))
    wave, rate = sf.read(path, dtype='float32')
    if rate != RATE or wave.ndim != 1 or not wave.size or not np.isfinite(wave).all() or sf.info(path).subtype != 'FLOAT':
        raise ValueError('Frozen WAV must preserve mono FLOAT PCM at the DSP sample rate')
    if audio_hash(wave) != row.get('audioHash') or len(wave) != row.get('audioSamples'):
        raise ValueError('Frozen WAV audio hash or sample count changed')
    return wave


def _replay(renderer, synth, params, seed, wave):
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Render seed must be an integer in [0, 2**32)')
    canonical, rendered = renderer.render(synth, params, seed)
    if canonical != params or not np.array_equal(rendered, wave):
        raise ValueError('Actual-DSP control replay differs from frozen PCM')
    return {'exact': True, 'canonicalParamsEqual': True, 'audioHash': audio_hash(rendered),
        'seed': seed, 'backend': 'actual-multisynth'}


def _prepare_case(row, metadata, renderer):
    source = renderer.inventory['sourceHash']; synth = row['sourceSynth']
    if row.get('sourceHash') != source or metadata.get('sourceHash') != source or metadata['spec'] != renderer.specs[synth] or metadata.get('engine') != synth:
        raise ValueError('Probe DSP source or model schema changed')
    target = _read_pcm(row)
    target_replay = _replay(renderer, synth, row['sourceParams'], row['sourceSeed'], target)
    if row.get('sourceReplay') != target_replay:
        raise ValueError('Frozen target sourceReplay binding is incompatible')
    before = row['arms']['acoustic']['candidates'].get('knownRaw')
    if not before or before.get('synth') != synth or before.get('sourceHash') != source:
        raise ValueError('Frozen knownRaw source-engine controls are absent or incompatible')
    before_wave = _read_pcm(before)
    before_replay = _replay(renderer, synth, before['params'], before['seed'], before_wave)
    return {'targetWave': target, 'beforeWave': before_wave,
        'targetReplay': target_replay, 'beforeReplay': before_replay, 'before': before}


def _loss(prediction, target, metadata):
    mean, std = _normalization(metadata, 'cpu')
    total, groups = feature_loss((torch.from_numpy(prediction)-mean)/std, (torch.from_numpy(target)-mean)/std)
    return {'total': float(total), 'groups': {name: float(value) for name, value in groups.items()}}


def _gesture(features):
    """Retain whole-sound descriptor evidence without a new distance model."""
    pitch = features[3888:3936]; voice = features[3936:3984]
    return {'relativeEnvelope': features[3840:3888].tolist(),
        'absoluteEnvelope': features[3984:4016].tolist(),
        'relativePitchHz': [float(55*2**(7*p)) if v > .3 else None for p, v in zip(pitch, voice)],
        'relativeVoicing': voice.tolist(), 'durationSeconds': float(2**features[4080]-.001),
        'normalizedRms': float(features[4082]),
        'meaning': 'existing full-sound descriptor contours; absolute envelope spans six seconds'}


def _save_audio(dest, name, wave, params, seed, synth, renderer, target_features, target_pitch, family, metadata, objective, replay=None):
    if wave.dtype != np.float32:
        raise ValueError('Scored DSP PCM must be float32')
    path = dest/(name+'.wav'); sf.write(path, wave, RATE, subtype='FLOAT')
    decoded, rate = sf.read(path, dtype='float32')
    if rate != RATE or not np.array_equal(decoded, wave):
        raise ValueError('Probe FLOAT WAV roundtrip changed scored PCM')
    features = describe(wave); pitch = pitch_diagnostic(wave)
    score = float(objective.score_batch([wave])[0])
    return {'synth': synth, 'params': deepcopy(params), 'seed': seed,
        'sourceHash': renderer.inventory['sourceHash'], 'waveFile': str(path.resolve()),
        'waveFileSha256': file_hash(path), 'audioHash': audio_hash(wave), 'audioSamples': len(wave),
        'sourceReplay': replay or _replay(renderer, synth, params, seed, wave),
        'descriptorHash': audio_hash(features), 'featureLoss': _loss(features, target_features, metadata),
        'matchObjective': score, 'pitch': pitch, 'pitchComparison': compare_pitch(target_pitch, pitch, family),
        'gesture': _gesture(features)}


def probe_case(row, model, metadata, renderer, output, steps=100, learning_rate=.01, *, prepared=None):
    """One-case actual-render check; run_probe enforces the full predictive gate."""
    _settings(steps, learning_rate)
    output = Path(output)
    if output.exists():
        raise FileExistsError('Probe case output must be fresh: '+str(output))
    prepared = prepared or _prepare_case(row, metadata, renderer)
    target_wave, before_wave, before = prepared['targetWave'], prepared['beforeWave'], prepared['before']
    target_features = describe(target_wave); target_pitch = pitch_diagnostic(target_wave)
    refinement = refine_controls(model, metadata, before['params'], target_features, steps, learning_rate)
    canonical, after_wave = renderer.render(row['sourceSynth'], refinement['params'], before['seed'])
    _fixed_controls(ControlSchema(metadata['spec']), before['params'], canonical)
    unit, categories = ControlSchema(metadata['spec']).encode(canonical)
    device = next(model.parameters()).device
    mean, std = _normalization(metadata, device)
    with torch.no_grad():
        canonical_loss, canonical_groups = feature_loss(
            model(torch.tensor(unit[None], device=device), torch.tensor(categories[None], device=device)),
            ((torch.tensor(target_features, device=device)-mean)/std).unsqueeze(0))
    refinement['canonicalLoss'] = float(canonical_loss)
    refinement['canonicalGroups'] = {name: float(value) for name, value in canonical_groups.items()}
    # Canonical controls, rather than pre-render proposals, own the saved PCM.
    after_replay = _replay(renderer, row['sourceSynth'], canonical, before['seed'], after_wave)
    output.mkdir(parents=True, exist_ok=False)
    context = (row['sourceSynth'], renderer, target_features, target_pitch, row['family'], metadata, MatchObjective(target_wave))
    target = _save_audio(output, 'target', target_wave, row['sourceParams'], row['sourceSeed'], *context, replay=prepared['targetReplay'])
    saved_before = _save_audio(output, 'before', before_wave, before['params'], before['seed'], *context, replay=prepared['beforeReplay'])
    after = _save_audio(output, 'after', after_wave, canonical, before['seed'], *context, replay=after_replay)
    result = {'id': row['id'], 'family': row['family'], 'sourceSynth': row['sourceSynth'],
        'gestureKind': row.get('gesture'), 'target': target, 'before': saved_before, 'after': after,
        'surrogate': refinement, 'checkpointHash': metadata['checkpointHash'],
        'normalizationHash': metadata['normalizationHash'],
        'frozenTargetWaveFileSha256': row['waveFileSha256'],
        'frozenBeforeWaveFileSha256': before['waveFileSha256'],
        'actualImproved': after['featureLoss']['total'] < saved_before['featureLoss']['total'],
        'lostReliablePitch': bool(target_pitch['reliable'] and saved_before['pitch']['reliable'] and not after['pitch']['reliable'])}
    _json_write(output/'report.json', result)
    return result


def _summary(rows):
    before = [r['before']['featureLoss']['total'] for r in rows]
    after = [r['after']['featureLoss']['total'] for r in rows]
    initial = [r['surrogate']['initialLoss'] for r in rows]
    best = [r['surrogate']['bestLoss'] for r in rows]
    improved = sum(b < a for a, b in zip(before, after))
    lost = sum(r['target']['pitch']['reliable'] and r['before']['pitch']['reliable'] and not r['after']['pitch']['reliable'] for r in rows)
    return {'cases': len(rows), 'actualImproved': improved, 'lostReliablePitch': lost,
        'meanActualBefore': float(np.mean(before)), 'meanActualAfter': float(np.mean(after)),
        'meanSurrogateInitial': float(np.mean(initial)), 'meanSurrogateBest': float(np.mean(best)),
        'surrogateImproved': sum(b < a for a, b in zip(initial, best))}


def summarize(rows):
    if not rows:
        raise ValueError('No actual-DSP probe cases')
    result = _summary(rows)
    gate = {'policy': deepcopy(ACTUAL_GATE_POLICY), 'improved': result['actualImproved'],
        'casesPassed': len(rows) == 20, 'countPassed': result['actualImproved'] >= 15,
        'meanPassed': result['meanActualAfter'] < result['meanActualBefore'],
        'pitchPassed': result['lostReliablePitch'] == 0}
    gate['passed'] = all(gate[name] for name in ('casesPassed', 'countPassed', 'meanPassed', 'pitchPassed'))
    result['actualGate'] = gate
    result['byFamily'] = {name: _summary([r for r in rows if r['family'] == name]) for name in sorted({r['family'] for r in rows})}
    result['byEngine'] = {name: _summary([r for r in rows if r['sourceSynth'] == name]) for name in sorted({r['sourceSynth'] for r in rows})}
    return result


def _bind_file(path, expected, bindings, meaning):
    path = Path(path)
    if not expected or file_hash(path) != expected:
        raise ValueError(meaning+' hash changed: '+str(path))
    bindings[str(path.resolve())] = expected


def _benchmark_inputs(path, loaded, renderer):
    report = json.loads(path.read_text()); config = report.get('metadata', {})
    if config.get('complete') is not True or config.get('sourceHash') != renderer.inventory['sourceHash']:
        raise ValueError('Frozen benchmark completion or DSP source is incompatible')
    bindings = {str(path.resolve()): file_hash(path)}
    _bind_file(Path(__file__).with_name('benchmark.py'), config.get('benchmarkCodeSha256'), bindings, 'Benchmark code')
    models, hashes = config.get('models', {}), config.get('modelHashes', {})
    if not models or set(models) != set(hashes) or 'acoustic' not in models:
        raise ValueError('Frozen benchmark model hash bindings are absent')
    for name, model_path in models.items():
        _bind_file(model_path, hashes[name], bindings, 'Frozen inverse model')
    expected_features = {'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
        'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM}
    manifests = {}
    if not config.get('datasets'):
        raise ValueError('Frozen benchmark feature binding is absent')
    for dataset in config['datasets']:
        data_path = Path(dataset['path']); manifest_path = data_path/'manifest.json'
        _bind_file(manifest_path, dataset.get('manifestSha256'), bindings, 'Frozen dataset manifest')
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('complete') is not True or manifest.get('sourceHash') != config['sourceHash'] or any(manifest.get(k) != v for k, v in expected_features.items()):
            raise ValueError('Frozen benchmark feature provenance is incompatible')
        verify_dataset_files(data_path, manifest)
        for name, files in manifest['files'].items():
            bindings[str((data_path/(name+'.npz')).resolve())] = files['npzSha256']
            bindings[str((data_path/(name+'.json')).resolve())] = files['metadataSha256']
        manifests[dataset['manifestSha256']] = (data_path, manifest)
    # The acoustic checkpoint selects the exact v2 training data. Membership in
    # the benchmark's dataset list alone would also admit the older v1 dataset.
    acoustic_metadata = torch.load(models['acoustic'], map_location='cpu', weights_only=True)['metadata']
    training_hash = acoustic_metadata.get('dataManifestHash')
    if training_hash not in manifests or any(metadata.get('dataManifestHash') != training_hash for _, metadata in loaded.values()):
        raise ValueError('Forward training dataset must match the frozen acoustic model exactly')
    training_path, training_manifest = manifests[training_hash]
    for name, (_, metadata) in loaded.items():
        if metadata.get('datasetFiles') != training_manifest['files'].get(name):
            raise ValueError('Forward training dataset shard file binding differs: '+name)
        shard = json.loads((training_path/(name+'.json')).read_text())
        splits = {key: shard[key] for key in ('train', 'val')}
        if training_manifest.get('splits', {}).get(name) != splits or metadata.get('splitHash') != _hash_json(splits):
            raise ValueError('Forward training split binding differs: '+name)
    rows = [r for r in report.get('results', []) if r.get('sourceSynth') in ENGINES]
    if len(rows) != 20 or Counter(r['family'] for r in rows) != Counter({'native': 3, 'static': 9, 'moving': 8}) or len({r['id'] for r in rows}) != 20:
        raise ValueError('Expected exactly 20 frozen cases: 3 native, 9 static, 8 moving')
    for row in rows:
        identifier = row['id']
        if Path(identifier).name != identifier or identifier in ('.', '..'):
            raise ValueError('Unsafe benchmark case identifier')
        arm = row['arms']['acoustic']; before = arm['candidates']['knownRaw']
        if not before or arm.get('checkpointSha256') != hashes['acoustic'] or before.get('provenance', {}).get('checkpointHash') != hashes['acoustic']:
            raise ValueError('Frozen knownRaw inverse model binding is incompatible')
        for source in (row, before):
            _bind_file(source['waveFile'], source.get('waveFileSha256'), bindings, 'Frozen PCM')
    return rows, bindings


def _verify_completion(bindings, source_hash, count):
    if count != 20:
        raise ValueError('Actual-DSP probe completion requires all 20 cases')
    for path, bound in bindings.items():
        if file_hash(path) != bound:
            raise ValueError('Probe input changed during run: '+path)
    # A new worker reads today's shipped DSP; the original worker's inventory
    # is a snapshot and cannot detect source files changing during the probe.
    with Renderer() as current:
        if current.inventory['sourceHash'] != source_hash:
            raise ValueError('Actual-DSP source changed during probe')


def run_probe(benchmark, models, output, steps=100, learning_rate=.01):
    """Run only on the 20 unchanged frozen cases and gate-passing forward models.

    models is a parent directory containing all three engine directories, or a
    mapping of engine names to their directory/checkpoint paths.
    """
    output, benchmark = Path(output).resolve(), Path(benchmark).resolve()
    if output.exists():
        raise FileExistsError('Forward probe output must be fresh: '+str(output))
    _settings(steps, learning_rate)
    paths = {name: Path(models)/name for name in ENGINES} if not isinstance(models, dict) else {name: Path(path) for name, path in models.items()}
    if set(paths) != set(ENGINES):
        raise ValueError('All three forward engine models are required')
    loaded = {name: load_forward(paths[name]) for name in ENGINES}
    if any(metadata.get('predictiveGate', {}).get('passed') is not True for _, metadata in loaded.values()):
        raise ValueError('Every forward predictive gate must pass before the actual-DSP probe')
    torch.set_num_threads(1)
    started = time.monotonic()
    with Renderer() as renderer:
        rows, bindings = _benchmark_inputs(benchmark, loaded, renderer)
        for name, path in paths.items():
            checkpoint = path/'best.pt' if path.is_dir() else path
            _bind_file(checkpoint, loaded[name][1]['checkpointHash'], bindings, 'Forward checkpoint')
            report_path = checkpoint.parent/'training.json'
            bindings[str(report_path.resolve())] = file_hash(report_path)
        prepared = {r['id']: _prepare_case(r, loaded[r['sourceSynth']][1], renderer) for r in rows}
        code_paths = [Path(__file__), Path(__file__).with_name('forward.py'), Path(__file__).with_name('schema.py'),
            Path(__file__).with_name('features.py'), Path(__file__).with_name('data.py'),
            Path(__file__).resolve().parents[1]/'multisynth'/'renderer.py',
            Path(__file__).resolve().parents[1]/'render'/'multisynth_worker.js',
            Path(__file__).resolve().parents[1]/'match'/'objective.py',
            Path(__file__).resolve().parents[1]/'match'/'features.py',
            Path(__file__).resolve().parents[1]/'match'/'audio.py']
        code_hashes = {str(path): file_hash(path) for path in code_paths}
        bindings.update(code_hashes)
        config = {'complete': False, 'version': 1, 'benchmark': str(benchmark),
            'benchmarkSha256': file_hash(benchmark), 'sourceHash': renderer.inventory['sourceHash'],
            'featureVersion': VERSION, 'featureHash': FEATURE_HASH, 'featureCodeHash': FEATURE_CODE_HASH,
            'lossPolicy': deepcopy(LOSS_POLICY), 'codeHashes': code_hashes,
            'models': {name: {'path': str(paths[name].resolve()), 'checkpointHash': metadata['checkpointHash'],
                'normalizationHash': metadata['normalizationHash'], 'predictiveGate': metadata['predictiveGate'],
                'dataManifestHash': metadata['dataManifestHash'], 'datasetFiles': metadata['datasetFiles'],
                'splitHash': metadata['splitHash']}
                for name, (_, metadata) in loaded.items()},
            'steps': steps, 'learningRate': learning_rate, 'optimizer': 'Adam', 'device': 'cpu',
            'actualGatePolicy': deepcopy(ACTUAL_GATE_POLICY), 'caseIds': [r['id'] for r in rows],
            'inputFileHashes': bindings,
            'scope': 'surrogate-only continuous refinement; fixed categorical/text/random controls and seeds; no perceptual likeness claim'}
        output.mkdir(parents=True, exist_ok=False)
        result = {'metadata': config, 'results': []}
        _json_write(output/'results.json', result)
        for row in rows:
            model, metadata = loaded[row['sourceSynth']]
            case = probe_case(row, model, metadata, renderer, output/row['id'], steps, learning_rate, prepared=prepared[row['id']])
            result['results'].append(case)
            _json_write(output/'results.json', result)
            print(json.dumps({'event': 'probe-case', 'id': row['id'], 'actualImproved': case['actualImproved'],
                'beforeLoss': case['before']['featureLoss']['total'], 'afterLoss': case['after']['featureLoss']['total']}), flush=True)
        for case in result['results']:
            for role in ('target', 'before', 'after'):
                _read_pcm(case[role])
        _verify_completion(bindings, config['sourceHash'], len(result['results']))
        result['summary'] = summarize(result['results'])
        config.update(complete=True, seconds=time.monotonic()-started)
        _json_write(output/'results.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', required=True)
    parser.add_argument('--models', required=True, help='Parent directory with Bfxr, Transfxr and Pluckr checkpoints')
    parser.add_argument('--output', required=True)
    parser.add_argument('--steps', type=int, default=100)
    parser.add_argument('--learning-rate', type=float, default=.01)
    args = parser.parse_args()
    run_probe(args.benchmark, args.models, args.output, args.steps, args.learning_rate)


if __name__ == '__main__':
    main()
