"""Retained PCM, exact DSP replays, exclusions and selection accounting."""
import importlib.util
import json
from pathlib import Path
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_selection import select_candidate, rejection_reasons
from neural_invert.data import file_hash, _json_write, parameter_hash

torch.set_num_threads(1)
root=Path('tools/multisynth/runs/coverage-selection-v1')
source=root/'results.json';report=json.loads(source.read_text());assert report['complete']
script=Path('tools/multisynth/evaluations/coverage-selection-v1.py')
assert report['scriptSha256']==file_hash(script)
assert report['policySha256']==file_hash('tools/neural_invert/coverage_selection.py')
assert report['targetsSha256']==file_hash(root/'targets.json')
spec=importlib.util.spec_from_file_location('selection_eval',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.summarize(report['fresh'])==report['freshSummary']
for group in report['retrospective'].values():assert module.summarize(group['rows'])==group['summary']
frozen=json.loads((root/'targets.json').read_text())
data=Path('tools/multisynth/runs/native-coverage-v1/data')
assert frozen['dataManifestSha256']==file_hash(data/'manifest.json')
meta=json.loads((data/'Transfxr.json').read_text())
old=Path('tools/multisynth/runs/native-coverage-v1/models/fresh-targets.json')
assert frozen['excludedTargetsSha256']==file_hash(old)
excluded={r['parameterHash'] for r in json.loads(old.read_text())['rows']}
training={meta['rows'][i]['parameterHash'] for i in meta['splits']['oldTrain']+meta['splits']['newTrain']}
assert len(frozen['rows'])==len(report['fresh'])==32
assert len({r['parameterHash'] for r in frozen['rows']})==32
files=0;replays=0;max_error=0.
with Renderer() as renderer:
    for target,row in zip(frozen['rows'],report['fresh']):
        assert target==row['target'] and target['parameterHash'] not in excluded|training
        assert target['sourceRow'] in meta['splits']['newVal']
        assert parameter_hash(dict(synth='Transfxr',params=target['sourceParams']))==target['parameterHash']
        p,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
        assert p==target['sourceParams'] and audio_hash(wave)==target['audioHash']
        objective=MatchObjective(wave)
        for arm,count in (('control',8),('expanded',4)):
            assert len(row['pools'][arm])==count and not row['failures'][arm]
            for c in row['pools'][arm]:
                assert file_hash(c['waveFile'])==c['waveFileSha256']
                audio,rate=sf.read(c['waveFile'],dtype='float32')
                assert rate==44100 and audio_hash(audio)==c['audioHash'];files+=1
        selected=module.selections(row['targetPitch'],row['pools']['control'][:4],row['pools']['expanded'],row['pools']['control'])
        assert selected==row['selections']
        for c in {c['audioHash']:c for c in selected.values()}.values():
            p,audio=renderer.render(c['synth'],c['params'],c['seed'])
            assert p==c['params'] and audio_hash(audio)==c['audioHash']
            error=abs(float(objective.score_batch([audio])[0])-c['score']);assert error<1e-8
            max_error=max(error,max_error);replays+=1
summary=report['freshSummary'];old4=summary['old-four']['meanObjective'];new=summary['guarded-ensemble']['meanObjective']
checks=dict(fivePercentOverOldFour=new<=.95*old4,beatsOldEight=new<summary['old-eight']['meanObjective'],
            individualGuards=summary['guarded-ensemble']['individualGuardRegressions']==0)
assert checks==report['checks'] and all(checks.values())==report['numericalGatePassed']
audit=dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(source),
    candidateFilesVerified=files,distinctSelectedDspReplays=replays,maxRescoreError=max_error,
    scope='Reuses pitch diagnostics; numerical safeguard outcomes are partly guaranteed by construction.',
    freshSummary=summary,checks=checks,
    improvementOverOldFourFraction=(old4-new)/old4,
    improvementOverOldEightFraction=1-new/summary['old-eight']['meanObjective'],
    objectiveGainRejectedBySafeguard=new-summary['unguarded-ensemble']['meanObjective'],
    retrospectiveSummary={k:v['summary'] for k,v in report['retrospective'].items()})
dest=Path('tools/multisynth/evaluations/coverage-selection-v1-audit.json')
if dest.exists():raise FileExistsError('Fresh audit required')
_json_write(dest,audit);print(json.dumps(audit),flush=True)
