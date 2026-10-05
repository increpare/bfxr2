"""Derive fine onset arrays by replaying immutable synthetic training rows."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time

import numpy as np
import torch

from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .data import _json_write, file_hash, verify_dataset_files
from .onset import FEATURE_POLICY, onset_features


def replay_chunk(name, rows, source_hash):
    torch.set_num_threads(1)
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != source_hash:
            raise ValueError('Source DSP changed')
        result = []
        for row in rows:
            canonical, wave = renderer.render(name, row['params'], row['seed'])
            if canonical != row['params'] or audio_hash(wave) != row['audioHash']:
                raise ValueError(f'Actual DSP replay mismatch at {name}:{row["parameterHash"]}')
            result.append(onset_features(wave).astype('<f2'))
        return np.stack(result)


def build(source, output, engines=('Bfxr', 'Transfxr'), jobs=4):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Use a fresh onset data directory')
    manifest = json.loads((source/'manifest.json').read_text())
    verify_dataset_files(source, manifest)
    if not manifest.get('complete') or not set(engines) <= set(manifest['engines']):
        raise ValueError('Incomplete or missing source data')
    output.mkdir(parents=True)
    record = {'complete': False, 'sourcePath': str(source),
              'sourceManifestSha256': file_hash(source/'manifest.json'),
              'sourceHash': manifest['sourceHash'], 'featurePolicy': FEATURE_POLICY,
              'featureCodeSha256': file_hash(Path(__file__).with_name('onset.py')),
              'generatorCodeSha256': file_hash(__file__), 'engines': list(engines),
              'files': {}, 'jobs': jobs, 'chunkSize': 256}
    _json_write(output/'manifest.json', record)
    torch.set_num_threads(1)
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != record['sourceHash']:
            raise ValueError('Source DSP changed')
        for name in engines:
            meta = json.loads((source/(name+'.json')).read_text())
            if meta['spec'] != renderer.specs[name]:
                raise ValueError('Source control schema changed')
            arr = np.lib.format.open_memmap(output/(name+'.npy'), mode='w+',
                                           dtype='<f2', shape=(len(meta['rows']),64,128))
            started = time.monotonic()
            completed = 0
            with ProcessPoolExecutor(max_workers=jobs) as pool:
                futures = {pool.submit(replay_chunk,name,meta['rows'][start:start+256],record['sourceHash']):start
                           for start in range(0,len(arr),256)}
                for future in as_completed(futures):
                    start = futures[future]
                    chunk = future.result()
                    arr[start:start+len(chunk)] = chunk
                    completed += len(chunk)
                    arr.flush()
                    print(json.dumps({'engine':name,'rows':completed,'seconds':round(time.monotonic()-started,1)}),flush=True)
            arr.flush()
            record['files'][name] = {'onsetSha256':file_hash(output/(name+'.npy')),
                                      'rows':len(arr),'replayedExactPcm':len(arr),
                                      'seconds':time.monotonic()-started}
            del arr
            _json_write(output/'manifest.json', record)
    record['complete'] = True
    _json_write(output/'manifest.json', record)
    return record


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True); p.add_argument('--output',required=True)
    p.add_argument('--engines',nargs='+',default=['Bfxr','Transfxr'])
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args(); build(a.source,a.output,a.engines,a.jobs)
