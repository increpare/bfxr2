"""Generate four fresh Transfxr native shards with the existing sampler."""
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
from pathlib import Path
import time
from neural_invert.data import generate_dataset,file_hash,_json_write


def worker(index):
    path=Path('tools/multisynth/runs/native-coverage-v1/shards')/str(index)
    generate_dataset(path,per_synth=8192,jobs=1,seed=20261020+index,synths=['Transfxr'])
    manifest=json.loads((path/'manifest.json').read_text())
    if not manifest['complete']:raise ValueError('Incomplete native shard')
    return dict(index=index,path=str(path.resolve()),manifestSha256=file_hash(path/'manifest.json'))


if __name__=='__main__':
    root=Path('tools/multisynth/runs/native-coverage-v1')
    if root.exists():raise FileExistsError('Fresh generation directory required')
    root.mkdir(parents=True)
    report=dict(complete=False,started=time.time(),scriptSha256=file_hash(__file__),
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/data.py'),Path('tools/neural_invert/features.py'),
                   Path('tools/neural_invert/schema.py'),Path('tools/multisynth/renderer.py')]},
        totalRows=32768,rowsPerShard=8192,seeds=list(range(20261020,20261024)),shards=[])
    _json_write(root/'job.json',report)
    try:
        with ProcessPoolExecutor(max_workers=4) as pool:
            for future in as_completed([pool.submit(worker,i) for i in range(4)]):
                report['shards'].append(future.result());_json_write(root/'job.json',report)
        report.update(complete=True,finished=time.time())
    except BaseException as error:
        report['error']=repr(error);_json_write(root/'job.json',report);raise
    _json_write(root/'job.json',report)
