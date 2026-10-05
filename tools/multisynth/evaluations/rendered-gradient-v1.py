"""Eight-case diagnostic of finite differences through actual shipped DSP."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.features import describe
from neural_invert.forward import load_forward
from neural_invert.forward_probe import _loss, _fixed_controls
from neural_invert.local_gradient import local_step
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.rendered_gradient import slope
from neural_invert.schema import ControlSchema


def summarize(rows, arm):
    pairs=[(r,r['before'],r['steps'][arm]) for r in rows]
    return dict(cases=len(rows),improvements=sum(b['featureLoss']['total']<a['featureLoss']['total'] for _,a,b in pairs),
        meanBefore=float(np.mean([a['featureLoss']['total'] for _,a,_ in pairs])),
        meanAfter=float(np.mean([b['featureLoss']['total'] for _,_,b in pairs])),
        meanObjectiveBefore=float(np.mean([a['objective'] for _,a,_ in pairs])),
        meanObjectiveAfter=float(np.mean([b['objective'] for _,_,b in pairs])),
        reliablePitchLosses=sum(r['targetPitch']['reliable'] and a['pitch']['reliable'] and not b['pitch']['reliable'] for r,a,b in pairs),
        staticPitchLosses=sum(r['static'] and a['pitchComparison']['medianErrorSemitones'] is not None and a['pitchComparison']['medianErrorSemitones']<=1
            and (b['pitchComparison']['medianErrorSemitones'] is None or b['pitchComparison']['medianErrorSemitones']>1) for r,a,b in pairs),
        movingDirectionLosses=sum(r['moving'] and a['pitchComparison']['directionMatches'] is True and b['pitchComparison']['directionMatches'] is not True for r,a,b in pairs))


def run():
    torch.set_num_threads(1)
    previous=Path('tools/multisynth/runs/local-gradient-v1/results.json')
    source=json.loads(previous.read_text());assert source['complete']
    selected=[r for kind in ('native','structured') for r in [x for x in source['rows'] if x['stratum']==kind][:4]]
    assert len(selected)==8
    _,metadata=load_forward('tools/multisynth/runs/forward-audio-pilot-v1/model/Transfxr')
    assert metadata['checkpointHash']==source['checkpointSha256'] and metadata['normalizationHash']==source['normalizationHash']
    schema=ControlSchema(metadata['spec'])
    output=Path('tools/multisynth/runs/rendered-gradient-v1')
    if output.exists():raise FileExistsError('Fresh rendered-gradient diagnostic required')
    output.mkdir()
    _json_write(output/'targets.json',dict(sourceReportSha256=file_hash(previous),ids=[r['id'] for r in selected],
        selection='first four native and first four structured, in frozen report order'))
    report=dict(complete=False,sourceReportSha256=file_hash(previous),scriptSha256=file_hash(__file__),
        targetsSha256=file_hash(output/'targets.json'),checkpointSha256=metadata['checkpointHash'],normalizationHash=metadata['normalizationHash'],
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/features.py'),Path('tools/neural_invert/rendered_gradient.py'),
            Path('tools/neural_invert/forward_probe.py'),Path('tools/neural_invert/local_gradient.py'),*Path('tools/neural_invert').glob('pitch_v5*.py'),*Path('tools/match').glob('*.py')]},
        epsilon=.001,scope='Eight reused development cases. Scale-dependent secants, not exact gradients or perceptual ground truth. No model promotion.',rows=[])
    _json_write(output/'results.json',report)
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==metadata['sourceHash']
        for old in selected:
            folder=output/old['id'];folder.mkdir()
            p,target=renderer.render('Transfxr',old['targetParams'],old['targetSeed'])
            assert p==old['targetParams'] and audio_hash(target)==old['targetAudioHash']
            before=old['before'];p,wave=renderer.render('Transfxr',before['params'],before['seed'])
            assert p==before['params'] and audio_hash(wave)==before['audioHash']
            features=describe(target);objective=MatchObjective(target);unit,cats=schema.encode(before['params'])
            assert abs(_loss(describe(wave),features,metadata)['total']-before['featureLoss']['total'])<1e-7
            row=dict(id=old['id'],stratum=old['stratum'],targetPitch=old['targetPitch'],static=old['static'],moving=old['moving'],
                before=before,secants=[],steps={},targetParams=old['targetParams'],targetSeed=old['targetSeed'],targetAudioHash=old['targetAudioHash'])
            def persist(label,params,audio,diagnostics=False):
                _fixed_controls(schema,before['params'],params)
                path=folder/(label+'.wav');sf.write(path,audio,44100,subtype='FLOAT')
                decoded,sr=sf.read(path,dtype='float32');assert sr==44100 and np.array_equal(decoded,audio)
                value=dict(params=params,seed=before['seed'],audioHash=audio_hash(audio),waveFile=str(path.resolve()),
                    waveFileSha256=file_hash(path),featureLoss=_loss(describe(audio),features,metadata))
                if diagnostics:
                    pitch=descriptor_pitch(audio)
                    value.update(objective=float(objective.score_batch([audio])[0]),pitch=pitch,
                        pitchComparison=compare_descriptor_pitch(old['targetPitch'],pitch),silent=bool(np.max(np.abs(audio))<1e-8))
                return value
            gradient=[]
            for j,control in enumerate(schema.continuous):
                sides=[]
                for direction in (-1,1):
                    params=deepcopy(before['params']);position=float(np.clip(float(unit[j])+direction*.001,0,1))
                    schema._write(params,control['path'],float(control['min']+position*(control['max']-control['min'])))
                    canonical,audio=renderer.render('Transfxr',params,before['seed'])
                    actual,c=schema.encode(canonical)
                    assert np.array_equal(c,cats) and np.array_equal(np.delete(actual,j),np.delete(unit,j))
                    result=persist(f'coordinate-{j:02d}-{direction:+d}',canonical,audio)
                    result['actualUnit']=float(actual[j]);sides.append(result)
                low,high=sides
                derivative=slope(low['featureLoss']['total'],high['featureLoss']['total'],low['actualUnit'],high['actualUnit'])
                gradient.append(derivative);row['secants'].append(dict(control=control['name'],low=low,high=high,derivative=derivative))
            g=np.asarray(gradient);sg=np.asarray(old['gradient']);norm=np.linalg.norm(g)*np.linalg.norm(sg)
            row['gradient']=gradient;row['surrogateGradient']=old['gradient']
            row['cosineAgreement']=float(np.dot(g,sg)/norm) if norm else None
            active=np.abs(g)>1e-9
            row['signAgreement']=float(np.mean(np.sign(g[active])==np.sign(sg[active]))) if active.any() else None
            for radius,direction in ((.001,1),(.005,1),(.005,-1)):
                updated=local_step(unit,g,radius,direction);params=deepcopy(before['params'])
                for control,value in zip(schema.continuous,updated):
                    schema._write(params,control['path'],float(control['min']+value*(control['max']-control['min'])))
                canonical,audio=renderer.render('Transfxr',params,before['seed'])
                key=f'{radius:g}-{direction:+d}'
                row['steps']['rendered-'+key]=persist('rendered-'+key,canonical,audio,True)
                row['steps']['surrogate-'+key]=old['steps'][key]
            report['rows'].append(row);_json_write(output/'results.json',report)
            print(json.dumps(dict(id=old['id'],cosine=row['cosineAgreement'],before=before['featureLoss']['total'],
                after={k:v['featureLoss']['total'] for k,v in row['steps'].items()})),flush=True)
    report['summaries']={arm:summarize(report['rows'],arm) for arm in report['rows'][0]['steps']}
    report['complete']=True;_json_write(output/'results.json',report)
    print(json.dumps(report['summaries']),flush=True)


if __name__=='__main__':run()
