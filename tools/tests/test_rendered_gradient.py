import pytest
from neural_invert.rendered_gradient import slope


def test_quadratic_central_difference():
    assert slope(.3**2,.5**2,.3,.5)==pytest.approx(.8)


def test_clipped_boundary_uses_actual_distance():
    assert slope(2.,2.002,0.,.001)==pytest.approx(2.)


@pytest.mark.parametrize('values',[(1.,2.,.1,.1),(1.,2.,.2,.1),(float('nan'),2.,0.,1.)])
def test_invalid_secants(values):
    with pytest.raises(ValueError):slope(*values)
