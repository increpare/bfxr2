"""A saved nonparametric inverse model, balanced across synths and recipes."""
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
from .features import VERSION, DIM, describe, distances


class Library:
    def __init__(self, rows, descriptors, metadata):
        self.rows = rows
        self.descriptors = np.asarray(descriptors, dtype=np.float32)
        self.metadata = metadata
        if not rows or self.descriptors.shape != (len(rows), DIM) or not np.isfinite(self.descriptors).all():
            raise ValueError('Invalid or empty library')

    def save(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(directory/'descriptors.npz', descriptors=self.descriptors)
        (directory/'library.json').write_text(json.dumps({'metadata': self.metadata, 'rows': self.rows}, indent=2)+'\n')

    @classmethod
    def load(cls, directory, source_hash=None):
        directory = Path(directory)
        data = json.loads((directory/'library.json').read_text())
        meta = data['metadata']
        if meta.get('featureVersion') != VERSION:
            raise ValueError('Feature version changed; rebuild library')
        if source_hash is not None and meta.get('sourceHash') != source_hash:
            raise ValueError('Synth source changed; rebuild library')
        with np.load(directory/'descriptors.npz', allow_pickle=False) as archive:
            descriptors = archive['descriptors']
        return cls(data['rows'], descriptors, meta)

    def retrieve(self, target, per_synth=3, synths=None, metric=None):
        scores = (metric.distances if metric else distances)(target, self.descriptors)
        counts, selected = {}, []
        for i in np.argsort(scores, kind='stable'):
            row = self.rows[i]
            synth = row['synth']
            if synths is not None and synth not in synths:
                continue
            if counts.get(synth, 0) >= per_synth:
                continue
            counts[synth] = counts.get(synth, 0)+1
            selected.append(dict(deepcopy(row), score=float(scores[i]), library_index=int(i)))
        return selected


def duration_variant(name, params, factor):
    params = deepcopy(params)
    if 'duration' in params:
        params['duration'] *= factor
    elif name == 'Bfxr':
        for key in ('attackTime', 'sustainTime', 'decayTime'):
            if key in params:
                params[key] *= np.sqrt(factor)
    return params


def _build_synth(task):
    from .renderer import Renderer
    name, spec, per_preset, seed, source_hash = task
    rng = np.random.default_rng(seed+sum((i+1)*ord(c) for i,c in enumerate(name)))
    rows, descriptors, failures = [], [], []
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != source_hash:
            raise ValueError('Synth sources changed during library build')
        for preset in spec['presets']:
            for index in range(per_preset):
                render_seed = int(rng.integers(0, 2**31))
                try:
                    params = renderer.sample(name, preset, render_seed)
                    if index % 3:
                        factor = float(np.exp(rng.uniform(np.log(.18), np.log(1.8))))
                        params = duration_variant(name, params, factor)
                    params, wave = renderer.render(name, params, render_seed)
                    descriptor = describe(wave)
                except ValueError as exc:
                    failures.append({'synth':name,'preset':preset,'seed':render_seed,'error':str(exc)})
                    continue
                rows.append({'synth':name,'preset':preset,'seed':render_seed,'params':params})
                descriptors.append(descriptor)
    print(f'{name}: {len(rows)} usable sounds, {len(failures)} rejected', flush=True)
    return rows, descriptors, failures


def build(renderer, output, per_preset=12, seed=1729, synths=None, jobs=4):
    from concurrent.futures import ThreadPoolExecutor
    import torch
    if per_preset < 1 or jobs < 1:
        raise ValueError('per_preset and jobs must be positive')
    torch.set_num_threads(1)
    rows, descriptors, failures = [], [], []
    started = time.monotonic()
    selected = [name for name,spec in renderer.specs.items()
                if (name in synths if synths is not None else spec.get('collectionCompatible', False))]
    tasks = [(name,renderer.specs[name],per_preset,seed,renderer.inventory['sourceHash']) for name in selected]
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for rr,dd,ff in executor.map(_build_synth,tasks):
            rows.extend(rr)
            descriptors.extend(dd)
            failures.extend(ff)
    metadata = {'featureVersion':VERSION,'sourceHash':renderer.inventory['sourceHash'],
                'seed':seed,'perPreset':per_preset,'seconds':time.monotonic()-started,
                'synths':selected, 'jobs':jobs,
                'excluded':renderer.inventory.get('excluded',[]),'failures':failures}
    library = Library(rows, descriptors, metadata)
    library.save(output)
    return library
