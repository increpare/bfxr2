"""Actual DSP fixtures exercise replay, immutable data bindings and deployment."""
import hashlib
import json
import shutil

import numpy as np
import pytest
import torch

from multisynth.renderer import Renderer
from neural_invert.data import generate_dataset, file_hash
from neural_invert import pitch_features


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, allow_nan=False))


def digest(values, dtype):
    return hashlib.sha256(values.astype(dtype).tobytes()).hexdigest()


@pytest.fixture(scope='module')
def frozen_source(tmp_path_factory):
    path = tmp_path_factory.mktemp('pitch-source')
    generate_dataset(path, per_synth=8, jobs=1)
    return path


@pytest.fixture(scope='module')
def pitch_dataset(frozen_source, tmp_path_factory):
    from neural_invert.pitch_data import reextract
    output = tmp_path_factory.mktemp('pitch-data')
    reextract(frozen_source, output, jobs=1)
    return output


def rebind_shard(path, name='Bfxr'):
    manifest = read(path/'manifest.json')
    manifest['files'][name] = {'npzSha256': file_hash(path/(name+'.npz')),
                              'metadataSha256': file_hash(path/(name+'.json'))}
    write(path/'manifest.json', manifest)


def test_reextract_preserves_every_row_label_split_and_metadata(frozen_source, pitch_dataset):
    from neural_invert.pitch_data import reextract, load_dataset
    manifest = read(pitch_dataset/'manifest.json')
    source = read(frozen_source/'manifest.json')
    assert manifest['complete'] is True
    assert manifest['sourceManifest'] == source
    assert manifest['engines'] == source['engines']
    assert len(manifest['engines']) == 22
    unchanged = np.ones(pitch_features.DIM, dtype=bool)
    unchanged[3888:3984] = False; unchanged[4016:4080] = False
    for name in source['engines']:
        old = read(frozen_source/(name+'.json')); new = read(pitch_dataset/(name+'.json'))
        assert new['train'] == old['train'] and new['val'] == old['val']
        for key in old.keys()-{'rows','featureVersion','featureHash','featureCodeHash','featureDim','featureHashMeaning'}:
            assert new[key] == old[key]
        for a,b in zip(old['rows'], new['rows']):
            assert b['sourceFeatureHash'] == a['featureHash']
            assert b['sourcePackedFeatureHash'] == a['packedFeatureHash']
            assert {k:b[k] for k in a.keys()-{'featureHash','packedFeatureHash'}} == {k:v for k,v in a.items() if k not in ('featureHash','packedFeatureHash')}
        with np.load(frozen_source/(name+'.npz')) as a, np.load(pitch_dataset/(name+'.npz')) as b:
            for key in a.files:
                np.testing.assert_array_equal(a[key][:,unchanged] if key=='features' else a[key],
                                              b[key][:,unchanged] if key=='features' else b[key])
    before = file_hash(pitch_dataset/'manifest.json')
    assert reextract(frozen_source, pitch_dataset, jobs=3) == manifest
    assert file_hash(pitch_dataset/'manifest.json') == before
    loaded = load_dataset(pitch_dataset)
    assert loaded[4]['engines'] == source['engines']
    assert loaded[4]['trainRows'] == sum(len(s['train']) for s in source['splits'].values())


def test_descriptor_roundtrip_uses_actual_replayed_wave(pitch_dataset):
    row = read(pitch_dataset/'Bfxr.json')['rows'][0]
    with Renderer() as renderer:
        canonical, wave = renderer.render('Bfxr', row['params'], row['seed'])
    assert canonical == row['params']
    features = pitch_features.describe(wave)
    assert digest(features, '<f4') == row['featureHash']
    assert digest(features, '<f2') == row['packedFeatureHash']
    with np.load(pitch_dataset/'Bfxr.npz') as shard:
        np.testing.assert_array_equal(features.astype(np.float16), shard['features'][0])


@pytest.mark.parametrize('field', ['audioHash','audioSamples','parameterHash','featureCodeHash','continuous','features','split'])
def test_source_tampering_rejected_even_with_rebound_files(frozen_source, tmp_path, field):
    from neural_invert.pitch_data import reextract
    source = tmp_path/'source'; shutil.copytree(frozen_source, source)
    meta = read(source/'Bfxr.json')
    if field in ('audioHash','parameterHash'): meta['rows'][0][field] = '0'*64
    elif field=='audioSamples': meta['rows'][0][field] += 1
    elif field=='featureCodeHash': meta[field] = '0'*64
    elif field=='split': meta['val'] = meta['train'][:1]
    else:
        with np.load(source/'Bfxr.npz') as packed: arrays = {k:packed[k] for k in packed.files}
        arrays[field][0,0] += .125
        if field=='features': meta['rows'][0]['packedFeatureHash'] = digest(arrays[field][0], '<f2')
        np.savez_compressed(source/'Bfxr.npz', **arrays)
    write(source/'Bfxr.json',meta); rebind_shard(source)
    with pytest.raises(ValueError): reextract(source,tmp_path/'output',jobs=1)


@pytest.mark.parametrize('field', ['featureConfig','codeFiles','sourceManifest','files'])
def test_completed_resume_rejects_bound_configuration_or_file_tampering(frozen_source, pitch_dataset, tmp_path, field):
    from neural_invert.pitch_data import reextract
    output = tmp_path/'output'; shutil.copytree(pitch_dataset,output)
    manifest = read(output/'manifest.json')
    if field=='files': (output/'Bfxr.npz').write_bytes(b'broken')
    else: manifest[field] = {}; write(output/'manifest.json',manifest)
    with pytest.raises(ValueError): reextract(frozen_source,output,jobs=1)


@pytest.fixture(scope='module')
def trained(pitch_dataset,tmp_path_factory):
    from neural_invert.pitch_temporal import train_temporal
    output = tmp_path_factory.mktemp('pitch-training')/'run'
    train_temporal(pitch_dataset,output,engines=['Bfxr'],epochs=2,modes=4,device='cpu',batch_size=4)
    return output


def test_train_load_predict_roundtrip_and_all_engine_normalization(trained,pitch_dataset):
    from neural_invert.pitch_temporal import load_temporal,predict_temporal
    from neural_invert.pitch_data import load_dataset
    model,metadata = load_temporal(trained/'Bfxr')
    manifest,specs,shards,metas,norm,splits = load_dataset(pitch_dataset)
    all_train = np.concatenate([s['features'][s['train']].numpy() for s in shards.values()]).astype(np.float64)
    np.testing.assert_array_equal(norm['mean'],all_train.mean(0).astype(np.float32))
    np.testing.assert_allclose(norm['std'],np.maximum(all_train.std(0),.025).astype(np.float32),rtol=1e-6)
    assert metadata['normalization'] == norm
    with Renderer() as renderer:
        row = metas['Bfxr']['rows'][0]
        _,wave = renderer.render('Bfxr',row['params'],row['seed'])
        captured = []
        hook = model.register_forward_pre_hook(lambda module,args:captured.append(args[0].clone()))
        proposals = predict_temporal(model,metadata,wave,renderer)
        hook.remove()
    expected = (pitch_features.describe(wave)-np.array(norm['mean'],dtype=np.float32))/np.array(norm['std'],dtype=np.float32)
    np.testing.assert_array_equal(captured[0].numpy()[0],expected)
    assert len(proposals)==4
    assert {p['provenance']['mode'] for p in proposals}==set(range(4))
    assert len({json.dumps(p['params'],sort_keys=True) for p in proposals})==4


@pytest.mark.parametrize('field', ['complete','history','bestEpoch','checkpoint','normalization','code','source','weights','split','parentReport'])
def test_loader_rejects_corrupt_training_binding(trained,tmp_path,field):
    from neural_invert.pitch_temporal import load_temporal
    output = tmp_path/'run'; shutil.copytree(trained,output)
    path = output/'Bfxr'; report = read(path/'training.json')
    checkpoint = torch.load(path/'best.pt',weights_only=True)
    if field=='complete': report['complete']=False
    elif field=='history': report['history'].pop()
    elif field=='bestEpoch': report['bestEpoch']=999
    elif field=='checkpoint': (path/'best.pt').write_bytes((path/'best.pt').read_bytes()+b'corrupt')
    elif field=='parentReport': write(output/'training.json', {'complete':False})
    else:
        meta=checkpoint['metadata']
        if field=='normalization': meta['normalization']['mean'][0] += .1
        elif field=='code': meta['pitchTemporalCodeHash']='0'*64
        elif field=='source': meta['sourceDataset']['manifestSha256']='0'*64
        elif field=='weights': meta['rowWeightsHash']='0'*64
        elif field=='split': meta['splitHash']='0'*64
        torch.save(checkpoint,path/'best.pt');report['checkpointHash']=file_hash(path/'best.pt');report['metadata']=meta
        parent=read(output/'training.json');parent['perEngine']['Bfxr']=report;write(output/'training.json',parent)
    write(path/'training.json',report)
    with pytest.raises(ValueError): load_temporal(path)


def test_load_resolves_symlinked_engine_to_own_training_report(trained,tmp_path):
    from neural_invert.pitch_temporal import load_temporal
    assembly=tmp_path/'assembly';assembly.mkdir()
    (assembly/'Bfxr').symlink_to(trained/'Bfxr',target_is_directory=True)
    model,metadata=load_temporal(assembly/'Bfxr')
    assert metadata['engine']=='Bfxr' and model.modes==4


def test_interrupted_resume_regenerates_only_uncommitted_engine(frozen_source,pitch_dataset,tmp_path):
    from neural_invert.pitch_data import reextract
    output=tmp_path/'resume';shutil.copytree(pitch_dataset,output)
    manifest=read(output/'manifest.json');manifest['complete']=False;write(output/'manifest.json',manifest)
    (output/'Bfxr.done.json').unlink()
    (output/'Bfxr.npz').write_bytes(b'incomplete pair')
    preserved={p.name:p.stat().st_mtime_ns for p in output.glob('*.npz') if p.name!='Bfxr.npz'}
    restored=reextract(frozen_source,output,jobs=3)
    assert restored==read(pitch_dataset/'manifest.json')
    assert preserved=={name:(output/name).stat().st_mtime_ns for name in preserved}


@pytest.mark.parametrize('change',['labels','features','metadata','split'])
def test_rebound_output_still_enforces_frozen_data_contract(pitch_dataset,tmp_path,change):
    from neural_invert.pitch_data import load_dataset
    output=tmp_path/'data';shutil.copytree(pitch_dataset,output)
    meta=read(output/'Bfxr.json')
    if change in ('labels','features'):
        with np.load(output/'Bfxr.npz') as packed: arrays={k:packed[k] for k in packed.files}
        key='continuous' if change=='labels' else 'features';arrays[key][0,0]+=.125
        if change=='features':meta['rows'][0]['packedFeatureHash']=digest(arrays[key][0],'<f2')
        np.savez_compressed(output/'Bfxr.npz',**arrays)
    elif change=='metadata':meta['sampling']={}
    else:meta['train'],meta['val']=meta['val'],meta['train']
    write(output/'Bfxr.json',meta);rebind_shard(output)
    receipt=read(output/'Bfxr.done.json');receipt['files']=read(output/'manifest.json')['files']['Bfxr'];write(output/'Bfxr.done.json',receipt)
    with pytest.raises(ValueError):load_dataset(output)


def test_unchanged_columns_require_exact_bytes_including_signed_zero(pitch_dataset,tmp_path):
    from neural_invert.pitch_data import load_dataset,UNCHANGED
    output=tmp_path/'signed-zero';shutil.copytree(pitch_dataset,output)
    with np.load(output/'Bfxr.npz') as packed: arrays={k:packed[k] for k in packed.files}
    i,j=np.argwhere((arrays['features']==0)&UNCHANGED[None,:])[0]
    arrays['features'].view(np.uint16)[i,j]^=0x8000
    np.savez_compressed(output/'Bfxr.npz',**arrays)
    meta=read(output/'Bfxr.json');meta['rows'][i]['packedFeatureHash']=digest(arrays['features'][i],'<f2');write(output/'Bfxr.json',meta)
    rebind_shard(output)
    receipt=read(output/'Bfxr.done.json');receipt['files']=read(output/'manifest.json')['files']['Bfxr'];write(output/'Bfxr.done.json',receipt)
    with pytest.raises(ValueError):load_dataset(output)


@pytest.mark.parametrize('engine,encoder',[('Transfxr','flat'),('Pluckr','temporal')])
def test_other_selected_expert_architectures_use_same_training_recipe(pitch_dataset,tmp_path,engine,encoder):
    from neural_invert.pitch_temporal import train_temporal,load_temporal
    from neural_invert.temporal import _recipe,TemporalExpert
    output=tmp_path/engine
    report=train_temporal(pitch_dataset,output,engines=[engine],epochs=1,modes=1,device='cpu',encoder_kind=encoder)
    model,metadata=load_temporal(output/engine)
    assert isinstance(model,TemporalExpert) and model.encoder_kind==encoder
    assert metadata['trainingRecipe']==_recipe(1,128,1,20261009,1,encoder)
    assert report['complete'] is True
