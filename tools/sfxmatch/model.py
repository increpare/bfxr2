"""Spectrogram CNN -> which synth, and binned controls for every synth.

Controls are classified into bins rather than regressed. One sound often has
several valid parameter settings; a regression averages them into a setting
that matches none, while a distribution over bins keeps the modes apart and
can be sampled for several distinct proposals.

Every synth has its own head, but all heads write the same padded layout
(preset family | controls x bins | categoricals x options) so one masked loss
covers a mixed batch.
"""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from neural_invert.schema import ControlSchema
from .mel import BANDS, FRAMES, REL_FRAMES

BINS = 32


class Block(nn.Module):
    def __init__(self, cin, cout, stride):
        super().__init__()
        self.a = nn.Conv2d(cin, cout, 3, stride, 1, bias=False)
        self.b = nn.Conv2d(cout, cout, 3, 1, 1, bias=False)
        self.na, self.nb = nn.BatchNorm2d(cout), nn.BatchNorm2d(cout)
        self.skip = None if stride == 1 and cin == cout else nn.Sequential(
            nn.Conv2d(cin, cout, 1, stride, bias=False), nn.BatchNorm2d(cout))

    def forward(self, x):
        y = F.gelu(self.na(self.a(x)))
        y = self.nb(self.b(y))
        return F.gelu(y + (x if self.skip is None else self.skip(x)))


def tower(widths, stem_stride):
    """One residual block per stage, each halving both axes. Sized for ~1k rows/s on an M1 Max."""
    layers = [nn.Conv2d(1, widths[0], 3, stem_stride, 1, bias=False), nn.BatchNorm2d(widths[0]), nn.GELU()]
    for cin, cout in zip(widths, widths[1:]):
        layers.append(Block(cin, cout, 2))
    return nn.Sequential(*layers)


class InverseModel(nn.Module):
    def __init__(self, specs, width=512):
        super().__init__()
        self.names = list(specs)
        schemas = [ControlSchema(spec) for spec in specs.values()]
        controls = [len(s.continuous) for s in schemas]
        options = [[len(c['values']) for c in s.categorical] for s in schemas]
        generators = [len(spec['presets']) for spec in specs.values()]
        self.C, self.K, self.G = max(controls), max(len(o) for o in options), max(generators)
        self.V = max(max(o, default=1) for o in options)
        synths = len(self.names)
        control_mask = torch.zeros(synths, self.C)
        option_mask = torch.zeros(synths, self.K, self.V, dtype=torch.bool)
        generator_mask = torch.zeros(synths, self.G, dtype=torch.bool)
        for i in range(synths):
            control_mask[i, :controls[i]] = 1
            generator_mask[i, :generators[i]] = True
            for k, count in enumerate(options[i]):
                option_mask[i, k, :count] = True
        self.register_buffer('control_mask', control_mask)
        self.register_buffer('option_mask', option_mask)
        self.register_buffer('generator_mask', generator_mask)
        self.controls, self.options = controls, options
        self.absolute = tower([32, 64, 128, 256, 384], 2)   # 64x256 -> 2x8
        self.relative = tower([32, 64, 128, 256], 1)        # 64x32  -> 8x4
        flat = 384*(BANDS//32)*(FRAMES//32) + 256*(BANDS//8)*(REL_FRAMES//8)
        self.embed = nn.Sequential(nn.Linear(flat+1, width), nn.GELU(), nn.Dropout(.1))
        self.synth = nn.Linear(width, synths)
        out = self.G + self.C*BINS + self.K*self.V
        self.heads = nn.ModuleList(nn.Sequential(nn.Linear(width, 384), nn.GELU(), nn.Linear(384, out))
                                   for _ in range(synths))

    def encode(self, mel, rel, duration):
        """mel/rel: uint8 or float in [0,255] of shape (B, bands, frames); duration: log2 seconds."""
        a = self.absolute(mel.float().unsqueeze(1)/255).flatten(1)
        b = self.relative(rel.float().unsqueeze(1)/255).flatten(1)
        return self.embed(torch.cat((a, b, duration.float().unsqueeze(1)/4), 1))

    def controls_for(self, embedding, synth, counts=None):
        """Padded head outputs. With `counts` the batch must be sorted by synth
        (counts[i] rows of synth i); otherwise every row uses the one given synth index."""
        if counts is None:
            raw = self.heads[synth](embedding)
            synth = torch.full((len(embedding),), synth, device=embedding.device)
        else:
            parts, start = [], 0
            for index, count in enumerate(counts):
                if count:
                    parts.append(self.heads[index](embedding[start:start+count]))
                start += count
            raw = torch.cat(parts)
        generator = raw[:, :self.G].masked_fill(~self.generator_mask[synth], -1e4)
        bins = raw[:, self.G:self.G+self.C*BINS].reshape(-1, self.C, BINS)
        options = raw[:, self.G+self.C*BINS:].reshape(-1, self.K, self.V).masked_fill(~self.option_mask[synth], -1e4)
        return {'generator': generator, 'bins': bins, 'options': options}

    def control_loss(self, out, synth, continuous, categorical, generator):
        """Mean over rows of (binned-control CE + categorical CE + half preset-family CE)."""
        mask = self.control_mask[synth]
        binned = -(soft_bins(continuous[:, :self.C])*out['bins'].log_softmax(-1)).sum(-1)
        loss = (binned*mask).sum(1)/mask.sum(1)
        used = self.option_mask[synth].any(-1).float()
        picked = out['options'].log_softmax(-1).gather(-1, categorical[:, :self.K].unsqueeze(-1)).squeeze(-1)
        loss = loss - (picked*used).sum(1)/used.sum(1).clamp(min=1)
        return (loss + .5*F.cross_entropy(out['generator'], generator, reduction='none')).mean()

    def control_error(self, out, synth, continuous):
        """Sum of |predicted - true| over real controls, and how many there were."""
        mask = self.control_mask[synth]
        return float(((expected_unit(out['bins'])-continuous[:, :self.C]).abs()*mask).sum()), float(mask.sum())


def soft_bins(unit, sigma=.75):
    """Targets for binned controls: a narrow Gaussian over neighbouring bins."""
    centres = (torch.arange(BINS, device=unit.device)+.5)/BINS
    weights = torch.exp(-.5*((unit.unsqueeze(-1)-centres)*BINS/sigma)**2)
    return weights/weights.sum(-1, keepdim=True)


def expected_unit(bins):
    """Sub-bin estimate of each control: probability-weighted mean around the top bin."""
    probabilities = bins.softmax(-1)
    top = probabilities.argmax(-1, keepdim=True)
    index = torch.arange(BINS, device=bins.device).expand_as(probabilities)
    local = probabilities*((index-top).abs() <= 2)
    return (local*(index+.5)/BINS).sum(-1)/local.sum(-1)


@torch.no_grad()
def proposals(model, out, synth, count, temperature=.8):
    """Row 0 is the most likely setting; the rest are samples from the predicted distribution.

    `out` holds one sound for synth index `synth`.
    Returns (unit [count, C], categorical [count, K], generator [count]) as numpy.
    """
    controls, options = model.controls[synth], model.options[synth]
    bins = out['bins'][0, :controls]
    logits = [out['options'][0, k, :size] for k, size in enumerate(options)]
    unit = [expected_unit(bins[None])[0]]
    cats = [[int(l.argmax()) for l in logits]]
    gens = [int(out['generator'][0].argmax())]
    for _ in range(count-1):
        picked = torch.multinomial((bins/temperature).softmax(-1), 1)[:, 0]
        unit.append((picked+torch.rand(len(picked), device=bins.device))/BINS)
        cats.append([int(torch.multinomial((l/temperature).softmax(-1), 1)) for l in logits])
        gens.append(int(torch.multinomial((out['generator'][0]/temperature).softmax(-1), 1)))
    return (torch.stack(unit).clamp(0, 1).cpu().numpy(), np.asarray(cats, dtype=np.int64).reshape(count, len(options)),
            np.asarray(gens, dtype=np.int64))
