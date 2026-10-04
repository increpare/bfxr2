"""Neural expert predictions, decoded across declared global control ranges."""
import hashlib
from pathlib import Path
import numpy as np
import torch
from .features import describe, DIM, VERSION, FEATURE_HASH, FEATURE_CODE_HASH
from .model import MultiSynthModel
from .schema import ControlSchema


def load_model(path):
    path = Path(path)
    if path.is_dir():
        path = path/'best.pt'
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    metadata = checkpoint['metadata']
    if metadata.get('featureVersion') != VERSION or metadata.get('featureDim') != DIM:
        raise ValueError('Checkpoint feature representation is incompatible')
    if metadata.get('featureHash') != FEATURE_HASH:
        raise ValueError('Checkpoint feature hash is incompatible')
    if metadata.get('featureCodeHash') != FEATURE_CODE_HASH:
        raise ValueError('Checkpoint feature code hash is incompatible')
    for key in ('mean','std'):
        vector = np.asarray(metadata['normalization'][key])
        if vector.shape != (DIM,) or not np.isfinite(vector).all() or (key == 'std' and np.any(vector<=0)):
            raise ValueError('Checkpoint feature normalization is invalid')
    if set(metadata['engines']) != set(metadata['specs']):
        raise ValueError('Checkpoint engine schemas disagree')
    model = MultiSynthModel(metadata['specs'], DIM, metadata.get('hidden', 256))
    model.load_state_dict(checkpoint['model'], strict=True); model.eval()
    metadata = dict(metadata, checkpointHash=hashlib.sha256(path.read_bytes()).hexdigest(),
                    checkpointEpoch=checkpoint.get('epoch'))
    return model, metadata


def predict(model, metadata, wave, renderer, per_synth=2):
    if per_synth < 1:
        raise ValueError('At least one proposal per synth required')
    if metadata.get('sourceHash') and metadata['sourceHash'] != renderer.inventory['sourceHash']:
        raise ValueError('Neural checkpoint DSP source hash differs from renderer')
    if metadata['featureVersion'] != VERSION:
        raise ValueError('Neural feature version mismatch')
    packed = describe(wave)
    mean, std = (np.asarray(metadata['normalization'][key], dtype=np.float32) for key in ('mean','std'))
    device = next(model.parameters()).device
    x = torch.from_numpy((packed-mean)/std).to(device)[None]
    if metadata.get('ignorePeakGain', True):
        x[:, -2] = 0
    candidates = []
    with torch.no_grad():
        embedding = model.encoder(x)
        for name in metadata['engines']:
            spec = metadata['specs'][name]; schema = ControlSchema(spec); head = model.heads[name]
            probabilities = head.generator(embedding).softmax(-1)[0]
            ranks = probabilities.argsort(descending=True)[:min(per_synth, len(spec['presets']))].tolist()
            for rank, generator_index in enumerate(ranks):
                generator = spec['presets'][generator_index]
                prediction = head(embedding, torch.tensor([generator_index], device=device))
                unit = prediction['continuous'][0].cpu().numpy()
                categorical = [int(logits[0].argmax()) for logits in prediction['categorical']]
                # Anchors contribute TEXT and randomness only: all mutable controls
                # are overwritten by neural predictions with global decoding.
                seed = 20261004+generator_index
                anchor = renderer.sample(name, generator, seed)
                params = schema.decode(unit, categorical, anchor)
                provenance = {'method': 'neural-global-controls', 'neuralRaw': True, 'generator': generator,
                              'generatorProbability': float(probabilities[generator_index]), 'proposalRank': rank,
                              'checkpointHash': metadata.get('checkpointHash'), 'anchorSeed': seed,
                              'fixedText': schema.fixed_text, 'fixedRandomness': schema.fixed_randomness,
                              'structureScope': 'TEXT phrase is a fixed generator draw; phrase-dependent controls do not regenerate it.' if schema.fixed_text else 'numeric individual synth'}
                # Canonicalize through actual DSP, surfacing failures to evaluator.
                # Returning an unrendered fallback would hide broken expert proposals.
                try:
                    canonical, _ = renderer.render(name, params, seed)
                except (ValueError, RuntimeError) as error:
                    provenance['renderError'] = str(error); canonical = params
                candidates.append({'synth': name, 'params': canonical, 'seed': seed, 'provenance': provenance})
    return candidates
