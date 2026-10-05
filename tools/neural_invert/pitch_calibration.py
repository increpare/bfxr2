"""Bounded pitch proposals verified against actual DSP PCM.

V5 evidence is diagnostic: relative-time samples retain null/unvoiced gaps and
cannot certify human likeness or whole-sound endpoint/duration agreement.
"""
from copy import deepcopy
import math

import numpy as np

from match.objective import MatchObjective
from .benchmark import audio_hash
from .pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch


POLICY = {
    'version': 'actual-render-pitch-calibration-v1',
    'maxAdditionalRenders': 3,
    'attemptAccounting': 'attempts includes unrendered bounds_unchanged proposals; '
                         'renderCount is 1 for each renderer call, including errors, '
                         'and 0 for unrendered proposals. additionalRenderCount excludes the original.',
    'audiblePeak': 1e-6,
    'targetVoicedFraction': .8,
    'minimumVoicedFrames': 16,
    'minimumAlignedPairs': 16,
    'stationarySpanSemitones': .5,
    'maximumStepSemitones': 24.,
    'tinyOffsetSemitones': .1,
    'minimumContourImprovementSemitones': .01,
    'maximumSpanWorseningSemitones': .25,
    'durationToleranceSamples': 2,
    'durationToleranceFraction': .02,
    'selection': {'voicedFraction': .8, 'medianErrorSemitones': 1.,
                  'activeFrameWithinOneSemitoneFraction': .75,
                  'spanErrorFloorSemitones': 1., 'spanErrorTargetFraction': .2,
                  'baselineContourWorseningSemitones': .05,
                  'preserveBaselineActiveFraction': True,
                  'preserveBaselineMatchingDirection': True},
    'registerMappings': {'Bfxr': 'sqrt(max(0,(s*s+.001)*2**(semitones/12)-.001))',
                         'Transfxr': 'pitch.start and pitch.end += semitones/84',
                         'Pluckr': 'pitch += semitones/48'},
    'stationaryMappings': {
        'Bfxr': {'frequency_start': 'sqrt(max(0,hz/3528-.001))',
                 'zero': ['frequency_slide', 'frequency_acceleration', 'vibratoDepth',
                          'pitch_jump_amount', 'pitch_jump_2_amount']},
        'Transfxr': {'pitch.start/end': 'log2(hz/40)/7', 'vibrato.start/end': 0},
        'Pluckr': {'pitch': 'log2(hz/55)/4', 'vibrato': 0}},
    'acceptance': 'Reliable pitch, no aligned-pair or target-active tolerance loss; '
                  'mean contour improves; span and original duration bounded. Same seed.',
    'selectionObjective': 'Unchanged MatchObjective; exact original baseline fallback.',
    'limitations': 'Diagnostic eligibility is not human-quality certification. '
                  'Null/unvoiced gaps are retained; alignment is active-relative time.',
}
ENGINES = tuple(POLICY['registerMappings'])


def _validate_synth(synth, spec):
    if synth not in ENGINES or spec['name'] != synth:
        raise ValueError('Unsupported or mismatched synth')


def _set(params, spec, name, value, side=None, clamps=None):
    control = next(p for p in spec['params'] if p['name'] == name)
    requested = float(value)
    value = float(np.clip(requested, control['min'], control['max']))
    if clamps is not None and value != requested:
        clamps.append(dict(control=name if side is None else name+'.'+side,
            requested=requested, applied=value, min=control['min'], max=control['max']))
    if side is None:
        params[name] = value
    else:
        params[name][side] = value


def shift_register(synth, params, semitones, spec):
    """Copy controls, shifting only the primary register within schema bounds."""
    _validate_synth(synth, spec)
    if not np.isfinite(semitones):
        raise ValueError('Register shift must be finite')
    return _register(synth, params, semitones, spec)


def _register(synth, params, semitones, spec, clamps=None):
    """Audited callers supply the bounded (at most 24 semitone) residual."""
    result = deepcopy(params)
    if synth == 'Bfxr':
        # Bound the exponent before evaluation so even extreme finite shifts
        # saturate safely at the actual schema maximum without overflow.
        control = next(p for p in spec['params'] if p['name'] == 'frequency_start')
        base = params['frequency_start']**2+.001
        ceiling = 12*math.log2((control['max']**2+.001)/base)
        shifted = (control['max'] if clamps is None and semitones >= ceiling else
                   math.sqrt(max(0, base*2**(semitones/12)-.001)))
        _set(result, spec, 'frequency_start', shifted, clamps=clamps)
    elif synth == 'Transfxr':
        for side in ('start', 'end'):
            _set(result, spec, 'pitch', params['pitch'][side]+semitones/84, side, clamps)
    else:
        _set(result, spec, 'pitch', params['pitch']+semitones/48, clamps=clamps)
    return result


def _stationary(synth, params, hz, spec, clamps=None):
    result = deepcopy(params)
    if synth == 'Bfxr':
        _set(result, spec, 'frequency_start', math.sqrt(max(0, hz/3528-.001)), clamps=clamps)
        for name in POLICY['stationaryMappings']['Bfxr']['zero']:
            _set(result, spec, name, 0, clamps=clamps)
    elif synth == 'Transfxr':
        for side in ('start', 'end'):
            _set(result, spec, 'pitch', math.log2(hz/40)/7, side, clamps)
            _set(result, spec, 'vibrato', 0, side, clamps)
    else:
        _set(result, spec, 'pitch', math.log2(hz/55)/4, clamps=clamps)
        _set(result, spec, 'vibrato', 0, clamps=clamps)
    return result


class _InvalidAudio(ValueError):
    """Expected invalid render result; implementation exceptions still propagate."""


def _wave(wave, require_audible=True):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.all(np.isfinite(wave)):
        raise _InvalidAudio('invalid_audio')
    if require_audible and np.max(np.abs(wave)) < POLICY['audiblePeak']:
        raise _InvalidAudio('silent_audio')
    return wave


def _evidence(row, wave, target_pitch, objective):
    wave = _wave(wave)
    score = float(objective.score_batch([wave])[0])
    if not np.isfinite(score):
        raise _InvalidAudio('nonfinite_score')
    pitch = descriptor_pitch(wave)
    return {**row, 'wave': wave, 'audioHash': audio_hash(wave), 'score': score,
            'v5Pitch': pitch, 'v5PitchComparison': compare_descriptor_pitch(target_pitch, pitch)}


def _strong(pitch):
    return (pitch['reliable'] and pitch['voicedFraction'] >= POLICY['targetVoicedFraction']
            and pitch['voicedFrames'] >= POLICY['minimumVoicedFrames'])


def _paired(row):
    return (row['v5Pitch']['reliable'] and
            row['v5PitchComparison']['reliableContourPairs'] >= POLICY['minimumAlignedPairs'])


def _offset(target, candidate):
    return float(np.median([12*math.log2(a/b)
        for a,b in zip(target['contourHz'], candidate['contourHz'])
        if a is not None and b is not None]))


def _acceptance(row, current, original):
    comparison, previous = row['v5PitchComparison'], current['v5PitchComparison']
    if not _paired(row):
        return 'unreliable_candidate'
    if comparison['reliableContourPairs'] < previous['reliableContourPairs']:
        return 'voiced_pairs_decreased'
    tolerance = max(POLICY['durationToleranceSamples'],
                    POLICY['durationToleranceFraction']*len(original['wave']))
    if abs(len(row['wave'])-len(original['wave'])) > tolerance:
        return 'duration_changed'
    if previous['contourErrorSemitones']-comparison['contourErrorSemitones'] < POLICY['minimumContourImprovementSemitones']:
        return 'no_contour_improvement'
    if comparison['spanErrorSemitones']-previous['spanErrorSemitones'] > POLICY['maximumSpanWorseningSemitones']:
        return 'span_worsened'
    if comparison['activeFrameWithinOneSemitoneFraction'] < previous['activeFrameWithinOneSemitoneFraction']:
        return 'active_fraction_decreased'
    return None


def calibrate_candidate(candidate, target_wave, renderer, objective, max_steps=3):
    """Replay the original, then request at most three same-seed adjustments.

    Only renderer ValueError/RuntimeError/OSError and explicit invalid audio
    results become failed attempts. Unexpected scoring/diagnostic bugs propagate.
    Attempts include unrendered no-change proposals. Sum their renderCount (or
    use additionalRenderCount) for the extra-render budget, not len(attempts).
    rendered=True means a renderer call was requested, including failed calls.
    requestedParams are clamped; clamps preserve every clipped raw value/bound.
    """
    if type(max_steps) is not int or not 0 <= max_steps <= POLICY['maxAdditionalRenders']:
        raise ValueError('max_steps must be an integer from zero to three')
    synth = candidate['synth']
    if synth not in ENGINES:
        raise ValueError('Unsupported synth')
    spec = renderer.specs[synth]
    _validate_synth(synth, spec)
    target_pitch = descriptor_pitch(_wave(target_wave, require_audible=False))
    seed = candidate['seed']
    canonical, wave = renderer.render(synth, deepcopy(candidate['params']), seed)
    original = _evidence({**deepcopy(candidate), 'params': deepcopy(canonical), 'seed': seed,
        'provenance': {**deepcopy(candidate.get('provenance', {})), 'pitchCalibration': {
            'version': POLICY['version'], 'role': 'original', 'targetAudioHash': audio_hash(target_wave)}}},
        wave, target_pitch, objective)
    result = dict(original=original, accepted=[], attempts=[], status='step_limit', additionalRenderCount=0)
    if not _strong(target_pitch):
        result['status'] = 'weak_target'
        return result
    if not _paired(original):
        result['status'] = 'unreliable_candidate'
        return result
    current = original
    seen = {original['audioHash']}
    seen_params = [original['params']]
    stationary = target_pitch['spanSemitones'] <= POLICY['stationarySpanSemitones']
    for step in range(max_steps):
        offset = _offset(target_pitch, current['v5Pitch'])
        initialize = stationary and step == 0
        false_motion = current['v5Pitch']['spanSemitones'] > POLICY['stationarySpanSemitones']
        if abs(offset) < POLICY['tinyOffsetSemitones'] and not (initialize and false_motion):
            result['status'] = 'tiny_offset'
            break
        raw_offset = offset
        offset = float(np.clip(offset, -POLICY['maximumStepSemitones'], POLICY['maximumStepSemitones']))
        clamps = []
        params = (_stationary(synth, current['params'], target_pitch['medianHz'], spec, clamps) if initialize
                  else _register(synth, current['params'], offset, spec, clamps))
        attempt = dict(step=step+1, synth=synth, seed=seed,
            mode='stationary_initialization' if initialize else 'register_shift',
            rawOffsetSemitones=raw_offset, offsetSemitones=offset,
            requestedParams=deepcopy(params), clamps=clamps, canonicalParams=None,
            audioHash=None, accepted=False, reason=None, rendered=False, renderCount=0,
            duplicateCanonicalParams=None, duplicateAudio=None)
        result['attempts'].append(attempt)
        if params == current['params']:
            attempt['reason'] = result['status'] = 'bounds_unchanged'
            break
        attempt.update(rendered=True, renderCount=1)
        result['additionalRenderCount'] += 1
        try:
            canonical, wave = renderer.render(synth, params, seed)
        except (ValueError, RuntimeError, OSError) as exc:
            attempt.update(reason='render_error', error=str(exc))
            result['status'] = 'render_error'
            break
        attempt['canonicalParams'] = deepcopy(canonical)
        attempt['duplicateCanonicalParams'] = canonical in seen_params
        seen_params.append(deepcopy(canonical))
        # Retain actual returned PCM even when it is rejected as silent/invalid.
        attempt['wave'] = wave
        attempt['audioHash'] = audio_hash(wave)
        attempt['duplicateAudio'] = attempt['audioHash'] in seen
        try:
            row = _evidence({**current, 'params': deepcopy(canonical),
                'provenance': {**deepcopy(candidate.get('provenance', {})), 'pitchCalibration': {
                    'version': POLICY['version'], 'role': 'adjusted', 'step': step+1,
                    'mode': attempt['mode'], 'originalAudioHash': original['audioHash'],
                    'parentAudioHash': current['audioHash'], 'targetAudioHash': audio_hash(target_wave)}}},
                wave, target_pitch, objective)
        except _InvalidAudio as exc:
            attempt.update(reason=str(exc), error=str(exc))
            result['status'] = str(exc)
            break
        for key in ('score', 'v5Pitch', 'v5PitchComparison'):
            attempt[key] = row[key]
        reason = ('duplicate_canonical_params' if attempt['duplicateCanonicalParams'] else
                  'duplicate_audio' if attempt['duplicateAudio'] else _acceptance(row, current, original))
        seen.add(row['audioHash'])
        attempt['reason'] = reason or 'accepted'
        if reason:
            result['status'] = reason
            break
        attempt['accepted'] = True
        result['accepted'].append(row)
        current = row
    return result


def _eligibility(row, target, baseline):
    pitch, comparison = row['v5Pitch'], row['v5PitchComparison']
    thresholds = POLICY['selection']
    if not _paired(row) or pitch['voicedFraction'] < thresholds['voicedFraction']:
        return 'unreliable_candidate'
    if comparison['medianErrorSemitones'] > thresholds['medianErrorSemitones']:
        return 'median_error'
    if comparison['activeFrameWithinOneSemitoneFraction'] < thresholds['activeFrameWithinOneSemitoneFraction']:
        return 'active_fraction'
    if comparison['directionMatches'] is not True:
        return 'direction_mismatch'
    if comparison['spanErrorSemitones'] > max(thresholds['spanErrorFloorSemitones'],
                                             thresholds['spanErrorTargetFraction']*target['spanSemitones']):
        return 'span_error'
    if baseline['v5Pitch']['reliable']:
        old = baseline['v5PitchComparison']
        if comparison['activeFrameWithinOneSemitoneFraction'] < old['activeFrameWithinOneSemitoneFraction']:
            return 'baseline_active_fraction'
        if (old['contourErrorSemitones'] is not None and
            comparison['contourErrorSemitones'] > old['contourErrorSemitones']+thresholds['baselineContourWorseningSemitones']):
            return 'baseline_contour_error'
        if comparison['spanErrorSemitones'] > old['spanErrorSemitones']+POLICY['maximumSpanWorseningSemitones']:
            return 'baseline_span_error'
        if old['directionMatches'] is True and comparison['directionMatches'] is not True:
            return 'baseline_direction'
    return None


def select_candidates(originals, accepted, target_wave):
    """Compare unchanged objective scores with conservative pitch eligibility.

    Refresh every score and descriptor from supplied actual PCM, ignoring stale
    cached fields. Returned rows are copies; exact original controls/seed/PCM are
    retained. No rendering, reweighting, resampling, or gap interpolation occurs.
    """
    if not originals:
        raise ValueError('At least one original is required')
    target = descriptor_pitch(_wave(target_wave, require_audible=False))
    objective = MatchObjective(target_wave)
    baseline_rows = [_evidence(deepcopy(row), row['wave'], target, objective) for row in originals]
    baseline = min(baseline_rows, key=lambda row: row['score'])
    records, rows = [], list(baseline_rows)
    identities = [('original', index) for index in range(len(baseline_rows))]
    for index, row in enumerate(accepted):
        try:
            rows.append(_evidence(deepcopy(row), row['wave'], target, objective))
            identities.append(('accepted', index))
        except _InvalidAudio as exc:
            records.append(dict(pool='accepted', index=index, eligible=False, reason=str(exc)))
    eligible = []
    for (pool, index), row in zip(identities, rows):
        reason = _eligibility(row, target, baseline) if _strong(target) else 'weak_target'
        records.append(dict(pool=pool, index=index,
            audioHash=row['audioHash'], score=row['score'], eligible=reason is None,
            reason=reason or 'eligible', v5Pitch=row['v5Pitch'], v5PitchComparison=row['v5PitchComparison']))
        if reason is None:
            eligible.append(row)
    return dict(baseline=baseline, expandedObjective=min(rows, key=lambda row: row['score']),
        selected=min(eligible, key=lambda row: row['score']) if eligible else baseline,
        eligibility=records, reason='eligible_minimum_objective' if eligible else
            'weak_target' if not _strong(target) else 'no_eligible_candidates',
        v5TargetPitch=target)
