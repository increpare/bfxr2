"""Joint Boomr/Transfxr Mixr inverse with masked parameter reconstruction.

Loss weights are control-space priorities, not a perceptual or physical metric.
Inputs to the codec are canonical native Mixr parameters. Source metadata is
not learned; decoding emits fixed source identities and deterministic seeds.
"""
from copy import deepcopy
import json

import numpy as np
import torch
from torch import nn

from .schema import ControlSchema
from .temporal import pack_features

ENGINES = ('Boomr', 'Transfxr')
MODEL_POLICY = dict(version='pair-temporal-inverse-v1', engines=list(ENGINES),
                    channels=[51, 64, 128], kernel=5, stride=2, padding=2,
                    relativeFrames=48, absoluteFrames=32, hidden=256,
                    activation='GELU', pooling='ordered-flatten',
                    scalars=[4080, 4082], ignoredIndices=[4081],
                    structures=['Boomr-only', 'Transfxr-only', 'both'],
                    heads='independent-complete-patch-hypotheses')
LOSS_POLICY = dict(version='pair-masked-control-v1', numericWeight=8.,
                   numericPriorities=dict(pitch=4., time=2., other=1.),
                   categoryWeight=.2, structureWeight=.3, balanceWeight=4.,
                   reduction='per-source-active-control-means-then-mean-present-sources',
                   masks=['absent-source', 'equal-endpoint-curve', 'disabled-Transfxr-morph',
                          'singleton-balance'],
                   coordinateSpace='normalized-native-controls', temperature=.1, routingKLWeight=.01)


class PairCodec:
    """Boomr controls, Transfxr controls, then balance/structure coordinates.

    Structure labels are 0 Boomr-only, 1 Transfxr-only, 2 both. Absent sources
    encode schema defaults. Singleton balance encodes/decodes to 0 or 1 and
    is ignored by the loss because Mixr gives a lone source full weight.
    """
    def __init__(self, specs):
        self.specs = {name: deepcopy(specs[name]) for name in ENGINES}
        self.schemas = {name: ControlSchema(spec) for name, spec in self.specs.items()}
        self.continuous_slices, self.categorical_slices = {}, {}
        self.cat_sizes = []
        offset = 0
        for name, schema in self.schemas.items():
            if schema.spec.get('name') != name or schema.fixed_text or not schema.continuous:
                raise ValueError('Unsupported pair source schema')
            self.continuous_slices[name] = slice(offset, offset+len(schema.continuous))
            offset += len(schema.continuous)
            start = len(self.cat_sizes)
            self.cat_sizes.extend(len(c['values']) for c in schema.categorical)
            self.categorical_slices[name] = slice(start, len(self.cat_sizes))
        self.balance_index = offset
        self.n_continuous = offset+1
        self.structure_index = len(self.cat_sizes)
        self.cat_sizes.append(3)

    def encode(self, params):
        try:
            sources = json.loads(params['sources'])
            balance = float(params['balance'])
            if (not isinstance(sources, list) or len(sources) != 2
                    or not any(source is not None for source in sources)
                    or not np.isfinite(balance) or not 0 <= balance <= 1):
                raise ValueError('Invalid pair sources or balance')
            units, categories = [], []
            for name, source in zip(ENGINES, sources):
                schema = self.schemas[name]
                if source is not None and (not isinstance(source, dict) or source.get('synth') != name):
                    raise ValueError('Pair sources must be ordered Boomr, Transfxr')
                controls = source['params'] if source is not None else schema.spec['defaults']
                # Validate before ControlSchema.encode can clip infinities.
                for control in schema.continuous:
                    value = schema._read(controls, control['path'])
                    if not np.isfinite(value) or not control['min'] <= value <= control['max']:
                        raise ValueError('Source controls must be finite and canonical')
                unit, cat = schema.encode(controls)
                units.append(unit); categories.append(cat)
            structure = 2 if all(source is not None for source in sources) else int(sources[0] is None)
            units.append(np.array([balance if structure == 2 else float(structure)], dtype=np.float32))
            categories.append(np.array([structure], dtype=np.int64))
            return np.concatenate(units), np.concatenate(categories)
        except (KeyError, TypeError, IndexError, OverflowError) as error:
            raise ValueError('Invalid canonical pair parameters') from error

    def decode(self, unit, categorical):
        unit, categorical = np.asarray(unit), np.asarray(categorical)
        if (unit.shape != (self.n_continuous,) or categorical.shape != (len(self.cat_sizes),)
                or unit.dtype.kind not in 'fiu' or not np.isfinite(unit).all()
                or categorical.dtype.kind not in 'iu'
                or (categorical < 0).any() or (categorical >= self.cat_sizes).any()):
            raise ValueError('Invalid pair control vectors')
        structure = int(categorical[self.structure_index])
        sources = []
        for slot, name in enumerate(ENGINES):
            if structure not in (slot, 2):
                sources.append(None)
                continue
            schema = self.schemas[name]
            controls = schema.decode(unit[self.continuous_slices[name]], categorical[self.categorical_slices[name]])
            for key in schema.fixed_randomness:
                controls[key] = .5
            sources.append(dict(synth=name, name=name, params=controls, renderSeed=.5))
        balance = float(np.clip(unit[self.balance_index], 0, 1)) if structure == 2 else float(structure)
        return dict(sources=json.dumps(sources, separators=(',', ':'), allow_nan=False),
                    balance=balance, seed=.5, masterVolume=.5)


class PairInverse(nn.Module):
    """Separate ordered relative/absolute temporal streams; complete mode heads."""
    def __init__(self, codec, modes=4):
        super().__init__()
        if type(modes) is not int or modes < 1:
            raise ValueError('Pair modes must be a positive integer')
        self.codec, self.modes = codec, modes

        def stream():
            return nn.Sequential(nn.Conv1d(51, 64, 5, stride=2, padding=2), nn.GELU(),
                                 nn.Conv1d(64, 128, 5, stride=2, padding=2), nn.GELU(), nn.Flatten(1))

        self.relative, self.absolute = stream(), stream()
        self.encoder = nn.Sequential(nn.Linear(128*(12+8)+2, 256), nn.GELU())
        self.numeric_heads = nn.ModuleList([nn.Linear(256, codec.n_continuous) for _ in range(modes)])
        self.category_heads = nn.ModuleList([
            nn.ModuleList([nn.Linear(256, size) for size in codec.cat_sizes]) for _ in range(modes)])
        self.mode_head = nn.Linear(256, modes)

    def forward(self, features):
        relative, absolute, scalars = pack_features(features)
        hidden = self.encoder(torch.cat((self.relative(relative), self.absolute(absolute), scalars), -1))
        return dict(continuous=torch.stack([head(hidden).sigmoid() for head in self.numeric_heads], 1),
                    categorical=[torch.stack([heads[i](hidden) for heads in self.category_heads], 1)
                                 for i in range(len(self.codec.cat_sizes))],
                    mode_logits=self.mode_head(hidden))


def pair_energy(prediction, continuous, categorical, codec):
    """Return B×modes masked parameter energy, suitable for mixture_loss."""
    estimated = prediction['continuous']
    if (continuous.ndim != 2 or continuous.shape[1] != codec.n_continuous
            or estimated.ndim != 3 or estimated.shape[0] != len(continuous)
            or estimated.shape[2] != codec.n_continuous or estimated.shape[1] < 1
            or categorical.shape != (len(continuous), len(codec.cat_sizes))
            or categorical.dtype != torch.int64
            or not continuous.is_floating_point() or not estimated.is_floating_point()
            or not torch.isfinite(continuous).all() or not torch.isfinite(estimated).all()
            or ((continuous < 0) | (continuous > 1)).any()
            or ((estimated < 0) | (estimated > 1)).any()
            or len(prediction['categorical']) != len(codec.cat_sizes)):
        raise ValueError('Invalid pair continuous/categorical shapes or values')
    batch, modes = estimated.shape[:2]
    for i, size in enumerate(codec.cat_sizes):
        logits = prediction['categorical'][i]
        if (logits.shape != (batch, modes, size) or not logits.is_floating_point()
                or not torch.isfinite(logits).all()
                or ((categorical[:, i] < 0) | (categorical[:, i] >= size)).any()):
            raise ValueError('Invalid pair categorical targets or logits')

    def cross_entropy(index):
        return -prediction['categorical'][index].log_softmax(-1).gather(
            -1, categorical[:, index, None, None].expand(-1, modes, 1)).squeeze(-1)

    structure = categorical[:, codec.structure_index]
    total = torch.zeros_like(estimated[:, :, 0])
    present_count = continuous.new_zeros(batch)
    for slot, name in enumerate(ENGINES):
        schema = codec.schemas[name]
        ns, cs = codec.continuous_slices[name], codec.categorical_slices[name]
        true = continuous[:, ns]
        present = (structure == slot) | (structure == 2)
        numeric_mask = torch.ones_like(true)
        names = {control['name']: i for i, control in enumerate(schema.continuous)}
        cats = {control['name']: cs.start+i for i, control in enumerate(schema.categorical)}
        morph_active = None
        if name == 'Transfxr':
            wave_values = schema.categorical[cats['waveTo']-cs.start]['values']
            morph_active = categorical[:, cats['waveTo']] != wave_values.index(-1)
            for control in ('morph.start', 'morph.end'):
                numeric_mask[:, names[control]] = morph_active.to(true.dtype)
        priorities = []
        for control in schema.continuous:
            lower = control['name'].lower()
            priorities.append(4. if any(key in lower for key in ('pitch', 'frequency', 'vibrato')) else
                              2. if any(key in lower for key in ('attack', 'sustain', 'decay', 'duration', 'release', 'repeat', 'strum')) else 1.)
        weights = numeric_mask*true.new_tensor(priorities)
        numeric = ((estimated[:, :, ns]-true[:, None]).square()*weights[:, None]).sum(-1)
        numeric = numeric/weights.sum(-1).clamp(min=1)[:, None]
        category_total = torch.zeros_like(numeric)
        category_count = true.new_zeros(batch)
        for i, control in enumerate(schema.categorical):
            active = torch.ones_like(present)
            if control['name'].endswith('.curve'):
                prefix = control['name'][:-6]
                start, end = names[prefix+'.start'], names[prefix+'.end']
                span = schema.continuous[start]['max']-schema.continuous[start]['min']
                active = ((true[:, start]-true[:, end])*span).abs() > 1e-6
                if name == 'Transfxr' and prefix == 'morph':
                    active = active & morph_active
            category_total = category_total+cross_entropy(cs.start+i)*active[:, None]
            category_count = category_count+active
        source_energy = 8*numeric+.2*category_total/category_count.clamp(min=1)[:, None]
        total = total+source_energy*present[:, None]
        present_count = present_count+present
    balance = (estimated[:, :, codec.balance_index]-continuous[:, None, codec.balance_index]).square()
    energy = (total/present_count.clamp(min=1)[:, None]
              + .3*cross_entropy(codec.structure_index)+4*balance*(structure == 2)[:, None])
    if not torch.isfinite(energy).all():
        raise ValueError('Nonfinite pair reconstruction energy')
    return energy
