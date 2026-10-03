import json
import numpy as np

from multisynth.refine import RecipeSpace, distinct_starts


def test_recipe_mutation_preserves_phrase_discrete_controls_and_trust_region():
    spec = {'name':'Test','params':[
        {'name':'pitch','type':'KNOB','min':0,'max':1},
        {'name':'material','type':'BUTTONSELECT','min':0,'max':3},
        {'name':'syllables','type':'RANGE','min':1,'max':16},
        {'name':'duration','type':'KNOB','min':.01,'max':12},
        {'name':'phrase','type':'TEXT'},
        {'name':'tone','type':'KNOB_TRANSITION','min':0,'max':1}]}
    anchor = {'pitch':.5,'material':2,'syllables':4,'duration':.5,'phrase':'[1,2,3]',
              'tone':{'start':.2,'end':.8,'curve':'Ease Out'}}
    space = RecipeSpace(anchor,spec)
    rng = np.random.default_rng(9)
    child = anchor
    for _ in range(100):
        child = space.mutate(child,rng,.1)
        assert child['material']==2 and child['phrase']=='[1,2,3]' and child['syllables']==4
        assert child['tone']['curve']=='Ease Out'
        assert .28 <= child['pitch'] <= .72
        assert .2 <= child['duration'] <= 1.25
    assert anchor['pitch']==.5


def test_soundboard_mutation_keeps_source_identity_seed_and_alignment():
    specs = {'Test':{'name':'Test','params':[{'name':'pitch','type':'KNOB','min':0,'max':1}]}}
    source = {'synth':'Test','params':{'pitch':.5},'renderSeed':.4,'generator':'generate_hit'}
    anchor = {'sources':json.dumps([source,source]),'align':2,'balance':.5,'offset':0,'seed':.5}
    space = RecipeSpace(anchor,None,specs)
    child = space.mutate(anchor,np.random.default_rng(3),.1)
    assert child['align']==2 and child['seed']==.5
    for s in json.loads(child['sources']):
        assert s['synth']=='Test' and s['renderSeed']==.4 and s['generator']=='generate_hit'


def test_distinct_starts_preserve_multiple_engines_and_recipes():
    rows=[{'backend':'legacy','synth':'A','preset':'x'},
          {'backend':'legacy','synth':'A','preset':'x'},
          {'backend':'board','synth':'Soundboard','signature':'B:x+C:y'},
          {'backend':'legacy','synth':'D','preset':'z'}]
    assert distinct_starts(rows,np.array([.1,.11,.2,.3]),3)==[0,2,3]
