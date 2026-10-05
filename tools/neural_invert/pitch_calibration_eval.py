"""Bounded hybrid inference over the frozen temporal-v3 actual-render pool.

No models are trained or asked to predict. Model loading validates the frozen
checkpoint/data/code bindings. Extra real DSP calls are explicitly accounted;
this experiment is not an equal-compute training comparison.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .data import _json_write, file_hash
from .pitch_calibration import POLICY, ENGINES, calibrate_candidate, select_candidates
from .pitch_v5_eval import load_experts, descriptor_pitch
from .pitch_v5_features import FEATURE_HASH, FEATURE_CODE_HASH

VERSIONS = ('temporal-v3', 'pitch-v4', 'pitch-v5')
SOURCE_CODE = ('pitch_v5_gallery.py', 'pitch_v5_eval.py', 'pitch_v5_features.py',
    'pitch_v5_temporal.py', 'pitch_v5_data.py', 'pitch_features.py', 'pitch_temporal.py',
    'pitch_data.py', 'temporal.py', 'train.py', 'acoustic.py', 'features.py',
    'temporal_eval.py', 'benchmark.py', 'evaluate.py', 'data.py', 'schema.py',
    'model.py', 'predict.py')
MODEL_KEYS = ('checkpointHash', 'dataManifestHash', 'featureHash', 'featureCodeHash', 'sourceHash')
SOURCE_AUDIT = Path(__file__).parents[1]/'multisynth'/'evaluations'/'pitch-v5-comparison.json'


def bind_source_audit(path, bindings):
    """Require prior whole-report audit identity, even for relocated copies."""
    path = Path(path).resolve()
    if not SOURCE_AUDIT.is_file():
        raise ValueError('Frozen source audit binding missing')
    _bind(bindings, SOURCE_AUDIT)
    audit = _read(SOURCE_AUDIT)
    actual = file_hash(path)
    match = [r for r in audit.get('reports', {}).values()
             if r['reportSha256'] == actual]
    if audit.get('complete') is not True or len(match) != 1:
        raise ValueError('Frozen source whole-report audit binding differs')
    _bind(bindings, path, match[0]['reportSha256'])


def source_code_hashes():
    """The complete code inventory declared by the frozen pitch-v5 evaluator."""
    result = {name: file_hash(Path(__file__).with_name(name)) for name in SOURCE_CODE}
    result.update({str(p): file_hash(p) for p in (Path(__file__).parents[1]/'match').glob('*.py')})
    return result


def _read(path):
    def reject(value):
        raise ValueError('Nonfinite JSON value: '+value)
    return json.loads(Path(path).read_text(), parse_constant=reject)


def _hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _bind(bindings, path, expected=None):
    # Preserve symlink routes: expert assembly directories use them, and a
    # retargeted checkpoint must be detected by the end-of-run recheck.
    path = str(Path(path).absolute())
    actual = file_hash(path)
    if expected is not None and actual != expected:
        raise ValueError('File binding changed: '+path)
    if path in bindings and bindings[path] != actual:
        raise ValueError('File changed during validation: '+path)
    bindings[path] = actual
    return actual


def _check_bindings(bindings):
    for path, expected in bindings.items():
        if file_hash(path) != expected:
            raise ValueError('File binding changed during evaluation: '+path)


def _dataset_bindings(bindings, path, manifest_hash, files):
    path = Path(path)
    _bind(bindings, path/'manifest.json', manifest_hash)
    for name, hashes in files.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('Unsafe dataset engine')
        for extension, key in (('.json', 'metadataSha256'), ('.npz', 'npzSha256')):
            _bind(bindings, path/(name+extension), hashes[key])


def read_audio(path, file_sha256, pcm_hash, bindings=None):
    """Require the exact saved mono float32 actual-DSP waveform."""
    if bindings is None:
        bindings = {}
    _bind(bindings, path, file_sha256)
    info = sf.info(path)
    wave, rate = sf.read(path, dtype='float32')
    if (rate != 44100 or info.subtype != 'FLOAT' or wave.ndim != 1 or not wave.size
            or not np.all(np.isfinite(wave)) or audio_hash(wave) != pcm_hash):
        raise ValueError('Frozen float PCM binding differs: '+str(path))
    return wave


def validate_source(path, renderer):
    """Return the immutable source and every file binding to recheck at the end."""
    path = Path(path).resolve()
    bindings = {}
    _bind(bindings, path)
    bind_source_audit(path, bindings)
    source = _read(path)
    meta = source['metadata']
    if meta.get('complete') is not True or meta.get('experiment') != 'pitch-initial-lobe-v5':
        raise ValueError('Complete frozen pitch-v5 comparison required')
    manifest = path.parent/'manifest.json'
    _bind(bindings, manifest)
    if _read(manifest) != meta:
        raise ValueError('Source manifest/report mismatch')
    if (meta.get('sourceHash') != renderer.inventory['sourceHash'] or
            meta.get('candidateBudgetPerEngine') != 4 or meta.get('candidateBudgetTotal') != 12):
        raise ValueError('Source DSP or original candidate budget differs')
    if (meta.get('codeHashes') != source_code_hashes() or
            meta.get('v5DiagnosticFeatureHash') != FEATURE_HASH or
            meta.get('v5DiagnosticCodeHash') != FEATURE_CODE_HASH):
        raise ValueError('Frozen source code/feature binding differs')
    for name, expected in meta['codeHashes'].items():
        _bind(bindings, Path(name) if Path(name).is_absolute() else Path(__file__).with_name(name), expected)
    _bind(bindings, meta['benchmarkPath'], meta['benchmarkSha256'])
    parent = _read(meta['benchmarkPath'])
    if parent['metadata'].get('complete') is not True or parent['metadata'].get('sourceHash') != meta['sourceHash']:
        raise ValueError('Parent benchmark incomplete or DSP differs')
    targets = [r for r in parent['results'] if r['sourceSynth'] in ENGINES]
    rows = source['results']
    ids = [r['id'] for r in rows]
    if (not rows or len(set(ids)) != len(ids) or any(not isinstance(i, str) or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', i) for i in ids)):
        raise ValueError('Nonempty unique safe target identifiers required')
    if ids != [r['id'] for r in targets]:
        raise ValueError('Source target identities/order differ from parent benchmark')
    if set(meta.get('models', {})) != set(VERSIONS) or set(meta.get('modelDirectories', {})) != set(VERSIONS):
        raise ValueError('Frozen model inventory incomplete')
    for version in VERSIONS:
        root = Path(meta['modelDirectories'][version])
        # Loaders verify training history, checkpoint weights, feature/schema,
        # dataset contents, and actual DSP identity. Their predictor is unused.
        experts, _ = load_experts(root, version)
        if set(experts) != set(ENGINES) or set(meta['models'][version]) != set(ENGINES):
            raise ValueError('Frozen engine model inventory incomplete')
        # Production roots assemble separately trained experts with symlinks.
        # The loaders validate the training reports at each resolved engine.
        for report_name in ('assembly.json', 'training.json'):
            if (root/report_name).is_file():
                _bind(bindings, root/report_name)
        for name, (_, metadata) in experts.items():
            if {key: metadata[key] for key in MODEL_KEYS} != meta['models'][version][name]:
                raise ValueError('Frozen model checkpoint/data/feature binding differs')
            if metadata['sourceHash'] != meta['sourceHash'] or metadata['spec'] != renderer.specs[name]:
                raise ValueError('Frozen model DSP/schema differs')
            _bind(bindings, root/name/'best.pt', metadata['checkpointHash'])
            _bind(bindings, root/name/'training.json')
            parent_training = (root/name).resolve().parent/'training.json'
            if parent_training.is_file():
                _bind(bindings, parent_training)
            _dataset_bindings(bindings, metadata['datasetPath'], metadata['dataManifestHash'], metadata['datasetFiles'])
            if 'sourceDataset' in metadata:
                data = metadata['sourceDataset']
                _dataset_bindings(bindings, data['path'], data['manifestSha256'], data['files'])
        del experts
    for row, target in zip(rows, targets):
        report = path.parent/row['id']/'report.json'
        _bind(bindings, report)
        if _read(report) != row:
            raise ValueError('Per-target report differs from source report')
        if (any(row[key] != target[key] for key in ('id', 'family', 'sourceSynth', 'sourceParams', 'sourceSeed'))
                or target['sourceHash'] != meta['sourceHash'] or
                row['referenceWaveFile'] != target['waveFile'] or
                row['referenceWaveFileSha256'] != target['waveFileSha256'] or
                row['referenceAudioHash'] != target['audioHash']):
            raise ValueError('Source target differs from parent benchmark')
        read_audio(row['referenceWaveFile'], row['referenceWaveFileSha256'], row['referenceAudioHash'], bindings)
        arm = row['arms']['temporal-v3']
        candidates, proposals = arm['candidates'], arm['proposals']
        if (len(candidates) != 12 or len(proposals) != 12 or arm.get('failures') or
                any(sum(c['synth'] == name for c in candidates) != 4 or
                    sum(c['synth'] == name for c in proposals) != 4 for name in ENGINES)):
            raise ValueError('All twelve original temporal-v3 candidates required')
        for candidate in candidates:
            if candidate.get('provenance', {}).get('checkpointHash') != meta['models']['temporal-v3'][candidate['synth']]['checkpointHash']:
                raise ValueError('Candidate checkpoint identity differs')
            read_audio(candidate['waveFile'], candidate['waveFileSha256'], candidate['audioHash'], bindings)
        known = [c for c in candidates if c['synth'] == row['sourceSynth']]
        if (arm.get('selected') != min(known, key=lambda c: c['score']) or
                arm.get('unrestrictedSelected') != min(candidates, key=lambda c: c['score'])):
            raise ValueError('Frozen original selections differ from candidate pool')
    return source, bindings


def save_audio(stem, wave):
    """Persist every returned array; malformed/nonfinite PCM remains an NPY artifact."""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    wave = np.asarray(wave)
    reason = ('malformed_shape' if wave.ndim != 1 or not wave.size else
              'nonfinite_audio' if not np.all(np.isfinite(wave)) else
              'non_float32_audio' if wave.dtype != np.dtype('float32') else None)
    metadata = dict(audioShape=list(wave.shape), audioDtype=str(wave.dtype),
                    audioHash=audio_hash(wave), audioSamples=int(wave.size), audible=False)
    if reason:
        path = stem.with_suffix('.npy')
        np.save(path, wave, allow_pickle=False)
        metadata['failureArtifact'] = dict(path=str(path.resolve()), sha256=file_hash(path),
            shape=list(wave.shape), dtype=str(wave.dtype), reason=reason,
            arraySha256=hashlib.sha256(wave.tobytes()).hexdigest())
        return metadata
    path = stem.with_suffix('.wav')
    sf.write(path, wave, 44100, subtype='FLOAT')
    decoded, rate = sf.read(path, dtype='float32')
    if rate != 44100 or not np.array_equal(wave, decoded):
        raise ValueError('Persisted actual render differs')
    metadata.update(waveFile=str(path.resolve()), waveFileSha256=file_hash(path),
                    audible=bool(np.max(np.abs(wave)) >= POLICY['audiblePeak']))
    return metadata


def _without_wave(value):
    if isinstance(value, dict):
        return {k: _without_wave(v) for k, v in value.items() if k != 'wave'}
    if isinstance(value, (list, tuple)):
        return [_without_wave(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


class ArtifactPersistenceError(Exception):
    """Fatal evidence loss, deliberately outside tolerated renderer exceptions."""


def _persist(call, operation, *args, **kwargs):
    try:
        return operation(*args, **kwargs)
    except Exception as exc:
        call['persistenceFailure'] = dict(type=type(exc).__name__, error=str(exc))
        raise ArtifactPersistenceError('Artifact persistence failed: '+str(exc)) from exc


class _AuditedRenderer:
    """Persist calls before calibration/scoring so exceptions retain evidence."""
    def __init__(self, renderer, candidate, objective, dest, index):
        self.renderer, self.specs = renderer, renderer.specs
        self.candidate, self.objective = candidate, objective
        self.dest, self.index, self.calls = Path(dest), index, []

    def render(self, synth, params, seed):
        call = dict(sourceCandidateIndex=self.index, synth=synth, seed=seed,
                    requestedParams=deepcopy(params), renderCount=1, rendered=True,
                    role='original_validation' if not self.calls else 'calibration', status='started')
        self.calls.append(call)
        number = len(self.calls)-1
        path = self.dest/f'{number:02d}.json'
        try:
            _persist(call, self.dest.mkdir, parents=True, exist_ok=True)
            _persist(call, _json_write, path, call)
        except ArtifactPersistenceError:
            # Persistence failed before entering the renderer: no call consumed.
            call.update(renderCount=0, rendered=False, status='not_rendered')
            raise
        try:
            canonical, wave = self.renderer.render(synth, params, seed)
        except BaseException as exc:
            call.update(status='render_error', error=str(exc), errorType=type(exc).__name__)
            _persist(call, _json_write, path, call)
            raise
        call.update(canonicalParams=deepcopy(canonical), status='returned')
        call.update(_persist(call, save_audio, self.dest/f'{number:02d}', wave))
        _persist(call, _json_write, path, call)
        if number == 0:
            source = self.candidate
            frozen = read_audio(source['waveFile'], source['waveFileSha256'], source['audioHash'])
            if canonical != source['params'] or not np.array_equal(wave, frozen):
                raise ValueError('Original canonical controls/actual DSP PCM replay differs')
            score = float(self.objective.score_batch([wave])[0])
            if not np.isfinite(score) or not np.isclose(score, source['score'], rtol=1e-9, atol=1e-9):
                raise ValueError('Original actual-DSP objective score differs')
            call.update(status='validated', score=score)
            _persist(call, _json_write, path, call)
        return canonical, wave


def _attach_audio(row, call):
    keys = ('audioHash', 'audioShape', 'audioDtype', 'audioSamples', 'audible',
            'waveFile', 'waveFileSha256', 'failureArtifact')
    # Remove source WAV locations before attaching the newly persisted PCM.
    return {**{k: v for k, v in row.items() if k not in keys},
            **{k: call[k] for k in keys if k in call}}


def evaluate_target(source, renderer, output):
    """Evaluate one validated target while preserving all per-candidate attempts."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    target = read_audio(source['referenceWaveFile'], source['referenceWaveFileSha256'], source['referenceAudioHash'])
    record = {k: deepcopy(source[k]) for k in ('id', 'family', 'sourceSynth', 'sourceParams', 'sourceSeed',
                'referenceWaveFile', 'referenceWaveFileSha256', 'referenceAudioHash')}
    record.update(complete=False, originals=[], accepted=[], calibrations=[],
                  accounting=dict(originalValidationReplays=0, additionalRenderCount=0,
                                  failedRenderCalls=0, targetValidationReplays=0))
    _json_write(output/'report.json', record)
    record['accounting']['targetValidationReplays'] = 1
    target_call = dict(synth=source['sourceSynth'], seed=source['sourceSeed'],
                       requestedParams=source['sourceParams'], renderCount=1, status='started')
    _json_write(output/'report.json', record)
    _json_write(output/'target-validation.json', target_call)
    try:
        canonical, replay = renderer.render(source['sourceSynth'], source['sourceParams'], source['sourceSeed'])
    except BaseException as exc:
        target_call.update(status='render_error', error=str(exc), errorType=type(exc).__name__)
        record['accounting']['failedRenderCalls'] += 1
        record['failure'] = target_call
        _json_write(output/'target-validation.json', target_call)
        _json_write(output/'report.json', record)
        raise
    target_artifact = save_audio(output/'target-validation', replay)
    target_call.update(canonicalParams=canonical, **target_artifact, status='returned')
    _json_write(output/'target-validation.json', target_call)
    if canonical != source['sourceParams'] or not np.array_equal(replay, target):
        raise ValueError('Target controls or actual DSP PCM differs')
    record['accounting']['targetValidationReplays'] = 1
    record['v5TargetPitch'] = descriptor_pitch(target)
    objective = MatchObjective(target)
    originals, accepted = [], []
    for index, candidate in enumerate(source['arms']['temporal-v3']['candidates']):
        audited = _AuditedRenderer(renderer, candidate, objective, output/f'candidate-{index:02d}', index)
        try:
            result = calibrate_candidate({**candidate, 'sourceCandidateIndex': index}, target, audited, objective)
        except BaseException as exc:
            record['accounting']['originalValidationReplays'] += sum(c['renderCount'] for c in audited.calls[:1])
            record['accounting']['additionalRenderCount'] += sum(c['renderCount'] for c in audited.calls[1:])
            record['accounting']['failedRenderCalls'] += sum(c['status'] == 'render_error' for c in audited.calls)
            record['failure'] = dict(sourceCandidateIndex=index, type=type(exc).__name__, error=str(exc),
                                     renderCalls=deepcopy(audited.calls))
            _json_write(output/'report.json', record)
            raise
        original = _attach_audio(result['original'], audited.calls[0])
        originals.append(original)
        steps, cursor = {}, 1
        for attempt in result['attempts']:
            attempt['sourceCandidateIndex'] = index
            if attempt['renderCount']:
                attempt.update({k: v for k, v in _attach_audio(attempt, audited.calls[cursor]).items() if k != 'wave'})
                cursor += 1
            steps[attempt['step']] = attempt
        if cursor != len(audited.calls) or result['additionalRenderCount'] != len(audited.calls)-1:
            raise ValueError('Calibration render accounting mismatch')
        for row in result['accepted']:
            step = row['provenance']['pitchCalibration']['step']
            accepted.append({**_attach_audio(row, steps[step]), 'sourceCandidateIndex': index, 'calibrationStep': step})
        record['originals'].append(_without_wave(original))
        record['accepted'] = _without_wave(accepted)
        record['calibrations'].append(dict(sourceCandidateIndex=index, status=result['status'],
            additionalRenderCount=result['additionalRenderCount'], attempts=_without_wave(result['attempts'])))
        record['accounting']['originalValidationReplays'] += 1
        record['accounting']['additionalRenderCount'] += result['additionalRenderCount']
        record['accounting']['failedRenderCalls'] += sum(call['status'] == 'render_error' for call in audited.calls)
        if record['accounting']['additionalRenderCount'] > 36:
            raise ValueError('Additional actual-render budget exceeded')
        _json_write(output/'report.json', record)
    record['unrestricted'] = _without_wave(select_candidates(originals, accepted, target))
    record['sourceEngine'] = _without_wave(select_candidates(
        [r for r in originals if r['synth'] == source['sourceSynth']],
        [r for r in accepted if r['synth'] == source['sourceSynth']], target))
    record['complete'] = True
    _json_write(output/'report.json', record)
    return record


def benchmark(benchmark_path, output):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Calibration output must be fresh')
    torch.set_num_threads(1)
    with Renderer() as renderer:
        source, bindings = validate_source(benchmark_path, renderer)
        code_hashes = {str(Path(__file__).with_name(name)): file_hash(Path(__file__).with_name(name))
                      for name in ('pitch_calibration_eval.py', 'pitch_calibration.py')}
        code_hashes.update({str(p): file_hash(p) for p in (
            Path(__file__).parents[1]/'multisynth'/'renderer.py',
            Path(__file__).parents[1]/'render'/'multisynth_worker.js')})
        bindings.update(code_hashes)
        meta = dict(complete=False, experiment=POLICY['version'], sourceReportPath=str(Path(benchmark_path).resolve()),
            sourceReportSha256=file_hash(benchmark_path), sourceManifestSha256=file_hash(Path(benchmark_path).parent/'manifest.json'),
            sourceMetadata=deepcopy(source['metadata']), sourceHash=renderer.inventory['sourceHash'],
            policy=deepcopy(POLICY), policySha256=_hash_json(POLICY), codeHashes=code_hashes,
            inputBindings=bindings, targetIds=[r['id'] for r in source['results']],
            candidateBudgetTotal=12, maximumAdditionalRendersPerTarget=36,
            scope='Hybrid inference with extra real DSP renders; no equal-compute training or human-likeness claim.',
            selection='Unchanged actual-PCM MatchObjective; primary unrestricted and separate source-engine diagnostic.',
            reports=[])
        output.mkdir(parents=True)
        _json_write(output/'manifest.json', meta)
        records, outputs = [], {}
        try:
            for row in source['results']:
                dest = output/row['id']
                records.append(evaluate_target(row, renderer, dest))
                for path in dest.rglob('*'):
                    if path.is_file():
                        _bind(outputs, path)
                meta['reports'].append(dict(id=row['id'], reportFile=str(dest/'report.json'),
                                             reportFileSha256=file_hash(dest/'report.json')))
                _json_write(output/'manifest.json', meta)
                print(json.dumps(dict(id=row['id'], **records[-1]['accounting'])), flush=True)
            _check_bindings(bindings)
            _check_bindings(outputs)
            with Renderer() as final_renderer:
                if final_renderer.inventory['sourceHash'] != meta['sourceHash']:
                    raise ValueError('DSP changed during evaluation')
            if _hash_json(POLICY) != meta['policySha256']:
                raise ValueError('Calibration policy changed during evaluation')
        except BaseException as exc:
            meta['failure'] = dict(type=type(exc).__name__, error=str(exc), completedTargets=len(records))
            _json_write(output/'manifest.json', meta)
            raise
    meta.update(complete=True, outputBindings=outputs)
    result = dict(metadata=meta, results=records)
    _json_write(output/'results.json', result)
    _json_write(output/'manifest.json', meta)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', required=True, help='One complete frozen pitch-v5 comparison results.json')
    parser.add_argument('--output', required=True, help='Fresh output directory')
    args = parser.parse_args()
    benchmark(args.benchmark, args.output)


if __name__ == '__main__':
    main()
