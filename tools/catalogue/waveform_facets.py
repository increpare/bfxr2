"""Measured audio traits, without guessing source, synthesis, or game function."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

try:
    from .acoustic import decode_windows
except ImportError:
    from acoustic import decode_windows

VERSION = 'pcm-acoustic-facets-v1'
RATE = 24000
THRESHOLDS = dict(tonal_periodicity=0.8, tonal_peak_energy=0.5, tonal_flatness=0.05,
                  noisy_flatness=0.15, noisy_periodicity=0.45, brief_seconds=0.25,
                  near_silent_peak=1e-7, pitch_motion_semitones=3)


def window_metrics(samples):
    import numpy as np
    from scipy.signal import find_peaks, resample_poly
    x = resample_poly(samples, 1, 2).astype(np.float64)
    peak = float(np.abs(x).max())
    rms = float(np.sqrt(np.square(x).mean()))
    length = len(x)
    base = dict(seconds=length/RATE, rms=rms, peak=peak,
                crest_factor=peak/max(rms, 1e-15), sampled_silent=peak <= THRESHOLDS['near_silent_peak'])
    if base['sampled_silent']:
        return base
    # Remove silence only for frame selection, retaining original energy timing.
    energy = np.square(x)
    cumulative = np.cumsum(energy) / max(float(energy.sum()), 1e-30)
    q05, q50, q95 = [int(np.searchsorted(cumulative, q)) for q in (.05, .5, .95)]
    base.update(energy_05_seconds=q05/RATE, energy_50_seconds=q50/RATE,
                energy_95_seconds=q95/RATE, energy_span_90_seconds=(q95-q05)/RATE,
                zero_crossing_rate=float(np.mean(np.signbit(x[1:]) != np.signbit(x[:-1]))))
    frame_size = min(2048, length)
    if frame_size < 48:
        base['insufficient_samples_for_spectral_facets'] = True
        return base
    # Half-overlap frames and an explicit tail; ~234 frames per10s window.
    starts = list(range(0, max(1, length-frame_size+1), max(1, frame_size//2)))
    if starts[-1] != length-frame_size:
        starts.append(length-frame_size)
    frame_rows = []
    for start in starts:
        frame = x[start:start+frame_size]
        frame_rms = float(np.sqrt(np.square(frame).mean()))
        if frame_rms < max(rms*.05, 1e-8):
            continue
        centered = frame-frame.mean()
        tapered = centered*np.hanning(frame_size)
        spectrum = np.abs(np.fft.rfft(tapered))**2
        spectrum[0] = 0
        total = float(spectrum.sum())
        if total <= 1e-25:
            continue
        positive = spectrum[1:]
        floor = max(float(positive.max())*1e-12, 1e-30)
        flatness = float(np.exp(np.log(np.maximum(positive, floor)).mean()) / positive.mean())
        top_bin = int(np.argmax(spectrum))
        peak_energy = float(spectrum[max(1, top_bin-2):top_bin+3].sum()/total)
        centroid = float(np.dot(np.arange(len(spectrum))*RATE/frame_size, spectrum)/total)
        # Biased autocorrelation penalises lags supported by few cycles. Local peaks
        # distinguish periodicity from the large adjacent-sample correlation of lowpass noise.
        fft_size = 1 << (2*frame_size-1).bit_length()
        transform = np.fft.rfft(centered, n=fft_size)
        acf = np.fft.irfft(np.abs(transform)**2, n=fft_size)[:frame_size]
        acf /= max(float(acf[0]), 1e-30)
        candidates, _ = find_peaks(acf, prominence=.08)
        candidates = candidates[(candidates >= 4) & (candidates <= min(frame_size//2, RATE//35))]
        periodicity = max(0.0, float(acf[candidates].max())) if len(candidates) else 0.0
        frame_rows.append(dict(flatness=flatness, peak_energy=peak_energy, centroid=centroid,
                               periodicity=periodicity, dominant_hz=top_bin*RATE/frame_size,
                               time=(start+frame_size/2)/RATE))
    if not frame_rows:
        base['insufficient_samples_for_spectral_facets'] = True
        return base
    def quantiles(key):
        return [round(float(a), 6) for a in np.quantile([f[key] for f in frame_rows], [.1, .5, .9])]
    tonal = [f for f in frame_rows if f['periodicity'] >= THRESHOLDS['tonal_periodicity']
             and f['peak_energy'] >= THRESHOLDS['tonal_peak_energy'] and f['flatness'] <= THRESHOLDS['tonal_flatness']]
    noisy = [f for f in frame_rows if f['flatness'] >= THRESHOLDS['noisy_flatness']
             and f['periodicity'] <= THRESHOLDS['noisy_periodicity']]
    base.update(analysed_frames=len(frame_rows), frame_samples=frame_size,
                spectral_flatness_p10_p50_p90=quantiles('flatness'),
                dominant_peak_energy_p10_p50_p90=quantiles('peak_energy'),
                periodicity_p10_p50_p90=quantiles('periodicity'),
                spectral_centroid_hz_p10_p50_p90=quantiles('centroid'),
                dominant_hz_p10_p50_p90=quantiles('dominant_hz'),
                strongly_tonal_frame_fraction=len(tonal)/len(frame_rows),
                broadband_noisy_frame_fraction=len(noisy)/len(frame_rows))
    if len(tonal) >= 3:
        frequencies = np.array([f['dominant_hz'] for f in tonal])
        base['tonal_dominant_frequency_span_semitones'] = float(12*np.log2(np.quantile(frequencies,.9)/np.quantile(frequencies,.1)))
        # This measures dominant spectral-bin motion, not reliable fundamental pitch.
    return base


def describe(root, record):
    try:
        windows = [dict(start_seconds=start, **window_metrics(samples)) for start, samples in decode_windows(root, record)]
        facets = []
        if float(record.get('duration') or windows[0]['seconds']) <= THRESHOLDS['brief_seconds']:
            facets.append('brief')
        if any(w.get('strongly_tonal_frame_fraction', 0) >= .6 for w in windows):
            facets.append('tonal_dominant')
        if any(w.get('broadband_noisy_frame_fraction', 0) >= .6 for w in windows):
            facets.append('broadband_noisy')
        if any(w.get('tonal_dominant_frequency_span_semitones', 0) >= THRESHOLDS['pitch_motion_semitones'] for w in windows):
            facets.append('dominant_frequency_moves')
        return dict(id=record['id'], path=record['path'], sha256=record['sha256'],
                    windows=windows, facets=facets, measurements_version=VERSION, thresholds=THRESHOLDS,
                    expected_category=record.get('category'), expected_catid=record.get('catid'),
                    category=None, catid=None, accepted=False, audio_verified=False, training_eligible=False,
                    reason='Objective timbral facets only. Tonality does not establish synthesis: voices, musical instruments and ringing impacts can be tonal. No source or game function inferred.')
    except Exception as exc:
        return dict(id=record['id'], path=record['path'], sha256=record['sha256'], error=str(exc),
                    measurements_version=VERSION, accepted=False, category=None, catid=None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--reuse', type=Path)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((args.root/'_catalogue').resolve()):
        raise ValueError('Derived output must remain inside the catalogue')
    records = json.loads(args.input.read_text(encoding='utf-8'))
    cached = {}
    if args.reuse:
        for line in args.reuse.read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            if row.get('measurements_version') == VERSION and row.get('thresholds') == THRESHOLDS and not row.get('error'):
                cached[(row['id'], row['sha256'])] = row
    def analyse(record):
        prior = cached.get((record['id'], record['sha256']))
        if prior and prior['path'] == record['path']:
            return dict(prior, expected_category=record.get('category'), expected_catid=record.get('catid'))
        return describe(args.root, record)
    started = time.monotonic()
    done, errors = 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as pool, args.output.open('w', encoding='utf-8') as output:
        for row in pool.map(analyse, records):
            output.write(json.dumps(row, ensure_ascii=False)+'\n')
            done += 1
            if row.get('error'):
                errors.append(dict(id=row['id'], error=row['error']))
            if done%100 == 0 or done == len(records):
                output.flush()
                print(json.dumps(dict(processed=done, total=len(records), errors=len(errors), seconds=round(time.monotonic()-started,2))), flush=True)
    args.output.with_suffix('.report.json').write_text(json.dumps(dict(processed=done, errors=errors, seconds=round(time.monotonic()-started,2),
        version=VERSION, thresholds=THRESHOLDS, sampling_rate=RATE, reused=sum((r['id'],r['sha256']) in cached for r in records), window_policy='first/middle/last <=10s',
        interpretation='Measured facets only; no UCS assignments or synthesis claims'),indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
