"""One-shot continuation of native generation: merge, matched training, renders."""
import json
import os
from pathlib import Path
import runpy
import time
from neural_invert.data import _json_write,file_hash
from neural_invert.coverage_data import build
from neural_invert.coverage_train import train

root=Path('tools/multisynth/runs/native-coverage-v1')
status=root/'continuation.json'
if status.exists():raise FileExistsError('Continuation already started; inspect retained status')
report=dict(complete=False,pid=os.getpid(),started=time.time(),stage='waiting-for-native-shards',
    scriptSha256=file_hash(__file__),codeHashes={str(p):file_hash(p) for p in [
        Path('tools/neural_invert/coverage_data.py'),Path('tools/neural_invert/coverage_train.py'),
        Path('tools/multisynth/evaluations/native-coverage-v1-evaluate.py')]})
_json_write(status,report)
try:
    deadline=time.monotonic()+2700
    while True:
        job=json.loads((root/'job.json').read_text())
        if job.get('error'):raise RuntimeError('Generation failed: '+job['error'])
        if job.get('complete'):break
        if time.monotonic()>deadline:raise TimeoutError('Generation did not complete within continuation wait budget')
        time.sleep(15)
    report['stage']='merging-and-verifying';_json_write(status,report)
    build(root/'data')
    report['stage']='paired-training';_json_write(status,report)
    train(root/'data',root/'models',device='mps')
    report['stage']='actual-dsp-evaluation';_json_write(status,report)
    runpy.run_path('tools/multisynth/evaluations/native-coverage-v1-evaluate.py',run_name='__main__')
    report.update(complete=True,stage='awaiting-results-review',finished=time.time())
except BaseException as error:
    report.update(error=repr(error),failedStage=report['stage'],stage='failed');_json_write(status,report);raise
_json_write(status,report)
