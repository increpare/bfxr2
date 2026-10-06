import copy
import numpy as np
import pytest
from multisynth.control_diagnosis import control_variants


def test_transfxr_frequency_and_cutoff_offsets_preserve_curve_and_other_controls():
    p={'pitch':{'start':.3,'end':.6,'curve':'Bounce'},'tone':{'start':.3,'end':.6,'curve':'Smooth'},'seed':.25,'duration':.4}
    before=copy.deepcopy(p)
    for axis,field,scale,semitones in [('pitch','pitch',84,6),('tone','tone',12*np.log2(160),3)]:
        variants=control_variants('Transfxr',p,axis)
        for sign,q in zip([-1,1],variants):
            for edge in ['start','end']:assert q[field][edge]==pytest.approx(p[field][edge]+sign*semitones/scale)
            assert q[field]['curve']==p[field]['curve']
            q_without=copy.deepcopy(q);q_without[field]=p[field];assert q_without==p
    assert p==before
    with pytest.raises(ValueError):control_variants('Transfxr',{**p,'tone':{'start':0.,'end':1.,'curve':'Smooth'}},'tone')


@pytest.mark.parametrize('synth,axis,current,expected',[
 ('Zappr','voltage',.3,[.15,.45]),('Zappr','spark',.13,[0.,.5]),
 ('Squishr','wetness',.97,[.35,.65]),('Bfxr','bitCrush',.29,[0.,.6]),
 ('Pluckr','pitch',.5,[.5-2/48,.5+2/48])])
def test_scalar_variants_preserve_every_other_parameter(synth,axis,current,expected):
    p={axis:current,'seed':.25,'duration':.4,'nested':{'control':.7}}
    before=copy.deepcopy(p);out=control_variants(synth,p,axis)
    assert [q[axis] for q in out]==pytest.approx(expected)
    for q in out:
        q[axis]=current;assert q==p
        q['nested']['control']=0.;assert p==before


def test_unsupported_or_out_of_range_interventions_fail_without_clamping():
    with pytest.raises(ValueError):control_variants('Zappr',{'voltage':.9},'voltage')
    with pytest.raises(ValueError):control_variants('Zappr',{'pitch':.5},'pitch')
    with pytest.raises(ValueError):control_variants('Pluckr',{'pitch':float('nan')},'pitch')
