"""Actual-render diagnostics and guarded refinement for temporal inverse trials.

Numerical checks diagnose pitch/gesture failures; they do not certify likeness.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import audio_hash, compare_pitch, pitch_diagnostic
from .data import _json_write, file_hash
from .evaluate import mutate_controls, rendered_candidates, serializable
from .features import describe

ENGINES = ('Bfxr', 'Transfxr', 'Pluckr')
GUARD_POLICY = {'version': 'actual-pitch-gesture-v1', 'targetVoicing': .75,
                'estimatorAgreementSemitones': 3., 'preservedPitchSemitones': 1.,
                'scope': 'Experimental diagnostic safeguard; requires human evaluation.'}


def pitch_consensus(primary, secondary):
    a, b = primary.get('medianHz'), secondary.get('medianHz')
    return bool(primary.get('reliable') and a and b and
                min(primary['voicedFraction'], secondary['voicedFraction']) >= .75 and
                abs(12*np.log2(a/b)) <= 3.)


def target_diagnostics(wave):
    primary = pitch_diagnostic(wave)
    feature = describe(wave)
    envelope, pitch, voice = feature[3840:3888], feature[3888:3936], feature[3936:3984]
    active = envelope > .05
    voiced = active & (voice >= .6)
    secondary = {'voicedFraction': float(voiced.sum()/max(1, active.sum())),
                 'medianHz': float(np.median(55*2**(7*pitch[voiced]))) if voiced.any() else None}
    return {**primary, 'secondary': secondary, 'guardReliable': pitch_consensus(primary, secondary)}


def guard_accepts(target, before, after):
    """Preserve already matched reliable register and rise/fall/stationary motion."""
    if not target['guardReliable']:
        return True
    hz = target['medianHz']
    before_hz, after_hz = before.get('medianHz'), after.get('medianHz')
    if before.get('reliable') and before_hz:
        if not after.get('reliable') or not after_hz:
            return False
        if abs(12*np.log2(before_hz/hz)) <= 1. and abs(12*np.log2(after_hz/hz)) > 1.:
            return False
        direction = target.get('direction')
        if direction is not None and before.get('direction') == direction and after.get('direction') != direction:
            return False
    return True


def refine_guarded(row, renderer, objective, target, budget=256, seed=0):
    if budget < 0:
        raise ValueError('Refinement budget must be nonnegative')
    rng = np.random.default_rng(seed)
    best = deepcopy(row)
    if not np.isfinite(best['score']):
        raise ValueError('Initial refinement score must be finite')
    before_pitch = pitch_diagnostic(best['wave'])
    trace, failures, rejected = [], 0, 0
    for step in range(budget):
        sigma = (.15, .07, .025, .01)[min(3, step*4//max(1, budget))]
        proposal = {**best, 'params': mutate_controls(best['params'], renderer.specs[best['synth']], rng, sigma)}
        accepted, errors = rendered_candidates([proposal], renderer, objective)
        failures += len(errors)
        if not accepted:
            continue
        candidate = accepted[0]
        if not np.isfinite(candidate['score']):
            failures += 1
            continue
        if not candidate['score'] < best['score']:
            continue
        candidate_pitch = pitch_diagnostic(candidate['wave'])
        allowed = guard_accepts(target, before_pitch, candidate_pitch)
        trace.append({'step': step, 'params': candidate['params'], 'seed': candidate['seed'],
                      'score': candidate['score'], 'pitch': candidate_pitch, 'accepted': allowed,
                      'audioHash': audio_hash(candidate['wave'])})
        if allowed:
            best, before_pitch = candidate, candidate_pitch
        else:
            rejected += 1
    best['provenance'] = {**best.get('provenance', {}), 'refinement': {
        'method': 'actual-DSP-guarded-local-search', 'budget': budget, 'seed': seed,
        'initialScore': row['score'], 'finalScore': best['score'], 'renderFailures': failures,
        'guardRejections': rejected, 'policy': GUARD_POLICY, 'improvingProposalTrace': trace}}
    return best


def verify_target(row, wave, renderer):
    if row['sourceHash'] != renderer.inventory['sourceHash']:
        raise ValueError('Benchmark DSP differs')
    canonical, replay = renderer.render(row['sourceSynth'], row['sourceParams'], row['sourceSeed'])
    if canonical != row['sourceParams'] or audio_hash(wave) != row['audioHash'] or not np.array_equal(wave, replay):
        raise ValueError('Benchmark controls or PCM replay differs')


def summarize_arm(rows):
    statics = [r['selected']['pitchComparison'].get('absolutePitchErrorSemitones')
               for r in rows if r['family'] == 'static' and r['selected']]
    moving = [r['selected']['pitchComparison'] for r in rows if r['family'] == 'moving' and r['selected']]
    return {'meanMatchObjective': float(np.mean([r['selected']['score'] for r in rows if r['selected']]))
            if any(r['selected'] for r in rows) else None,
            'staticWithinOneSemitone': sum(e is not None and e <= 1. for e in statics),
            'staticTotal': sum(r['family'] == 'static' for r in rows),
            'movingDirectionMatches': sum(r.get('directionMatches') is True for r in moving),
            'movingTotal': sum(r['family'] == 'moving' for r in rows),
            'missingCandidates': sum(r['selected'] is None for r in rows),
            'missingRenderedSlots': sum(r.get('accounting', {}).get('missingRendered', 0) for r in rows)}


def proposal_accounting(expected, proposed, rendered):
    if not 0 <= rendered <= proposed <= expected:
        raise ValueError('Invalid candidate budget accounting')
    return {'expected': expected, 'proposed': proposed, 'rendered': rendered,
            'missingProposals': expected-proposed, 'failedRenders': proposed-rendered,
            'missingRendered': expected-rendered}


def load_experts(root):
    from .temporal import load_temporal
    return {name: load_temporal(Path(root)/name) for name in ENGINES}


def proposals(experts, wave, renderer, count=4):
    from .temporal import predict_temporal
    return [candidate for model, metadata in experts.values()
            for candidate in predict_temporal(model, metadata, wave, renderer, count=count)]


def benchmark(benchmark_path, models, output, old_model, count=4):
    """Compare four raw proposals per source engine; no refinement or target hints."""
    from .predict import load_model, predict
    if count < 1 or Path(output).exists():
        raise ValueError('Positive candidate count and fresh output required')
    torch.set_num_threads(1)
    output = Path(output)
    source = json.loads(Path(benchmark_path).read_text())
    loaded = {label: load_experts(path) for label, path in models.items()}
    old, old_metadata = load_model(old_model)
    old_metadata = {**old_metadata, 'engines': list(ENGINES)}
    rows = [r for r in source['results'] if r['sourceSynth'] in ENGINES]
    output.mkdir(parents=True)
    metadata = {'complete': False, 'benchmarkSha256': file_hash(benchmark_path),
                'codeSha256': file_hash(__file__), 'candidateBudgetPerEngine': count,
                'oldCheckpointSha256': file_hash(old_model), 'engines': list(ENGINES),
                'scope': 'Fixed development probes, not held-out human likeness evaluation.',
                'modelHashes': {label: {name: meta['checkpointHash'] for name, (_, meta) in experts.items()}
                                for label, experts in loaded.items()}}
    _json_write(output/'manifest.json', metadata)
    records = []
    with Renderer() as renderer:
        metadata['sourceHash'] = renderer.inventory['sourceHash']
        for target in rows:
            if file_hash(target['waveFile']) != target['waveFileSha256']:
                raise ValueError('Frozen target WAV changed')
            wave, rate = sf.read(target['waveFile'], dtype='float32')
            if rate != 44100:
                raise ValueError('Target rate differs')
            verify_target(target, wave, renderer)
            objective, pitch = MatchObjective(wave), pitch_diagnostic(wave)
            record = {'id': target['id'], 'family': target['family'], 'sourceSynth': target['sourceSynth'],
                      'referenceAudioHash': audio_hash(wave), 'arms': {}}
            options = {'v2': predict(old, old_metadata, wave, renderer, per_synth=count)}
            options.update({label: proposals(experts, wave, renderer, count) for label, experts in loaded.items()})
            dest = output/target['id']; dest.mkdir()
            for label, candidates in options.items():
                # Inputs contain no source-synth hint; source-engine filtering is diagnostic only.
                actual, errors = rendered_candidates(candidates, renderer, objective)
                saved = []
                for i, c in enumerate(actual):
                    canonical, replay = renderer.render(c['synth'], c['params'], c['seed'])
                    if canonical != c['params'] or not np.array_equal(replay, c['wave']):
                        raise ValueError('Candidate actual-DSP replay differs')
                    path = dest/f'{label}-{i}.wav'
                    sf.write(path, c['wave'], 44100, subtype='FLOAT')
                    decoded, _ = sf.read(path, dtype='float32')
                    if not np.array_equal(decoded, c['wave']):
                        raise ValueError('Saved candidate differs from scored float PCM')
                    cp = pitch_diagnostic(c['wave'])
                    saved.append({**serializable(c), 'audioHash': audio_hash(c['wave']),
                                  'waveFile': str(path.resolve()), 'waveFileSha256': file_hash(path),
                                  'pitch': cp, 'pitchComparison': compare_pitch(pitch, cp, target['family'])})
                known = [c for c in saved if c['synth'] == target['sourceSynth']]
                accounting = proposal_accounting(count,
                    sum(c['synth'] == target['sourceSynth'] for c in candidates), len(known))
                if accounting['missingProposals']:
                    errors.append({'synth': target['sourceSynth'], 'error': 'Missing proposal slots',
                                   'count': accounting['missingProposals']})
                record['arms'][label] = {'candidates': saved, 'failures': errors,
                    'accounting': accounting,
                    'selected': min(known, key=lambda c: c['score']) if known else None,
                    'unrestrictedSelected': min(saved, key=lambda c: c['score']) if saved else None}
            records.append(record)
            _json_write(dest/'report.json', record)
            print(json.dumps({'id': target['id'], 'scores': {k: v['selected']['score'] if v['selected'] else None
                  for k, v in record['arms'].items()}}), flush=True)
        if renderer_hash() != metadata['sourceHash']:
            raise ValueError('DSP changed during evaluation')
    summary = {}
    for label in ('v2', *models):
        arm = [{**r['arms'][label], 'family': r['family']} for r in records]
        summary[label] = summarize_arm(arm)
        summary[label]['improvedVersusV2'] = sum(
            bool(r['arms'][label]['selected'] and r['arms']['v2']['selected']) and
            r['arms'][label]['selected']['score'] < r['arms']['v2']['selected']['score'] for r in records)
    metadata['complete'] = True
    result = {'metadata': metadata, 'summary': summary, 'results': records}
    _json_write(output/'results.json', result)
    _json_write(output/'manifest.json', metadata)
    print(json.dumps(summary), flush=True)
    return result


def renderer_hash():
    with Renderer() as renderer:
        return renderer.inventory['sourceHash']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--old-model', type=Path, required=True)
    parser.add_argument('--model', action='append', required=True, help='label=directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    models = dict(item.split('=', 1) for item in args.model)
    if len(models) != len(args.model) or 'v2' in models or any(not k.isidentifier() for k in models):
        parser.error('Unique identifier labels required')
    benchmark(args.benchmark, models, args.output, args.old_model)


if __name__ == '__main__':
    main()
