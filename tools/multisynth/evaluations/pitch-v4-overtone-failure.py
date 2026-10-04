"""Reproduce initial-lobe pitch errors on known tones and actual synth rows."""
import json
from pathlib import Path
import numpy as np
from neural_invert.pitch_eval import descriptor_pitch
from neural_invert.pitch_features import FEATURE_CODE_HASH
from neural_invert.data import file_hash
from neural_invert.benchmark import audio_hash
from multisynth.renderer import Renderer


def dominant_fft(wave):
    section=wave[len(wave)//4:len(wave)*3//4]
    spectrum=np.abs(np.fft.rfft(section*np.hanning(len(section))))
    frequencies=np.fft.rfftfreq(len(section),1/44100)
    return float(frequencies[np.argmax(spectrum)])


def main():
    time=np.arange(22050)/44100;synthetic=[];actual=[]
    for frequency in (100,165,220,330,440):
        for partial in (0.,.1,.25):
            wave=(.75*np.sin(2*np.pi*frequency*time)+partial*np.sin(2*np.pi*20*frequency*time)).astype('float32')
            synthetic.append({'fundamentalHz':frequency,'fundamentalAmplitude':.75,'twentiethPartialAmplitude':partial,
                'audioHash':audio_hash(wave),'dominantFftHz':dominant_fft(wave),'tracker':descriptor_pitch(wave)})
    with Renderer() as renderer:
        for engine,index in (('Bfxr',2059),('Transfxr',2066)):
            path=Path('tools/multisynth/runs/pitch-v4/data')/(engine+'.json')
            row=json.loads(path.read_text())['rows'][index]
            params,wave=renderer.render(engine,row['params'],row['seed'])
            assert params==row['params'] and audio_hash(wave)==row['audioHash']
            actual.append({'engine':engine,'rowIndex':index,'metadataSha256':file_hash(path),'params':params,'seed':row['seed'],
                'audioHash':audio_hash(wave),'dominantFftHz':dominant_fft(wave),'tracker':descriptor_pitch(wave),
                'nominalGesture':row.get('structuredGesture')})
        source_hash=renderer.inventory['sourceHash']
    result={'complete':True,'scriptSha256':file_hash(__file__),'descriptorCodeSha256':FEATURE_CODE_HASH,'sourceHash':source_hash,
        'interpretation':'V4 accepts short-lag ripples inside the initial positive autocorrelation lobe when a weak distant partial overlays a strong low fundamental. Sine/nearby-harmonic tests miss this case. High apparent training coverage and median output pitch are not trusted as fundamental estimates on these timbres. V4 is not promoted; listening generation stopped before delivery.',
        'synthetic':synthetic,'actual':actual}
    Path('tools/multisynth/evaluations/pitch-v4-overtone-failure.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Recorded',len(synthetic),'known synthetic tones and',len(actual),'exact actual DSP failures')


if __name__=='__main__':
    main()
