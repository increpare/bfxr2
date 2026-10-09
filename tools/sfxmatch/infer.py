"""Turn a sound into ranked control proposals with the trained inverse model."""
import torch

from neural_invert.schema import ControlSchema
from .mel import describe
from .model import proposals
from .train import load


class Inverter:
    def __init__(self, checkpoint, device='cpu'):
        self.model, self.specs = load(checkpoint, device)
        self.device = device
        self.schemas = {name: ControlSchema(spec) for name, spec in self.specs.items()}

    @torch.no_grad()
    def embed(self, wave):
        mel, rel, duration = describe(wave)
        to = lambda a: torch.as_tensor(a, device=self.device)[None]
        return self.model.encode(to(mel), to(rel), to(duration))

    @torch.no_grad()
    def propose(self, wave, renderer, synths=None, top_synths=3, per_synth=8, seed=0):
        """-> [{'synth','params','seed','synthProbability','rank'}], most likely synth first.

        Rank 0 of each synth is the most likely setting; later ranks are samples.
        TEXT and seed controls come from a draw of the predicted preset family.
        """
        torch.manual_seed(seed)
        embedding = self.embed(wave)
        probability = self.model.synth(embedding).softmax(-1)[0]
        names = self.model.names
        chosen = synths or [names[i] for i in probability.argsort(descending=True)[:top_synths].tolist()]
        result = []
        for name in chosen:
            schema, presets = self.schemas[name], self.specs[name]['presets']
            index = names.index(name)
            unit, cats, gens = proposals(self.model, self.model.controls_for(embedding, index), index, per_synth)
            for rank in range(per_synth):
                anchor = renderer.sample(name, presets[int(gens[rank])], 1+rank)
                result.append({'synth': name, 'params': schema.decode(unit[rank], cats[rank], anchor), 'seed': 1,
                               'synthProbability': float(probability[names.index(name)]), 'rank': rank})
        return result
