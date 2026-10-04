"""V5 regression coverage, including the frozen v4 signal-contract checks."""
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
    from neural_invert.pitch_v5_features import pitch_track
    frequency, voice = pitch_track(tone(hz), POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('seed', range(5))
def test_white_noise_is_unvoiced(seed):
    from neural_invert.pitch_v5_features import pitch_track
    wave = np.random.default_rng(seed).normal(size=RATE).astype(np.float32)
    frequency, voice = pitch_track(wave, np.linspace(.05, .95, 80))
    assert np.count_nonzero(voice) <= 2
    assert np.array_equal(frequency == 0, voice == 0)


def test_dc_only_is_unvoiced():
    from neural_invert.pitch_v5_features import pitch_track
    frequency, voice = pitch_track(np.ones(RATE, dtype=np.float32), POSITIONS)
    assert not np.count_nonzero(voice)
    assert not np.count_nonzero(frequency)


@pytest.mark.parametrize('hz', [55, 65, 220, 3200, 8000])
def test_dc_offset_tone_retains_pitch(hz):
    from neural_invert.pitch_v5_features import pitch_track
    frequency, voice = pitch_track(tone(hz)+2., POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('hz', [55, 65, 220, 880, 2000, 4638.413, 5107.861, 5900., 5902.604, 6000.])
@pytest.mark.parametrize('fundamental', [0., .35, 1.])
def test_harmonic_tones_retain_fundamental(hz, fundamental):
    from neural_invert.pitch_v5_features import pitch_track
    wave = fundamental*tone(hz) + tone(2*hz) + .8*tone(3*hz)
    frequency, voice = pitch_track(wave, POSITIONS)
    voiced = voice > .6
    assert voiced.mean() >= .95
    assert np.median(np.abs(12*np.log2(frequency[voiced]/hz))) < .5


@pytest.mark.parametrize('start,end', [(220, 880), (880, 220), (2000, 4000), (4000, 2000)])
def test_glide_tracks_direction_and_frequency(start, end):
    from neural_invert.pitch_v5_features import pitch_track
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
    from neural_invert.pitch_v5_features import describe, DIM
    expected = frozen.describe(wave)
    actual = describe(wave)
    untouched = np.ones(DIM, dtype=bool)
    untouched[3888:3984] = False
    untouched[4016:4080] = False
    assert actual.shape == (4083,) and actual.dtype == np.float32
    assert actual[untouched].tobytes() == expected[untouched].tobytes()
    assert np.isfinite(actual).all()


def test_silence_gain_and_padding_contract():
    from neural_invert.pitch_v5_features import describe, pitch_track
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
    from neural_invert.pitch_v5_features import describe, pitch_track
    with pytest.raises(ValueError, match='finite nonempty mono'):
        describe(wave)
    with pytest.raises(ValueError, match='finite nonempty mono'):
        pitch_track(wave, POSITIONS)


def test_version_binds_new_and_frozen_implementations():
    from neural_invert import pitch_v5_features as new
    from neural_invert import pitch_features as v4
    assert new.VERSION == 'neural-pitch-v5'
    assert new.VERSION != v4.VERSION != frozen.VERSION
    assert new.FEATURE_HASH != v4.FEATURE_HASH
    assert new.FEATURE_CODE_HASH != v4.FEATURE_CODE_HASH
    assert {k: v for k, v in new.CONFIG.items() if k not in ('version', 'peakSelection')} == {
        k: v for k, v in v4.CONFIG.items() if k != 'version'}
    assert new.DIM == frozen.DIM == 4083
    assert new.FEATURE_CODE_HASH == hashlib.sha256(Path(new.__file__).read_bytes()).hexdigest()
    assert new.FROZEN_FEATURE_CODE_HASH == frozen.FEATURE_CODE_HASH
    assert new.CONFIG['frozenFeatureCodeHash'] == frozen.FEATURE_CODE_HASH
    assert new.FEATURE_HASH == hashlib.sha256(json.dumps(new.CONFIG, sort_keys=True).encode()).hexdigest()


def test_interpolated_autocorrelation_preserves_integer_lags_and_nyquist():
    from neural_invert.pitch_v5_features import _autocorrelation, OVERSAMPLE
    wave = np.stack([np.random.default_rng(21).normal(size=2048),
                     (-1.)**np.arange(2048), np.eye(1, 2048, 500)[0]])
    actual = _autocorrelation(wave)[:, ::OVERSAMPLE][:, :2048]
    expected = np.stack([np.correlate(row, row, mode='full')[2047:] for row in wave])
    np.testing.assert_allclose(actual, expected, atol=1e-9)


@pytest.mark.parametrize('hz', [55, 100, 165, 440, 880])
@pytest.mark.parametrize('partial', [.1, .25])
@pytest.mark.parametrize('phase', [0., .7, 2.4])
@pytest.mark.parametrize('gain', [1., .001])
def test_weak_distant_partial_does_not_replace_strong_fundamental(hz, partial, phase, gain):
    from neural_invert.pitch_v5_features import pitch_track
    time = np.arange(RATE//2)/RATE
    wave = gain*(.75*np.sin(2*np.pi*hz*time+phase)
                 + partial*np.sin(2*np.pi*20*hz*time-.3*phase))
    frequency, voice = pitch_track(wave, POSITIONS)
    assert np.mean(voice > .6) >= .95
    assert np.percentile(np.abs(12*np.log2(frequency/hz)), 95) < .5


# Exact archived controls and PCM hashes make these actual DSP regressions
# independent of the large, ignored training archives.
WHISTLE_CASES = [{'synth': 'Bfxr',
  'params': {'masterVolume': 0.5,
             'waveType': 7,
             'attackTime': 0.13018725510360668,
             'sustainTime': 0.3751751989030536,
             'sustainPunch': 0.06902544705000341,
             'decayTime': 0.14826434544118894,
             'compressionAmount': 0,
             'frequency_start': 0.21399947653059262,
             'frequency_slide': 0,
             'frequency_acceleration': 0,
             'min_frequency_relative_to_starting_frequency': 0,
             'vibratoDepth': 0,
             'vibratoSpeed': 0,
             'pitch_jump_repeat_speed': 0,
             'pitch_jump_amount': 0,
             'pitch_jump_onset_percent': 0,
             'pitch_jump_2_amount': 0,
             'pitch_jump_onset2_percent': 0,
             'overtones': 0,
             'overtoneFalloff': 0,
             'squareDuty': 0.5208297172880835,
             'dutySweep': 0,
             'repeatSpeed': 0,
             'flangerOffset': 0,
             'flangerSweep': 0,
             'lpFilterCutoff': 1,
             'lpFilterCutoffSweep': 0,
             'lpFilterResonance': 0,
             'hpFilterCutoff': 0,
             'hpFilterCutoffSweep': 0,
             'bitCrush': 0,
             'bitCrushSweep': 0},
  'seed': 201529735,
  'audioHash': 'fe1a945e64f5c33e9378b7621255bcaafa41cc1f353548796f516e244304d4b5',
  'nominalHz': 165.09549757053713},
 {'synth': 'Transfxr',
  'params': {'masterVolume': 0.5,
             'waveType': 6,
             'duration': 1.715474525672735,
             'pitch': {'start': 0.43883361047985214, 'end': 0.43883361047985214, 'curve': 'Linear'},
             'tone': {'start': 0.877025519274959, 'end': 0.877025519274959, 'curve': 'Linear'},
             'vibrato': {'start': 0, 'end': 0, 'curve': 'Linear'},
             'level': {'start': 0.7772969749831294, 'end': 0.7772969749831294, 'curve': 'Linear'},
             'attack': 0.11221640509273072,
             'release': 0.1830037257734718,
             'resonance': 0.1008737719689858,
             'echo': 0,
             'waveTo': -1,
             'morph': {'start': 0, 'end': 1, 'curve': 'Smooth'}},
  'seed': 62121637,
  'audioHash': '24339a98534e769ffbe6c4521bd0e2ec38651595e8e2e155b518b733776a836c',
  'nominalHz': 336.33692583035577}]


@pytest.mark.parametrize('case', WHISTLE_CASES, ids=lambda c: c['synth'])
def test_actual_synth_whistle_tracks_dominant_fundamental(case):
    from multisynth.renderer import Renderer
    from neural_invert.pitch_v5_features import pitch_track, describe
    with Renderer() as renderer:
        _, wave = renderer.render(case['synth'], case['params'], case['seed'])
    assert hashlib.sha256(wave.astype('<f4').tobytes()).hexdigest() == case['audioHash']
    # Estimate expected pitch independently from the dominant interior FFT bin.
    interior = wave[len(wave)//4:3*len(wave)//4]
    power = np.abs(np.fft.rfft(interior*np.hanning(len(interior))))
    expected = np.fft.rfftfreq(len(interior), 1/RATE)[np.argmax(power)]
    assert abs(12*np.log2(expected/case['nominalHz'])) < .5
    positions = np.linspace(.25, .75, 35)*len(wave)/RATE
    frequency, voice = pitch_track(wave, positions)
    assert np.mean(voice > .6) >= .95
    assert np.percentile(np.abs(12*np.log2(frequency/expected)), 95) < .5
    actual, original = describe(wave), frozen.describe(wave)
    untouched = np.ones(len(actual), dtype=bool)
    untouched[3888:3984] = untouched[4016:4080] = False
    assert actual[untouched].tobytes() == original[untouched].tobytes()


@pytest.mark.parametrize('length', [1, 2, 10, 128, 1024])
def test_short_audio_has_finite_features_and_tracks(length):
    from neural_invert.pitch_v5_features import pitch_track, describe
    wave = tone(440, seconds=length/RATE)
    assert np.isfinite(describe(wave)).all()
    frequency, voice = pitch_track(wave, [0., .001, 1.])
    assert np.isfinite(frequency).all() and np.isfinite(voice).all()
    assert frequency[-1] == voice[-1] == 0


@pytest.mark.parametrize('positions', [[np.nan], [np.inf], [[0.]], 1.])
def test_invalid_positions_are_rejected(positions):
    from neural_invert.pitch_v5_features import pitch_track
    with pytest.raises(ValueError, match='finite one-dimensional seconds'):
        pitch_track(tone(440), positions)


def test_long_sound_retains_frozen_frame_schedule_and_nonpitch_columns():
    from neural_invert import pitch_v5_features as new
    wave = tone(220, seconds=7.)
    times, contours, duration = new._contours(wave)
    assert len(times) == contours.shape[1] == new.CONFIG['maxAnalysisFrames']
    down_length = (round(duration*RATE)+1)//2
    expected = np.unique(np.linspace(0, down_length-1, 512).astype(int))/frozen.RATE
    np.testing.assert_array_equal(times, expected)
    old, actual = frozen.describe(wave), new.describe(wave)
    untouched = np.ones(new.DIM, dtype=bool)
    untouched[3888:3984] = untouched[4016:4080] = False
    assert actual[untouched].tobytes() == old[untouched].tobytes()
