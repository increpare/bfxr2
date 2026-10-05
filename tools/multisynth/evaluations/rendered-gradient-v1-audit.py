"""Verify secant PCM/losses and every final actual-DSP step."""
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
from neural_invert.forward import load_forward
from neural_invert.forward_probe import _loss
from neural_invert.rendered_gradient import slope
from neural_invert.schema import ControlSchema

torch.set_num_threads(1)
source=Path('tools/multisynth/runs/rendered-gradient-v1/results.json')
r=json.loads(source.read_text());assert r['complete']
script=Path('tools/multisynth/evaluations/rendered-gradient-v1.py');assert r['scriptSha256']==file_hash(script)
for path,digest in r['codeHashes'].items():assert file_hash(path)==digest
spec=importlib.util.spec_from_file_location('rendered_gradient_eval',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
_,meta=load_forward('tools/multisynth/runs/forward-audio-pilot-v1/model/Transfxr')
schema=ControlSchema(meta['spec']);assert r['checkpointSha256']==meta['checkpointHash']
previous=Path('tools/multisynth/runs/local-gradient-v1/results.json');assert r['sourceReportSha256']==file_hash(previous)
prior=json.loads(previous.read_text());old_by_id={x['id']:x for x in prior['rows']}
expected=[x['id'] for kind in ('native','structured') for x in [y for y in prior['rows'] if y['stratum']==kind][:4]]
assert [x['id'] for x in r['rows']]==expected
files=0;replays=0;max_loss_error=0.;max_objective_error=0.
with Renderer() as renderer:
    for row in r['rows']:
        old=old_by_id[row['id']];assert row['before']==old['before'] and row['surrogateGradient']==old['gradient']
        params,target=renderer.render('Transfxr',row['targetParams'],row['targetSeed'])
        assert params==row['targetParams'] and audio_hash(target)==row['targetAudioHash']
        feature=describe(target);objective=MatchObjective(target)
        def check(c,replay=False):
            global files,replays,max_loss_error,max_objective_error
            assert file_hash(c['waveFile'])==c['waveFileSha256']
            wave,rate=sf.read(c['waveFile'],dtype='float32');assert rate==44100 and audio_hash(wave)==c['audioHash'];files+=1
            loss=_loss(describe(wave),feature,meta)
            error=max(abs(loss['groups'][k]-v) for k,v in c['featureLoss']['groups'].items())
            error=max(error,abs(loss['total']-c['featureLoss']['total']));assert error<1e-7
            max_loss_error=max(max_loss_error,error)
            if replay:
                p,audio=renderer.render('Transfxr',c['params'],c['seed'])
                assert p==c['params'] and np.array_equal(audio,wave);replays+=1
            if 'objective' in c:
                error=abs(float(objective.score_batch([wave])[0])-c['objective']);assert error<1e-8
                max_objective_error=max(max_objective_error,error)
        for j,secant in enumerate(row['secants']):
            assert secant['control']==schema.continuous[j]['name']
            for side in ('low','high'):check(secant[side])
            derivative=slope(secant['low']['featureLoss']['total'],secant['high']['featureLoss']['total'],
                secant['low']['actualUnit'],secant['high']['actualUnit'])
            assert derivative==secant['derivative']==row['gradient'][j]
        for key,c in row['steps'].items():
            if key.startswith('rendered-'):check(c,True)
            else:assert c==old['steps'][key.removeprefix('surrogate-')]
for arm,summary in r['summaries'].items():assert module.summarize(r['rows'],arm)==summary
audit=dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(source),
    candidateFilesVerified=files,allCandidateDescriptorLossesRecomputed=True,finalStepDspReplays=replays,
    maxDescriptorLossError=max_loss_error,maxObjectiveError=max_objective_error,summaries=r['summaries'],
    cosineAgreement={row['id']:row['cosineAgreement'] for row in r['rows']},
    targetPitchReliable={row['id']:row['targetPitch']['reliable'] for row in r['rows']},
    conclusion='Mixed local directions. Rendered descent does not outperform surrogate descent here; no training promotion.',
    scope='Eight reused development cases. Final-step DSP replays; secants verified from saved PCM and losses, not all replayed. Pitch diagnostics reused.')
dest=Path('tools/multisynth/evaluations/rendered-gradient-v1-audit.json')
if dest.exists():raise FileExistsError('Fresh audit required')
_json_write(dest,audit);print(json.dumps(audit),flush=True)
