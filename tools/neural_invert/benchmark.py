"""Fresh paired actual-DSP diagnostics; numerical scores are not listening judgments."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf
import torch

from match.features import FeatureExtractor
from match.objective import MatchObjective
from match.optimizer import freq_param_from_hz
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from .data import _json_write, file_hash, parameter_hash, verify_dataset_files
from .evaluate import OriginalBfxr, approximate, serializable
from .features import DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
from .predict import load_model
from .schema import ControlSchema

ROLES = ('knownRaw', 'unrestrictedRaw', 'neuralRefined', 'selected', 'original')
FAMILIES = ('native', 'static', 'moving')
RATE = 44100


def audio_hash(wave):
    return hashlib.sha256(np.asarray(wave, dtype='<f4').tobytes()).hexdigest()


def control_hash(spec, params):
    """Exact learned control vector plus all TEXT; ignore gain/random anchors."""
    schema = ControlSchema(spec)
    numeric, categories = schema.encode(params)
    payload = {'synth': spec['name'], 'continuous': numeric.tolist(),
               'categorical': categories.tolist(),
               'text': {name: params.get(name, spec['defaults'].get(name)) for name in schema.fixed_text}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def exact_replay(row, renderer, bfxr):
    """Close the controls -> DSP -> scored PCM loop without transformations."""
    if row.get('expert') == 'original-bfxr':
        canonical = row['params']
        wave = bfxr.render(row['params'], seed=row['seed'])
    else:
        canonical, wave = renderer.render(row['synth'], row['params'], row['seed'])
    if canonical != row['params'] or audio_hash(wave) != audio_hash(row['wave']):
        raise ValueError('Exact control replay differs from scored PCM: '+row['synth'])
    return {'exact': True, 'canonicalParamsEqual': True, 'audioHash': audio_hash(wave),
            'seed': row['seed'], 'backend': 'original-bfxr' if row.get('expert') == 'original-bfxr' else 'actual-multisynth'}


def pitch_diagnostic(wave):
    """Sixteen bins over the active span, retaining unvoiced gaps as nulls."""
    wave = np.asarray(wave, dtype=np.float32)
    wave = np.pad(wave, (0, max(2048-len(wave), 0)))
    with torch.no_grad():
        features = FeatureExtractor().extract(torch.from_numpy(wave[None]))
    active = features.active[0].numpy()
    voiced = features.voiced[0].numpy() & active
    log = features.f0_log2[0].numpy()
    ids = np.flatnonzero(active)
    contour = [None]*16
    if len(ids):
        # Bin frame centres by active-relative time; don't rescale voiced-only
        # frames or interpolate across missing voiced sections.
        normalized = (np.arange(len(active))-ids[0]) / max(1, ids[-1]-ids[0])
        for i in range(16):
            mask = voiced & (normalized >= i/16) & (normalized < (i+1)/16 if i < 15 else normalized <= 1)
            if mask.any():
                contour[i] = float(2**np.median(log[mask]))
    fraction = float(voiced.sum()/max(1, active.sum()))
    reliable = fraction >= .6 and voiced.sum() >= 3
    median = float(2**np.median(log[voiced])) if reliable else None
    valid = [12*np.log2(hz) for hz in contour if hz is not None]
    start = [12*np.log2(hz) for hz in contour[:3] if hz is not None]
    end = [12*np.log2(hz) for hz in contour[-3:] if hz is not None]
    delta = float(np.median(end)-np.median(start)) if reliable and start and end else None
    return {'activeFrames': int(active.sum()), 'voicedFrames': int(voiced.sum()),
            'voicedFraction': fraction, 'medianHz': median, 'reliable': bool(reliable),
            'contourHz': contour, 'contourTime': np.linspace(1/32, 31/32, 16).tolist(),
            'contourMeaning': 'median voiced Hz in sixteen active-span time bins; null bins have no reliable voiced frames',
            'startToEndSemitones': delta,
            'direction': (1 if delta > .5 else -1 if delta < -.5 else 0) if delta is not None else None,
            'excursionSemitones': float(max(valid)-min(valid)) if reliable and len(valid) >= 3 else None}


def compare_pitch(target, candidate, family):
    reliable = target.get('medianHz') is not None and candidate.get('medianHz') is not None
    error = float(abs(12*np.log2(candidate['medianHz']/target['medianHz']))) if reliable else None
    pairs = [(a, b) for a, b in zip(target.get('contourHz', []), candidate.get('contourHz', []))
             if a is not None and b is not None]
    contour_error = float(np.mean([abs(12*np.log2(b/a)) for a, b in pairs])) if reliable and pairs else None
    excursion_a, excursion_b = target.get('excursionSemitones'), candidate.get('excursionSemitones')
    return {'absolutePitchErrorSemitones': error if family == 'static' else None,
            'contourErrorSemitones': contour_error if family == 'moving' else None,
            'reliableContourPairs': len(pairs) if reliable else 0,
            'directionMatches': bool(target['direction'] == candidate['direction'])
                if family == 'moving' and target.get('direction') is not None and candidate.get('direction') is not None else None,
            'excursionErrorSemitones': float(abs(excursion_b-excursion_a))
                if family == 'moving' and excursion_a is not None and excursion_b is not None else None}


def probe_controls(spec, rng, hz, gesture='stationary'):
    """Supported quiet tonal controls, with fresh durations and actual motion."""
    name = spec['name']; p = deepcopy(spec['defaults'])
    duration = float(rng.uniform(.78, 1.17))
    end = hz*(.55 if gesture == 'fall' else 1.8) if gesture in ('rise', 'fall', 'jump') else hz
    p['masterVolume'] = .5
    if name == 'Bfxr':
        p.update(waveType=2, frequency_start=freq_param_from_hz(hz), attackTime=.025,
                 sustainTime=float(np.sqrt((duration-.10)*RATE/100000)),
                 decayTime=float(np.sqrt(.10*RATE/100000)), sustainPunch=0.,
                 frequency_slide=0., frequency_acceleration=0., vibratoDepth=0., vibratoSpeed=0.,
                 pitch_jump_amount=0., pitch_jump_2_amount=0., pitch_jump_repeat_speed=0., repeatSpeed=0.,
                 overtones=0., lpFilterCutoff=1., hpFilterCutoff=0.)
        if gesture in ('rise', 'fall'):
            p['frequency_slide'] = float(np.cbrt((1-(hz/end)**(1/(duration*RATE)))/.01))
        elif gesture == 'jump':
            p['pitch_jump_amount'] = float(np.sqrt((1-hz/end)/.9))
            p['pitch_jump_onset_percent'] = .45
        elif gesture == 'vibrato':
            p['vibratoDepth'] = .085
            p['vibratoSpeed'] = float(np.sqrt(5.3*2*np.pi/(RATE*.01)))
    elif name == 'Transfxr':
        transition = lambda a, b=None, curve='Linear': {'start': float(a), 'end': float(a if b is None else b), 'curve': curve}
        p.update(duration=duration, waveType=0, waveTo=-1, echo=0., resonance=0., attack=.015, release=.12,
                 pitch=transition(np.log2(hz/40)/7, np.log2(end/40)/7, 'Steps' if gesture == 'jump' else 'Linear'),
                 vibrato=transition(.16 if gesture == 'vibrato' else 0.),
                 tone=transition(1.), level=transition(.7))
    elif name == 'Pluckr':
        if gesture != 'stationary':
            raise ValueError('Pluckr controlled benchmark supports static only')
        p.update(pitch=float(np.log2(hz/55)/4), strings=1, material=0, inharmonic=0., coupling=0.,
                 strum=0., vibrato=0., tremolo=0., duration=duration, damping=.12, brightness=.7)
    else:
        raise ValueError('Unsupported controlled probe '+name)
    return p, {'kind': gesture, 'nominalStartHz': float(hz), 'nominalEndHz': float(end),
               'nominalDurationSeconds': duration, 'pitchMeaning': 'nominal control only; calibrated on actual audio'}


def draw_target(renderer, synth, family, excluded, seed, hz=None, gesture=None):
    rng = np.random.default_rng(seed); failures = []
    spec = renderer.specs[synth]
    for attempt in range(128):
        sample_seed, render_seed = [int(rng.integers(0, 2**32)) for _ in range(2)]
        source_generator = None; control_info = None
        try:
            if family == 'native':
                source_generator = spec['presets'][int(rng.integers(len(spec['presets'])))]
                params = renderer.sample(synth, source_generator, sample_seed)
                # One native generator plus a fresh sparse global-control draw.
                if 'params' in spec:
                    params = ControlSchema(spec).mutate(params, np.random.default_rng(sample_seed), 'sparse')
            else:
                params, control_info = probe_controls(spec, np.random.default_rng(sample_seed),
                                                     hz if hz is not None else 311., gesture or 'stationary')
            canonical, wave = renderer.render(synth, params, render_seed)
            key = parameter_hash({'synth': synth, 'params': canonical})
            controls = control_hash(spec, canonical) if 'params' in spec else key
            if key in excluded or controls in excluded:
                raise ValueError('excluded controls')
            if not len(wave) or not np.isfinite(wave).all() or np.max(np.abs(wave)) < 1e-7:
                raise ValueError('silent or nonfinite source')
            pitch = pitch_diagnostic(wave)
            calibration = None
            if family == 'static':
                if pitch['medianHz'] is None:
                    raise ValueError('unreliable static source')
                error = float(abs(12*np.log2(pitch['medianHz']/hz)))
                if error >= .5:
                    raise ValueError('static source pitch calibration failed')
                calibration = {'absoluteSemitones': error, 'measuredHz': pitch['medianHz']}
            elif family == 'moving':
                threshold = .2 if gesture == 'vibrato' else 2.
                if pitch['excursionSemitones'] is None or pitch['excursionSemitones'] < threshold:
                    raise ValueError('moving source excursion calibration failed')
                if gesture != 'vibrato' and pitch['direction'] != (-1 if gesture == 'fall' else 1):
                    raise ValueError('moving source direction calibration failed')
                calibration = {'direction': pitch['direction'], 'excursionSemitones': pitch['excursionSemitones'],
                               'startToEndSemitones': pitch['startToEndSemitones']}
            return {'family': family, 'sourceSynth': synth, 'sourceGenerator': source_generator,
                    'sourceParams': canonical, 'sampleSeed': sample_seed, 'sourceSeed': render_seed,
                    'drawSeed': seed, 'sourceHash': renderer.inventory['sourceHash'],
                    'parameterHash': key, 'controlHash': controls, 'audioHash': audio_hash(wave), 'audioSamples': len(wave),
                    'controlInfo': control_info, 'expectedHz': hz, 'gesture': gesture,
                    'targetPitch': pitch, 'calibration': calibration, 'rejections': failures, 'wave': wave}
        except (ValueError, RuntimeError) as error:
            failures.append({'attempt': attempt, 'sampleSeed': sample_seed, 'sourceSeed': render_seed, 'reason': str(error)})
    raise ValueError('Unable to draw calibrated fresh target '+synth+'/'+family+': '+json.dumps(failures[-3:]))


def create_targets(renderer, excluded, seed):
    engines = [s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
    plan = [(n, 'native', None, None) for n in engines]
    plan += [(n, 'static', hz, None) for n in ('Bfxr', 'Transfxr', 'Pluckr') for hz in (137, 311, 673)]
    plan += [(n, 'moving', None, gesture) for n in ('Bfxr', 'Transfxr') for gesture in ('rise', 'fall', 'jump', 'vibrato')]
    targets = []
    seen = set(excluded)
    for i, (name, family, hz, gesture) in enumerate(plan):
        target = draw_target(renderer, name, family, seen, seed+i*104729, hz=hz, gesture=gesture)
        target['id'] = f'{i+1:03d}-{name}-{family}'
        target['evaluationSeed'] = seed+i*71
        target['sourceReplay'] = exact_replay({'synth': name, 'params': target['sourceParams'],
                    'seed': target['sourceSeed'], 'wave': target['wave']}, renderer, None)
        seen.add(target['parameterHash']); seen.add(target['controlHash']); targets.append(target)
        print(json.dumps({'event': 'target', 'id': target['id'], 'sourceSeed': target['sourceSeed']}), flush=True)
    return targets


class FrozenOriginal:
    """Reuse one original search per target while checking paired search settings."""
    def __init__(self, row, budget, seed, target_wave=None):
        self.row = deepcopy(row); self.budget = budget; self.seed = seed
        self.target_hash = audio_hash(target_wave) if target_wave is not None else None

    def approximate(self, wave, objective, budget=2000, seed=0):
        if budget != self.budget or seed != self.seed:
            raise ValueError('Frozen original budget or seed changed')
        if self.target_hash is not None and audio_hash(wave) != self.target_hash:
            raise ValueError('Frozen original target PCM changed')
        return deepcopy(self.row)


def summarize(records, arms, engines):
    result = {'arms': {}, 'broadCoverage': {'engines': list(engines),
              'observedEngines': sorted({r['sourceSynth'] for r in records if r['family'] == 'native'}),
              'missingEngines': sorted(set(engines)-{r['sourceSynth'] for r in records if r['family'] == 'native'})}}
    for arm in arms:
        result['arms'][arm] = {}
        for family in ('all',)+FAMILIES:
            targets = [r for r in records if family == 'all' or r['family'] == family]
            result['arms'][arm][family] = {}
            for role in ROLES:
                pairs = [(r, r['arms'].get(arm, {}).get('candidates', {}).get(role)) for r in targets]
                present = [(r, c) for r, c in pairs if c is not None]
                scores = [c['score'] for _, c in present]
                static = [(r, c) for r, c in pairs if r['family'] == 'static']
                errors = [c.get('pitchComparison', {}).get('absolutePitchErrorSemitones') if c else None for _, c in static]
                valid = [e for e in errors if e is not None]
                motion_errors = [c.get('pitchComparison', {}).get('contourErrorSemitones')
                                 for r, c in present if r['family'] == 'moving']
                motion_valid = [e for e in motion_errors if e is not None]
                moving = [(r, c) for r, c in pairs if r['family'] == 'moving']
                directions = [c.get('pitchComparison', {}).get('directionMatches') if c else None for _, c in moving]
                directions_valid = [d for d in directions if d is not None]
                excursions = [c.get('pitchComparison', {}).get('excursionErrorSemitones') if c else None for _, c in moving]
                excursions_valid = [e for e in excursions if e is not None]
                result['arms'][arm][family][role] = {'total': len(pairs), 'count': len(present),
                    'missing': len(pairs)-len(present), 'meanScore': float(np.mean(scores)) if scores else None,
                    'medianScore': float(np.median(scores)) if scores else None,
                    'sourceEngineRecovery': sum(c['synth'] == r['sourceSynth'] for r, c in present),
                    'sourceEngineRecoveryTotal': len(pairs), 'staticTotal': len(static),
                    'withinOneSemitone': sum(e <= 1 for e in valid), 'pitchUnreliableOrMissing': len(errors)-len(valid),
                    'meanAbsolutePitchSemitones': float(np.mean(valid)) if valid else None,
                    'medianAbsolutePitchSemitones': float(np.median(valid)) if valid else None,
                    'movingPitchReliableCount': len(motion_valid),
                    'movingPitchUnreliableOrMissing': sum(r['family'] == 'moving' for r, _ in pairs)-len(motion_valid),
                    'meanContourErrorSemitones': float(np.mean(motion_valid)) if motion_valid else None,
                    'medianContourErrorSemitones': float(np.median(motion_valid)) if motion_valid else None,
                    'movingDirectionMatches': sum(directions_valid),
                    'movingDirectionReliableCount': len(directions_valid),
                    'movingDirectionUnreliableOrMissing': len(directions)-len(directions_valid),
                    'meanExcursionErrorSemitones': float(np.mean(excursions_valid)) if excursions_valid else None,
                    'medianExcursionErrorSemitones': float(np.median(excursions_valid)) if excursions_valid else None,
                    'excursionUnreliableOrMissing': len(excursions)-len(excursions_valid),
                    'voicedTargetUnvoicedFinalist': sum(r['targetPitch'].get('medianHz') is not None and
                        c.get('pitch', {}).get('medianHz') is None for r, c in present)}
    return result


def parse_models(values):
    result = {}
    for value in values:
        if '=' not in value:
            raise ValueError('Model must be NAME=PATH')
        name, path = value.split('=', 1)
        if not name or not name.replace('-', '').replace('_', '').isalnum() or name in result:
            raise ValueError('Model names must be unique safe names')
        path = Path(path).resolve()
        result[name] = path/'best.pt' if path.is_dir() else path
    return result


def validate_inputs(models, data_paths, renderer):
    """Validate every supplied dataset, not just the one used by an arm."""
    expected = {'featureVersion': VERSION, 'featureHash': FEATURE_HASH,
                'featureCodeHash': FEATURE_CODE_HASH, 'featureDim': DIM}
    excluded = set(); datasets = []
    actual = renderer.inventory['sourceHash']
    engines = [s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
    for path in data_paths:
        path = Path(path).resolve(); manifest = json.loads((path/'manifest.json').read_text())
        if not manifest.get('complete') or any(manifest.get(k) != v for k, v in expected.items()):
            raise ValueError('Dataset feature binding or completeness incompatible')
        if manifest.get('sourceHash') != actual:
            raise ValueError('Dataset DSP source differs from actual renderer')
        verify_dataset_files(path, manifest)
        for name in manifest['engines']:
            shard = json.loads((path/(name+'.json')).read_text())
            if shard.get('sourceHash') != actual or any(shard.get(k) != v for k, v in expected.items()):
                raise ValueError('Dataset shard feature/source binding incompatible: '+name)
            if shard['spec'] != renderer.specs[name]:
                raise ValueError('Dataset actual DSP schema differs: '+name)
            for row in shard['rows']:
                excluded.add(parameter_hash({'synth': name, 'params': row['params']}))
                excluded.add(control_hash(shard['spec'], row['params']))
        datasets.append({'path': str(path), 'manifestSha256': file_hash(path/'manifest.json'),
                         'sourceHash': actual, 'engines': manifest['engines']})
    hashes = {d['manifestSha256'] for d in datasets}
    for name, (_, metadata) in models.items():
        if metadata.get('dataManifestHash') not in hashes:
            raise ValueError('Model training data binding absent from supplied datasets: '+name)
        if metadata.get('sourceHash') != actual:
            raise ValueError('Model DSP source differs from actual renderer: '+name)
        if set(metadata['engines']) != set(engines) or metadata['specs'] != {n: renderer.specs[n] for n in engines}:
            raise ValueError('Benchmark models must cover all active actual DSP engines: '+name)
    return excluded, datasets, engines


def save_candidate(dest, role, row, target, source_hash):
    if row is None:
        return None
    wave = row['wave']; pitch = pitch_diagnostic(wave)
    path = dest/(role+'.wav')
    # FLOAT WAV preserves exactly the actual scored waveform and its timing.
    sf.write(path, wave, RATE, subtype='FLOAT')
    decoded, rate = sf.read(path, dtype='float32')
    if rate != RATE or not np.array_equal(decoded, wave):
        raise ValueError('Candidate WAV PCM replay mismatch')
    return {**serializable(row), 'sourceHash': source_hash, 'waveFile': str(path),
            'waveFileSha256': file_hash(path), 'audioHash': audio_hash(wave), 'audioSamples': len(wave),
            'pitch': pitch, 'pitchComparison': compare_pitch(target['targetPitch'], pitch, target['family'])}


def evaluate_target(item):
    config, target = item
    started = time.monotonic()
    torch.set_num_threads(1)
    dest = Path(config['output'])/target['id']
    wave, rate = sf.read(target['waveFile'], dtype='float32')
    if rate != RATE or audio_hash(wave) != target['audioHash']:
        raise ValueError('Target decoded PCM binding changed')
    record = {**target, 'arms': {}}
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        if renderer.inventory['sourceHash'] != target['sourceHash']:
            raise ValueError('DSP source changed during benchmark')
        original = OriginalBfxr(config['bfxrCheckpoint'], bfxr)
        if config.get('bfxrCheckpointSha256') and original.checkpoint_hash != config['bfxrCheckpointSha256']:
            raise ValueError('Original checkpoint changed during benchmark')
        objective = MatchObjective(wave)
        baseline = original.approximate(wave, objective, budget=config['bfxrBudget'], seed=target['evaluationSeed'])
        original_seconds = time.monotonic()-started
        frozen = FrozenOriginal(baseline, config['bfxrBudget'], target['evaluationSeed'], target_wave=wave)
        for name, path in config['models'].items():
            arm_started = time.monotonic()
            model, metadata = load_model(path)
            if metadata['checkpointHash'] != config['modelHashes'][name]:
                raise ValueError('Checkpoint changed during benchmark: '+name)
            evaluated = approximate(model, metadata, wave, renderer, frozen, starts=4,
                        budget=config['budget'], bfxr_budget=config['bfxrBudget'], seed=target['evaluationSeed'])
            known = [r for r in evaluated['allRaw'] if r['synth'] == target['sourceSynth']]
            roles = {'knownRaw': min(known, key=lambda r: r['score']) if known else None,
                     'unrestrictedRaw': evaluated['raw'], 'neuralRefined': evaluated['neural'],
                     'selected': evaluated['selected'], 'original': evaluated['original']}
            roles['selected']['controlReplay'] = exact_replay(roles['selected'], renderer, bfxr)
            arm_dest = dest/name; arm_dest.mkdir()
            saved = {role: save_candidate(arm_dest, role, row, target, target['sourceHash']) for role, row in roles.items()}
            # Retain all audible raw proposals, including candidates omitted by
            # the shortlist. Render failures remain explicit in the arm report.
            all_raw = [save_candidate(arm_dest, 'raw-'+str(i), row, target, target['sourceHash'])
                       for i, row in enumerate(evaluated['allRaw'])]
            all_refined = [save_candidate(arm_dest, 'refined-'+str(i), row, target, target['sourceHash'])
                           for i, row in enumerate(evaluated.get('allRefined', []))]
            record['arms'][name] = {'candidates': saved, 'allRaw': all_raw,
                'allRefined': all_refined,
                'failures': evaluated['failures'], 'evaluations': evaluated['evaluations'],
                'checkpointSha256': metadata['checkpointHash'], 'evaluationSeed': target['evaluationSeed'],
                'budgetPerRefinedStart': config['budget'], 'requestedRefinedStarts': 4,
                'actualRefinedStarts': len(all_refined),
                'originalSharedAcrossArms': True, 'bfxrBudget': config['bfxrBudget'],
                'originalSeconds': original_seconds, 'seconds': time.monotonic()-arm_started}
            record['seconds'] = time.monotonic()-started
            _json_write(dest/'report.json', record)
            print(json.dumps({'event': 'evaluated', 'target': target['id'], 'arm': name,
                  'selectedScore': saved['selected']['score'], 'seconds': record['seconds']}), flush=True)
    return record


def run(args):
    started = time.monotonic()
    if min(args.jobs, args.budget, args.bfxr_budget) < 1:
        raise ValueError('Jobs and budgets must be positive')
    output = Path(args.output).resolve()
    if output.exists():
        raise ValueError('Use a fresh immutable benchmark output directory')
    paths = parse_models(args.model)
    if not paths or not args.data:
        raise ValueError('At least one model and dataset required')
    loaded = {name: load_model(path) for name, path in paths.items()}
    model_hashes = {name: metadata['checkpointHash'] for name, (_, metadata) in loaded.items()
                    if 'checkpointHash' in metadata}
    # Fail training-data binding before creating output or starting a renderer.
    hashes = {file_hash(Path(path)/'manifest.json') for path in args.data}
    if any(metadata.get('dataManifestHash') not in hashes for _, metadata in loaded.values()):
        raise ValueError('Model training data binding absent from supplied datasets')
    torch.set_num_threads(1)
    with Renderer() as renderer:
        excluded, datasets, engines = validate_inputs(loaded, args.data, renderer)
        # Validate original checkpoint before creating artifacts, too.
        with BfxrRenderer(jobs=1) as bfxr:
            original_hash = OriginalBfxr(args.bfxr_checkpoint, bfxr).checkpoint_hash
        targets = create_targets(renderer, excluded, args.seed)
    if any(file_hash(paths[name]) != bound for name, bound in model_hashes.items()):
        raise ValueError('Checkpoint changed during benchmark preparation')
    if file_hash(args.bfxr_checkpoint) != original_hash:
        raise ValueError('Original checkpoint changed during benchmark preparation')
    output.mkdir(parents=True)
    stored = []
    for target in targets:
        dest = output/target['id']; dest.mkdir()
        path = dest/'target.wav'
        sf.write(path, target['wave'], RATE, subtype='FLOAT')
        pcm, rate = sf.read(path, dtype='float32')
        if rate != RATE or not np.array_equal(pcm, target['wave']):
            raise ValueError('Source WAV exact PCM binding failed')
        row = {k: v for k, v in target.items() if k != 'wave'}
        row.update(waveFile=str(path), waveFileSha256=file_hash(path))
        _json_write(dest/'source.json', row); stored.append(row)
    config = {'complete': False, 'output': str(output), 'models': {n: str(p) for n, p in paths.items()},
        'modelHashes': model_hashes, 'datasets': datasets,
        'bfxrCheckpoint': str(Path(args.bfxr_checkpoint).resolve()),
        'bfxrCheckpointSha256': original_hash, 'seed': args.seed,
        'budget': args.budget, 'bfxrBudget': args.bfxr_budget, 'jobs': args.jobs,
        'sourceHash': stored[0]['sourceHash'], 'benchmarkCodeSha256': file_hash(__file__),
        'scope': 'Fresh control holdouts and actual-audio calibrated pitch diagnostics; no human likeness claim; no loss-function comparison.'}
    _json_write(output/'target-manifest.json', {'metadata': config, 'targets': stored})
    items = [(config, target) for target in stored]
    if args.jobs == 1:
        records = [evaluate_target(item) for item in items]
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            records = list(pool.map(evaluate_target, items))
    # Detect changes in inputs during a long run before claiming completion.
    for dataset in datasets:
        path = Path(dataset['path'])
        if file_hash(path/'manifest.json') != dataset['manifestSha256']:
            raise ValueError('Dataset manifest changed during benchmark')
        verify_dataset_files(path, json.loads((path/'manifest.json').read_text()))
    if file_hash(args.bfxr_checkpoint) != config['bfxrCheckpointSha256']:
        raise ValueError('Original checkpoint changed during benchmark')
    summary = summarize(records, list(paths), engines)
    report = {'metadata': {**config, 'complete': True, 'seconds': time.monotonic()-started},
              'summary': summary, 'results': records}
    _json_write(output/'results.json', report)
    print(json.dumps({'event': 'complete', 'targets': len(records), 'summary': summary}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', action='append', required=True, metavar='NAME=PATH')
    parser.add_argument('--data', action='append', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--bfxr-checkpoint', required=True, type=Path)
    parser.add_argument('--seed', type=int, default=20261006)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--budget', type=int, default=128)
    parser.add_argument('--bfxr-budget', type=int, default=2000)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
