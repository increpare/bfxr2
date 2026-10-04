"""Reproduce descriptor-only diagnostics; no synth/model evaluation is implied.

PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 tools/.venv/bin/python \
    tools/multisynth/evaluations/pitch-v4-input-diagnostics.py
"""
import json
import hashlib
from pathlib import Path
import time

import numpy as np
import soundfile as sf

from neural_invert import features as old
from neural_invert import pitch_features as new

RATE = 44100


def measure(wave, positions, expected):
    hz, confidence = new.pitch_track(wave, positions)
    voiced = confidence > .6
    expected = np.broadcast_to(expected, hz.shape)
    errors = np.abs(12*np.log2(hz[voiced]/expected[voiced]))
    return {'voicedFraction': float(voiced.mean()),
            'medianAbsoluteSemitones': float(np.median(errors)) if errors.size else None,
            'maxAbsoluteSemitones': float(errors.max()) if errors.size else None,
            'medianConfidence': float(np.median(confidence))}


def main():
    t = np.arange(RATE//2)/RATE
    positions = np.linspace(.08, .42, 70)
    frequencies = sorted(set([40, 50, 54, 55, 65, 110, 220, 440, 880, 1500,
                              2000, 2200, 2500, 3200, 4000, 6000, 7500, 8000,
                              8100, 8500, 9000] + list(np.geomspace(55, 8000, 161))))
    tones = [{'frequency': hz, **measure(np.sin(2*np.pi*hz*t).astype(np.float32), positions, hz)}
             for hz in frequencies]
    harmonics = []
    for fundamental in [0., .35, 1.]:
        for hz in sorted(set(list(np.geomspace(55, 7000, 100)) + [4638.413, 5107.861, 5900., 5902.604, 6000.])):
            wave = (fundamental*np.sin(2*np.pi*hz*t) + np.sin(2*np.pi*2*hz*t)
                    + .8*np.sin(2*np.pi*3*hz*t)).astype(np.float32)
            harmonics.append({'frequency': hz, 'fundamentalAmplitude': fundamental,
                              **measure(wave, positions, hz)})
    noise = []
    for seed in range(20):
        wave = np.random.default_rng(seed).normal(size=RATE).astype(np.float32)
        hz, voice = new.pitch_track(wave, np.linspace(.05, .95, 100))
        noise.append({'seed': seed, 'voicedFraction': float((voice > .6).mean()),
                      'nonzeroConfidenceFraction': float((voice > 0).mean())})
    glides = []
    for start, end, seconds in [(220, 880, 1.), (880, 220, 1.), (2000, 4000, 1.),
                                 (4000, 2000, 1.), (55, 8000, .5), (8000, 55, .5),
                                 (110, 880, .1), (880, 110, .1)]:
        time_axis = np.arange(round(RATE*seconds))/RATE
        slope = (end-start)/seconds
        wave = np.sin(2*np.pi*(start*time_axis+.5*slope*time_axis**2)).astype(np.float32)
        positions = np.linspace(seconds*.15, seconds*.85, 60)
        glides.append({'startHz': start, 'endHz': end, 'seconds': seconds,
                       **measure(wave, positions, start+slope*positions)})
    timings = []
    for seconds in [.1, .5, 2., 6., 12.]:
        wave = np.sin(2*np.pi*440*np.arange(round(RATE*seconds))/RATE).astype(np.float32)
        for module in [old, new]:
            module.describe(wave)
            elapsed = []
            for _ in range(10):
                start = time.perf_counter()
                module.describe(wave)
                elapsed.append(time.perf_counter()-start)
            timings.append({'seconds': seconds, 'descriptor': module.VERSION,
                            'medianMilliseconds': 1000*float(np.median(elapsed)),
                            'repetitions': len(elapsed)})
    dc = [{'offset': offset, 'frequency': hz,
           **measure((offset+np.sin(2*np.pi*hz*t)).astype(np.float32),
                     np.linspace(.08, .42, 70), hz)}
          for offset in [0., 2.] for hz in [55, 65, 220, 3200, 8000]]
    targets = []
    root = Path(__file__).resolve().parents[3]
    for folder in range(1, 7):
        path = root/'tools/multisynth/runs/temporal-v3-listening'/f'{folder:03d}'/'target.wav'
        if not path.exists():
            targets.append({'folder': folder, 'available': False})
            continue
        wave, rate = sf.read(path, dtype='float32')
        if rate != RATE or wave.ndim != 1:
            raise ValueError(f'Unexpected target format: {path}')
        row = {'folder': folder, 'available': True,
               'wavSha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        for label, module in [('old', old), ('new', new)]:
            feature = module.describe(wave)
            active = feature[3840:3888] > .05
            voiced = active & (feature[3936:3984] >= .6)
            row[label] = {'voicedFraction': float(voiced.sum()/max(1, active.sum())),
                          'medianHz': float(np.median(55*2**(7*feature[3888:3936][voiced]))) if voiced.any() else None}
        targets.append(row)
    report = {'featureCodeHash': new.FEATURE_CODE_HASH, 'featureHash': new.FEATURE_HASH,
              'frozenFeatureCodeHash': new.FROZEN_FEATURE_CODE_HASH, 'config': new.CONFIG,
              'tones': tones, 'harmonicTones': harmonics, 'whiteNoise': noise, 'glides': glides, 'timings': timings,
              'dcOffsetTones': dc, 'listeningTargets': targets,
              'limitations': [
                  'Native 2048-sample windows contain only about 2.5 cycles at 55 Hz; a three-native-sample lag guard covers phase-dependent endpoint movement in harmonic tones.',
                  'The configured frequency range is approximate: out-of-range tones can alias to integer subharmonic periods; this is not an out-of-band classifier.',
                  'Rapid chirps are not locally periodic; voiced coverage/error is reported without requiring accuracy.',
                  'Frozen linear sampling of log-pitch and confidence is retained; voiced/unvoiced transitions can yield intermediate encoded pitch.',
                  'No synthetic diagnostic establishes performance on real effects or human listening preference.'
              ]}
    output = Path(__file__).with_suffix('.json')
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(output)
    inside = [row for row in tones if 55 <= row['frequency'] <= 8000]
    print(json.dumps({'minimumToneVoicedFraction': min(r['voicedFraction'] for r in inside),
                      'worstToneMedianSemitones': max(r['medianAbsoluteSemitones'] or 0 for r in inside),
                      'maximumNoiseVoicedFraction': max(r['voicedFraction'] for r in noise),
                      'minimumHarmonicVoicedFraction': min(r['voicedFraction'] for r in harmonics),
                      'worstHarmonicMedianSemitones': max(r['medianAbsoluteSemitones'] or 0 for r in harmonics),
                      'glides': glides, 'timings': timings}, indent=2))


if __name__ == '__main__':
    main()
