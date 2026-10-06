"""Reference-balanced nonnegative listener metric with six texture blocks."""
import json
from pathlib import Path
import numpy as np
import torch
from . import listener_metric, texture
from .preference import reference_weights
from neural_invert.data import file_hash

VERSION='texture-listener-v1'
NAMES=(*listener_metric.NAMES,*('texture_'+n for n in texture.NAMES))
PRIOR=np.r_[listener_metric.PRIOR*.7,np.full(6,.3/6)]
RECIPE=dict(steps=800,learningRate=.03,temperature=4.,regularization=.08,scaleFloor=.01,
            folds=5,foldSeed=1729,prior=PRIOR.tolist(),gateAblationImprovement=.03,
            gateMustMatchFrozenPreference=True,gateMustMatchSoft=True)


def bindings():
    return {**listener_metric.bindings(),**{str(p):file_hash(p) for p in (Path(__file__),Path(texture.__file__))}}


def fit(differences,preferences,references):
    x,y,refs=np.asarray(differences,float),np.asarray(preferences,float),np.asarray(references)
    if x.shape!=(len(y),27) or not len(y) or refs.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(y==0):
        raise ValueError('Need finite27-component strict preferences and reference IDs')
    weights=reference_weights(refs);scales=np.maximum(np.sqrt(weights@(x*x)),RECIPE['scaleFloor'])
    signed=torch.tensor(RECIPE['temperature']*np.sign(y)[:,None]*x/scales,dtype=torch.float64)
    row_weights=torch.tensor(weights,dtype=torch.float64);prior=torch.tensor(PRIOR,dtype=torch.float64)
    logits=prior.log().clone().requires_grad_(True);optimizer=torch.optim.Adam([logits],lr=RECIPE['learningRate'])
    for _ in range(RECIPE['steps']):
        w=logits.softmax(0)
        loss=row_weights@torch.nn.functional.softplus(signed@w)+RECIPE['regularization']*(w*(w/prior).log()).sum()
        if not torch.isfinite(loss):raise ValueError('Nonfinite texture-listener loss')
        optimizer.zero_grad();loss.backward();optimizer.step()
    return TextureListener(logits.softmax(0).detach().numpy(),scales)


class TextureListener:
    def __init__(self,weights=None,scales=None):
        self.weights=np.array(PRIOR if weights is None else weights,float,copy=True)
        self.scales=np.array(np.ones(27) if scales is None else scales,float,copy=True)
        if self.weights.shape!=(27,) or self.scales.shape!=(27,) or not np.isfinite(self.weights).all() or not np.isfinite(self.scales).all() or (self.weights<0).any() or self.weights.sum()<=0 or (self.scales<=0).any():
            raise ValueError('Invalid texture-listener weights/scales')
        self.weights/=self.weights.sum()
    def objective(self,reference):return PreparedObjective(self,reference)
    def save(self,path,provenance):
        path=Path(path)
        if path.exists():raise FileExistsError('Preserve texture-listener checkpoint')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(dict(version=VERSION,components=NAMES,recipe=RECIPE,textureConfig=texture.CONFIG,
            bindings=bindings(),weights=self.weights.tolist(),scales=self.scales.tolist(),provenance=provenance),indent=2,allow_nan=False)+'\n')
    @classmethod
    def load(cls,path):
        d=json.loads(Path(path).read_text())
        if d.get('version')!=VERSION or d.get('components')!=list(NAMES) or d.get('recipe')!=RECIPE or d.get('textureConfig')!=texture.CONFIG or d.get('bindings')!=bindings():
            raise ValueError('Texture-listener checkpoint policy/code mismatch')
        return cls(d['weights'],d['scales'])


class PreparedObjective:
    def __init__(self,model,reference):
        self.model=model;self.base=listener_metric.ListenerMetric().objective(reference);self.reference=texture.describe(reference)
    def components(self,wave):
        return np.r_[self.base.components(wave),texture.components(self.reference,texture.describe(wave))]
    def score(self,wave):return float(self.components(wave)@(self.model.weights/self.model.scales))
