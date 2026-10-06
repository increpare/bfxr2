import json
import numpy as np
import pytest
from multisynth.listener_metric import source_groups, fit, ListenerMetric, PRIOR, RECIPE


def test_external_groups_join_tag_source_hash_and_pcm_and_exclude_synthetic():
    def row(pcm,name,sha,path=True,synthetic=False):
        return dict(reference=pcm,source=dict(name=name,sha256=sha,**({'path':'/corpus/tags/'+name} if path else {}),synthetic=synthetic))
    rows=[row('a','hit/a.wav','one'),row('b','hit/b.wav','two'),row('c','door/c.wav','two'),
          row('c','bell/d.wav','three'),row('e','coin/e.wav','four'),row('s','native.wav','five',False),row('q','native2.wav','six',True,True)]
    groups=source_groups(rows)
    assert groups['a']==groups['b']==groups['c']
    assert groups['e']!=groups['a'] and 's' not in groups and 'q' not in groups


def test_fit_uses_only_supplied_rows_and_correct_preference_direction():
    x=np.zeros((12,21));x[:,0]=-1;x[:,1]=1
    model=fit(x,np.ones(12),np.repeat(['a','b','c'],4))
    assert (x@(model.weights/model.scales)<0).all()
    assert model.scales[0]==pytest.approx(1) and model.scales[2]==pytest.approx(.01)
    assert np.all(model.weights>=0) and model.weights.sum()==pytest.approx(1)
    with pytest.raises(ValueError):fit(x,np.zeros(12),np.arange(12))
    with pytest.raises(ValueError):fit(x[:,:20],np.ones(12),np.arange(12))


def test_metric_serialization_rejects_changed_policy_or_invalid_values(tmp_path):
    model=ListenerMetric(PRIOR,np.ones(21));path=tmp_path/'metric.json';model.save(path,{'purpose':'unit test'})
    restored=ListenerMetric.load(path)
    np.testing.assert_array_equal(model.weights,restored.weights)
    obj=json.loads(path.read_text());obj['recipe']['steps']+=1;path.write_text(json.dumps(obj))
    with pytest.raises(ValueError):ListenerMetric.load(path)
    with pytest.raises(ValueError):ListenerMetric(np.r_[np.ones(20),-1],np.ones(21))


def test_prepared_audio_score_matches_direct_components_and_rejects_nan():
    from multisynth.features import describe
    from multisynth.preference import PreferenceMetric
    from multisynth.soft_periodicity import SoftPeriodicityObjective
    t=np.arange(11025)/44100;target=(.4*np.sin(2*np.pi*440*t)*np.exp(-t*10)).astype(np.float32)
    candidate=(.4*np.sin(2*np.pi*490*t)*np.exp(-t*10)).astype(np.float32)
    expected=np.r_[PreferenceMetric().raw_components(describe(target),[describe(candidate)])[0],SoftPeriodicityObjective(target).score(candidate)]
    model=ListenerMetric();objective=model.objective(target)
    np.testing.assert_allclose(objective.components(candidate),expected,rtol=1e-7,atol=1e-7)
    assert objective.score(candidate)==pytest.approx(float(expected@PRIOR))
    with pytest.raises(ValueError):objective.score(np.array([np.nan]))
