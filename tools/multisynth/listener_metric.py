"""Small listener-trained ranking objective; no inverse or synth code changes."""
from pathlib import Path
import json
import numpy as np
import torch
from . import preference
from .features import describe
from .soft_periodicity import SoftPeriodicityObjective
from neural_invert.data import file_hash

VERSION='listener-metric-v1'
NAMES=(*preference.NAMES,'soft_periodicity')
PRIOR=np.r_[preference.PRIOR*.5,.5]
RECIPE=dict(steps=800,learningRate=.03,temperature=4.,regularization=.08,scaleFloor=.01,
            folds=5,foldSeed=1729,prior=PRIOR.tolist(),training='strict external likeness; equal total weight per reference',
            validation='connected source/tag groups held out; train-only scales',
            gateOldImprovement=.03,gateMustMatchSoft=True)


def bindings():
    paths=[Path(__file__),Path(__file__).with_name('preference.py'),Path(__file__).with_name('features.py'),
           Path(__file__).with_name('gesture.py'),Path(__file__).with_name('soft_periodicity.py')]
    paths += [Path('tools/match')/name for name in ('structure.py','objective.py','features.py','audio.py')]
    return {str(p):file_hash(p) for p in paths}


def source_groups(records):
    """Union exact identities and conservative tags/collection directories."""
    parent={}
    def find(key):
        parent.setdefault(key,key)
        if parent[key]!=key:parent[key]=find(parent[key])
        return parent[key]
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    included=set()
    for row in records:
        source=row['source'];path=source.get('path')
        if not isinstance(path,str) or not path or source.get('synthetic'):continue
        pcm='pcm:'+row['reference'];included.add(row['reference']);find(pcm)
        if source.get('sha256'):union(pcm,'file:'+source['sha256'])
        if '/tags/' in path.replace('\\','/'):
            group='tag:'+path.replace('\\','/').split('/tags/',1)[1].split('/')[0]
        else:group='collection:'+str(Path(source['name']).parent)
        union(pcm,group)
    return {pcm:find('pcm:'+pcm) for pcm in sorted(included)}


def fit(differences,preferences,references):
    x,y,refs=np.asarray(differences,float),np.asarray(preferences,float),np.asarray(references)
    if (x.shape!=(len(y),21) or not len(y) or refs.shape!=y.shape or not np.isfinite(x).all()
            or not np.isfinite(y).all() or np.any(y==0)):
        raise ValueError('Need finite21-component strict preferences and reference identities')
    weights=preference.reference_weights(refs)
    scales=np.maximum(np.sqrt(weights@(x*x)),RECIPE['scaleFloor'])
    signed=torch.tensor(RECIPE['temperature']*np.sign(y)[:,None]*x/scales,dtype=torch.float64)
    row_weights=torch.tensor(weights,dtype=torch.float64);prior=torch.tensor(PRIOR,dtype=torch.float64)
    logits=prior.log().clone().requires_grad_(True);optimizer=torch.optim.Adam([logits],lr=RECIPE['learningRate'])
    for _ in range(RECIPE['steps']):
        w=logits.softmax(0)
        loss=row_weights@torch.nn.functional.softplus(signed@w)+RECIPE['regularization']*(w*(w/prior).log()).sum()
        if not torch.isfinite(loss):raise ValueError('Nonfinite listener loss')
        optimizer.zero_grad();loss.backward();optimizer.step()
    return ListenerMetric(logits.softmax(0).detach().numpy(),scales)


class ListenerMetric:
    def __init__(self,weights=None,scales=None):
        self.weights=np.array(PRIOR if weights is None else weights,dtype=float,copy=True)
        self.scales=np.array(np.ones(21) if scales is None else scales,dtype=float,copy=True)
        if (self.weights.shape!=(21,) or self.scales.shape!=(21,) or not np.isfinite(self.weights).all()
                or not np.isfinite(self.scales).all() or (self.weights<0).any() or self.weights.sum()<=0 or (self.scales<=0).any()):
            raise ValueError('Invalid listener weights/scales')
        self.weights/=self.weights.sum()
    def objective(self,reference):return PreparedObjective(self,reference)
    def save(self,path,provenance):
        path=Path(path)
        if path.exists():raise FileExistsError('Preserve listener checkpoint')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(version=VERSION,components=NAMES,recipe=RECIPE,bindings=bindings(),
            weights=self.weights.tolist(),scales=self.scales.tolist(),provenance=provenance),indent=2,allow_nan=False)+'\n')
    @classmethod
    def load(cls,path):
        d=json.loads(Path(path).read_text())
        if d.get('version')!=VERSION or d.get('components')!=list(NAMES) or d.get('recipe')!=RECIPE or d.get('bindings')!=bindings():
            raise ValueError('Listener checkpoint policy/code mismatch')
        return cls(d['weights'],d['scales'])


class PreparedObjective:
    def __init__(self,model,reference):
        self.model=model;self.reference=describe(reference);self.auditory=preference.PreferenceMetric()
        self.soft=SoftPeriodicityObjective(reference)
    def components(self,wave):
        result=np.r_[self.auditory.raw_components(self.reference,[describe(wave)])[0],self.soft.score(wave)]
        if not np.isfinite(result).all():raise ValueError('Nonfinite listener components')
        return result
    def score(self,wave):return float(self.components(wave)@(self.model.weights/self.model.scales))
