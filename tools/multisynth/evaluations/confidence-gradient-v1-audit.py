"""Replay conditional steps and verify unchanged baseline evidence."""
import importlib.util
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
from neural_invert.forward import load_forward, feature_loss
from neural_invert.forward_probe import _loss, _normalization, _fixed_controls
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.schema import ControlSchema

torch.set_num_threads(1)
path=Path('tools/multisynth/runs/confidence-gradient-v1/results.json')
r=json.loads(path.read_text()); assert r['complete']
script=Path('tools/multisynth/evaluations/confidence-gradient-v1.py')
assert file_hash(script)==r['scriptSha256']
source_path=Path('tools/multisynth/runs/rendered-gradient-v1/results.json')
assert file_hash(source_path)==r['sourceReportSha256']
source=json.loads(source_path.read_text())
assert [x['id'] for x in source['rows']]==[x['id'] for x in r['rows']]
for p,h in r['codeHashes'].items(): assert file_hash(p)==h
model,meta=load_forward('tools/multisynth/runs/forward-audio-pilot-v1/model/Transfxr')
assert meta['checkpointHash']==r['checkpointSha256'] and meta['normalizationHash']==r['normalizationHash']
schema=ControlSchema(meta['spec']); mean,std=_normalization(meta,'cpu')
assert set(r['omittedGroups'])=={'relativePitch','absolutePitch','combinedVoicing'}
def masked(c, reliable):
    if reliable:return c['featureLoss']['total']
    g=c['featureLoss']['groups']
    return (g['relativeSpectrum']+g['absoluteSpectrum']+g['relativeEnvelope']+
            g['absoluteEnvelope']+g['duration']+g['rms'])/6
files=0;replays=0;max_error=0.;reliable_equal=0
with Renderer() as renderer:
    assert renderer.inventory['sourceHash']==meta['sourceHash']
    for old,row in zip(source['rows'],r['rows']):
        assert row['reliable']==old['targetPitch']['reliable']
        reliable=row['reliable']; before=old['before']
        p,target=renderer.render('Transfxr',old['targetParams'],old['targetSeed'])
        assert p==old['targetParams'] and audio_hash(target)==old['targetAudioHash']
        features=describe(target); objective=MatchObjective(target)
        assert descriptor_pitch(target)==old['targetPitch']
        unit,cats=schema.encode(before['params'])
        assert {k:v for k,v in row['before'].items() if k!='conditionalLoss'}==before
        assert row['before']['conditionalLoss']==masked(before,reliable)
        def check(c, replay):
            global files,replays,max_error
            assert file_hash(c['waveFile'])==c['waveFileSha256']
            wave,rate=sf.read(c['waveFile'],dtype='float32')
            assert rate==44100 and audio_hash(wave)==c['audioHash'];files+=1
            assert _loss(describe(wave),features,meta)==c['featureLoss']
            err=abs(float(objective.score_batch([wave])[0])-c['objective'])
            assert err<1e-8;max_error=max(max_error,err)
            if replay:
                p,audio=renderer.render('Transfxr',c['params'],c['seed'])
                assert p==c['params'] and np.array_equal(audio,wave);replays+=1
                pitch=descriptor_pitch(audio)
                assert pitch==c['pitch'] and compare_descriptor_pitch(old['targetPitch'],pitch)==c['pitchComparison']
            if 'conditionalLoss' in c: assert c['conditionalLoss']==masked(c,reliable)
        check(row['before'],True)
        for key,c in old['steps'].items():
            assert row['steps']['original-'+key]=={**c,'conditionalLoss':masked(c,reliable)}
            check(row['steps']['original-'+key],False)
        u=torch.tensor(unit[None],requires_grad=True)
        total,groups=feature_loss(model(u,torch.tensor(cats[None],dtype=torch.long)),((torch.tensor(features)-mean)/std)[None])
        if not reliable: total=torch.stack([v for k,v in groups.items() if k not in r['omittedGroups']]).mean()
        total.backward();assert np.array_equal(u.grad[0].numpy(),row['surrogateGradient'])
        if reliable:
            assert row['renderedGradient']==old['gradient']
        else:
            for j,s in enumerate(old['secants']):
                expected=(masked(s['high'],False)-masked(s['low'],False))/(s['high']['actualUnit']-s['low']['actualUnit'])
                assert row['renderedGradient'][j]==expected
        for key,c in row['steps'].items():
            if not key.startswith('conditional-'):continue
            legacy=key.removeprefix('conditional-')
            if reliable:
                assert c==row['steps']['original-'+legacy];reliable_equal+=1
                continue
            method,radius,direction=legacy.split('-',2)
            g=np.array(row[method+'Gradient']); scale=max(abs(g))
            updated=np.clip(np.array(unit,dtype=float)-int(direction)*float(radius)*g/scale,0,1)
            expected=dict(before['params'])
            from copy import deepcopy
            expected=deepcopy(expected)
            for control,value in zip(schema.continuous,updated):
                schema._write(expected,control['path'],float(control['min']+value*(control['max']-control['min'])))
            canonical,_=renderer.render('Transfxr',expected,before['seed'])
            assert c['params']==canonical and c['seed']==before['seed']
            _fixed_controls(schema,before['params'],c['params']);check(c,True)
spec=importlib.util.spec_from_file_location('conditional_eval',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for group,rows in [('all',r['rows']),('unreliable',[x for x in r['rows'] if not x['reliable']])]:
    for arm,summary in r['summaries'][group].items(): assert module.summarize(rows,arm)==summary
assert replays==26 and reliable_equal==30 and files==74
out=dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(path),
    candidateFilesRescored=files,dspReplays=replays,unchangedReliableSteps=reliable_equal,maxObjectiveError=max_error,
    summaries=r['summaries'],cosines={x['id']:dict(before=x['oldCosine'],after=x['cosine']) for x in r['rows']},
    scope=r['scope'],conclusion='Conditional rendered directions improve MatchObjective on three reused unreliable cases at .005, but masked loss mean does not improve. Conditional surrogate direction has a large regression. No training promotion.')
dest=Path('tools/multisynth/evaluations/confidence-gradient-v1-audit.json')
if dest.exists():raise FileExistsError('Fresh audit required')
_json_write(dest,out)
print(json.dumps({k:out[k] for k in ['candidateFilesRescored','dspReplays','unchangedReliableSteps','maxObjectiveError','conclusion']}),flush=True)
