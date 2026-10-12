"""Fast renderer and a process pool that renders and featurises in parallel."""
import base64
from concurrent.futures import ProcessPoolExecutor
import json
import os
import select
from pathlib import Path
import subprocess

import numpy as np

from multisynth.renderer import Renderer

FAST_WORKER = Path(__file__).resolve().parents[1] / 'render' / 'multisynth_fast_worker.js'


class FastRenderer(Renderer):
    """Drop-in Renderer backed by the main-realm worker (bit-identical, ~5x faster).

    A few control settings render for minutes. Rather than stall a whole batch,
    a request that exceeds `timeout` seconds kills the worker, starts a fresh
    one and fails as a ValueError like any other bad draw.
    """

    def __init__(self, timeout=30.):
        self.timeout = timeout
        self._start()
        self.inventory = self.request(op='inventory')
        self.specs = {s['name']: s for s in self.inventory['synths']}

    def _start(self):
        self.proc = subprocess.Popen(['node', str(FAST_WORKER)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=None, text=True)

    def request(self, **message):
        if self.proc.poll() is not None:
            raise RuntimeError('Synth worker exited')
        self.proc.stdin.write(json.dumps(message, allow_nan=False)+'\n')
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], self.timeout)[0]:
            self.proc.kill(); self.proc.wait()
            self._start()
            raise ValueError(f'Render exceeded {self.timeout:.0f} s')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Synth worker closed output')
        result = json.loads(line)
        if not result.get('ok'):
            raise ValueError(result.get('error', 'Synth request failed'))
        return result

    def mix(self, sources, balance=.5, offset_db=None):
        """Real Mixr output for one or two sources of {'synth','params','seed'} (seed in [0, 1)).

        With offset_db the balance is chosen so the second source sits that many dB
        (RMS) above the first. Returns (canonical sources, balance, wave, each source's RMS).
        """
        result = self.request(op='mix', sources=sources, balance=balance, offsetDb=offset_db)
        wave = np.frombuffer(base64.b64decode(result['audio']), dtype='<f4').copy()
        sources = [{'synth': s['synth'], 'params': s['params'], 'seed': s['renderSeed']} for s in result['sources']]
        return sources, result['balance'], wave, result['rms']


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

    def stream(self, tasks, chunk=8):
        """Like map, but yields results in order as they finish, so the caller can work while workers render."""
        return self.pool.map(_work, tasks, chunksize=chunk)

    def close(self):
        self.pool.shutdown(cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def active_synths(renderer):
    return [s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
