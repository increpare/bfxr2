"""Regression tests for the v4 archive boundary and preference learner."""
import hashlib
import json

import numpy as np
import pytest
import soundfile as sf

from multisynth import features
from multisynth import preference as p


def archive(root, schema=1, usefulness=(1, 5)):
    root.mkdir()
    def audio(name, hz):
        t = np.arange(5000)/44100
        wave = (10000*np.sin(2*np.pi*hz*t)*np.exp(-15*t)).astype('<i2')[:, None]
        sf.write(root/(name+'.flac'), wave, 44100, subtype='PCM_16')
        sha = hashlib.sha256(str((44100,wave.shape)).encode()+wave.tobytes()).hexdigest()
        return {'file':name+'.flac','pcmSha256':sha}
    ref, aa, bb = audio('ref',440),audio('a',480),audio('b',1200)
    label = 'likeness' if schema == 2 else 'rating'
    candidates = [{'id':'a',label:4,'usefulness':usefulness[0],'audio':aa},
                  {'id':'b',label:1,'usefulness':usefulness[1],'audio':bb},
                  {'id':'alias',label:4,'audio':aa}]
    target = {'id':'target','source':{'name':'fixture'},'referenceAudio':ref}
    rawtarget = {'id':'target'}
    if schema == 2:
        target['candidates'] = [{'id':c['id']} for c in candidates]
        rawtarget['candidates'] = [{k:v for k,v in c.items() if k != 'audio'} for c in candidates]
    else:
        for role,c in zip(('selected','bfxr','previous'), candidates):
            target[role] = c['id']
            rawtarget[role] = {k:v for k,v in c.items() if k != 'audio'}
    raw = json.dumps({'schemaVersion':schema,'experimentId':root.name,'targets':[rawtarget]}).encode()
    (root/'feedback.json').write_bytes(raw)
    manifest = {'schemaVersion':schema,'experimentId':root.name,'feedbackSha256':hashlib.sha256(raw).hexdigest(),
                'targets':[target],'candidates':candidates}
    (root/'manifest.json').write_text(json.dumps(manifest))
    return root


def test_components_have_fixed_schema_and_gain_invariance():
    t = np.arange(6000)/44100
    wave = (np.sin(2*np.pi*440*t)*np.exp(-30*t)).astype('float32')
    ref = features.describe(wave)
    near = features.describe(wave*.25)
    metric = p.PreferenceMetric()
    assert len(p.NAMES) == 20
    assert metric.raw_components(ref,[near]).shape == (1,20)
    assert metric.distances(ref,[near])[0] < 1e-5
    assert set(metric.components(ref,[near])) == set(p.NAMES)
    with pytest.raises(ValueError):
        metric.distances(ref,[near[:-1]])


def test_archive_grouping_alias_dedup_and_usefulness_ignored(tmp_path):
    one = archive(tmp_path/'one')
    two = archive(tmp_path/'two',2)
    data = p.training_pairs([one,two])
    assert data.x.shape == (2,20)
    assert data.y.tolist() == [3,3]
    assert len(set(data.groups)) == 1
    assert data.observations[0]['experimentId'] != data.observations[1]['experimentId']
    three = archive(tmp_path/'three',2,(5,1))
    changed = p.training_pairs([three])
    np.testing.assert_array_equal(data.x[1],changed.x[0])
    np.testing.assert_array_equal(data.y[1:],changed.y)


def test_archive_rejects_changed_raw_feedback_or_pcm(tmp_path):
    folder = archive(tmp_path/'one')
    with (folder/'feedback.json').open('a') as f:
        f.write(' ')
    with pytest.raises(ValueError,match='checksum'):
        p.training_pairs([folder])
    folder = archive(tmp_path/'two')
    sf.write(folder/'a.flac',np.ones(5000),44100,subtype='PCM_16')
    with pytest.raises(ValueError,match='checksum'):
        p.training_pairs([folder])


def test_training_scale_uses_training_rows_only_and_folds_group_pcm():
    x = np.tile(np.linspace(.1,2.,20),(12,1))
    x[:,1] *= -1
    y = np.ones(12)
    groups = np.array(['a','a','b','b','c','c','d','d','e','e','f','f'])
    changed = x.copy(); changed[groups=='f'] *= 1e8
    train = groups != 'f'
    before = p.fit(x[train],y[train],groups[train])
    after = p.fit(changed[train],y[train],groups[train])
    np.testing.assert_array_equal(before.scales,after.scales)
    assert not np.allclose(before.scales,p.fit(changed,y,groups).scales)
    assert before.weights[1] > max(np.delete(before.weights,1))
    assert np.all(before.weights >= 0)
    assert (x @ (before.weights/before.scales) < 0).all()
    for tr,te in p.grouped_folds(groups):
        assert not set(groups[tr]) & set(groups[te])


def test_reference_balancing_and_model_roundtrip(tmp_path):
    groups = np.array(['a']*8+['b']*2)
    w = p.reference_weights(groups)
    assert w[:8].sum() == pytest.approx(w[8:].sum())
    metric = p.PreferenceMetric(weights=np.arange(1,21),scales=np.linspace(.1,2,20))
    path = tmp_path/'model.json'
    metric.save(path)
    restored = p.PreferenceMetric.load(path)
    rng = np.random.default_rng(4)
    ref = rng.uniform(-1,0,features.DIM).astype('float32')
    candidates = rng.uniform(-1,0,(3,features.DIM)).astype('float32')
    np.testing.assert_allclose(metric.distances(ref,candidates),restored.distances(ref,candidates))
    payload = json.loads(path.read_text());payload['components'].reverse()
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError,match='Incompatible'):
        p.PreferenceMetric.load(path)
    with pytest.raises(ValueError):
        p.PreferenceMetric(scales=np.zeros(20))


def test_coarse_spectrum_keeps_all_bands_and_tolerates_within_bin_timing():
    reference = np.zeros(features.DIM,dtype='float32')
    candidate = reference.copy()
    reference[0] = -1
    candidate[1] = -1
    metric = p.PreferenceMetric()
    values = metric.raw_components(reference,[candidate])[0]
    assert values[0] > 0
    assert values[-3:].tolist() == [0,0,0]
    other_band = candidate.copy()
    other_band[1] = 0;other_band[33] = -1
    assert (metric.raw_components(reference,[other_band])[0,-3:] > 0).all()
