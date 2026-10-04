"""Fast whole-sound log-frequency, pitch and amplitude evidence.

Relative frames cover the entire active sound. Absolute frames cover its first
six seconds; duration retains the scale for longer sounds. No prefix cropping.
"""
from functools import lru_cache
import hashlib
from pathlib import Path
import numpy as np

VERSION = 'neural-fullsound-v1'
SAMPLE_RATE = 44100
RATE = 22050
FFT = 2048
BANDS = 48
RELATIVE = 48
ABSOLUTE = 32
ABS_SECONDS = 6.
DIM = BANDS*(RELATIVE+ABSOLUTE)+3*(RELATIVE+ABSOLUTE)+3
CONFIG = {'version': VERSION, 'sampleRate': SAMPLE_RATE, 'analysisRate': RATE,
          'fft': FFT, 'bands': BANDS, 'relative': RELATIVE, 'absolute': ABSOLUTE,
          'absoluteSeconds': ABS_SECONDS, 'maxAnalysisFrames': 512}
FEATURE_CODE_HASH = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
FEATURE_HASH = hashlib.sha256(__import__('json').dumps(CONFIG, sort_keys=True).encode()).hexdigest()


@lru_cache(maxsize=1)
def _bank():
    hz = np.fft.rfftfreq(FFT, 1/RATE)
    edges = np.geomspace(30, 10500, BANDS+2)
    bank = np.maximum(0, np.minimum((hz[None]-edges[:-2,None])/(edges[1:-1]-edges[:-2])[:,None],
                                   (edges[2:,None]-hz[None])/(edges[2:]-edges[1:-1])[:,None]))
    bank /= np.maximum(bank.sum(axis=1, keepdims=True), 1e-12)
    return bank.astype(np.float32), np.hanning(FFT).astype(np.float32)


def _sample(values, times, positions, right):
    return np.array([np.interp(positions, times, row, left=row[0], right=right) for row in np.atleast_2d(values)], dtype=np.float32)


def describe(wave):
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Audio must be finite nonempty mono')
    peak = float(np.max(np.abs(wave)))
    if peak < 1e-8:
        return np.concatenate([np.full(BANDS*(RELATIVE+ABSOLUTE), -1.), np.zeros(3*(RELATIVE+ABSOLUTE)), [np.log2(len(wave)/SAMPLE_RATE+.001), -12., 0.]]).astype(np.float32)
    active = np.flatnonzero(np.abs(wave) > peak*1e-4)
    wave = wave[active[0]:active[-1]+1]/peak
    duration = len(wave)/SAMPLE_RATE
    taps = np.arange(-16, 17)
    lowpass = .48*np.sinc(.48*taps)*np.hanning(33)
    lowpass /= lowpass.sum()
    down = np.convolve(wave, lowpass, mode="full")[16:16+len(wave):2].astype(np.float32)
    # Centred frames include the attack and terminal release.
    padded = np.pad(down, (FFT//2, FFT//2))
    starts = np.arange(0, len(down), 256)
    if len(starts) > 512:
        starts = np.unique(np.linspace(0, len(down)-1, 512).astype(int))
    frames = np.lib.stride_tricks.sliding_window_view(padded, FFT)[starts]
    bank, window = _bank()
    power = np.abs(np.fft.rfft(frames*window, axis=1))**2
    spectral = 10*np.log10(np.maximum(power @ bank.T, 1e-12)).T
    spectral = np.clip((spectral-spectral.max())/72, -1, 0)
    envelope = np.sqrt(np.mean(frames**2, axis=1))
    envelope /= max(float(envelope.max()), 1e-8)
    # FFT autocorrelation measures fundamental periodicity independently of the
    # log-frequency bins. Downsample frames for a useful 50–2205 Hz lag range.
    pitchframes = frames[:, ::2]*np.hanning(FFT//2)
    ac = np.fft.irfft(np.abs(np.fft.rfft(pitchframes, n=FFT, axis=1))**2, n=FFT, axis=1)
    lags = np.arange(5, 221)
    corr = ac[:, lags]/np.maximum(ac[:, :1], 1e-12)
    # Earliest strong local maximum reduces selecting the second octave period.
    maxima = (corr[:, 1:-1] > corr[:, :-2]) & (corr[:, 1:-1] >= corr[:, 2:])
    eligible = np.where(maxima, corr[:, 1:-1], -1.)
    best = eligible.max(axis=1, keepdims=True)
    strong = eligible >= np.maximum(.3, best*.9)
    chosen = np.where(strong.any(axis=1), strong.argmax(axis=1)+1, corr.argmax(axis=1))
    voice = np.maximum(0, corr[np.arange(len(corr)), chosen]).astype(np.float32)
    pitch = np.log2((RATE/2)/lags[chosen]/55)/7
    pitch *= (voice > .3)
    times = starts/RATE
    rel = np.linspace(0, duration, RELATIVE)
    absolute = np.linspace(0, ABS_SECONDS, ABSOLUTE)
    contours = np.stack([envelope, pitch, voice])
    result = np.concatenate([_sample(spectral, times, rel, -1).ravel(),
                             _sample(spectral, times, absolute, -1).ravel(),
                             _sample(contours, times, rel, 0).ravel(),
                             _sample(contours, times, absolute, 0).ravel(),
                             [np.log2(duration+.001), np.log2(peak+1e-8), float(np.sqrt(np.mean(wave**2)))]]).astype(np.float32)
    if result.shape != (DIM,) or not np.isfinite(result).all():
        raise ValueError('Invalid neural audio features')
    return result
