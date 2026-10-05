"""Equal-budget actual-DSP checks of paired physical-gesture fine-tuning."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

from multisynth.renderer import Renderer
from match.objective import MatchObjective
from neural_invert.data import file_hash, _json_write
from neural_invert.benchmark import audio_hash
from neural_invert.gesture_train import load
from neural_invert.temporal import load_temporal,predict_temporal
from neural_invert.evaluate import rendered_candidates,serializable
from neural_invert.pitch_v5_eval import descriptor_pitch,compare_descriptor_pitch


def summary(rows,arm):
    candidates=[r['arms'][arm]['selected'] for r in rows]
    def eligible(r):return r['targetPitch']['reliable'] and r['targetPitch']['direction'] in (-1,1)
    moving=[(r,c) for r,c in zip(rows,candidates) if eligible(r)]
    return dict(targets=len(rows),missing=sum(c is None for c in candidates),
        failures=sum(len(r['arms'][arm]['failures']) for r in rows),
        silence=sum(e.get('error')=='Silent prediction' for r in rows for e in r['arms'][arm]['failures']),
        meanObjective=float(np.mean([c['score'] for c in candidates if c])) if any(candidates) else None,
        staticPass=sum(r['static'] and c is not None and c['pitchComparison']['medianErrorSemitones'] is not None
                       and c['pitchComparison']['medianErrorSemitones']<=1 for r,c in zip(rows,candidates)),
        movingTargets=len(moving),
        movingDirectionPass=sum(c is not None and c['pitchComparison']['directionMatches'] is True for r,c in moving),
        movingContourCoverage=float(np.mean([c['pitchComparison']['activeFrameWithinOneSemitoneFraction'] or 0 if c else 0 for r,c in moving])) if moving else None,
        reliablePitch=sum(r['targetPitch']['reliable'] and c is not None and c['pitch']['reliable'] for r,c in zip(rows,candidates)))


def gate(control,treatment):
    checks=dict(complete=control['targets']==treatment['targets']>0 and control['missing']==treatment['missing']==0,
        objective=control['meanObjective'] is not None and treatment['meanObjective'] is not None
                  and treatment['meanObjective']<=.95*control['meanObjective'],
        renderFailures=treatment['failures']<=control['failures'],silence=treatment['silence']<=control['silence'],
        staticPitch=treatment['staticPass']>=control['staticPass'],
        reliablePitch=treatment['reliablePitch']>=control['reliablePitch'],
        movingDirection=treatment['movingDirectionPass']>=control['movingDirectionPass'],
        contourCoverage=control['movingContourCoverage'] is None or (treatment['movingContourCoverage'] is not None
                         and treatment['movingContourCoverage']>=control['movingContourCoverage']))
    return dict(passed=bool(all(checks.values())),checks=checks)


def run():
    torch.set_num_threads(1)
    output=Path('tools/multisynth/runs/gesture-v2/evaluation')
    if output.exists():raise FileExistsError('Fresh evaluation output required')
    models={arm:load(Path('tools/multisynth/runs/gesture-v2/models')/arm) for arm in ('control','gesture')}
    models['frozen-v3']=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
    for key in ('initialCheckpointSha256','sourceManifestSha256','splitHash','epochs','batchSize','seed','device','recipe'):
        assert models['control'][1]['gestureExperiment'][key]==models['gesture'][1]['gestureExperiment'][key]
    output.mkdir(parents=True)
    report=dict(complete=False,codeSha256=file_hash(__file__),
        scope='Reused development cases; four raw proposals per arm, no search. No human likeness inference.',
        checkpoints={arm:meta['checkpointHash'] for arm,(model,meta) in models.items()},sets={})
    with Renderer() as renderer:
        for name,target_file in (('validation','onset-v1-targets.json'),('probes','onset-v1-probe-targets.json')):
            path=Path('tools/multisynth/evaluations')/target_file
            targets=json.loads(path.read_text())
            selected=[r for r in targets['rows'] if r['sourceSynth']=='Transfxr']
            assert len(selected)==(32 if name=='validation' else 10)
            group=dict(targetsSha256=file_hash(path),rows=[])
            report['sets'][name]=group
            for target in selected:
                assert target['sourceHash']==renderer.inventory['sourceHash']
                params,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
                assert params==target['sourceParams'] and audio_hash(wave)==target['audioHash']
                folder=output/name/target['id'];folder.mkdir(parents=True)
                sf.write(folder/'target.wav',wave,44100,subtype='FLOAT')
                pitch=descriptor_pitch(wave);objective=MatchObjective(wave)
                row=dict(target=target,targetPitch=pitch,static=bool(pitch['reliable'] and pitch['spanSemitones']<=1),arms={})
                for arm,(model,meta) in models.items():
                    proposals=predict_temporal(model,meta,wave,renderer,count=4)
                    candidates,failures=rendered_candidates(proposals,renderer,objective)
                    failures += [dict(error='missing proposal slot') for _ in range(4-len(proposals))]
                    saved=[]
                    for i,candidate in enumerate(candidates):
                        dest=folder/f'{arm}-{i}.wav';sf.write(dest,candidate['wave'],44100,subtype='FLOAT')
                        decoded,rate=sf.read(dest,dtype='float32');assert rate==44100 and np.array_equal(decoded,candidate['wave'])
                        p=descriptor_pitch(candidate['wave'])
                        saved.append(dict(**serializable(candidate),waveFile=str(dest.resolve()),waveFileSha256=file_hash(dest),
                            audioHash=audio_hash(candidate['wave']),pitch=p,pitchComparison=compare_descriptor_pitch(pitch,p)))
                    row['arms'][arm]=dict(candidates=saved,failures=failures,selected=min(saved,key=lambda c:c['score']) if saved else None)
                group['rows'].append(row);_json_write(output/'results.json',report)
                print(json.dumps(dict(set=name,id=target['id'],scores={a:r['selected']['score'] if r['selected'] else None for a,r in row['arms'].items()})),flush=True)
            group['summaries']={arm:summary(group['rows'],arm) for arm in models}
            group['gate']=gate(group['summaries']['control'],group['summaries']['gesture'])
    report['primaryGate']=report['sets']['validation']['gate']
    probe=report['sets']['probes']['gate']['checks']
    report['probeSafeguards']=all(probe[k] for k in ('complete','silence','staticPitch','reliablePitch','movingDirection','contourCoverage'))
    report['listeningEligible']=bool(report['primaryGate']['passed'] and report['probeSafeguards'])
    report['complete']=True;_json_write(output/'results.json',report)
    print(json.dumps(dict(summaries={k:v['summaries'] for k,v in report['sets'].items()},primaryGate=report['primaryGate'],listeningEligible=report['listeningEligible'])),flush=True)


if __name__=='__main__':run()
