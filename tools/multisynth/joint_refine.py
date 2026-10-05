"""Actual-render search over fixed Mixr source identities and mutable controls."""
from copy import deepcopy
import json
import numpy as np
from .search import ControlSpace


class MixSpace:
    def __init__(self, specs):
        self.spaces={name:ControlSpace(spec) for name,spec in specs.items()}

    def mutate(self, params, rng, sigma):
        result=deepcopy(params)
        sources=json.loads(result['sources'])
        if not isinstance(sources,list) or not 1<=len(sources)<=2 or not any(sources):
            raise ValueError('One or two sources required')
        active=[i for i,s in enumerate(sources) if s is not None]
        if any(sources[i]['synth'] not in self.spaces for i in active):
            raise ValueError('Unknown source synth')
        if len(active)==2 and rng.random()<.2:
            result['balance']=float(np.clip(result['balance']+rng.normal()*sigma,.1,.9))
        else:
            slots=active if len(active)==2 and rng.random()<.25 else [int(rng.choice(active))]
            for slot in slots:
                source=sources[slot]
                source['params']=self.spaces[source['synth']].mutate(source['params'],rng,sigma)
        result['sources']=json.dumps(sources,separators=(',',':'))
        return result


def optimize(starts, space, evaluate, *, budget, seed):
    """Retain incumbents; evaluate returns canonical params and finite scalar loss."""
    if not starts or type(budget) is not int or budget<0:
        raise ValueError('Nonempty starts and nonnegative integer budget required')
    rng=np.random.default_rng(seed);elites=[]
    for params in starts:
        canonical,score=evaluate(deepcopy(params))
        if not np.isfinite(score):raise ValueError('Invalid initial score')
        elites.append(dict(params=canonical,score=float(score)))
    elites.sort(key=lambda c:c['score']);initial=elites[0]['score'];trace=[initial];failures=0
    for step in range(budget):
        parent=elites[0] if step%3 else elites[int(rng.integers(len(elites)))]
        sigma=(.18,.09,.04,.015)[min(3,step*4//max(1,budget))]
        try:
            params=space.mutate(parent['params'],rng,sigma)
            canonical,score=evaluate(params)
            if not np.isfinite(score):raise ValueError('Invalid proposal score')
        except (ValueError,RuntimeError):
            failures+=1;trace.append(elites[0]['score']);continue
        candidate=dict(params=canonical,score=float(score))
        if all(candidate['params']!=c['params'] for c in elites):
            elites=sorted(elites+[candidate],key=lambda c:c['score'])[:4]
        trace.append(elites[0]['score'])
    return {**elites[0],'initialScore':initial,'attempts':budget,'initialRenders':len(starts),
            'failures':failures,'trace':trace,'seed':seed}
