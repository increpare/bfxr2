"""Fast renderer and a process pool that renders and featurises in parallel."""
from concurrent.futures import ProcessPoolExecutor
import os
from pathlib import Path
import subprocess

import numpy as np

from multisynth.renderer import Renderer

FAST_WORKER = Path(__file__).resolve().parents[1] / 'render' / 'multisynth_fast_worker.js'


class FastRenderer(Renderer):
    """Drop-in Renderer backed by the main-realm worker (bit-identical, ~5x faster)."""

    def __init__(self):
        self.proc = subprocess.Popen(['node', str(FAST_WORKER)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=None, text=True)
        self.inventory = self.request(op='inventory')
        self.specs = {s['name']: s for s in self.inventory['synths']}


_renderer = None
_fn = None


def _init(fn):
    global _renderer, _fn
    # One BLAS thread per worker; the pool itself provides the parallelism.
    import torch
    torch.set_num_threads(1)
    _renderer, _fn = FastRenderer(), fn


def _work(task):
    try:
        return _fn(_renderer, task)
    except (ValueError, RuntimeError) as error:
        return None, str(error)


class RenderAnd:
    """Task (synth, params, seed) -> (canonical params, featurise(wave))."""

    def __init__(self, featurise):
        self.featurise = featurise

    def __call__(self, renderer, task):
        synth, params, seed = task
        canonical, wave = renderer.render(synth, params, seed)
        return canonical, self.featurise(wave)


class RenderPool:
    """Run fn(renderer, task) across processes, one FastRenderer per process.

    Workers return features rather than audio, which keeps inter-process
    traffic small and parallelises feature extraction too. A task that raises
    ValueError/RuntimeError comes back as (None, message) so a search can treat
    it as an infeasible point.
    """

    def __init__(self, fn, jobs=None):
        self.jobs = jobs or max(1, (os.cpu_count() or 2) - 1)
        self.pool = ProcessPoolExecutor(self.jobs, initializer=_init, initargs=(fn,))

    def map(self, tasks):
        tasks = list(tasks)
        chunk = max(1, len(tasks) // (self.jobs * 4))
        return list(self.pool.map(_work, tasks, chunksize=chunk))

    def close(self):
        self.pool.shutdown(cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def active_synths(renderer):
    return [s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
