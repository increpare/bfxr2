"""Actual native Stackr timeline, independent of frozen renderer identities."""
from pathlib import Path
import subprocess
from .composition import CompositionRenderer

class TimelineRenderer(CompositionRenderer):
    def __init__(self):
        worker=Path(__file__).resolve().parents[1]/'render/timeline_worker.js'
        self.proc=subprocess.Popen(['node',str(worker)],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=None,text=True)
        self.inventory=self.request(op='inventory')

    def source(self,source,seed=.5):
        result=self.request(op='source',source=source,seed=seed)
        return result['source'],self._decode(result)
