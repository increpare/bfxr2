"""Clients for the native multi-synth worker.

NativeWorker is the bare worker: canonical controls in, PCM out.
NativeRenderer is a drop-in for sfxmatch's FastRenderer: Node still samples
presets and canonicalises controls, and renders any synth without a native engine.
"""
import json
import os
from pathlib import Path
import struct
import subprocess

import numpy as np

from sfxmatch.render import FastRenderer

WORKER = Path(os.environ.get('MULTISYNTH_NATIVE_WORKER') or Path(__file__).resolve().parent / 'build' / 'multisynth_worker')
_HEADER = struct.Struct('<IiI')
_ERRORS = {1: 'Synth returned no usable audio', 2: 'Bad render request', 3: 'Synth has no native engine'}


class NativeWorker:
    """Renders canonical controls (as returned by the Node renderer) on the C++ engines."""

    def __init__(self, path=WORKER):
        self.proc = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        self.synths = frozenset(json.loads(self.proc.stderr.readline())['synths'])
        self.count = 0

    def render(self, synth, params):
        self.count = (self.count + 1) & 0x7fffffff
        line = json.dumps({'id': self.count, 'synth': synth, 'params': params}, allow_nan=False, separators=(',', ':'))
        self.proc.stdin.write(line.encode()+b'\n')
        self.proc.stdin.flush()
        header = self.proc.stdout.read(_HEADER.size)
        if len(header) != _HEADER.size:
            raise RuntimeError('Native synth worker closed output')
        ident, status, frames = _HEADER.unpack(header)
        data = self.proc.stdout.read(frames*4)
        if status:
            raise ValueError(_ERRORS.get(status, f'Native render failed with status {status}'))
        if ident != self.count or len(data) != frames*4:
            raise RuntimeError('Native synth worker lost framing')
        return np.frombuffer(data, dtype='<f4').copy()

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc.stdout.close()
        self.proc.stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class NativeRenderer(FastRenderer):
    """FastRenderer whose render() uses the native engines where they exist."""

    def __init__(self, path=WORKER):
        super().__init__()
        self.native = NativeWorker(path)

    def render(self, synth, params, seed=1):
        if synth not in self.native.synths:
            return super().render(synth, params, seed)
        canonical = self.request(op='canonical', synth=synth, params=params)['params']
        return canonical, self.native.render(synth, canonical)

    def close(self):
        self.native.close()
        super().close()
