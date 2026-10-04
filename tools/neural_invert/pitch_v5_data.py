"""Re-extract frozen DSP rows with pitch-v5; preserve labels and provenance."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from multisynth.renderer import Renderer
from . import features as frozen
from . import pitch_v5_features as features
from .data import _json_write, file_hash, parameter_hash, verify_dataset_files
from .schema import ControlSchema

TOOLS = Path(__file__).resolve().parents[1]
POLICY = {'version': 'pitch-only-replay-v1', 'changedSlices': [[3888,3984],[4016,4080]],
          'storage': 'little-endian-float16', 'normalization': 'all-engine-training-rows-only',
          'replay': 'exact-canonical-params-seed-audio-hash-and-sample-count',
          'preservation': 'all-labels-splits-row-order-and-nonpitch-packed-bytes'}
FEATURE_KEYS = ('featureVersion','featureHash','featureCodeHash','featureDim','featureHashMeaning')
UNCHANGED = np.ones(features.DIM, dtype=bool)
for start,stop in POLICY['changedSlices']:
    UNCHANGED[start:stop] = False


def hash_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _read(path):
    try:
        value=json.loads(Path(path).read_text()); hash_json(value)
        return value
    except (OSError,ValueError,TypeError) as error:
        raise ValueError('Missing or invalid JSON binding: '+str(path)) from error


def array_hash(value,dtype):
    return hashlib.sha256(value.astype(dtype).tobytes()).hexdigest()


def _same_bytes(a,b):
    return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()


def code_bindings():
    names=('neural_invert/pitch_v5_data.py','neural_invert/pitch_v5_features.py','neural_invert/features.py',
           'neural_invert/data.py','neural_invert/schema.py','multisynth/renderer.py','render/multisynth_worker.js',
           'neural_invert/__init__.py','multisynth/__init__.py')
    result={name:file_hash(TOOLS/name) for name in names}
    if result['neural_invert/features.py']!=frozen.FEATURE_CODE_HASH or result['neural_invert/pitch_v5_features.py']!=features.FEATURE_CODE_HASH:
        raise ValueError('Feature code changed after import')
    return result


def _feature_binding(module):
    return {'featureVersion':module.VERSION,'featureHash':module.FEATURE_HASH,
            'featureCodeHash':module.FEATURE_CODE_HASH,'featureDim':module.DIM}


def _source(source,renderer):
    source=Path(source).resolve(); manifest=_read(source/'manifest.json')
    if manifest.get('complete') is not True:
        raise ValueError('Source dataset is incomplete')
    expected=_feature_binding(frozen)
    if any(manifest.get(k)!=v for k,v in expected.items()) or manifest.get('featureConfig')!=frozen.CONFIG:
        raise ValueError('Source feature/code configuration is incompatible')
    engines=manifest.get('engines')
    available=[s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible')]
    if not isinstance(engines,list) or len(engines)!=len(set(engines)) or set(engines)!=set(available):
        raise ValueError('Source normalization population must contain all active engines')
    if manifest.get('sourceHash')!=renderer.inventory['sourceHash']:
        raise ValueError('Source DSP binding is incompatible')
    if set(manifest.get('files',{}))!=set(engines) or set(manifest.get('splits',{}))!=set(engines):
        raise ValueError('Source files/splits population is incompatible')
    for name,digest in manifest.get('augmentationCodeFiles',{}).items():
        file=(TOOLS/name).resolve()
        if not file.is_relative_to(TOOLS) or not file.is_file() or file_hash(file)!=digest:
            raise ValueError('Source augmentation code is incompatible: '+name)
    verify_dataset_files(source,manifest)
    return manifest


def _arrays(path):
    try:
        with np.load(path,allow_pickle=False) as packed:
            return {key:packed[key] for key in packed.files}
    except (OSError,ValueError,KeyError) as error:
        raise ValueError('Invalid dataset arrays: '+str(path)) from error


def _source_shard(source,name,manifest,spec):
    meta=_read(source/(name+'.json')); arrays=_arrays(source/(name+'.npz'))
    if meta.get('spec')!=spec or meta.get('synth')!=name or meta.get('sourceHash')!=manifest['sourceHash']:
        raise ValueError('Source schema/DSP binding is incompatible: '+name)
    if any(meta.get(k)!=v for k,v in _feature_binding(frozen).items()):
        raise ValueError('Source shard feature/code binding is incompatible: '+name)
    schema=ControlSchema(spec); rows=meta.get('rows',[]); count=len(rows)
    shapes={'features':(count,features.DIM),'continuous':(count,len(schema.continuous)),
            'categorical':(count,len(schema.categorical)),'generator':(count,)}
    if set(arrays)!=set(shapes) or count<2:
        raise ValueError('Source array schema is incompatible')
    for key,shape in shapes.items():
        array=arrays[key]
        if array.shape!=shape or not np.isfinite(array).all():
            raise ValueError('Source array shape/values are incompatible: '+key)
        if key in ('categorical','generator') and array.dtype.kind not in 'iu':
            raise ValueError('Source label dtype is incompatible')
    if arrays['features'].dtype!=np.dtype('<f2') or arrays['continuous'].dtype!=np.dtype('<f4'):
        raise ValueError('Source feature/control dtype is incompatible')
    splits={key:meta.get(key) for key in ('train','val')}
    for ids in splits.values():
        if not isinstance(ids,list) or not ids or any(type(i) is not int or not 0<=i<count for i in ids) or len(set(ids))!=len(ids):
            raise ValueError('Source split indices are invalid')
    if set(splits['train'])&set(splits['val']) or set(splits['train']+splits['val'])!=set(range(count)) or splits!=manifest['splits'][name]:
        raise ValueError('Source split coverage/binding is incompatible')
    for i,row in enumerate(rows):
        if row.get('synth')!=name or row.get('parameterHash')!=parameter_hash(row):
            raise ValueError('Source canonical parameter hash is incompatible')
        if type(row.get('seed')) is not int or not 0<=row['seed']<2**32 or type(row.get('audioSamples')) is not int or row['audioSamples']<1:
            raise ValueError('Source audio replay schema is invalid')
        for key in ('audioHash','featureHash','packedFeatureHash'):
            value=row.get(key)
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Source row hash is invalid: '+key)
        if array_hash(arrays['features'][i],'<f2')!=row['packedFeatureHash']:
            raise ValueError('Source packed feature hash is incompatible')
        numeric,categorical=schema.encode(row['params'])
        if not np.array_equal(numeric,arrays['continuous'][i]) or not np.array_equal(categorical,arrays['categorical'][i]):
            raise ValueError('Source labels disagree with canonical controls')
        g=row.get('generatorIndex')
        if type(g) is not int or not 0<=g<len(spec['presets']) or spec['presets'][g]!=row.get('generator') or arrays['generator'][i]!=g:
            raise ValueError('Source generator label is incompatible')
    if {rows[i]['parameterHash'] for i in splits['train']}&{rows[i]['parameterHash'] for i in splits['val']}:
        raise ValueError('Source canonical groups leak across splits')
    return meta,arrays


def _config(source,manifest):
    return {'version':5,**_feature_binding(features),'featureConfig':features.CONFIG,
            'sourceHash':manifest['sourceHash'],'engines':manifest['engines'],
            'sourceDataset':{'path':str(source),'manifestSha256':file_hash(source/'manifest.json'),
                             'files':manifest['files']},'sourceManifest':manifest,
            'policy':POLICY,'codeFiles':code_bindings(),'numpyVersion':np.__version__}


def _metadata(old,config):
    meta=deepcopy(old)
    meta.update(_feature_binding(features))
    meta['featureHashMeaning']='row featureHash: new prequantization little-endian float32; packedFeatureHash: new persisted little-endian float16; sourceFeatureHash/sourcePackedFeatureHash: unchanged source row hashes'
    meta['sourceFeatureProvenance']={k:old[k] for k in FEATURE_KEYS if k in old}
    meta['sourceDataset']=config['sourceDataset']
    meta['extractionConfigHash']=hash_json(config)
    return meta


def _files(output,name):
    return {'npzSha256':file_hash(output/(name+'.npz')),'metadataSha256':file_hash(output/(name+'.json'))}


def _verify_output_shard(output,name,config,old,original):
    receipt=_read(output/(name+'.done.json'))
    if receipt!={'configHash':hash_json(config),'files':_files(output,name)}:
        raise ValueError('Completed shard receipt/configuration is incompatible: '+name)
    meta=_read(output/(name+'.json')); arrays=_arrays(output/(name+'.npz'))
    expected=_metadata(old,config)
    if {k:v for k,v in meta.items() if k!='rows'}!={k:v for k,v in expected.items() if k!='rows'}:
        raise ValueError('Re-extracted metadata/provenance is incompatible: '+name)
    if set(arrays)!=set(original) or len(meta.get('rows',[]))!=len(old['rows']):
        raise ValueError('Re-extracted row/array schema is incompatible')
    for key,a in arrays.items():
        b=original[key]
        if a.shape!=b.shape or a.dtype!=b.dtype or not np.isfinite(a).all():
            raise ValueError('Re-extracted array values/schema are incompatible')
        if not _same_bytes(a[:,UNCHANGED] if key=='features' else a,b[:,UNCHANGED] if key=='features' else b):
            raise ValueError('Re-extraction changed frozen columns/labels')
    for i,(before,after) in enumerate(zip(old['rows'],meta['rows'])):
        expected=deepcopy(before)
        expected.update(sourceFeatureHash=before['featureHash'],sourcePackedFeatureHash=before['packedFeatureHash'],
                        featureHash=after.get('featureHash'),packedFeatureHash=array_hash(arrays['features'][i],'<f2'))
        if after!=expected or not isinstance(after['featureHash'],str) or len(after['featureHash'])!=64:
            raise ValueError('Re-extracted row provenance/hash is incompatible')
    return meta,arrays


def _extract_engine(source,output,name,config):
    try:
        from threadpoolctl import threadpool_limits
        limiter=threadpool_limits(limits=1)
    except ImportError:
        from contextlib import nullcontext
        limiter=nullcontext()
    source,output=Path(source),Path(output)
    with limiter,Renderer() as renderer:
        if config['codeFiles']!=code_bindings() or renderer.inventory['sourceHash']!=config['sourceHash']:
            raise ValueError('Extraction code/DSP changed during replay')
        old,arrays=_source_shard(source,name,config['sourceManifest'],renderer.specs[name])
        if (output/(name+'.done.json')).exists():
            _verify_output_shard(output,name,config,old,arrays)
            return name
        meta=_metadata(old,config); meta['rows']=[]
        result=np.empty_like(arrays['features'])
        for i,row in enumerate(old['rows']):
            canonical,wave=renderer.render(name,row['params'],row['seed'])
            if canonical!=row['params'] or len(wave)!=row['audioSamples'] or array_hash(wave,'<f4')!=row['audioHash']:
                raise ValueError('Source audio/canonical replay mismatch: '+name+' row '+str(i))
            feature=features.describe(wave); packed=feature.astype('<f2')
            if not _same_bytes(packed[UNCHANGED],arrays['features'][i,UNCHANGED]):
                raise ValueError('Source unaffected feature columns mismatch: '+name+' row '+str(i))
            result[i]=packed
            updated=deepcopy(row)
            updated.update(sourceFeatureHash=row['featureHash'],sourcePackedFeatureHash=row['packedFeatureHash'],
                           featureHash=array_hash(feature,'<f4'),packedFeatureHash=array_hash(packed,'<f2'))
            meta['rows'].append(updated)
            if (i+1)%256==0:
                print(json.dumps({'engine':name,'replayedRows':i+1,'totalRows':len(old['rows'])}),flush=True)
        arrays['features']=result
        temp=output/(name+'.tmp.npz'); np.savez_compressed(temp,**arrays);temp.replace(output/(name+'.npz'))
        _json_write(output/(name+'.json'),meta)
        # The receipt is the atomic commit marker for the NPZ/JSON pair. A crash
        # before it is written leaves an uncommitted pair that is regenerated.
        _json_write(output/(name+'.done.json'),{'configHash':hash_json(config),'files':_files(output,name)})
        return name


def reextract(source,output,jobs=3):
    if type(jobs) is not int or jobs<1:raise ValueError('jobs must be a positive integer')
    source,output=Path(source).resolve(),Path(output).resolve()
    if source==output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('Source and output must be separate dataset directories')
    with Renderer() as renderer:
        manifest=_source(source,renderer)
    config=_config(source,manifest)
    output.mkdir(parents=True,exist_ok=True); path=output/'manifest.json'
    if path.exists():
        previous=_read(path)
        if any(previous.get(k)!=v for k,v in config.items()):
            raise ValueError('Existing extraction configuration/source/code is incompatible')
        if previous.get('complete') is True:
            load_dataset(output)
            return previous
    elif any(output.iterdir()):
        raise ValueError('Output contains files without an extraction manifest')
    _json_write(path,dict(config,complete=False))
    tasks=[(str(source),str(output),name,config) for name in manifest['engines']]
    if jobs==1:
        for task in tasks:_extract_engine(*task)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures=[pool.submit(_extract_engine,*task) for task in tasks]
            for future in as_completed(futures):future.result()
    # Recheck inputs before declaring completion; committed shards each bind
    # the original snapshot and can be independently validated on resume.
    with Renderer() as renderer:
        if _source(source,renderer)!=manifest or config!=_config(source,manifest):
            raise ValueError('Source/configuration changed during extraction')
    complete=dict(config,complete=True,files={name:_files(output,name) for name in manifest['engines']},
                  splits=manifest['splits'],totalRows=sum(len(_read(output/(name+'.json'))['rows']) for name in manifest['engines']))
    _json_write(path,complete)
    load_dataset(output)
    return complete


def load_dataset(path):
    """Validate both data generations and recompute train-only normalization."""
    import torch
    path=Path(path).resolve(); manifest=_read(path/'manifest.json')
    if manifest.get('complete') is not True:raise ValueError('Pitch dataset is incomplete')
    source=Path(manifest.get('sourceDataset',{}).get('path','')).resolve()
    specs,shards,metas,splits={},{},{},{}
    sums=np.zeros(features.DIM,dtype=np.float64); squared=sums.copy(); count=0
    with Renderer() as renderer:
        original=_source(source,renderer);config=_config(source,original)
        if any(manifest.get(k)!=v for k,v in config.items()):
            raise ValueError('Pitch dataset source/code/configuration is incompatible')
        verify_dataset_files(path,manifest)
        if manifest.get('splits')!=original['splits'] or set(manifest.get('files',{}))!=set(original['engines']):
            raise ValueError('Pitch dataset splits/population is incompatible')
        for name in original['engines']:
            old,arrays=_source_shard(source,name,original,renderer.specs[name])
            meta,arrays=_verify_output_shard(path,name,config,old,arrays)
            specs[name]=meta['spec'];metas[name]=meta;splits[name]={key:meta[key] for key in ('train','val')}
            shard={key:torch.from_numpy(a.astype(np.float32 if key in ('features','continuous') else np.int64)) for key,a in arrays.items()}
            for key in ('train','val'):shard[key]=torch.tensor(meta[key],dtype=torch.long)
            tr=shard['features'][shard['train']].numpy().astype(np.float64)
            sums+=tr.sum(0);squared+=(tr*tr).sum(0);count+=len(tr);shards[name]=shard
    if manifest.get('totalRows')!=sum(len(m['rows']) for m in metas.values()):
        raise ValueError('Pitch dataset total row binding is incompatible')
    mean=sums/count;std=np.maximum(np.sqrt(np.maximum(0,squared/count-mean*mean)),.025)
    normalization={'mean':mean.astype(np.float32).tolist(),'std':std.astype(np.float32).tolist(),
                   'scope':'all-engine-training-rows-only','stdFloor':.025,'engines':original['engines'],
                   'trainRows':count,'trainingIndicesHash':hash_json({n:s['train'] for n,s in splits.items()})}
    return manifest,specs,shards,metas,normalization,splits


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--jobs',type=int,default=3)
    args=parser.parse_args();reextract(args.source,args.output,args.jobs)


if __name__=='__main__':main()
