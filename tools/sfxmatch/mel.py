"""Log-mel input for the inverse model: an absolute-time view plus a whole-sound view.

The absolute view keeps attack and retrigger timing (11.6 ms frames, first
~3 s). The relative view squeezes the entire sound into 32 columns so long
sounds are still seen whole. Both are dB relative to the clip's loudest bin,
stored as uint8 so a million examples fit in memory.
"""
from functools import lru_cache

import numpy as np

SAMPLE_RATE = 44100
RATE = 22050
FFT = 1024
HOP = 256
BANDS = 64
FRAMES = 256
REL_FRAMES = 32
FLOOR_DB = 80.


@lru_cache(maxsize=1)
def _filters():
    hz = np.fft.rfftfreq(FFT, 1/RATE)
    mel = lambda f: 2595*np.log10(1+f/700)
    edges = 700*(10**(np.linspace(mel(40), mel(11000), BANDS+2)/2595)-1)
    bank = np.maximum(0, np.minimum((hz[None]-edges[:-2, None])/(edges[1:-1]-edges[:-2])[:, None],
                                    (edges[2:, None]-hz[None])/(edges[2:]-edges[1:-1])[:, None]))
    bank /= np.maximum(bank.sum(axis=1, keepdims=True), 1e-9)
    taps = np.arange(-16, 17)
    lowpass = .48*np.sinc(.48*taps)*np.hanning(33)
    return bank.astype(np.float32), np.hanning(FFT).astype(np.float32), (lowpass/lowpass.sum()).astype(np.float32)


def trim(wave):
    """Peak-normalise and cut leading/trailing audio below -60 dB of peak."""
    wave = np.asarray(wave, dtype=np.float32)
    if wave.ndim != 1 or not wave.size or not np.isfinite(wave).all():
        raise ValueError('Audio must be finite nonempty mono')
    peak = float(np.max(np.abs(wave)))
    if peak < 1e-7:
        raise ValueError('Silent audio')
    active = np.flatnonzero(np.abs(wave) > peak*1e-3)
    return wave[active[0]:active[-1]+1]/peak


def logmel(wave):
    """dB log-mel of trimmed 44.1 kHz audio, shape (BANDS, frames), range [-FLOOR_DB, 0]."""
    bank, window, lowpass = _filters()
    down = np.convolve(wave, lowpass, mode='full')[16:16+len(wave):2]
    padded = np.pad(down, (FFT//2, FFT//2))
    frames = np.lib.stride_tricks.sliding_window_view(padded, FFT)[::HOP]
    power = np.abs(np.fft.rfft(frames*window, axis=1))**2
    db = 10*np.log10(np.maximum(power @ bank.T, 1e-12)).T
    return np.clip(db-db.max(), -FLOOR_DB, 0).astype(np.float32)


def _quantise(db):
    return np.round((db+FLOOR_DB)*(255/FLOOR_DB)).astype(np.uint8)


def describe(wave):
    """-> (mel uint8 BANDS x FRAMES, rel uint8 BANDS x REL_FRAMES, log2 seconds)."""
    wave = trim(wave)
    db = logmel(wave)
    count = db.shape[1]
    absolute = np.full((BANDS, FRAMES), -FLOOR_DB, dtype=np.float32)
    absolute[:, :min(count, FRAMES)] = db[:, :FRAMES]
    if count >= REL_FRAMES:
        relative = np.stack([part.mean(axis=1) for part in np.array_split(db, REL_FRAMES, axis=1)], axis=1)
    else:
        positions = np.linspace(0, count-1, REL_FRAMES)
        relative = np.stack([np.interp(positions, np.arange(count), row) for row in db])
    return _quantise(absolute), _quantise(relative), np.float32(np.log2(len(wave)/SAMPLE_RATE))
