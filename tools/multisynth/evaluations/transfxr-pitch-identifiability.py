"""Actual-DSP evidence of a locally non-identifiable Transfxr pitch control."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash


def main():
    rows=[]
    with Renderer() as renderer:
        for waveform in (0,7,9):
            for hz in (500,1500,2800,4000,5000):
                params=deepcopy(renderer.specs['Transfxr']['defaults'])
                params.update(waveType=waveform,duration=.2,waveTo=-1,echo=0)
                pitch=float(np.log2(hz/40)/7)
                params['pitch']={'start':pitch,'end':pitch,'curve':'Linear'}
                canonical,wave=renderer.render('Transfxr',params,1234)
                rows.append({'waveType':waveform,'nominalHz':hz,'params':canonical,'seed':1234,
                    'audioHash':audio_hash(wave),'samples':len(wave),'peak':float(np.max(np.abs(wave)))})
        source_hash=renderer.inventory['sourceHash']
    white=[r for r in rows if r['waveType']==7 and r['nominalHz']>=2800]
    assert len({r['audioHash'] for r in white}) == 1
    assert all(r['peak']>1e-6 for r in white)
    assert len({r['audioHash'] for r in rows if r['waveType']==0}) == 5
    result={'complete':True,'sourceHash':source_hash,'scriptSha256':file_hash(__file__),
        'relevantCode':{p:file_hash(p) for p in ('js/audio/Transfxr_DSP.js','js/audio/BfxrWaveforms.js','tools/neural_invert/temporal.py')},
        'finding':'With these fixed controls and seed, Transfxr White at2800/4000/5000Hz produces byte-identical audible PCM. White updates its random value at each phase cell; above this rate every oversampled call changes cell. This is one demonstrated equivalence region, not a claim that pitch is always inactive for noise.',
        'trainingImplication':'The frozen Transfxr control loss imposes an octave penalty even on this many-to-one region. Consider a separately controlled audibility-aware loss or equivalence-class objective after the pitch-input experiment; do not change the running v5 recipe.',
        'rows':rows}
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified three distinct pitch settings produce identical audible white-noise PCM; tonal controls differ.')


if __name__=='__main__':
    main()
