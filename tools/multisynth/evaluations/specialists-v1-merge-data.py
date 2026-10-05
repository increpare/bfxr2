"""Merge independently rendered Boomr parts, then regroup controls globally."""
import json
from pathlib import Path
import numpy as np
from neural_invert.data import file_hash, verify_dataset_files, split_rows, _json_write

ROOT = Path('tools/multisynth/runs/specialists-v1/data')
OUT = ROOT/'Boomr-parallel'


def main():
    if OUT.exists():
        raise FileExistsError('Fresh merged dataset required')
    sources, metas, arrays = [], [], []
    for part in range(4):
        path = ROOT/'Boomr-parts'/str(part)
        manifest = json.loads((path/'manifest.json').read_text())
        assert manifest['complete'] and manifest['engines']==['Boomr'] and manifest['perSynth']==3072
        assert manifest['seed']==20261109+104729*part
        verify_dataset_files(path, manifest)
        meta = json.loads((path/'Boomr.json').read_text())
        sources.append(dict(path=str(path.resolve()), manifestSha256=file_hash(path/'manifest.json'),
                            seed=manifest['seed'], files=manifest['files']))
        metas.append(meta)
        with np.load(path/'Boomr.npz') as data:
            arrays.append({k:data[k] for k in data.files})
        if part:
            for key in ('sourceHash', 'featureVersion', 'featureHash', 'featureCodeHash', 'featureDim', 'spec', 'sampling'):
                assert meta[key] == metas[0][key]
    rows = [row for meta in metas for row in meta['rows']]
    assert len(rows)==12288
    train, val = split_rows(rows, seed=20261109)
    assert not ({rows[i]['parameterHash'] for i in train}&{rows[i]['parameterHash'] for i in val})
    OUT.mkdir()
    np.savez_compressed(OUT/'Boomr.npz', **{k:np.concatenate([a[k] for a in arrays]) for k in arrays[0]})
    meta = {**metas[0], 'perSynth':len(rows), 'seed':20261109, 'rows':rows, 'train':train, 'val':val,
            'attempts':sum(m['attempts'] for m in metas), 'elapsedSeconds':None,
            'failures':[dict(part=i, **f) for i,m in enumerate(metas) for f in m['failures']],
            'sourceParts':sources, 'mergeCodeSha256':file_hash(__file__)}
    _json_write(OUT/'Boomr.json', meta)
    manifest.update(perSynth=len(rows), seed=20261109, sourceParts=sources,
        splits={'Boomr':{'train':train, 'val':val}}, mergeCodeSha256=file_hash(__file__),
        shards=[dict(synth='Boomr', rows=len(rows), parts=4)],
        files={'Boomr':dict(npzSha256=file_hash(OUT/'Boomr.npz'), metadataSha256=file_hash(OUT/'Boomr.json'))})
    _json_write(OUT/'manifest.json', manifest)
    verify_dataset_files(OUT, manifest)
    print(json.dumps(dict(rows=len(rows), train=len(train), validation=len(val), manifestSha256=file_hash(OUT/'manifest.json'))))


if __name__ == '__main__':
    main()
