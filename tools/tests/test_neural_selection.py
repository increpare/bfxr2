import numpy as np


def test_preference_reranker_does_not_overwrite_search_score_or_default():
    from neural_invert.selection import select_preferred
    class Metric:
        def distances(self,target,candidates):
            return candidates[:,0]
    rows=[{'synth':'first','score':1.,'wave':np.array([2.]),'provenance':{}},
          {'synth':'second','score':2.,'wave':np.array([1.]),'provenance':{}}]
    selected=select_preferred(np.array([0.]),rows,Metric(),lambda x:x,'modelhash')
    assert selected['synth']=='second' and selected['score']==2.
    assert selected['provenance']['preferenceScore']==1.
    assert selected['provenance']['selectorModelSha256']=='modelhash'
    assert 'preferenceScore' not in rows[1]['provenance']


def test_preference_reranker_rejects_invalid_rankings():
    import pytest
    from neural_invert.selection import select_preferred
    class Metric:
        def distances(self,target,candidates):return np.full(len(candidates),np.nan)
    with pytest.raises(ValueError,match='finite'):
        select_preferred(np.array([0.]),[{'wave':np.array([1.])}],Metric(),lambda x:x,'hash')


def test_coarse_pitch_guard_ignores_small_detuning_but_catches_register_and_voice_loss():
    from neural_invert.selection import coarse_pitch_penalty
    ref={'voicedFraction':.9,'medianHz':440.}
    assert coarse_pitch_penalty(ref,{'voicedFraction':1.,'medianHz':440.*2**(2/12)})==0.
    assert coarse_pitch_penalty(ref,{'voicedFraction':1.,'medianHz':110.})>.8
    assert coarse_pitch_penalty(ref,{'voicedFraction':0.,'medianHz':None})==2.
    assert coarse_pitch_penalty({'voicedFraction':.2,'medianHz':440.}, {'voicedFraction':0.,'medianHz':None})==0.


def test_voiced_target_does_not_pick_noise_or_a_different_register(monkeypatch):
    from neural_invert.selection import select_preferred
    import neural_invert.selection as selection
    monkeypatch.setattr(selection,'pitch_summary',lambda x:{'voicedFraction':1. if x[0] else 0.,'medianHz':float(x[0]) or None})
    class Metric:
        def distances(self,target,candidates):return np.array([1.0,1.01,1.3])
    rows=[{'wave':np.array([0.]),'provenance':{}}, {'wave':np.array([110.]),'provenance':{}}, {'wave':np.array([440.]),'provenance':{}}]
    chosen=select_preferred(np.array([440.]),rows,Metric(),lambda x:x,'hash')
    assert chosen['wave'][0]==440.
    assert chosen['provenance']['coarsePitchPenalty']==0.


def test_available_matching_register_takes_priority_over_out_of_register_metric_winner(monkeypatch):
    from neural_invert.selection import select_preferred
    import neural_invert.selection as selection
    monkeypatch.setattr(selection,'pitch_summary',lambda x:{'voicedFraction':1.,'medianHz':float(x[0])})
    class Metric:
        def distances(self,target,candidates):return np.array([.01,3.])
    rows=[{'synth':'low','wave':np.array([110.]),'provenance':{}}, {'synth':'matching','wave':np.array([440.]),'provenance':{}}]
    chosen=select_preferred(np.array([440.]),rows,Metric(),lambda x:x,'hash')
    assert chosen['synth']=='matching'
    assert chosen['provenance']['matchingRegisterCandidates']==1
    # With no matching register available, retain a usable best-effort output.
    rows[1]['wave']=np.array([100.])
    chosen=select_preferred(np.array([440.]),rows,Metric(),lambda x:x,'hash')
    assert chosen['synth']=='low' and chosen['provenance']['matchingRegisterCandidates']==0
