"""Verify retained render evidence and recompute corrected promotion gates."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash
from neural_invert.onset_eval import gate,summary

root=Path('tools/multisynth/runs/onset-v1')
output=Path('tools/multisynth/evaluations/onset-v1-render-audit.json')
if output.exists():raise FileExistsError('Fresh audit output required')
torch.set_num_threads(1)
result={'scriptSha256':file_hash(__file__),'correctedGateCodeSha256':file_hash('tools/neural_invert/onset_eval.py'),
        'corrections':['Both arms must cover every target before comparing means.',
                       'Count silence independently of other render failures.',
                       'Static pass means median-pitch accuracy, not whole-contour fidelity.'],
        'reports':{},'allVerified':False}
with Renderer() as renderer:
    for folder in ('validation-renders','probe-renders'):
        path=root/folder/'results.json';report=json.loads(path.read_text())
        assert report['complete']
        assert report['codeSha256']==file_hash(root/'evaluation-code-started.py')
        files=0;selected_replays=0;max_error=0.
        for row in report['rows']:
            assert row['sourceHash']==renderer.inventory['sourceHash']
            reference,sr=sf.read(root/folder/row['id']/'target.wav',dtype='float32')
            assert sr==44100 and audio_hash(reference)==row['audioHash']
            objective=MatchObjective(reference)
            for arm,record in row['arms'].items():
                assert len(record['candidates'])+len(record['failures'])==4
                for candidate in record['candidates']:
                    assert file_hash(candidate['waveFile'])==candidate['waveFileSha256']
                    wave,sr=sf.read(candidate['waveFile'],dtype='float32')
                    assert sr==44100 and audio_hash(wave)==candidate['audioHash']
                    files+=1
                selected=record['selected']
                if selected is None:
                    assert not record['candidates'];continue
                assert selected==min(record['candidates'],key=lambda c:c['score'])
                params,wave=renderer.render(selected['synth'],selected['params'],selected['seed'])
                assert params==selected['params'] and audio_hash(wave)==selected['audioHash']
                score=float(objective.score_batch([wave])[0]);error=abs(score-selected['score'])
                assert error<1e-5,(folder,row['id'],arm,error)
                max_error=max(max_error,error);selected_replays+=1
        summaries={name:{arm:summary([r for r in report['rows'] if r['sourceSynth']==name],arm)
                         for arm in ('control','onset','frozen-v3')} for name in ('Bfxr','Transfxr')}
        gates={name:gate(s['control'],s['onset']) for name,s in summaries.items()}
        result['reports'][folder]={'sourceReportSha256':file_hash(path),'targets':len(report['rows']),
                                  'verifiedCandidateFiles':files,'selectedDspReplays':selected_replays,
                                  'maxRescoreError':max_error,'summaries':summaries,'correctedGates':gates}
        print(json.dumps({'report':folder,'summaries':summaries,'gates':gates}),flush=True)
result['listeningPromotion']={}
for name in ('Bfxr','Transfxr'):
    validation=result['reports']['validation-renders']['correctedGates'][name]
    probes=result['reports']['probe-renders']['summaries'][name]
    pitch_ok=probes['onset']['staticPass']>=probes['control']['staticPass']
    result['listeningPromotion'][name]={'passed':bool(validation['passed'] and pitch_ok),
                                      'validationGatePassed':validation['passed'],'probeMedianPitchPreserved':pitch_ok}
result['allVerified']=True
result['conclusion']='No human likeness evidence is inferred from parameter loss or objective scores.'
output.write_text(json.dumps(result,indent=2)+'\n')
