"""Separate actual-Mixr bridge, preserving the existing single-synth renderer."""
import base64
from pathlib import Path
import subprocess
import numpy as np
from .renderer import Renderer

class CompositionRenderer(Renderer):
    def __init__(self):
        worker=Path(__file__).resolve().parents[1]/'render/composition_worker.js'
        self.proc=subprocess.Popen(['node',str(worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=None,text=True)
        self.inventory=self.request(op='inventory')

    @staticmethod
    def _decode(result):
        if result['sampleRate']!=44100:raise ValueError('Unexpected mix sample rate')
        return np.frombuffer(base64.b64decode(result['audio']),dtype='<f4').copy()

    def source(self,source):
        result=self.request(op='source',source=source)
        return result['source'],self._decode(result)

    def render(self,params,*,uncached=False):
        result=self.request(op='render',params=params,uncached=uncached)
        return result['params'],self._decode(result)
