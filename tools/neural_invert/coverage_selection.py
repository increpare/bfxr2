"""Experimental selection using rendered descriptor evidence, never likeness labels."""
import math

POLICY = dict(version='coverage-selection-v1', staticSemitones=1.,
    baseline='fixed old-four minimum actual-DSP distance',
    scope='Descriptor safeguards are selection inputs, not independent perceptual validation')


def rejection_reasons(target, baseline, candidate):
    if candidate is None or not math.isfinite(candidate.get('score', float('nan'))):
        return ['invalidScore']
    if not target['reliable']:
        return []
    a, b = baseline['pitchComparison'], candidate['pitchComparison']
    reasons = []
    if baseline['pitch']['reliable'] and not candidate['pitch']['reliable']:
        reasons.append('reliablePitch')
    if target['spanSemitones'] <= 1 and a['medianErrorSemitones'] is not None and a['medianErrorSemitones'] <= 1:
        if b['medianErrorSemitones'] is None or b['medianErrorSemitones'] > 1:
            reasons.append('staticMedian')
    if target['direction'] in (-1, 1) and a['directionMatches'] is True and b['directionMatches'] is not True:
        reasons.append('movingDirection')
    for key in ('activeFrameWithinOneSemitoneFraction', 'reliableContourPairs'):
        if a[key] is not None and (b[key] is None or b[key] < a[key]):
            reasons.append(key)
    key = 'contourErrorSemitones'
    if a[key] is not None and (b[key] is None or b[key] > a[key]):
        reasons.append(key)
    return reasons


def select_candidate(target, baseline, candidates):
    """Keep baseline unless a lower-distance proposal preserves its pitch evidence."""
    if baseline is None or not math.isfinite(baseline.get('score', float('nan'))):
        raise ValueError('A finite baseline is required')
    allowed = [baseline] + [c for c in candidates if not rejection_reasons(target, baseline, c)]
    return min(allowed, key=lambda c: c['score'])
