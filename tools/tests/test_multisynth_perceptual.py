"""Synthetic diagnostics of representation behavior, not perceptual validation."""
import numpy as np
import pytest
from multisynth import features
from multisynth import perceptual as p


def texture(seed=1, rate=8):
    t = np.arange(44100)/44100
    env = .15 + .85 * (.5 + .5*np.sin(2*np.pi*rate*t))**2
    return (np.random.default_rng(seed).normal(size=len(t))*env).astype('float32')


def test_descriptor_prefix_shape_and_invalid_audio():
    wave = texture()
    desc = p.describe(wave)
    assert desc.dtype == np.float32
    assert desc.shape == (p.DIM,)
    assert p.DIM == features.DIM + sum(n for _, n in p.EXTRA_BLOCKS)
    np.testing.assert_array_equal(desc[:features.DIM], features.describe(wave))
    for bad in ([], np.zeros(20), [np.nan], [np.inf], np.ones((4, 2))):
        with pytest.raises(ValueError):
            p.describe(bad)
    assert np.isfinite(p.describe(np.array([1.], dtype='float32'))).all()


def test_gain_onset_and_identity_invariance():
    wave = texture()
    target = p.describe(wave)
    near = p.describe(np.pad(wave*.125, (813, 1024)))
    values = p.extra_components(target, [target, near])
    assert list(values) == [name for name, _ in p.EXTRA_BLOCKS]
    assert max(v[0] for v in values.values()) == 0
    assert max(v[1] for v in values.values()) < 1e-5
    with pytest.raises(ValueError):
        p.extra_components(target, [near[:-1]])


def test_event_order_and_repetition_are_retained():
    t = np.arange(44100)/44100
    def sound(centers):
        env = sum(amp*np.exp(-((t-center)/.012)**2) for center, amp in centers)
        return (env*np.sin(2*np.pi*1500*t)).astype('float32')
    ref = p.describe(sound([(.1,1),(.35,.4),(.6,.8),(.9,.5)]))
    reordered = p.describe(sound([(.1,1),(.35,.8),(.6,.4),(.9,.5)]))
    regular = p.describe(sound([(.1,1),(.37,.4),(.63,.8),(.9,.5)]))
    values = p.extra_components(ref, [ref,reordered,regular])
    assert values['fine_envelope'][1] > .01
    assert values['event_sequence'][1] > .001
    assert values['repetition'][2] > .005


def test_new_noise_seed_is_closer_than_changed_modulation():
    ref = p.describe(texture(1,8))
    near = p.describe(texture(2,8))
    changed = p.describe(texture(3,21))
    values = p.extra_components(ref, [near,changed])
    for family in ('fine_envelope','subband_modulation','repetition'):
        assert values[family][0] < values[family][1], family
