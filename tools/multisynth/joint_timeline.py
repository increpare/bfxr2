"""Experimental native Stackr refinement scored in the full sound context."""
from collections import Counter
from copy import deepcopy
import json
import numpy as np
from neural_invert.evaluate import mutate_controls


def refine(params,renderer,specs,objective,budget,seed,joint):
    rng=np.random.default_rng(seed)
    params,wave=renderer.render(deepcopy(params))
    score=float(objective.score_batch([wave])[0]);trace=[score]
    starts=[l['start'] for l in json.loads(params['layers'])]
    attempted=Counter(source=0,timeline=0);accepted=Counter(source=0,timeline=0);failures=0
    for step in range(budget):
        proposal=deepcopy(params);layers=json.loads(proposal['layers'])
        slot=int(rng.integers(len(layers)));layer=layers[slot]
        scale=(1,.5,.25,.1)[min(3,step*4//budget)]
        # Draw in both arms, keeping random-step schedules comparable.
        kind='source' if rng.random()<.75 and joint else 'timeline'
        attempted[kind]+=1
        if kind=='source':
            layer['params']=mutate_controls(layer['params'],specs[layer['synth']],rng,.12*scale)
        else:
            field=rng.choice(['start','gain','pitch'])
            if field=='start':
                layer[field]=0. if slot==0 else float(np.clip(layer[field]+rng.normal()*.025*scale,max(0,starts[slot]-.04),starts[slot]+.04))
            elif field=='gain':layer[field]=float(np.clip(layer[field]+rng.normal()*.2*scale,.01,1))
            else:layer[field]=float(np.clip(layer[field]+rng.normal()*2*scale,-12,12))
        proposal['layers']=json.dumps(layers)
        try:
            pp,ww=renderer.render(proposal)
            if not len(ww) or not np.isfinite(ww).all() or np.max(np.abs(ww))<1e-8:
                raise ValueError('Silent or nonfinite proposal')
            value=float(objective.score_batch([ww])[0])
            if not np.isfinite(value):raise ValueError('Nonfinite score')
            if value<score:
                params,wave,score=pp,ww,value;accepted[kind]+=1
        except (ValueError,RuntimeError):failures+=1
        trace.append(score)
    return dict(params=params,wave=wave,score=score,trace=trace,attempted=dict(attempted),accepted=dict(accepted),failures=failures)
