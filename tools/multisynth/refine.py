"""Continuous refinement inside a fixed recipe, with an explicit trust region."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import numpy as np

from .features import describe

# Melody/event identity and random texture are fixed while numeric tone is refined.
FIXED = {'seed','masterVolume','instrumentSeed','noteCount','contour','rhythm',
         'key','scale','octave','phrase','sources','layers','align',
         'syllables','packets','count','arcs','folds','fragments','bounces',
         'voices','repeats','steps','grains','events'}


def board_specs(snapshot):
    script = r'''
const path=require('node:path');
const api=require(path.join(process.argv[1],'tests/helpers/board-context.js')).createBoardContext();
process.stdout.write(JSON.stringify(api.run(`Stackr.sources().map(C=>{
 const s=new C();return {name:s.name,params:s.param_info.map(raw=>{
  const p=s.get_param_normalized(raw);return {name:p.name,type:p.type,min:p.min_value,max:p.max_value};
 })};})`)));
'''
    rows = json.loads(subprocess.check_output(['node','-e',script,str(Path(snapshot).resolve())],text=True))
    return {r['name']:r for r in rows}


def _get(obj,path):
    for key in path:
        obj=obj[key]
    return obj


class RecipeSpace:
    def __init__(self,anchor,spec=None,source_specs=None):
        self.board = source_specs is not None
        self.controls=[]
        original=self.decode(anchor)
        if self.board:
            for index,source in enumerate(original['sources']):
                self.add(original,('sources',index,'params'),source_specs[source['synth']])
            if len(original['sources'])>1:
                self.controls += [(('balance',),max(0,anchor['balance']-.22),min(1,anchor['balance']+.22)),
                                  (('offset',),max(-1,anchor['offset']-.12),min(1,anchor['offset']+.12))]
        else:
            self.add(original,(),spec)

    def decode(self,params):
        result=deepcopy(params)
        if self.board:
            result['sources']=json.loads(result['sources'])
        return result

    def add(self,original,prefix,spec):
        for p in spec['params']:
            name=p['name']
            if name in FIXED or p['type'] in ('TEXT','BUTTONSELECT'):
                continue
            low,high=p.get('min'),p.get('max')
            if not isinstance(low,(int,float)) or not isinstance(high,(int,float)) or high<=low:
                continue
            paths = [prefix+(name,side) for side in ('start','end')] if p['type']=='KNOB_TRANSITION' else [prefix+(name,)]
            for path in paths:
                try:
                    value=_get(original,path)
                except (KeyError,TypeError):
                    continue
                if not isinstance(value,(int,float)) or isinstance(value,bool):
                    continue
                lo,hi=max(low,value-.22*(high-low)),min(high,value+.22*(high-low))
                if name in ('duration','attack','release') and value>0:
                    lo,hi=max(low,value*.4),min(high,value*2.5)
                self.controls.append((path,lo,hi))

    def mutate(self,params,rng,sigma):
        result=self.decode(params)
        if self.controls:
            for i in rng.choice(len(self.controls),size=min(len(self.controls),int(rng.integers(1,4))),replace=False):
                path,low,high=self.controls[i]
                parent=_get(result,path[:-1])
                parent[path[-1]]=float(np.clip(parent[path[-1]]+rng.normal()*sigma*(high-low),low,high))
        if self.board:
            result['sources']=json.dumps(result['sources'],separators=(',',':'))
        return result


def recipe_key(row):
    return (row['backend'],row['synth'],row.get('signature',row.get('preset','')))


def distinct_starts(rows,scores,count):
    chosen,seen=[],set()
    for index in np.argsort(scores,kind='stable'):
        key=recipe_key(rows[index])
        if key not in seen:
            chosen.append(int(index));seen.add(key)
        if len(chosen)>=count:
            break
    return chosen


def refine(start,render,spec,source_specs,reference,metric,other_metric,budget,seed):
    """Return an incumbent plus diverse best proposals under both objectives."""
    rng=np.random.default_rng(seed)
    space=RecipeSpace(start['params'],spec,source_specs)
    initial=deepcopy(start)
    params,wave=render(initial)
    descriptor=describe(wave)
    initial.update(params=params,score=float(metric.distances(reference,descriptor[None])[0]),
                   otherScore=float(other_metric.distances(reference,descriptor[None])[0]))
    elites=[initial];alternatives=[initial];trace=[initial['score']];failures=0
    for step in range(budget):
        parent=elites[0] if step%3 else elites[int(rng.integers(len(elites)))]
        sigma=(.22,.12,.06,.025)[min(3,step*4//max(budget,1))]
        proposal={**parent,'params':space.mutate(parent['params'],rng,sigma)}
        try:
            params,wave=render(proposal)
            descriptor=describe(wave)
            proposal.update(params=params,score=float(metric.distances(reference,descriptor[None])[0]),
                            otherScore=float(other_metric.distances(reference,descriptor[None])[0]))
        except (ValueError,RuntimeError):
            failures+=1
            trace.append(elites[0]['score'])
            continue
        elites=sorted(elites+[proposal],key=lambda r:r['score'])[:4]
        alternatives=sorted(alternatives+[proposal],key=lambda r:r['otherScore'])[:2]
        trace.append(elites[0]['score'])
    return elites+alternatives,{'initialScore':initial['score'],'finalScore':elites[0]['score'],
                                'evaluations':budget,'failures':failures,'trace':trace}
