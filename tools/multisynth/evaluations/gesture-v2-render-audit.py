"""Check retained files, selected DSP replay/scores and expose individual regressions."""
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

torch.set_num_threads(1)
script=Path('tools/multisynth/evaluations/gesture-v2-evaluate.py')
spec=importlib.util.spec_from_file_location('gesture_evaluator',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=Path('tools/multisynth/runs/gesture-v2/evaluation/results.json')
output=Path('tools/multisynth/evaluations/gesture-v2-render-audit.json')
if output.exists():raise FileExistsError('Fresh audit required')
report=json.loads(source.read_text());assert report['complete'] and report['codeSha256']==file_hash(script)
audit=dict(complete=False,scriptSha256=file_hash(__file__),rawReportSha256=file_hash(source),
    scope='All candidate PCM/file hashes; selected actual-DSP replays/rescores; summary/gate recomputation from retained pitch diagnostics. Does not independently re-estimate pitch.',
    diagnosticCodeHashes={str(p):file_hash(p) for p in [*Path('tools/match').glob('*.py'),*Path('tools/neural_invert').glob('pitch_v5*.py')]},sets={})
with Renderer() as renderer:
    for name,group in report['sets'].items():
        files=0;replays=0;max_error=0.;regressions=[]
        for row in group['rows']:
            target=row['target'];params,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
            assert params==target['sourceParams'] and audio_hash(wave)==target['audioHash']
            objective=MatchObjective(wave)
            for arm,pool in row['arms'].items():
                assert len(pool['candidates'])+len(pool['failures'])==4
                for c in pool['candidates']:
                    assert file_hash(c['waveFile'])==c['waveFileSha256']
                    audio,rate=sf.read(c['waveFile'],dtype='float32');assert rate==44100 and audio_hash(audio)==c['audioHash']
                    files+=1
                selected=pool['selected']
                assert selected==min(pool['candidates'],key=lambda c:c['score'])
                p,audio=renderer.render('Transfxr',selected['params'],selected['seed'])
                assert p==selected['params'] and audio_hash(audio)==selected['audioHash']
                error=abs(float(objective.score_batch([audio])[0])-selected['score']);assert error<1e-5
                max_error=max(max_error,error);replays+=1
            a=row['arms']['control']['selected'];b=row['arms']['gesture']['selected']
            ap,bp=a['pitchComparison'],b['pitchComparison']
            reasons=[]
            if row['static'] and ap['medianErrorSemitones'] is not None and ap['medianErrorSemitones']<=1 and (bp['medianErrorSemitones'] is None or bp['medianErrorSemitones']>1):reasons.append('staticMedian')
            if row['targetPitch']['reliable'] and row['targetPitch']['direction'] in (-1,1) and ap['directionMatches'] is True and bp['directionMatches'] is not True:reasons.append('voicedSpanDirection')
            if reasons:regressions.append(dict(id=target['id'],reasons=reasons))
        summaries={arm:module.summary(group['rows'],arm) for arm in ('control','gesture','frozen-v3')}
        assert summaries==group['summaries'];assert module.gate(summaries['control'],summaries['gesture'])==group['gate']
        audit['sets'][name]=dict(summaries=summaries,gate=group['gate'],verifiedCandidateFiles=files,
            selectedDspReplays=replays,maxRescoreError=max_error,individualRegressions=regressions)
        print(json.dumps({name:audit['sets'][name]}),flush=True)
audit.update(complete=True,listeningEligible=report['listeningEligible'],conclusion='No promotion: primary mean objective worsened, and probe contour coverage regressed.')
_json_write(output,audit)
