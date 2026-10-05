"""Replay the bounded calibration experiment and apply its predeclared gate."""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash
from neural_invert.pitch_calibration import POLICY, select_candidates
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_wave(row):
    path = row['waveFile']
    require(file_hash(path) == row['waveFileSha256'], 'Changed WAV: '+path)
    wave, rate = sf.read(path, dtype='float32')
    require(rate == 44100 and wave.ndim == 1 and wave.size > 0, 'Invalid WAV: '+path)
    require(audio_hash(wave) == row['audioHash'], 'Changed PCM: '+path)
    return wave


def same_candidate(a, b):
    return all(a[k] == b[k] for k in ('synth', 'params', 'seed', 'audioHash'))


def evidence(row, wave, target, objective):
    pitch = descriptor_pitch(wave)
    require(row['v5Pitch'] == pitch, 'Pitch evidence differs')
    require(row['v5PitchComparison'] == compare_descriptor_pitch(target, pitch),
            'Pitch comparison differs')
    require(abs(objective.score(wave)-row['score']) < 1e-6, 'Objective differs')


def audit_report(path, renderer):
    report = json.loads(path.read_text())
    meta = report['metadata']
    require(meta['complete'], 'Incomplete calibration report')
    require(meta['policy'] == POLICY, 'Calibration policy differs')
    require(meta['sourceHash'] == renderer.inventory['sourceHash'], 'DSP differs')
    require(json.loads((path.parent/'manifest.json').read_text()) == meta, 'Manifest differs')
    for group in ('inputBindings', 'outputBindings'):
        for filename, digest in meta[group].items():
            require(file_hash(filename) == digest, 'Changed bound artifact: '+filename)
    require(file_hash(meta['sourceReportPath']) == meta['sourceReportSha256'], 'Source report differs')
    frozen = json.loads(Path(__file__).with_name('pitch-v5-comparison.json').read_text())
    require(meta['sourceReportSha256'] in
            {r['reportSha256'] for r in frozen['reports'].values()},
            'Source report is not a previously audited frozen comparison')
    for filename, digest in meta['codeHashes'].items():
        code = Path(filename)
        if not code.is_absolute() and not code.is_file():
            code = Path(__file__).resolve().parents[2]/'neural_invert'/code
        require(file_hash(code) == digest, 'Calibration code differs: '+str(code))
    source = json.loads(Path(meta['sourceReportPath']).read_text())
    require([r['id'] for r in source['results']] == [r['id'] for r in report['results']],
            'Target population or ordering differs')
    compact, rendered = [], 0
    for row, old in zip(report['results'], source['results']):
        require(all(row[k] == old[k] for k in ('id', 'family', 'sourceSynth',
                    'sourceParams', 'sourceSeed', 'referenceAudioHash',
                    'referenceWaveFile', 'referenceWaveFileSha256')), 'Frozen target changed')
        target = read_wave(dict(waveFile=row['referenceWaveFile'],
            waveFileSha256=row['referenceWaveFileSha256'], audioHash=row['referenceAudioHash']))
        params, replay = renderer.render(row['sourceSynth'], row['sourceParams'], row['sourceSeed'])
        require(params == row['sourceParams'] and np.array_equal(target, replay), 'Target replay differs')
        target_pitch, objective = descriptor_pitch(target), MatchObjective(target)
        require(target_pitch == row['v5TargetPitch'], 'Target diagnostic differs')
        originals, accepted = [], []
        old_candidates = old['arms']['temporal-v3']['candidates']
        require(len(row['originals']) == len(old_candidates) == 12, 'Missing originals')
        for c, prior in zip(row['originals'], old_candidates):
            require(same_candidate(c, prior), 'Original candidate replaced')
            wave = read_wave(c)
            params, replay = renderer.render(c['synth'], c['params'], c['seed'])
            rendered += 1
            require(params == c['params'] and np.array_equal(wave, replay), 'Original replay differs')
            evidence(c, wave, target_pitch, objective)
            originals.append({**c, 'wave': wave})
        extra = failures = 0
        require(len(row['calibrations']) == 12, 'Missing calibration records')
        for index, calibration in enumerate(row['calibrations']):
            require(calibration['sourceCandidateIndex'] == index, 'Calibration ordering differs')
            attempts = calibration['attempts']
            require(len({a['step'] for a in attempts}) == len(attempts), 'Duplicated attempt step')
            count = sum(a['renderCount'] for a in attempts)
            require(count == calibration['additionalRenderCount'] and count <= 3,
                    'Additional render budget differs')
            extra += count
            journals = sorted((path.parent/row['id']/f'candidate-{index:02d}').glob('*.json'))
            require(len(journals) == 1+count, 'Persisted renderer call count differs')
            calls = [json.loads(p.read_text()) for p in journals]
            require(calls[0]['role'] == 'original_validation' and calls[0]['status'] == 'validated',
                    'Missing original validation journal')
            require(all(calls[0][k] == originals[index][k] for k in ('synth', 'seed', 'audioHash')),
                    'Original journal identity differs')
            call_index = 1
            for attempt in attempts:
                require(attempt['renderCount'] == int(attempt['rendered']), 'Attempt count differs')
                if not attempt['rendered']:
                    require(attempt['reason'] == 'bounds_unchanged', 'Unexplained unrendered attempt')
                    continue
                call = calls[call_index]
                call_index += 1
                require(all(call[k] == attempt[k] for k in ('synth', 'seed', 'requestedParams')),
                        'Attempt journal request differs')
                require(call['sourceCandidateIndex'] == index and call['renderCount'] == 1,
                        'Attempt journal count differs')
                require((call['status'] == 'render_error') == (attempt['reason'] == 'render_error'),
                        'Attempt journal failure differs')
                if attempt['reason'] != 'render_error':
                    require(all(call[k] == attempt[k] for k in ('canonicalParams', 'audioHash')),
                            'Attempt journal result differs')
                try:
                    params, replay = renderer.render(attempt['synth'], attempt['requestedParams'], attempt['seed'])
                except (ValueError, RuntimeError, OSError):
                    require(attempt['reason'] == 'render_error', 'Unexpected replay failure')
                    failures += 1
                    rendered += 1
                    continue
                rendered += 1
                require(attempt['reason'] != 'render_error', 'Recorded render failure does not replay')
                require(params == attempt['canonicalParams'], 'Attempt controls differ')
                require(audio_hash(replay) == attempt['audioHash'], 'Attempt PCM differs')
                if 'waveFile' in attempt:
                    wave = read_wave(attempt)
                    require(np.array_equal(replay, wave), 'Attempt WAV differs')
                else:
                    artifact = attempt['failureArtifact']
                    artifact_path = artifact['path']
                    require(file_hash(artifact_path) == artifact['sha256'], 'Failure artifact differs')
                    wave = np.load(artifact_path, allow_pickle=False)
                    require(np.array_equal(replay, wave, equal_nan=True), 'Failure array differs')
                if 'score' in attempt:
                    evidence(attempt, replay, target_pitch, objective)
        require(extra <= 36 and extra == row['accounting']['additionalRenderCount'], 'Target render budget differs')
        require(failures == row['accounting']['failedRenderCalls'], 'Failure accounting differs')
        require(row['accounting']['originalValidationReplays'] == 12, 'Original replay accounting differs')
        expected_accepted = {(index, attempt['step']): attempt
            for index, calibration in enumerate(row['calibrations'])
            for attempt in calibration['attempts'] if attempt['accepted']}
        seen_accepted = set()
        for c in row['accepted']:
            wave = read_wave(c)
            evidence(c, wave, target_pitch, objective)
            key = (c['sourceCandidateIndex'], c['calibrationStep'])
            require(key in expected_accepted and key not in seen_accepted,
                    'Missing or duplicated accepted attempt identity')
            attempt = expected_accepted[key]
            require(all(attempt[k] == c[k] for k in ('synth', 'seed', 'audioHash')) and
                    attempt['canonicalParams'] == c['params'], 'Accepted attempt identity differs')
            seen_accepted.add(key)
            accepted.append({**c, 'wave': wave})
        require(seen_accepted == set(expected_accepted), 'Accepted pool incomplete')
        actual_selections = {}
        for label, original_pool, accepted_pool in (
                ('unrestricted', originals, accepted),
                ('sourceEngine', [c for c in originals if c['synth'] == row['sourceSynth']],
                 [c for c in accepted if c['synth'] == row['sourceSynth']])):
            actual = select_candidates(original_pool, accepted_pool, target)
            actual_selections[label] = actual
            saved = row[label]
            for key in ('baseline', 'expandedObjective', 'selected'):
                require(same_candidate(actual[key], saved[key]), 'Selection differs: '+label+'/'+key)
                require(abs(actual[key]['score']-saved[key]['score']) < 1e-6, 'Selected score differs')
                evidence(saved[key], actual[key]['wave'], target_pitch, objective)
            require(actual['eligibility'] == saved['eligibility'], 'Eligibility differs')
            require(actual['reason'] == saved['reason'], 'Selection reason differs')
        selection = actual_selections['unrestricted']
        selected = selection['selected']
        eligible = any(c.get('audioHash') == selected['audioHash'] and c['eligible']
                       for c in selection['eligibility'])
        compact.append(dict(id=row['id'], family=row['family'], sourceSynth=row['sourceSynth'],
            pitchEligible=eligible, additionalRenderCount=extra,
            acceptedAdjustments=len(accepted), selectionReason=selection['reason'],
            **{k: {field: selection[k][field] for field in
                   ('synth', 'score', 'audioHash', 'v5Pitch', 'v5PitchComparison')}
               for k in ('baseline', 'expandedObjective', 'selected')}))
        print(json.dumps({'audited': row['id'], 'extraRenders': extra, 'eligible': eligible}), flush=True)
    return dict(path=str(path.resolve()), sha256=file_hash(path), rows=compact,
                candidateAndAttemptAuditRenders=rendered)


def gate(ordinary, high):
    require(len(ordinary) == 20 and len(high) == 4, 'Gate requires fixed20+4 cohorts')
    def avg(rows, key, field=None):
        values = [r[key]['v5PitchComparison'][field] if field else r[key]['score'] for r in rows]
        return float(np.mean(values)) if values and all(v is not None for v in values) else None
    lost_static = [r['id'] for r in ordinary if r['family'] == 'static' and
        r['baseline']['v5PitchComparison']['medianErrorSemitones'] is not None and
        r['baseline']['v5PitchComparison']['medianErrorSemitones'] <= 1 and
        (r['selected']['v5PitchComparison']['medianErrorSemitones'] is None or
         r['selected']['v5PitchComparison']['medianErrorSemitones'] > 1)]
    moving = [r for r in ordinary if r['family'] == 'moving']
    lost_direction = [r['id'] for r in moving if
        r['baseline']['v5PitchComparison']['directionMatches'] is True and
        r['selected']['v5PitchComparison']['directionMatches'] is not True]
    metrics = {'highEligible': sum(r['pitchEligible'] for r in high),
               'lostStatic': lost_static, 'lostMovingDirection': lost_direction}
    checks = {'highRegisterEligibility': metrics['highEligible'] >= 3,
              'preserveStaticMedian': not lost_static, 'preserveMovingDirection': not lost_direction}
    for field, allowance in (('contourErrorSemitones', .1), ('spanErrorSemitones', .25)):
        before, after = avg(moving, 'baseline', field), avg(moving, 'selected', field)
        metrics[field] = dict(baseline=before, selected=after, maximumIncrease=allowance)
        checks[field] = before is not None and after is not None and after <= before+allowance
    for name, rows, ratio in (('ordinaryObjective', ordinary, 1.1), ('highObjective', high, 1.)):
        before, after = avg(rows, 'baseline'), avg(rows, 'selected')
        metrics[name] = dict(baseline=before, selected=after, maximumRatio=ratio)
        checks[name] = before is not None and after is not None and after <= before*ratio
    checks['completeValidActualOutputs'] = True  # Established by fail-closed replay audit above.
    return dict(passed=all(checks.values()), checks=checks, metrics=metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('tools/multisynth/runs/pitch-calibration-v1'))
    parser.add_argument('--output', type=Path, default=Path('tools/multisynth/evaluations/pitch-calibration-audit.json'))
    args = parser.parse_args()
    require(not args.output.exists(), 'Audit output must be fresh')
    with Renderer() as renderer:
        reports = {name: audit_report(args.root/name/'results.json', renderer)
                   for name in ('paired', 'high-pitch')}
    result = dict(complete=True, scriptSha256=file_hash(__file__), reports=reports,
        gate=gate(reports['paired']['rows'], reports['high-pitch']['rows']),
        scope='Fixed development probes. Extra actual pitch renders, not an equal-compute learned-model gain. '
              'Pitch eligibility does not certify human likeness. No threshold changed after results.')
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result['gate'], indent=2), flush=True)


if __name__ == '__main__':
    main()
