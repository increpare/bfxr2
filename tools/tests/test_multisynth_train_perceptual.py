import hashlib
import json

import numpy as np
import pytest
from multisynth import features, perceptual, preference
from multisynth import train_perceptual as p
from test_multisynth_preference import archive


def test_metric_extends_old_raw_components_and_roundtrips(tmp_path):
    t = np.arange(6000)/44100
    ref = perceptual.describe(np.sin(2*np.pi*440*t).astype('float32'))
    other = perceptual.describe(np.sin(2*np.pi*1200*t).astype('float32'))
    metric = p.PerceptualMetric()
    values = metric.raw_components(ref,[ref,other])
    assert values.shape == (2,30)
    np.testing.assert_array_equal(values[:,:20],preference.PreferenceMetric().raw_components(ref[:features.DIM],[ref[:features.DIM],other[:features.DIM]]))
    assert metric.distances(ref,[ref])[0] == 0
    assert list(metric.components(ref,[other])) == list(p.NAMES)
    path = tmp_path/'model.json'
    metric.save(path, {'test':True})
    np.testing.assert_allclose(p.PerceptualMetric.load(path).distances(ref,[other]),metric.distances(ref,[other]))
    payload = json.loads(path.read_text())
    for key in ('featureSchemaSha256','featureCodeSha256','featureVersion','objectiveVersion'):
        changed = dict(payload); changed[key] = 'invalid'
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError,match='Incompatible'):
            p.PerceptualMetric.load(path)
    with pytest.raises(ValueError):
        metric.raw_components(ref,[other[:-1]])
    with pytest.raises(ValueError):
        p.PerceptualMetric(scales=np.zeros(30))


def test_training_reuses_strict_labels_and_exact_old_components(tmp_path):
    folder = archive(tmp_path/'one',2)
    baseline = preference.training_pairs([folder])
    data = p.training_pairs([folder])
    assert data.x.shape == (1,30)
    np.testing.assert_array_equal(data.x[:,:20],baseline.x)
    np.testing.assert_array_equal(data.y,baseline.y)
    np.testing.assert_array_equal(data.groups,baseline.groups)
    assert data.observations[0]['candidateAliasesA'] == ['a','alias']
    assert len(data.observations[0]['componentDifference']) == 30
    # Manifest-only label tampering must not be legitimized by PCM loading.
    manifest = json.loads((folder/'manifest.json').read_text())
    manifest['candidates'][0]['likeness'] = 5
    (folder/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='differs from raw'):
        p.training_pairs([folder])


def test_fit_uses_reference_balanced_train_only_scales_and_fixed_prior():
    x = np.tile(np.linspace(.1,3,30),(12,1)); x[:,25] *= -1
    y = np.ones(12); groups = np.array(['a']*6+['b']*2+['c']*2+['d']*2)
    model = p.fit(x,y,groups)
    expected = np.maximum(np.sqrt(preference.reference_weights(groups) @ (x*x)),.01)
    np.testing.assert_allclose(model.scales,expected)
    np.testing.assert_allclose(p.PRIOR[:20],.7*preference.PRIOR)
    np.testing.assert_allclose(p.PRIOR[20:],np.full(10,.03))
    assert model.weights[25] > max(np.delete(model.weights,25))
    assert np.all(x @ (model.weights/model.scales) < 0)
    for bad in (x[:,:29],np.full_like(x,np.nan)):
        with pytest.raises(ValueError):
            p.fit(bad,y,groups)


def test_report_pairs_baselines_on_identical_folds_and_records_provenance(tmp_path, monkeypatch):
    rng = np.random.default_rng(8)
    groups = np.repeat(np.array(list('abcdef')),2)
    x = rng.normal(size=(12,30)); y = np.sign(-x[:,24]);
    observations = [{'referencePcmSha256':str(g),'likenessA':4,'likenessB':1,
                     'componentDifference':row.tolist()} for g,row in zip(groups,x)]
    data = preference.TrainingData(x,y,groups,observations,[{'manifestSha256':'fixture'}],{})
    monkeypatch.setattr(p,'training_pairs',lambda _:data)
    baseline = tmp_path/'v4.json'; preference.PreferenceMetric().save(baseline)
    path = tmp_path/'model.json'; reportpath = tmp_path/'report.json'
    report = p.train([],path,reportpath,baseline_model=baseline)
    assert len(report['folds']) == 5
    assert len(report['pairs']) == 12
    assert report['hyperparameters']['fixedBeforeEvaluation'] is True
    assert report['frozenV4ModelSha256'] == hashlib.sha256(baseline.read_bytes()).hexdigest()
    for fold,(tr,te) in zip(report['folds'],preference.grouped_folds(groups)):
        assert fold['testGroups'] == np.unique(groups[te]).tolist()
        assert not set(fold['testGroups']) & set(fold['trainGroups'])
        expected = np.maximum(np.sqrt(preference.reference_weights(groups[tr]) @ (x[tr]**2)),.01)
        np.testing.assert_allclose(fold['scales'],expected)
        np.testing.assert_allclose(fold['refittedV4']['scales'],expected[:20])
    for row in report['pairs']:
        assert all(key in row for key in ('fold','heldOutDifference','refittedV4HeldOutDifference','auditoryDifference','frozenV4HistoricalDifference','preferenceSign'))
    assert p.PerceptualMetric.load(path).weights.shape == (30,)
    assert json.loads(reportpath.read_text())['scores'] == report['scores']


@pytest.mark.parametrize('module_name', ['multisynth.preference','multisynth.gesture',
                                         'match.features','match.audio'])
def test_model_rejects_changed_transitive_dependency(tmp_path, monkeypatch, module_name):
    import importlib
    from pathlib import Path
    module = importlib.import_module(module_name)
    path = tmp_path/'model.json'
    p.PerceptualMetric().save(path)
    changed = tmp_path/'changed.py'
    changed.write_bytes(Path(module.__file__).read_bytes()+b'\n# dependency changed\n')
    monkeypatch.setattr(module,'__file__',str(changed))
    with pytest.raises(ValueError,match='Incompatible'):
        p.PerceptualMetric.load(path)
def test_training_rejects_colliding_output_paths(tmp_path):
    import pytest
    from multisynth.train_perceptual import train
    baseline=tmp_path/'baseline.json'
    baseline.write_text('preserve me')
    with pytest.raises(ValueError,match='paths must be distinct'):
        train([],baseline,tmp_path/'report.json',baseline)
    with pytest.raises(ValueError,match='paths must be distinct'):
        train([],tmp_path/'v5.json',tmp_path/'v5.json',baseline)
    assert baseline.read_text()=='preserve me'
