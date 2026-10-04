import numpy as np


def test_both_objectives_choose_from_shared_pool_without_worsening():
    from multisynth.paired_search import search_pair
    class Metric:
        def __init__(self,goal):self.goal=goal
        def distances(self,target,candidates):return np.abs(candidates[:,0]-self.goal)
    rows=[{'backend':'legacy','synth':'Test','preset':str(v),'seed':7,'params':{'pitch':v}} for v in (.2,.8)]
    descriptors=np.array([[.2],[.8]])
    specs={'Test':{'params':[{'name':'pitch','type':'KNOB','min':0,'max':1}]}}
    def render(r):return r['params'],np.array([r['params']['pitch']])
    result=search_pair(rows,descriptors,np.array([0]),Metric(.1),Metric(.9),render,specs,{},
                       starts=1,budget=8,seed=12,describe_fn=lambda wave:wave)
    pool=result['pool']
    assert len(result['traces'])==2 and result['evaluations']==16
    assert result['choices']['v5']['v5Score']==min(r['v5Score'] for r in pool)
    assert result['choices']['v4']['v4Score']==min(r['v4Score'] for r in pool)
    for t in result['traces']: assert np.all(np.diff(t['trace'])<=0)
    assert result['choices']['v5']['v5Score']<=.1+1e-9
    assert result['choices']['v4']['v4Score']<=.1+1e-9
