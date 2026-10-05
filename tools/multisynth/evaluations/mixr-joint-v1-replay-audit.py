"""Verify final native renders and report effective layer energy without selecting on it."""
from pathlib import Path
import importlib.util
import json
import numpy as np
import soundfile as sf
import torch
from multisynth.composition import CompositionRenderer
from multisynth.coverage import verify_archived_audio
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from match.objective import MatchObjective
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.experiment import audition_pcm
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/mixr-joint-v1'

def main():
    torch.set_num_threads(1)
    spec=importlib.util.spec_from_file_location('joint_experiment',BASE/'evaluations/mixr-joint-v1.py')
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    p=json.loads((ROOT/'protocol.json').read_text());experiment.verify(p)
    report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    rows=[];total=0
    with CompositionRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        for r in report['rows']:
            target=r['target'];verify_archived_audio(experiment.ARCHIVE,target['referenceAudio'])
            verify_archived_audio(experiment.ARCHIVE,r['retained']['audio'])
            ref,rate=sf.read(experiment.ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
            soft=SoftPeriodicityObjective(ref);legacy=MatchObjective(ref);metric=PreferenceMetric.load(experiment.METRIC);desc=describe(ref)
            arms={}
            for arm,c in r['arms'].items():
                assert c['attempts']==p['budgetPerArm']==512 and c['initialRenders']==4
                assert np.all(np.diff(c['trace'])<=0) and len(c['trace'])==513
                params,wave=renderer.render(c['params'],uncached=True)
                assert params==c['params'] and np.array_equal(wave,read_wave(c))
                heard=audition_pcm(wave);assert audio_hash(heard)==c['auditionHash']
                scores=dict(soft=float(soft.score(heard)),preference=float(metric.distances(desc,describe(heard))[0]),legacy=float(legacy.score(heard)))
                assert all(abs(scores[k]-v)<1e-7 for k,v in c['scores'].items())
                sources=json.loads(params['sources']);active=[(i,s) for i,s in enumerate(sources) if s]
                energies=[];isolated=[]
                for slot,s in active:
                    canonical,source_wave=renderer.source(s);assert canonical==s
                    gain=(1 if len(active)==1 else 1-params['balance'] if slot==0 else params['balance'])*params['masterVolume']*2
                    energies.append(float(np.sum(np.square(source_wave[:len(wave)].astype(float)*gain))))
                    _,solo=renderer.render(dict(params,sources=json.dumps([s,None])),uncached=True)
                    solo=audition_pcm(solo)
                    isolated.append(dict(synth=s['synth'],soft=float(soft.score(solo)),
                        preference=float(metric.distances(desc,describe(solo))[0]),auditionHash=audio_hash(solo)))
                ratio=(float(10*np.log10(max(min(energies),1e-30)/max(max(energies),1e-30))) if len(energies)==2 else None)
                arms[arm]=dict(nativeReplay=True,scoreReplay=True,scores=scores,sourceEnergyBeforeClipping=energies,
                    weakerLayerDb=ratio,isolatedSourceScores=isolated,meaning='Energy diagnostic only; coherent interference, masking and audibility are not inferred.')
                total+=c['attempts']
            rows.append(dict(name=target['source']['name'],arms=arms))
    assert total==8192 and len(rows)==4
    out=dict(complete=True,attempts=total,finalists=16,rows=rows,scriptSha256=file_hash(__file__),
             reportSha256=file_hash(ROOT/'results.json'),protocolSha256=file_hash(ROOT/'protocol.json'))
    _json_write(BASE/'evaluations/mixr-joint-v1-replay-audit.json',out)
    print(json.dumps(dict(complete=True,finalists=16,attempts=total,layerDb=[(r['name'],{k:v['weakerLayerDb'] for k,v in r['arms'].items() if k.startswith('pair')}) for r in rows])),flush=True)

if __name__=='__main__':main()
