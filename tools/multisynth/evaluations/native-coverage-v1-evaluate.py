"""Actual-DSP comparison on old development cases and fresh native controls."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from multisynth.renderer import Renderer
from match.objective import MatchObjective
from neural_invert.data import file_hash,_json_write
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_train import load
from neural_invert.temporal import load_temporal,predict_temporal
from neural_invert.evaluate import rendered_candidates,serializable
from neural_invert.pitch_v5_eval import descriptor_pitch,compare_descriptor_pitch

helper_path=Path(__file__).with_name('gesture-v2-evaluate.py')
spec=importlib.util.spec_from_file_location('frozen_gesture_gate',helper_path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


def run():
    torch.set_num_threads(1)
    root=Path('tools/multisynth/runs/native-coverage-v1');output=root/'evaluation'
    if output.exists():raise FileExistsError('Fresh evaluation required')
    models={arm:load(root/'models'/arm) for arm in ('control','expanded')}
    models['frozen-v3']=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    for key in ('initialCheckpointSha256','dataManifestSha256','recipe','device'):
        assert models['control'][1]['coverageExperiment'][key]==models['expanded'][1]['coverageExperiment'][key]
    output.mkdir(parents=True)
    report=dict(complete=False,scriptSha256=file_hash(__file__),gateHelperSha256=file_hash(helper_path),
        checkpoints={arm:meta['checkpointHash'] for arm,(model,meta) in models.items()},
        diagnosticCodeHashes={str(p):file_hash(p) for p in [*Path('tools/match').glob('*.py'),*Path('tools/neural_invert').glob('pitch_v5*.py')]},
        scope='Four raw proposals per arm. Old cases are development evidence; fresh native controls are not held-out families or real recordings.',sets={})
    sources=[('validation',Path('tools/multisynth/evaluations/onset-v1-targets.json'),32),
             ('probes',Path('tools/multisynth/evaluations/onset-v1-probe-targets.json'),10),
             ('fresh-native',root/'models/fresh-targets.json',32)]
    with Renderer() as renderer:
        for name,path,count in sources:
            frozen=json.loads(path.read_text());targets=[r for r in frozen['rows'] if r['sourceSynth']=='Transfxr']
            assert len(targets)==count and len({r['id'] for r in targets})==count
            if name=='fresh-native':assert frozen['dataManifestSha256']==models['expanded'][1]['coverageExperiment']['dataManifestSha256']
            group=dict(targetsSha256=file_hash(path),rows=[]);report['sets'][name]=group
            for target in targets:
                assert target['sourceHash']==renderer.inventory['sourceHash']
                p,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
                assert p==target['sourceParams'] and audio_hash(wave)==target['audioHash']
                directory=output/name/target['id'];directory.mkdir(parents=True)
                sf.write(directory/'target.wav',wave,44100,subtype='FLOAT')
                pitch=descriptor_pitch(wave);objective=MatchObjective(wave)
                row=dict(target=target,targetPitch=pitch,static=bool(pitch['reliable'] and pitch['spanSemitones']<=1),arms={})
                for arm,(model,meta) in models.items():
                    proposals=predict_temporal(model,meta,wave,renderer,count=4)
                    accepted,failures=rendered_candidates(proposals,renderer,objective)
                    failures += [dict(error='missing proposal slot') for _ in range(4-len(proposals))]
                    saved=[]
                    for i,c in enumerate(accepted):
                        dest=directory/f'{arm}-{i}.wav';sf.write(dest,c['wave'],44100,subtype='FLOAT')
                        decoded,rate=sf.read(dest,dtype='float32');assert rate==44100 and np.array_equal(decoded,c['wave'])
                        candidate_pitch=descriptor_pitch(c['wave'])
                        saved.append(dict(**serializable(c),waveFile=str(dest.resolve()),waveFileSha256=file_hash(dest),audioHash=audio_hash(c['wave']),
                            pitch=candidate_pitch,pitchComparison=compare_descriptor_pitch(pitch,candidate_pitch)))
                    row['arms'][arm]=dict(candidates=saved,failures=failures,selected=min(saved,key=lambda c:c['score']) if saved else None)
                group['rows'].append(row);_json_write(output/'results.json',report)
                print(json.dumps(dict(set=name,id=target['id'],scores={a:p['selected']['score'] if p['selected'] else None for a,p in row['arms'].items()})),flush=True)
            group['summaries']={arm:helper.summary(group['rows'],arm) for arm in models}
            group['gate']=helper.gate(group['summaries']['control'],group['summaries']['expanded'])
    safeguards=('complete','renderFailures','silence','staticPitch','reliablePitch','movingDirection','contourCoverage')
    report['probeSafeguards']=all(report['sets']['probes']['gate']['checks'][k] for k in safeguards)
    report['listeningEligible']=bool(report['sets']['validation']['gate']['passed'] and report['sets']['fresh-native']['gate']['passed'] and report['probeSafeguards'])
    report['complete']=True;_json_write(output/'results.json',report)
    print(json.dumps(dict(summaries={k:v['summaries'] for k,v in report['sets'].items()},listeningEligible=report['listeningEligible'])),flush=True)


if __name__=='__main__':run()
