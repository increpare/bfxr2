import numpy as np
import pytest


def test_local_step_is_bounded_reversible_and_zero_safe():
    from neural_invert.local_gradient import local_step
    u = np.array([.5, .99, .01])
    g = np.array([2., -1., 1.])
    np.testing.assert_allclose(local_step(u, g, .02, 1), [.48, 1., 0.])
    np.testing.assert_allclose(local_step(u, g, .02, -1), [.52, .98, .02])
    np.testing.assert_array_equal(local_step(u, g*0, .02, 1), u)
    np.testing.assert_array_equal(u, [.5, .99, .01])
    for bad in (0, -.1, float('nan')):
        with pytest.raises(ValueError): local_step(u, g, bad, 1)
    with pytest.raises(ValueError): local_step(u, [np.nan, 1, 1], .02, 1)
    with pytest.raises(ValueError): local_step([-1, .5, .5], g, .02, 1)


def test_primary_gate_requires_complete_coverage_and_all_safeguards():
    from neural_invert.local_gradient import primary_gate
    s = dict(cases=32, improvements=24, meanBefore=2., meanAfter=1.9,
             additionalSilence=0, reliablePitchLosses=0, staticPitchLosses=0,
             movingDirectionLosses=0)
    assert primary_gate(s)['passed']
    for key in ('additionalSilence', 'reliablePitchLosses', 'staticPitchLosses', 'movingDirectionLosses'):
        assert not primary_gate({**s, key:1})['passed']
    assert not primary_gate({**s, 'cases':31})['passed']
    assert not primary_gate({**s, 'improvements':23})['passed']
    assert not primary_gate({**s, 'meanAfter':2.1})['passed']
