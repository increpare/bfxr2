"""Independent steady actual-DSP quality sweep, no training.

Run from repository root with PYTHONPATH=tools and BLAS threads=1.
Nominal pitch is a control reference, not perceptual ground truth for noise,
inharmonic wavetable voices, or dispersive Pluckr materials. The comparison
flags v4-good to v5-bad transitions; it is not an absolute synth quality score.
"""
import copy
import json
from pathlib import Path

import numpy as np

from multisynth.renderer import Renderer
from neural_invert.data import file_hash
from neural_invert.benchmark import audio_hash
from neural_invert import pitch_features as old, pitch_v5_features as new


def main():
    rows = []
    with Renderer() as renderer:
        for synth in ('Bfxr', 'Transfxr', 'Pluckr'):
            for waveform in range(6 if synth == 'Pluckr' else 12):
                frequencies = ([55, 65, 110, 220, 440, 880] if synth == 'Pluckr'
                               else [55, 65, 100, 165, 220, 440, 880, 1500, 2500, 3200])
                for hz in frequencies:
                    params = copy.deepcopy(renderer.specs[synth]['defaults'])
                    if synth == 'Bfxr':
                        params.update(waveType=waveform,
                                      frequency_start=float(np.sqrt(hz / 3528 - .001)),
                                      sustainTime=.4, decayTime=.1)
                    elif synth == 'Transfxr':
                        params.update(waveType=waveform, duration=.5, echo=0,
                                      resonance=0, attack=.01, release=.02)
                        for key, value in [('pitch', np.log2(hz / 40) / 7),
                                           ('tone', 1), ('vibrato', 0), ('level', .8)]:
                            params[key] = {'start': float(value), 'end': float(value),
                                           'curve': 'Linear'}
                    else:
                        params.update(material=waveform, duration=.5, strings=1,
                                      inharmonic=0, coupling=0, strum=0,
                                      pitch=float(np.log2(hz / 55) / 4), damping=.05)
                    canonical, wave = renderer.render(synth, params, seed=1)
                    positions = np.linspace(.1, .35, 20)
                    results = []
                    for module in (old, new):
                        frequency, voice = module.pitch_track(wave, positions)
                        mask = voice > .6
                        results.append({
                            'voiced': float(mask.mean()),
                            'hz': float(np.median(frequency[mask])) if mask.any() else 0,
                            'error': float(np.median(np.abs(12 * np.log2(
                                frequency[mask] / hz)))) if mask.any() else 999,
                        })
                    rows.append({'synth': synth, 'type': waveform, 'hz': hz,
                                 'params':canonical,'seed':1,'audioHash':audio_hash(wave),
                                 'old': results[0], 'new': results[1]})
    for synth in ('Bfxr', 'Transfxr', 'Pluckr'):
        subset = [row for row in rows if row['synth'] == synth]
        regressions = [row for row in subset
                       if row['old']['voiced'] >= .8 and row['old']['error'] < .5
                       and (row['new']['voiced'] < .8 or row['new']['error'] > .5)]
        fixes = [row for row in subset
                 if row['new']['voiced'] >= .8 and row['new']['error'] < .5
                 and (row['old']['voiced'] < .8 or row['old']['error'] > .5)]
        print(synth, 'cases', len(subset), 'regress', len(regressions), 'fixed', len(fixes))
        print('REGRESSIONS', json.dumps(regressions))
    report={'scriptSha256':file_hash(__file__),'sourceHash':renderer.inventory['sourceHash'],'v4FeatureCodeSha256':old.FEATURE_CODE_HASH,'v5FeatureCodeSha256':new.FEATURE_CODE_HASH,'scope':'Steady actual-DSP pitch diagnostics using nominal controls, not perceptual adequacy. Cases outside periodic behavior and Pluckr decay limitations remain.','rows':rows}
    Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
