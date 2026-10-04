"""Actual-DSP comparison of frozen temporal-v3 and pitch-only retraining.

The source synth is used only in a separately labelled diagnostic selection.
Unrestricted selection sees the same four proposals from every expert.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import audio_hash, compare_pitch, pitch_diagnostic
from .data import _json_write, file_hash
from .evaluate import rendered_candidates, serializable
from .pitch_features import describe, FEATURE_HASH, FEATURE_CODE_HASH
from .temporal_eval import ENGINES, proposal_accounting, summarize_arm, verify_target


def descriptor_pitch(wave):
    """Supplementary corrected-input diagnostic, never used to select output."""
    x = describe(wave)
    active = x[3840:3888] > .05
    voiced = active & (x[3936:3984] >= .6)
    fraction = float(voiced.sum()/max(1, active.sum()))
    reliable = bool(fraction >= .6 and voiced.sum() >= 3)
    return {'medianHz': float(np.median(55*np.exp2(7*x[3888:3936][voiced]))) if reliable else None,
            'voicedFraction': fraction, 'reliable': reliable,
            'meaning': 'Corrected descriptor diagnostic; not independent ground truth or selection criterion.'}


def conservative_pitch_summary(rows):
    """Keep the known limited old tracker from certifying octave errors alone."""
    statics = [r['selected'] for r in rows if r['family'] == 'static']
    pairs = [(c['pitchComparison'].get('absolutePitchErrorSemitones'),
              c.get('correctedPitchErrorSemitones')) if c else (None,None) for c in statics]
    return {'staticWithinOneSemitoneCorrected': sum(b is not None and b <= 1 for a,b in pairs),
            'staticWithinOneSemitoneBoth': sum(a is not None and b is not None and a <= 1 and b <= 1 for a,b in pairs),
            'staticTrackerPassDisagreements': sum(a is not None and b is not None and (a <= 1) != (b <= 1) for a,b in pairs),
            'staticCorrectedUnreliableOrMissing': sum(b is None for a,b in pairs)}


def evaluate_candidates(candidates, target, source_synth, family, renderer, output, count=4):
    """Save every audible actual render and account for every missing slot."""
    if (type(count) is not int or count < 1 or source_synth not in ENGINES
            or any(c['synth'] not in ENGINES for c in candidates)
            or any(sum(c['synth'] == n for c in candidates) > count for n in ENGINES)):
        raise ValueError('Invalid candidate budget or engine')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    objective, target_pitch = MatchObjective(target), pitch_diagnostic(target)
    corrected_target = descriptor_pitch(target)
    actual, failures = rendered_candidates(candidates, renderer, objective)
    saved = []
    for index, row in enumerate(actual):
        if not np.isfinite(row['score']):
            failures.append({'synth': row['synth'], 'error': 'Nonfinite candidate score'})
            continue
        canonical, replay = renderer.render(row['synth'], row['params'], row['seed'])
        if canonical != row['params'] or audio_hash(replay) != audio_hash(row['wave']):
            raise ValueError('Candidate actual-DSP replay differs')
        path = output/f'{index:02d}.wav'
        sf.write(path, replay, 44100, subtype='FLOAT')
        decoded, rate = sf.read(path, dtype='float32')
        if rate != 44100 or audio_hash(decoded) != audio_hash(replay):
            raise ValueError('Saved candidate differs from scored float PCM')
        pitch = pitch_diagnostic(replay)
        corrected = descriptor_pitch(replay)
        a,b = corrected_target['medianHz'],corrected['medianHz']
        corrected_error = float(abs(12*np.log2(b/a))) if family == 'static' and a and b else None
        saved.append({**serializable(row), 'audioHash': audio_hash(replay),
            'waveFile': str(path.resolve()), 'waveFileSha256': file_hash(path),
            'pitch': pitch, 'pitchComparison': compare_pitch(target_pitch, pitch, family),
            'correctedInputPitch': corrected, 'correctedPitchErrorSemitones': corrected_error})
    accounting = {name: proposal_accounting(count, sum(c['synth'] == name for c in candidates),
                                            sum(c['synth'] == name for c in saved)) for name in ENGINES}
    known = [c for c in saved if c['synth'] == source_synth]
    return {'proposals': candidates, 'candidates': saved, 'failures': failures,
            'accounting': accounting,
            'totalAccounting': proposal_accounting(count*len(ENGINES), len(candidates), len(saved)),
            'selected': min(known, key=lambda c: c['score']) if known else None,
            'unrestrictedSelected': min(saved, key=lambda c: c['score']) if saved else None}


def load_experts(root, version):
    if version == 'temporal-v3':
        from .temporal import load_temporal, predict_temporal
    elif version == 'pitch-v4':
        from .pitch_temporal import load_temporal, predict_temporal
    else:
        raise ValueError('Unknown expert version')
    return {name: load_temporal(Path(root)/name) for name in ENGINES}, predict_temporal


def proposals(bundle, wave, renderer, count=4):
    experts, predict = bundle
    return [candidate for model, metadata in experts.values()
            for candidate in predict(model, metadata, wave, renderer, count=count)]


def benchmark(benchmark_path, old_root, new_root, output, count=4):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Comparison output must be fresh')
    if type(count) is not int or count < 1:
        raise ValueError('Positive integer candidate budget required')
    torch.set_num_threads(1)
    source = json.loads(Path(benchmark_path).read_text())
    targets = [row for row in source['results'] if row['sourceSynth'] in ENGINES]
    if not targets or len({r['id'] for r in targets}) != len(targets):
        raise ValueError('Nonempty unique targets required')
    if any(Path(r['id']).name != r['id'] or r['id'] in ('.', '..') for r in targets):
        raise ValueError('Unsafe target identifier')
    bundles = {'temporal-v3': load_experts(old_root, 'temporal-v3'),
               'pitch-v4': load_experts(new_root, 'pitch-v4')}
    bindings = {version: {name: {k: meta[k] for k in
                ('checkpointHash', 'dataManifestHash', 'featureHash', 'featureCodeHash', 'sourceHash')}
                for name, (_, meta) in bundle[0].items()} for version, bundle in bundles.items()}
    source_hashes = {m['sourceHash'] for group in bindings.values() for m in group.values()}
    if len(source_hashes) != 1:
        raise ValueError('Expert DSP source hashes disagree')
    code_paths = ['pitch_eval.py', 'temporal_eval.py', 'benchmark.py', 'evaluate.py', 'data.py', 'pitch_features.py']
    code_hashes = {name: file_hash(Path(__file__).with_name(name)) for name in code_paths}
    code_hashes.update({str(p): file_hash(p) for p in (Path(__file__).parents[1]/'match').glob('*.py')})
    metadata = {'complete': False, 'experiment': 'pitch-input-only-v4',
        'benchmarkPath': str(Path(benchmark_path).resolve()), 'benchmarkSha256': file_hash(benchmark_path),
        'models': bindings, 'modelDirectories': {'temporal-v3': str(Path(old_root).resolve()), 'pitch-v4': str(Path(new_root).resolve())},
        'sourceHash': next(iter(source_hashes)), 'candidateBudgetPerEngine': count,
        'candidateBudgetTotal': count*len(ENGINES), 'codeHashes': code_hashes,
        'correctedDiagnosticFeatureHash': FEATURE_HASH, 'correctedDiagnosticCodeHash': FEATURE_CODE_HASH,
        'scope': 'Fixed development probes, including sparse upper-register coverage; not independent generalization or human likeness.',
        'selection': 'Unchanged MatchObjective over actual DSP float audio; source-engine and unrestricted summaries are separate.'}
    output.mkdir(parents=True)
    _json_write(output/'manifest.json', metadata)
    records = []
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('Evaluation DSP differs from training')
        for target in targets:
            if file_hash(target['waveFile']) != target['waveFileSha256']:
                raise ValueError('Frozen target WAV changed')
            wave, rate = sf.read(target['waveFile'], dtype='float32')
            if rate != 44100:
                raise ValueError('Target sample rate differs')
            verify_target(target, wave, renderer)
            record = {'id': target['id'], 'family': target['family'], 'sourceSynth': target['sourceSynth'],
                'sourceParams': target['sourceParams'], 'sourceSeed': target['sourceSeed'],
                'referenceAudioHash': audio_hash(wave), 'referenceWaveFile': target['waveFile'],
                'referenceWaveFileSha256': target['waveFileSha256'], 'targetPitch': pitch_diagnostic(wave),
                'correctedInputPitch': descriptor_pitch(wave), 'arms': {}}
            for version, bundle in bundles.items():
                predicted = proposals(bundle, wave, renderer, count)
                record['arms'][version] = evaluate_candidates(predicted, wave, target['sourceSynth'],
                    target['family'], renderer, output/target['id']/version, count)
            records.append(record)
            _json_write(output/target['id']/'report.json', record)
            print(json.dumps({'id': target['id'], 'scores': {k: {selection: v[selection]['score'] if v[selection] else None
                for selection in ('selected', 'unrestrictedSelected')} for k, v in record['arms'].items()}}), flush=True)
    summary = {}
    for version in bundles:
        summary[version] = {}
        for label, selection in (('sourceEngine', 'selected'), ('unrestricted', 'unrestrictedSelected')):
            rows = [{**r['arms'][version], 'family': r['family'], 'selected': r['arms'][version][selection],
                     'accounting': r['arms'][version]['accounting'][r['sourceSynth']] if label == 'sourceEngine'
                                   else r['arms'][version]['totalAccounting']} for r in records]
            summary[version][label] = {**summarize_arm(rows), **conservative_pitch_summary(rows)}
            summary[version][label]['improvedVersusTemporalV3'] = sum(
                bool(r['arms'][version][selection] and r['arms']['temporal-v3'][selection]) and
                r['arms'][version][selection]['score'] < r['arms']['temporal-v3'][selection]['score'] for r in records)
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('DSP changed during evaluation')
    metadata['complete'] = True
    result = {'metadata': metadata, 'summary': summary, 'results': records}
    _json_write(output/'results.json', result)
    _json_write(output/'manifest.json', metadata)
    print(json.dumps(summary), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', required=True)
    parser.add_argument('--old-root', required=True)
    parser.add_argument('--new-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    benchmark(args.benchmark, args.old_root, args.new_root, args.output)


if __name__ == '__main__':
    main()
