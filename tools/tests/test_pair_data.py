import pytest
from neural_invert.pair_data import component_id, split_for_id, check_component_splits


def test_component_group_ignores_display_name_but_not_actual_controls():
    source=dict(synth='Boomr',name='one',params={'duration':.3,'seed':.5},renderSeed=.5)
    key=component_id(source)
    assert key==component_id(dict(source,name='two'))
    assert key!=component_id(dict(source,params={'duration':.4,'seed':.5}))
    assert split_for_id(key)==split_for_id(component_id(dict(source,name='renamed')))
    with pytest.raises(ValueError):component_id(dict(source,renderSeed=float('nan')))


def test_component_not_just_pair_disjointness():
    bank={'a':{'split':'train'},'b':{'split':'val'},'c':{'split':'train'}}
    check_component_splits(bank,[{'split':'train','componentIds':['a','c']},{'split':'val','componentIds':['b',None]}])
    with pytest.raises(ValueError):
        check_component_splits(bank,[{'split':'train','componentIds':['a','c']},{'split':'val','componentIds':['b','a']}])
