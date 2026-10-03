import numpy as np
import hashlib
import pytest
import soundfile as sf

from multisynth.coverage import best_previous, copy_archived_audio, verify_archived_audio


def test_best_previous_uses_rating_with_previous_as_tie_break():
    target = {'selected':'new','previous':'old','bfxr':'bfxr'}
    candidates = {'new':{'rating':2},'old':{'rating':3},'bfxr':{'rating':3}}
    assert best_previous(target,candidates) == ('previous','old')
    candidates['new']['rating'] = 4
    assert best_previous(target,candidates) == ('selected','new')


def test_archived_audio_is_not_renormalized(tmp_path):
    pcm = np.array([0,1,-100,4096,-8192,0],dtype=np.int16)
    sf.write(tmp_path/'source.flac',pcm,44100,subtype='PCM_16')
    copy_archived_audio(tmp_path/'source.flac',tmp_path/'copy.wav')
    replay,rate = sf.read(tmp_path/'copy.wav',dtype='int16')
    assert rate == 44100
    np.testing.assert_array_equal(replay,pcm)


def test_archive_verification_rejects_substituted_pcm(tmp_path):
    pcm = np.array([[1],[-100],[4096]],dtype=np.int16)
    info = {'file':'source.flac','pcmSha256':hashlib.sha256(str((44100,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()}
    sf.write(tmp_path/'source.flac',pcm,44100,subtype='PCM_16')
    verify_archived_audio(tmp_path,info)
    sf.write(tmp_path/'source.flac',pcm*2,44100,subtype='PCM_16')
    with pytest.raises(ValueError,match='PCM checksum'):
        verify_archived_audio(tmp_path,info)
