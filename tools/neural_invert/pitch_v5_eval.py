"""Actual-DSP comparison of frozen temporal-v3, pitch-v4 and pitch-v5.

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
from .pitch_v5_features import describe, FEATURE_HASH, FEATURE_CODE_HASH
from .temporal_eval import ENGINES, proposal_accounting, summarize_arm, verify_target


def descriptor_pitch(wave):
    """Full v5 voiced relative-time evidence; independent of model selection.

    These 48 descriptor frames are diagnostic samples, not independent pitch
    ground truth. Nulls preserve inactive/unvoiced gaps instead of stretching
    voiced-only samples across the whole gesture.
    """
    x = describe(wave)
    active = x[3840:3888] > .05
    voiced = active & (x[3936:3984] >= .6)
    hz = 55*np.exp2(7*x[3888:3936])
    fraction = float(voiced.sum()/max(1, active.sum()))
    reliable = bool(fraction >= .6 and voiced.sum() >= 3)
    values = 12*np.log2(hz[voiced])
    ids = np.flatnonzero(voiced)
    positions = np.linspace(0, 1, 48)
    delta = float(np.median(12*np.log2(hz[ids[-3:]]))-
                  np.median(12*np.log2(hz[ids[:3]]))) if reliable else None
    return {'medianHz': float(np.median(hz[voiced])) if reliable else None,
            'voicedFraction': fraction, 'reliable': reliable,
            'activeFrames': int(active.sum()), 'voicedFrames': int(voiced.sum()),
            'activeMask': active.tolist(), 'voicedMask': voiced.tolist(),
            'contourHz': [float(h) if v else None for h,v in zip(hz, voiced)],
            'contourTime': positions.tolist(),
            'spanSemitones': float(np.ptp(values)) if reliable else None,
            'startToEndSemitones': delta,
            'directionSupport': {'startFrameIndices': ids[:3].tolist(),
                'endFrameIndices': ids[-3:].tolist(),
                'startRelativePositions': positions[ids[:3]].tolist(),
                'endRelativePositions': positions[ids[-3:]].tolist()} if reliable else None,
            'directionMeaning': 'direction and startToEndSemitones describe voiced-span motion between the median log pitches of the first and last three voiced frames; they do not establish motion at whole-sound endpoints.',
            'direction': (1 if delta > .5 else -1 if delta < -.5 else 0) if delta is not None else None,
            'meaning': 'V5 descriptor diagnostic on 48 active-sound relative-time positions; nulls are inactive or unvoiced. Not independent ground truth, likeness certification, or a selection criterion.'}


def compare_descriptor_pitch(target, candidate):
    """Compare all aligned voiced frames; missing frames cannot pass tolerance."""
    errors = [float(abs(12*np.log2(b/a))) if a is not None and b is not None else None
              for a,b in zip(target['contourHz'], candidate['contourHz'])]
    pairs = [e for e in errors if e is not None]
    active = target['activeFrames']
    passing = sum(e is not None and e <= 1 for e in errors)
    a,b = target['medianHz'], candidate['medianHz']
    sa,sb = target['spanSemitones'], candidate['spanSemitones']
    return {'medianErrorSemitones': float(abs(12*np.log2(b/a))) if a and b else None,
            'contourErrorSemitones': float(np.mean(pairs)) if pairs else None,
            'contourMaxErrorSemitones': float(max(pairs)) if pairs else None,
            'contourFrameErrorsSemitones': errors, 'reliableContourPairs': len(pairs),
            'spanErrorSemitones': float(abs(sb-sa)) if sa is not None and sb is not None else None,
            'directionMatches': bool(target['direction'] == candidate['direction'])
                if target['direction'] is not None and candidate['direction'] is not None else None,
            'targetActiveFrames': active,
            'activeFramesWithinOneSemitone': passing,
            'activeFrameWithinOneSemitoneFraction': float(passing/active) if active else None,
            'directionMeaning': 'Matches voiced-span direction on the reported support frames of each sound; not whole-sound endpoint evidence.',
            'meaning': 'Diagnostic only. Tolerance denominator includes every target-active frame; unvoiced or missing candidate frames do not pass. Relative-time alignment does not measure duration agreement.'}


def diagnostic_summary(rows):
    selected = [r['selected']['v5PitchComparison'] for r in rows if r['selected']]
    statics = [r['selected']['v5PitchComparison'] if r['selected'] else None
               for r in rows if r['family'] == 'static']
    moving = [r['selected']['v5PitchComparison'] if r['selected'] else None
              for r in rows if r['family'] == 'moving']
    def average(key, values):
        valid = [c[key] for c in values if c and c[key] is not None]
        return float(np.mean(valid)) if valid else None
    return {'staticTotal': len(statics),
            'staticMedianWithinOneSemitone': sum(c is not None and c['medianErrorSemitones'] is not None
                                                 and c['medianErrorSemitones'] <= 1 for c in statics),
            'movingTotal': len(moving),
            'movingDirectionMatches': sum(c is not None and c['directionMatches'] is True for c in moving),
            'meanMovingContourErrorSemitones': average('contourErrorSemitones', moving),
            'meanMovingSpanErrorSemitones': average('spanErrorSemitones', moving),
            'meanActiveFrameWithinOneSemitoneFraction': average('activeFrameWithinOneSemitoneFraction', selected),
            'missingSelections': sum(r['selected'] is None for r in rows),
            'unpairedContourSelections': sum(c['reliableContourPairs'] == 0 for c in selected),
            'meaning': 'V5 diagnostics applied identically to every arm. movingDirectionMatches counts voiced-span direction, not whole-sound endpoint motion. Median and direction agreement alone cannot establish accurate gesture or human likeness.'}


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
            'legacyPitch': pitch, 'legacyPitchComparison': compare_pitch(target_pitch, pitch, family),
            'v5Pitch': corrected, 'v5PitchComparison': compare_descriptor_pitch(corrected_target, corrected),
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
    elif version == 'pitch-v5':
        from .pitch_v5_temporal import load_temporal, predict_temporal
    else:
        raise ValueError('Unknown expert version')
    return {name: load_temporal(Path(root)/name) for name in ENGINES}, predict_temporal


def proposals(bundle, wave, renderer, count=4):
    experts, predict = bundle
    return [candidate for model, metadata in experts.values()
            for candidate in predict(model, metadata, wave, renderer, count=count)]


def benchmark(benchmark_path, old_root, v4_root, new_root, output, count=4):
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
               'pitch-v4': load_experts(v4_root, 'pitch-v4'),
               'pitch-v5': load_experts(new_root, 'pitch-v5')}
    bindings = {version: {name: {k: meta[k] for k in
                ('checkpointHash', 'dataManifestHash', 'featureHash', 'featureCodeHash', 'sourceHash')}
                for name, (_, meta) in bundle[0].items()} for version, bundle in bundles.items()}
    source_hashes = {m['sourceHash'] for group in bindings.values() for m in group.values()}
    if len(source_hashes) != 1:
        raise ValueError('Expert DSP source hashes disagree')
    code_paths = ['pitch_v5_gallery.py', 'pitch_v5_eval.py', 'pitch_v5_features.py', 'pitch_v5_temporal.py', 'pitch_v5_data.py',
                  'pitch_features.py', 'pitch_temporal.py', 'pitch_data.py', 'temporal.py', 'train.py', 'acoustic.py',
                  'features.py', 'temporal_eval.py', 'benchmark.py', 'evaluate.py', 'data.py',
                  'schema.py', 'model.py', 'predict.py']
    code_hashes = {name: file_hash(Path(__file__).with_name(name)) for name in code_paths}
    code_hashes.update({str(p): file_hash(p) for p in (Path(__file__).parents[1]/'match').glob('*.py')})
    metadata = {'complete': False, 'experiment': 'pitch-initial-lobe-v5',
        'benchmarkPath': str(Path(benchmark_path).resolve()), 'benchmarkSha256': file_hash(benchmark_path),
        'models': bindings, 'modelDirectories': {'temporal-v3': str(Path(old_root).resolve()), 'pitch-v4': str(Path(v4_root).resolve()), 'pitch-v5': str(Path(new_root).resolve())},
        'sourceHash': next(iter(source_hashes)), 'candidateBudgetPerEngine': count,
        'candidateBudgetTotal': count*len(ENGINES), 'codeHashes': code_hashes,
        'v5DiagnosticFeatureHash': FEATURE_HASH, 'v5DiagnosticCodeHash': FEATURE_CODE_HASH,
        'diagnosticPolicy': 'V5 full voiced relative-time contours, median, span and active-frame tolerance for all arms; legacy metrics retained separately. Never used to select or reweight outputs.',
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
                'legacyTargetPitch': pitch_diagnostic(wave), 'v5TargetPitch': descriptor_pitch(wave),
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
            legacy = summarize_arm(rows)
            summary[version][label] = {'meanMatchObjective': legacy['meanMatchObjective'],
                'missingCandidates': legacy['missingCandidates'], 'missingRenderedSlots': legacy['missingRenderedSlots'],
                'legacy': legacy, 'v5': diagnostic_summary(rows), **conservative_pitch_summary(rows)}
            summary[version][label]['improvedVersusTemporalV3'] = sum(
                bool(r['arms'][version][selection] and r['arms']['temporal-v3'][selection]) and
                r['arms'][version][selection]['score'] < r['arms']['temporal-v3'][selection]['score'] for r in records)
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != metadata['sourceHash']:
            raise ValueError('DSP changed during evaluation')
    if any(file_hash(Path(__file__).with_name(name)) != code_hashes[name] for name in code_paths):
        raise ValueError('Code changed during evaluation')
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
    parser.add_argument('--v4-root', required=True)
    parser.add_argument('--new-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    benchmark(args.benchmark, args.old_root, args.v4_root, args.new_root, args.output)


if __name__ == '__main__':
    main()
