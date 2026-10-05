"""Experimental frozen CLAP features and conservative reference-family grouping.

No production selector changes. Audio is encoded locally; text/source names are
used only for split grouping, never as model inputs.
"""
import hashlib
import json
from pathlib import Path
import re
import numpy as np


def validate_wave(wave):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not 0 < len(wave) <= 441000 or not np.isfinite(wave).all():
        raise ValueError('Expected finite mono 44100 Hz audio of at most ten seconds')
    return wave


def family_groups(references):
    """Connected ancestry aliases; numeric real-file variants grouped conservatively."""
    parent = list(range(len(references)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i, ref in enumerate(references):
        aliases = {'pcm:' + ref['pcm']}
        source = ref['source']
        node = source
        synthetic = 'sourceTarget' in source
        while isinstance(node, dict):
            for key in ('sha256', 'parameterHash', 'audioHash', 'baseId'):
                if node.get(key):
                    aliases.add(key + ':' + str(node[key]))
            if node is not source and node.get('id'):
                aliases.add('baseId:' + str(node['id']).split('/')[0])
            node = node.get('sourceTarget')
        if not synthetic:
            stem = Path(source['name']).stem.casefold()
            stem = re.sub(r'[^a-z]+', '', stem)
            if stem:
                aliases.add('recording-stem:' + stem)
        for alias in sorted(aliases):
            if alias in seen:
                a,b = root(i),root(seen[alias])
                parent[max(a,b)] = min(a,b)
            else:
                seen[alias] = i
    members = {}
    for i,ref in enumerate(references):
        members.setdefault(root(i),set()).add(ref['pcm'])
    identities = {k:hashlib.sha256('\n'.join(sorted(v)).encode()).hexdigest() for k,v in members.items()}
    return [identities[root(i)] for i in range(len(references))]


def fit_components(x, y, groups, prior):
    """Same reference-balanced logistic fit as preference.fit, arbitrary dimension."""
    import torch
    from .preference import reference_weights, TEMPERATURE, REGULARIZATION, SCALE_FLOOR
    x,y = np.asarray(x,float),np.asarray(y,float)
    prior = np.asarray(prior,float)
    if (x.shape != (len(y),len(prior)) or not len(y) or not np.isfinite(x).all()
            or not np.isfinite(y).all() or np.any(y == 0) or np.any(prior <= 0)):
        raise ValueError('Invalid strict preference components')
    prior = prior/prior.sum()
    rw = reference_weights(groups)
    scales = np.maximum(np.sqrt(rw @ (x*x)),SCALE_FLOOR)
    signed = torch.tensor(TEMPERATURE*np.sign(y)[:,None]*x/scales,dtype=torch.float64)
    rw,prior = torch.tensor(rw,dtype=torch.float64),torch.tensor(prior,dtype=torch.float64)
    logits = torch.log(prior).clone().requires_grad_(True)
    opt = torch.optim.Adam([logits],lr=.03)
    for _ in range(800):
        weights = torch.softmax(logits,0)
        loss = rw @ torch.nn.functional.softplus(signed @ weights)
        loss += REGULARIZATION*torch.sum(weights*torch.log(weights/prior))
        opt.zero_grad();loss.backward();opt.step()
    return torch.softmax(logits,0).detach().numpy(),scales


class Encoder:
    def __init__(self, weights):
        import torch
        from transformers import ClapAudioModelWithProjection, ClapFeatureExtractor
        self.torch = torch
        self.processor = ClapFeatureExtractor.from_pretrained(weights,local_files_only=True)
        # Weights-only deserialization; no hub code or text encoder needed.
        self.model, info = ClapAudioModelWithProjection.from_pretrained(
            weights,local_files_only=True,weights_only=True,output_loading_info=True)
        if info['missing_keys'] or info['mismatched_keys'] or info['error_msgs']:
            raise ValueError(f'Incomplete audio checkpoint: {info}')
        self.model.eval().requires_grad_(False)
        self.stats = []
        self.hooks = []
        self.blocks = []
        for i,stage in enumerate(self.model.audio_model.audio_encoder.layers[:3]):
            for j,block in enumerate(stage.blocks):
                self.blocks.append(f'audio_model.audio_encoder.layers.{i}.blocks.{j}')
                self.hooks.append(block.register_forward_hook(self._hook))

    def _hook(self, module, inputs, outputs):
        x = outputs[0]
        assert x.ndim == 3
        self.stats.append(self.torch.cat([x.mean(1),x.std(1,unbiased=False)],dim=-1))

    def __call__(self, wave):
        from scipy.signal import resample_poly
        x = resample_poly(validate_wave(wave),160,147).astype(np.float32)
        inputs = self.processor(x,sampling_rate=48000,return_tensors='pt',
                                padding='pad',truncation='rand_trunc')
        self.stats.clear()
        with self.torch.inference_mode():
            out = self.model(**inputs)
            style = self.torch.cat(self.stats,dim=-1)[0].numpy().copy()
            task = out.audio_embeds[0].numpy().copy()
        if not np.isfinite(style).all() or not np.isfinite(task).all():
            raise ValueError('Nonfinite encoder output')
        return {'task':task,'style':style}


def cosine(a,b):
    denom = np.linalg.norm(a)*np.linalg.norm(b)
    if not denom > 0:
        raise ValueError('Zero-norm embedding')
    return float(1-np.clip(np.dot(a,b)/denom,-1,1))
