"""Persistent bridge to the real browser DSP. No approximation of synthesis."""
import base64
import json
from pathlib import Path
import subprocess
import numpy as np

WORKER = Path(__file__).resolve().parents[1] / 'render' / 'multisynth_worker.js'


class Renderer:
    def __init__(self):
        self.proc = subprocess.Popen(['node', str(WORKER)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=None, text=True)
        self.inventory = self.request(op='inventory')
        self.specs = {s['name']: s for s in self.inventory['synths']}

    def request(self, **message):
        if self.proc.poll() is not None:
            raise RuntimeError('Synth worker exited')
        self.proc.stdin.write(json.dumps(message, allow_nan=False)+'\n')
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('Synth worker closed output')
        result = json.loads(line)
        if not result.get('ok'):
            raise ValueError(result.get('error', 'Synth request failed'))
        return result

    def sample(self, synth, preset, seed):
        return self.request(op='sample', synth=synth, preset=preset, seed=int(seed))['params']

    def render(self, synth, params, seed=1):
        result = self.request(op='render', synth=synth, params=params, seed=int(seed))
        wave = np.frombuffer(base64.b64decode(result['audio']), dtype='<f4').copy()
        return result['params'], wave

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
