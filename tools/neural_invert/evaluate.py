"""Render learned experts, refine global controls, and retain original Bfxr."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from match.bfxr_io import ParamSpace
from match.objective import MatchObjective
from match.optimizer import OptimizeSettings, StagedOptimizer, RENDER_SEED
from invert.predict import load_checkpoint, predict_wave


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rank_candidates(rows):
    if not rows:
        raise ValueError('No audible expert candidates')
    originals = [r for r in rows if r.get('expert') == 'original-bfxr']
    return {'selected':min(rows,key=lambda r:r['score']),
            'original':min(originals,key=lambda r:r['score']) if originals else None}


def mutate_controls(params,spec,rng,sigma):
    """Numeric controls use their full ranges; discrete pitch choices can change."""
    result = deepcopy(params)
    controls = [p for p in spec['params'] if p['name'] not in ('masterVolume','seed','instrumentSeed')
                and p['type'] != 'TEXT' and p['name'] in result]
    if not controls:
        return result
    for i in rng.choice(len(controls),size=min(len(controls),int(rng.integers(1,4))),replace=False):
        p = controls[i]; name = p['name']
        if p['type'] == 'BUTTONSELECT':
            result[name] = rng.choice(p['values']).item()
        elif p['type'] == 'KNOB_TRANSITION':
            if rng.random() < .25 and p.get('values'):
                result[name]['curve'] = rng.choice(p['values']).item()
            else:
                side = rng.choice(['start','end'])
                result[name][side] = float(np.clip(result[name][side]+rng.normal()*sigma*(p['max']-p['min']),p['min'],p['max']))
        elif isinstance(p.get('min'),(int,float)) and isinstance(p.get('max'),(int,float)):
            result[name] = float(np.clip(result[name]+rng.normal()*sigma*(p['max']-p['min']),p['min'],p['max']))
    return result


def rendered_candidates(candidates,renderer,objective):
    accepted,failures = [],[]
    for row in candidates:
        try:
            params,wave = renderer.render(row['synth'],row['params'],row['seed'])
            if np.max(np.abs(wave)) < 1e-6:
                raise ValueError('Silent prediction')
            score = float(objective.score_batch([wave])[0])
            accepted.append({**row,'params':params,'wave':wave,'score':score})
        except (ValueError,RuntimeError) as exc:
            failures.append({'synth':row['synth'],'error':str(exc)})
    return accepted,failures


def refine_candidate(row,renderer,objective,budget,seed):
    rng = np.random.default_rng(seed)
    best = deepcopy(row); trace = [best['score']]; failures = 0
    for step in range(budget):
        proposal = {**best,'params':mutate_controls(best['params'],renderer.specs[row['synth']],rng,
                    (.25,.12,.06,.025)[min(3,step*4//max(1,budget))])}
        accepted,rejected = rendered_candidates([proposal],renderer,objective)
        failures += len(rejected)
        if accepted and accepted[0]['score'] < best['score']:
            best = accepted[0]
        trace.append(best['score'])
    best['provenance'] = {**best.get('provenance',{}),'refinement':{
        'budget':budget,'seed':seed,'failures':failures,'initialScore':row['score'],
        'finalScore':best['score'],'trace':trace,'scope':'full numeric ranges and categorical controls'}}
    return best


class OriginalBfxr:
    def __init__(self,checkpoint,renderer):
        self.model,self.metadata = load_checkpoint(checkpoint)
        self.checkpoint = str(Path(checkpoint).resolve())
        self.checkpoint_hash = digest(checkpoint)
        self.renderer = renderer

    def approximate(self,wave,objective,budget=2000,seed=0):
        guesses = predict_wave(self.model,self.metadata,wave,top_k=3)
        settings = OptimizeSettings(budget=budget,top_k=1,verbose=False,rng_seed=seed,
                    seed_units=[(g['wave_type'],g['unit']) for g in guesses])
        optimizer = StagedOptimizer(ParamSpace(),self.renderer,objective,settings,target=wave)
        winners = optimizer.run()
        if not winners:
            raise ValueError('Original Bfxr produced no result')
        winner = winners[0]; params = optimizer.params_for(winner.unit,winner.wave_type)
        rendered = self.renderer.render(params,seed=RENDER_SEED)
        if rendered is None or not len(rendered) or np.max(np.abs(rendered)) < 1e-6:
            raise ValueError('Original Bfxr result is silent')
        return {'synth':'Bfxr','params':params,'seed':RENDER_SEED,'wave':rendered,
                'score':float(objective.score_batch([rendered])[0]),'expert':'original-bfxr',
                'provenance':{'checkpoint':self.checkpoint,'checkpointSha256':self.checkpoint_hash,
                    'budget':budget,'evaluations':optimizer.evals,'allowPitchShift':False,
                    'allowTimeStretch':False,'structureObjective':False,
                    'optimizer':'original StagedOptimizer with neural seeds'}}


def approximate(model,metadata,wave,renderer,original,starts=4,budget=128,bfxr_budget=2000,seed=0):
    from .predict import predict
    objective = MatchObjective(wave)
    proposals = predict(model,metadata,wave,renderer,per_synth=2)
    candidates,failures = rendered_candidates(proposals,renderer,objective)
    baseline=original.approximate(wave,objective,budget=bfxr_budget,seed=seed)
    if not candidates:
        return {'raw':None,'neural':None,'selected':baseline,'original':baseline,
                'allRaw':[],'allRefined':[],'failures':failures,
                'evaluations':len(proposals)+baseline['provenance']['evaluations']}
    raw = min(candidates,key=lambda r:r['score'])
    # Each engine supplies a prediction; choose distinct engines for refinement.
    initial=[];seen=set()
    for candidate in sorted(candidates,key=lambda r:r['score']):
        if candidate['synth'] not in seen:
            seen.add(candidate['synth']);initial.append(candidate)
        if len(initial) == starts:
            break
    refined=[refine_candidate(row,renderer,objective,budget,seed+i*71)
             for i,row in enumerate(initial)]
    choices=rank_candidates(refined+[baseline])
    return {'raw':raw,'neural':min(refined,key=lambda r:r['score']),**choices,
            'allRaw':candidates,'allRefined':refined,'failures':failures,
            'evaluations':len(proposals)+len(initial)*budget+baseline['provenance']['evaluations']}


def pitch_summary(wave):
    from match.features import FeatureExtractor
    wave=np.asarray(wave,dtype=np.float32).copy()
    wave=np.pad(wave,(0,max(2048-len(wave),0)))
    with torch.no_grad():
        f=FeatureExtractor().extract(torch.from_numpy(wave[None]))
    active=f.active[0]; voiced=f.voiced[0]&active
    return {'activeFrames':int(active.sum()),'voicedFrames':int(voiced.sum()),
            'voicedFraction':float(voiced.sum()/active.sum().clamp(min=1)),
            'medianHz':float(2**f.f0_log2[0][voiced].median()) if voiced.any() else None}


def serializable(row):
    if row is None:
        return None
    return {k:v for k,v in row.items() if k != 'wave'}
