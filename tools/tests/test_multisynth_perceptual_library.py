import json
import numpy as np
import pytest

from multisynth import features


def test_cached_library_rejects_changed_provenance_and_corrupt_shape(tmp_path):
    from multisynth.perceptual_library import CachedLibrary
    from multisynth.perceptual import DIM,VERSION
    path=tmp_path/'bank';path.mkdir()
    rows=[{'synth':'Bfxr','seed':7,'params':{}}]
    meta={'featureVersion':VERSION,'featureHash':'feature-a','sourceHash':'dsp-a',
          'baseLibraryHash':'library-a','complete':True}
    (path/'library.json').write_text(json.dumps({'metadata':meta,'rows':rows}))
    np.savez_compressed(path/'descriptors.npz',descriptors=np.zeros((1,DIM),np.float32))
    bank=CachedLibrary.load(path,source_hash='dsp-a',feature_hash='feature-a',base_library_hash='library-a')
    assert len(bank.rows)==1
    for kwargs in ({'source_hash':'dsp-b'},{'feature_hash':'feature-b'},{'base_library_hash':'library-b'}):
        with pytest.raises(ValueError,match='changed'):
            CachedLibrary.load(path,**kwargs)
    np.savez_compressed(path/'descriptors.npz',descriptors=np.zeros((1,features.DIM),np.float32))
    with pytest.raises(ValueError,match='shape'):
        CachedLibrary.load(path,feature_hash='feature-a')


def test_cached_library_rejects_partial_or_nonfinite_data(tmp_path):
    from multisynth.perceptual_library import CachedLibrary
    from multisynth.perceptual import DIM,VERSION
    rows=[{'synth':'Bfxr','seed':7,'params':{}}]
    with pytest.raises(ValueError,match='complete'):
        CachedLibrary(rows,np.zeros((1,DIM)),{'complete':False,'featureVersion':VERSION})
    with pytest.raises(ValueError,match='finite'):
        CachedLibrary(rows,np.full((1,DIM),np.nan),{'complete':True,'featureVersion':VERSION})


def test_audition_identity_matches_archived_pcm_and_ignores_gain():
    import io,hashlib,soundfile as sf
    from multisynth.perceptual_library import audition_hash
    wave=np.sin(np.arange(4410)*.1).astype(np.float32)
    buffer=io.BytesIO();sf.write(buffer,features.prepare(wave)*.5,44100,format='WAV',subtype='PCM_16');buffer.seek(0)
    pcm,rate=sf.read(buffer,dtype='int16',always_2d=True)
    expected=hashlib.sha256(str((rate,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()
    assert audition_hash(wave)==expected==audition_hash(wave*.5)
    assert audition_hash(-wave)!=expected
