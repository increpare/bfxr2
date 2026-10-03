import numpy as np
import pytest

from multisynth.features import describe
from multisynth.gesture import GestureMetric


def sound(envelope, start=440, end=440):
    t = np.arange(len(envelope))/44100
    phase = 2*np.pi*(start*t + (end-start)*t*t/(2*t[-1]))
    return (np.sin(phase)*envelope).astype('float32')


def test_gesture_preserves_motion_and_impact_under_detuning():
    metric = GestureMetric()
    t = np.linspace(0, 1, 22050)
    env = np.sin(np.pi*t)**.5
    up = describe(sound(env, 300, 1600))
    near = describe(sound(env, 400, 1800))
    down = describe(sound(env, 1600, 300))
    assert metric.distances(up, [near])[0] < metric.distances(up, [down])[0]
    longer = describe(sound(np.sin(np.pi*np.linspace(0,1,27562))**.5,300,1600))
    assert metric.distances(up,[longer])[0] < metric.distances(up,[down])[0]
    impact = describe(sound(np.exp(-8*t)))
    detuned = describe(sound(np.exp(-8*t), 550, 550))
    swell = describe(sound(np.exp(-8*(1-t))))
    assert metric.distances(impact, [detuned])[0] < metric.distances(impact, [swell])[0]


def test_gesture_keeps_burst_structure_and_gain_invariance():
    metric = GestureMetric()
    t = np.linspace(0, 1, 22050)
    env = np.maximum(0, np.sin(10*np.pi*t))**2
    wave = sound(env)
    ref = describe(wave)
    near = describe(sound(env, 500, 500))
    steady = describe(sound(np.sin(np.pi*t)**.5))
    assert metric.distances(ref, [near])[0] < metric.distances(ref, [steady])[0]
    assert metric.distances(ref, [describe(wave*.2)])[0] < 1e-5
    assert metric.distances(ref, [ref])[0] == pytest.approx(0)


def test_gesture_weights_are_validated_and_roundtrip(tmp_path):
    metric = GestureMetric()
    with pytest.raises(ValueError):
        GestureMetric(weights=[-1]*len(metric.names))
    path = tmp_path/'model.json'
    metric.save(path, {'purpose':'test'})
    restored = GestureMetric.load(path)
    np.testing.assert_array_equal(metric.weights, restored.weights)


def test_preference_fit_and_reference_grouped_folds():
    from multisynth.train_gesture import fit_weights, grouped_folds
    prior = np.array([.5, .5])
    # Feature 0 contradicts preference, feature 1 explains it.
    differences = np.tile([.1, -.3], (12, 1))
    learned = fit_weights(differences, np.ones(12), prior)
    assert learned[1] > learned[0]
    groups = np.array(['a','a','b','b','c','c','d','d'])
    for train, test in grouped_folds(groups, 3):
        assert not set(groups[train]) & set(groups[test])


def test_injected_metric_controls_retrieval_and_search_replay():
    from multisynth.library import Library
    from multisynth.renderer import Renderer
    from multisynth.search import approximate
    metric = GestureMetric()
    with Renderer() as renderer:
        params, wave = renderer.render('Clonkr', renderer.sample('Clonkr',renderer.specs['Clonkr']['presets'][0],7),7)
        descriptor = describe(wave)
        library = Library([{'synth':'Clonkr','params':params,'seed':7,'preset':'test'}], [descriptor],{})
        retrieved = library.retrieve(descriptor,metric=metric)
        assert retrieved[0]['score'] == pytest.approx(0)
        result = approximate(renderer,library,wave,experts=1,budget=3,metric=metric,
                             seed_candidates=[{'synth':'Clonkr','params':params,'seed':7,'preset':'previous'}])
        assert result['candidates'][0]['score'] == pytest.approx(0)
        assert set(result['candidates'][0]['components']) == set(metric.names)
        assert np.all(np.diff(result['candidates'][0]['trace']) <= 0)
        assert result['seed_renders'] == 1


def test_training_uses_previous_ratings_and_groups_all_pairs_by_reference(tmp_path):
    import hashlib
    import json
    import soundfile as sf
    from multisynth.train_gesture import training_pairs
    raw = b'{}'
    (tmp_path/'feedback.json').write_bytes(raw)
    t = np.linspace(0,1,4000)
    wave = (sound(np.exp(-5*t))*10000).astype('int16')[:,None]
    sf.write(tmp_path/'clip.flac',wave,44100,subtype='PCM_16')
    sha = hashlib.sha256(str((44100,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
    audio = {'file':'clip.flac','pcmSha256':sha}
    manifest = {'feedbackSha256':hashlib.sha256(raw).hexdigest(),
                'candidates':[{'id':name,'rating':rating,'audio':audio} for name,rating in [('a',3),('b',1),('c',4)]],
                'targets':[{'selected':'a','bfxr':'b','previous':'c','referenceAudio':audio,'source':{'name':'test'}}]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    x,y,groups,_,_,_ = training_pairs(tmp_path)
    assert x.shape == (3,9)
    assert set(y) == {2,-1,-3}
    assert len(set(groups)) == 1
