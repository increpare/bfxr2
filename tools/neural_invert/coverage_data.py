"""Bind expanded native rows to frozen original splits and normalization."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from .data import file_hash,parameter_hash,verify_dataset_files,_json_write


def assign_new_groups(hashes,old_train,old_val,reserved):
    if old_train & old_val or old_train & reserved:
        raise ValueError('Original training groups overlap held-out controls')
    result=[]
    for digest in hashes:
        if digest in old_val|reserved:group='reserved'
        elif digest in old_train:group='train'
        else:
            number=int(hashlib.sha256(('native-coverage-20261024:'+digest).encode()).hexdigest()[:16],16)
            group='val' if number/2**64<.15 else 'train'
        result.append(group)
    return result


def build(output):
    from multisynth.renderer import Renderer
    from .schema import ControlSchema
    from .features import describe,FEATURE_HASH,FEATURE_CODE_HASH
    from .benchmark import audio_hash
    output=Path(output)
    if output.exists():raise FileExistsError('Fresh expanded data required')
    source=Path('tools/multisynth/runs/temporal-v3/data')
    manifest=json.loads((source/'manifest.json').read_text());verify_dataset_files(source,manifest)
    original=json.loads((source/'Transfxr.json').read_text())
    with np.load(source/'Transfxr.npz') as f:arrays={k:[f[k]] for k in f.files}
    rows=original['rows'].copy();old_count=len(rows)
    train={rows[i]['parameterHash'] for i in original['train']}
    val={rows[i]['parameterHash'] for i in original['val']}
    probes=Path('tools/multisynth/evaluations/onset-v1-probe-targets.json')
    reserved={parameter_hash(dict(synth=r['sourceSynth'],params=r['sourceParams']))
              for r in json.loads(probes.read_text())['rows'] if r['sourceSynth']=='Transfxr'}
    generation=Path('tools/multisynth/runs/native-coverage-v1/job.json')
    job=json.loads(generation.read_text())
    if not job['complete'] or len(job['shards'])!=4:raise ValueError('Incomplete generation job')
    if sorted(s['index'] for s in job['shards'])!=list(range(4)):raise ValueError('Duplicate or missing shard identity')
    receipt=dict(complete=False,buildCodeSha256=file_hash(__file__),
        originalSource=str(source.resolve()),originalManifestSha256=file_hash(source/'manifest.json'),
        originalMetadataSha256=file_hash(source/'Transfxr.json'),generationSha256=file_hash(generation),
        probesSha256=file_hash(probes),oldCount=old_count,sourceHash=manifest['sourceHash'],
        featureHash=FEATURE_HASH,featureCodeHash=FEATURE_CODE_HASH,
        normalization='Use frozen v3 checkpoint normalization in both training arms.',shards=[])
    assignments=[];rng=np.random.default_rng(20261024)
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==manifest['sourceHash']
        schema=ControlSchema(renderer.specs['Transfxr'])
        assert schema.spec==original['spec']
        for item in sorted(job['shards'],key=lambda x:x['index']):
            path=Path(item['path']);assert file_hash(path/'manifest.json')==item['manifestSha256']
            m=json.loads((path/'manifest.json').read_text());verify_dataset_files(path,m)
            assert m['complete'] and m['sourceHash']==manifest['sourceHash'] and m['featureCodeHash']==FEATURE_CODE_HASH
            assert m['seed']==20261020+item['index'] and m['perSynth']==8192
            meta=json.loads((path/'Transfxr.json').read_text());assert meta['spec']==schema.spec
            with np.load(path/'Transfxr.npz') as f:packed={k:f[k] for k in f.files}
            assert len(meta['rows'])==8192 and set(packed)==set(arrays)
            for i,row in enumerate(meta['rows']):
                assert parameter_hash(row)==row['parameterHash']
                unit,cats=schema.encode(row['params'])
                assert np.array_equal(unit,packed['continuous'][i]) and np.array_equal(cats,packed['categorical'][i])
                assert hashlib.sha256(packed['features'][i].astype('<f2').tobytes()).hexdigest()==row['packedFeatureHash']
            samples=rng.choice(len(meta['rows']),16,replace=False).tolist()
            for i in samples:
                row=meta['rows'][i];p,wave=renderer.render('Transfxr',row['params'],row['seed'])
                assert p==row['params'] and audio_hash(wave)==row['audioHash']
                assert np.array_equal(describe(wave).astype('<f2'),packed['features'][i])
            assignments.extend(assign_new_groups([r['parameterHash'] for r in meta['rows']],train,val,reserved))
            rows.extend(meta['rows'])
            for key in arrays:arrays[key].append(packed[key])
            receipt['shards'].append(dict(**item,verifiedReplayRows=samples,failures=len(meta['failures'])))
    split=dict(oldTrain=original['train'],oldVal=original['val'],
        newTrain=[old_count+i for i,a in enumerate(assignments) if a=='train'],
        newVal=[old_count+i for i,a in enumerate(assignments) if a=='val'],
        reserved=[old_count+i for i,a in enumerate(assignments) if a=='reserved'])
    train_hashes={rows[i]['parameterHash'] for i in split['oldTrain']+split['newTrain']}
    held_hashes={rows[i]['parameterHash'] for i in split['oldVal']+split['newVal']+split['reserved']}
    assert not train_hashes & held_hashes and not train_hashes & reserved
    assert len(set(sum(split.values(),[])))==len(rows)
    output.mkdir(parents=True)
    np.savez_compressed(output/'Transfxr.npz',**{k:np.concatenate(v) for k,v in arrays.items()})
    _json_write(output/'Transfxr.json',dict(spec=schema.spec,rows=rows,splits=split))
    receipt.update(complete=True,totalRows=len(rows),counts={k:len(v) for k,v in split.items()},
        npzSha256=file_hash(output/'Transfxr.npz'),metadataSha256=file_hash(output/'Transfxr.json'))
    _json_write(output/'manifest.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k!='shards'}),flush=True)
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    build(p.parse_args().output)
