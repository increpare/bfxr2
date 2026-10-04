"""Independent signal checks for the isolated native-rate pitch descriptor."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from neural_invert import features as frozen

RATE = 44100
POSITIONS = np.linspace(.08, .42, 35)


def tone(hz, seconds=.5):
    return np.sin(2*np.pi*hz*np.arange(round(seconds*RATE))/RATE).astype(np.float32)


@pytest.mark.parametrize('hz', [55, 65, 110, 220, 440, 880, 1500, 2000, 2200,
                               2500, 3200, 4000, 6000, 7500, 8000])
def test_clean_tone_pitch_and_voicing(hz):
    from neural_invert.pitch_features import pitch_track
    frequency, voice = pitch_track(tone(hz), POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('seed', range(5))
def test_white_noise_is_unvoiced(seed):
    from neural_invert.pitch_features import pitch_track
    wave = np.random.default_rng(seed).normal(size=RATE).astype(np.float32)
    frequency, voice = pitch_track(wave, np.linspace(.05, .95, 80))
    assert np.count_nonzero(voice) <= 2
    assert np.array_equal(frequency == 0, voice == 0)


def test_dc_only_is_unvoiced():
    from neural_invert.pitch_features import pitch_track
    frequency, voice = pitch_track(np.ones(RATE, dtype=np.float32), POSITIONS)
    assert not np.count_nonzero(voice)
    assert not np.count_nonzero(frequency)


@pytest.mark.parametrize('hz', [55, 65, 220, 3200, 8000])
def test_dc_offset_tone_retains_pitch(hz):
    from neural_invert.pitch_features import pitch_track
    frequency, voice = pitch_track(tone(hz)+2., POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('hz', [55, 65, 220, 880, 2000, 4638.413, 5107.861, 5900., 5902.604, 6000.])
@pytest.mark.parametrize('fundamental', [0., .35, 1.])
def test_harmonic_tones_retain_fundamental(hz, fundamental):
    from neural_invert.pitch_features import pitch_track
    wave = fundamental*tone(hz) + tone(2*hz) + .8*tone(3*hz)
    frequency, voice = pitch_track(wave, POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('start,end', [(220, 880), (880, 220), (2000, 4000), (4000, 2000)])
def test_glide_tracks_direction_and_frequency(start, end):
    from neural_invert.pitch_features import pitch_track
    time = np.arange(RATE)/RATE
    wave = np.sin(2*np.pi*(start*time + .5*(end-start)*time**2)).astype(np.float32)
    positions = np.linspace(.1, .9, 60)
    frequency, voice = pitch_track(wave, positions)
    voiced = voice > .6
    assert voiced.mean() >= .9
    assert np.median(np.abs(12*np.log2(frequency[voiced]/(start+(end-start)*positions[voiced])))) < .5
    assert np.sign(np.median(np.diff(frequency))) == np.sign(end-start)


@pytest.mark.parametrize('wave', [tone(220), tone(3200), np.zeros(100),
                                np.random.default_rng(7).normal(size=8000).astype(np.float32),
                                np.pad(tone(880), (1234, 4567))])
def test_only_pitch_and_voicing_columns_change(wave):
    from neural_invert.pitch_features import describe, DIM
    expected = frozen.describe(wave)
    actual = describe(wave)
    untouched = np.ones(DIM, dtype=bool)
    untouched[3888:3984] = False
    untouched[4016:4080] = False
    assert actual.shape == (4083,) and actual.dtype == np.float32
    assert actual[untouched].tobytes() == expected[untouched].tobytes()
    assert np.isfinite(actual).all()


def test_silence_gain_and_padding_contract():
    from neural_invert.pitch_features import describe, pitch_track
    silence = np.zeros(RATE, dtype=np.float32)
    assert np.array_equal(describe(silence), frozen.describe(silence))
    assert all(np.count_nonzero(x) == 0 for x in pitch_track(silence, POSITIONS))
    wave = tone(3200)
    original = describe(wave)
    padded = describe(np.pad(wave, (530, 280)))
    quiet = describe(wave*.001)
    columns = np.r_[3888:3984, 4016:4080]
    np.testing.assert_array_equal(original, padded)
    np.testing.assert_allclose(original[columns], quiet[columns], atol=2e-6)
    pitch, voice = pitch_track(wave, [0., .25, 1.])
    assert pitch[-1] == voice[-1] == 0


@pytest.mark.parametrize('wave', [[], [np.nan], [np.inf], [[1., 2.]], 1.])
def test_invalid_audio_is_rejected(wave):
    from neural_invert.pitch_features import describe, pitch_track
    with pytest.raises(ValueError, match='finite nonempty mono'):
        describe(wave)
    with pytest.raises(ValueError, match='finite nonempty mono'):
        pitch_track(wave, POSITIONS)


def test_version_binds_new_and_frozen_implementations():
    from neural_invert import pitch_features as new
    assert new.VERSION != frozen.VERSION
    assert new.DIM == frozen.DIM == 4083
    assert new.FEATURE_CODE_HASH == hashlib.sha256(Path(new.__file__).read_bytes()).hexdigest()
    assert new.FROZEN_FEATURE_CODE_HASH == frozen.FEATURE_CODE_HASH
    assert new.CONFIG['frozenFeatureCodeHash'] == frozen.FEATURE_CODE_HASH
    assert new.FEATURE_HASH == hashlib.sha256(json.dumps(new.CONFIG, sort_keys=True).encode()).hexdigest()


def test_interpolated_autocorrelation_preserves_integer_lags_and_nyquist():
    from neural_invert.pitch_features import _autocorrelation, OVERSAMPLE
    wave = np.stack([np.random.default_rng(21).normal(size=2048),
                     (-1.)**np.arange(2048), np.eye(1, 2048, 500)[0]])
    actual = _autocorrelation(wave)[:, ::OVERSAMPLE][:, :2048]
    expected = np.stack([np.correlate(row, row, mode='full')[2047:] for row in wave])
    np.testing.assert_allclose(actual, expected, atol=1e-9)
