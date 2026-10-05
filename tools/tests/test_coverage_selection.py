from copy import deepcopy
import pytest
from neural_invert.coverage_selection import select_candidate


def candidate(score=5.):
    return dict(score=score, pitch=dict(reliable=True), pitchComparison=dict(
        medianErrorSemitones=.5, directionMatches=True,
        activeFrameWithinOneSemitoneFraction=.6, reliableContourPairs=32,
        contourErrorSemitones=.8))


@pytest.mark.parametrize('key,value', [('directionMatches', False),
    ('activeFrameWithinOneSemitoneFraction', .5), ('reliableContourPairs', 31),
    ('contourErrorSemitones', .9)])
def test_preserves_moving_gesture(key,value):
    old=candidate();new=candidate(2.);new['pitchComparison'][key]=value
    assert select_candidate(dict(reliable=True,direction=1,spanSemitones=8),old,[new]) is old


def test_static_register_and_reliability():
    old=candidate();new=candidate(2.);new['pitchComparison']['medianErrorSemitones']=1.2
    target=dict(reliable=True,direction=0,spanSemitones=.3)
    assert select_candidate(target,old,[new]) is old
    new=deepcopy(old);new['score']=2.;new['pitch']['reliable']=False
    assert select_candidate(target,old,[new]) is old


def test_unreliable_target_uses_finite_distance():
    old=candidate();new=candidate(2.);new['pitch']['reliable']=False
    assert select_candidate(dict(reliable=False),old,[None,candidate(float('nan')),new]) is new


def test_best_allowed_against_fixed_baseline():
    old=candidate();a=candidate(3.);b=candidate(2.)
    a['pitchComparison']['activeFrameWithinOneSemitoneFraction']=.9
    target=dict(reliable=True,direction=1,spanSemitones=8)
    assert select_candidate(target,old,[a,b]) is b
    assert select_candidate(target,old,[b,a]) is b
    assert select_candidate(target,old,[]) is old


def test_invalid_baseline_fails_closed():
    with pytest.raises(ValueError):select_candidate(dict(reliable=False),None,[candidate()])
