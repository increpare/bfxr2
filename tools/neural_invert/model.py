"""Shared learned audio encoder with separate generator-conditioned synth heads."""
import torch
from torch import nn
from torch.nn import functional as F
from .schema import ControlSchema


class ExpertHead(nn.Module):
    def __init__(self, spec, hidden):
        super().__init__()
        schema = ControlSchema(spec)
        self.generator = nn.Linear(hidden, len(spec['presets']))
        self.condition = nn.Embedding(len(spec['presets']), 24)
        self.hidden = nn.Sequential(nn.Linear(hidden+24, hidden//2), nn.GELU())
        self.continuous = nn.Linear(hidden//2, len(schema.continuous))
        self.categorical = nn.ModuleList([nn.Linear(hidden//2, len(c['values'])) for c in schema.categorical])

    def forward(self, embedding, generator=None):
        logits = self.generator(embedding)
        if generator is None:
            generator = logits.argmax(dim=-1)
        hidden = self.hidden(torch.cat([embedding, self.condition(generator)], dim=-1))
        return {'generator': logits, 'continuous': self.continuous(hidden).sigmoid(),
                'categorical': [head(hidden) for head in self.categorical]}


class MultiSynthModel(nn.Module):
    def __init__(self, specs, input_dim, hidden=256):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, hidden), nn.LayerNorm(hidden), nn.GELU(),
                                     nn.Linear(hidden, hidden), nn.LayerNorm(hidden), nn.GELU())
        self.heads = nn.ModuleDict({name: ExpertHead(spec, hidden) for name, spec in specs.items()})

    def forward(self, features, synth, generator=None):
        return self.heads[synth](self.encoder(features), generator)


def supervised_loss(prediction, labels):
    numeric = F.mse_loss(prediction['continuous'], labels['continuous'])
    generator = F.cross_entropy(prediction['generator'], labels['generator'])
    discrete = [F.cross_entropy(logits, labels['categorical'][:, i]) for i, logits in enumerate(prediction['categorical'])]
    cat_loss = torch.stack(discrete).mean() if discrete else numeric.new_zeros(())
    return numeric*8 + generator*.4 + cat_loss*.6
