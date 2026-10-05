"""Frozen additional native controls and explicit old-eight budget comparison."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_selection import POLICY, rejection_reasons, select_candidate
from neural_invert.coverage_train import load
from neural_invert.data import _json_write, file_hash
from neural_invert.evaluate import rendered_candidates, serializable
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.temporal import predict_temporal


def summarize(rows):
    names=rows[0]['selections']
    return {name:dict(meanObjective=float(np.mean([r['selections'][name]['score'] for r in rows])),
        selectedExpanded=sum(r['selections'][name]['origin']=='expanded' for r in rows),
        individualGuardRegressions=sum(bool(rejection_reasons(r['targetPitch'],r['selections']['old-four'],r['selections'][name])) for r in rows))
        for name in names}


def selections(pitch,old,new,old8=None):
    base=min(old,key=lambda c:c['score'])
    result={'old-four':base, 'unguarded-ensemble':min(old+new,key=lambda c:c['score']),
        'guarded-ensemble':select_candidate(pitch,base,old+new)}
    if old8 is not None:
        result['old-eight']=min(old+[c for c in old8],key=lambda c:c['score'])
        result['guarded-old-eight']=select_candidate(pitch,base,old+old8)
    return result


def run():
    torch.set_num_threads(1)
    native=Path('tools/multisynth/runs/native-coverage-v1')
    out=Path('tools/multisynth/runs/coverage-selection-v1')
    if out.exists():raise FileExistsError('Fresh experiment directory required')
    meta=json.loads((native/'data/Transfxr.json').read_text())
    manifest=json.loads((native/'data/manifest.json').read_text())
    previous=json.loads((native/'models/fresh-targets.json').read_text())
    excluded={r['parameterHash'] for r in previous['rows']}
    training={meta['rows'][i]['parameterHash'] for i in meta['splits']['oldTrain']+meta['splits']['newTrain']}
    chosen=[];seen=set(excluded)
    for i in np.random.default_rng(20261027).permutation(meta['splits']['newVal']):
        row=meta['rows'][int(i)]
        if row['parameterHash'] in seen:continue
        assert row['parameterHash'] not in training
        seen.add(row['parameterHash'])
        chosen.append(dict(id=f'Transfxr-selection-{int(i):05d}',sourceParams=row['params'],sourceSeed=row['seed'],
            audioHash=row['audioHash'],parameterHash=row['parameterHash'],sourceRow=int(i),sourceHash=manifest['sourceHash']))
        if len(chosen)==32:break
    assert len(chosen)==32
    out.mkdir(parents=True)
    _json_write(out/'targets.json',dict(rows=chosen,seed=20261027,
        dataManifestSha256=file_hash(native/'data/manifest.json'),excludedTargetsSha256=file_hash(native/'models/fresh-targets.json')))
    report=dict(complete=False,scriptSha256=file_hash(__file__),policy=POLICY,
        policySha256=file_hash('tools/neural_invert/coverage_selection.py'),targetsSha256=file_hash(out/'targets.json'),
        diagnosticCodeHashes={str(p):file_hash(p) for p in [*Path('tools/match').glob('*.py'),*Path('tools/neural_invert').glob('pitch_v5*.py')]},
        scope='New control-group holdout, shared preset families. Safeguard metrics are selection inputs. No human likeness claim.',
        budget='Old-four: 4; ensemble: 4 old + 4 expanded; old-eight: 8 old. Rendering/inference canonicalization overhead shared; unique proposals reported.',
        retrospective={},fresh=[])
    prior_path=native/'evaluation/results.json';prior=json.loads(prior_path.read_text());assert prior['complete']
    report['retrospectiveReportSha256']=file_hash(prior_path)
    for name,group in prior['sets'].items():
        rows=[]
        for r in group['rows']:
            old=[dict(c,origin='old') for c in r['arms']['control']['candidates']]
            new=[dict(c,origin='expanded') for c in r['arms']['expanded']['candidates']]
            rows.append(dict(id=r['target']['id'],targetPitch=r['targetPitch'],selections=selections(r['targetPitch'],old,new)))
        report['retrospective'][name]=dict(rows=rows,summary=summarize(rows))
    _json_write(out/'results.json',report)
    models={arm:load(native/'models'/arm) for arm in ('control','expanded')}
    report['checkpoints']={arm:m['checkpointHash'] for arm,(_,m) in models.items()}
    with Renderer() as renderer:
        for target in chosen:
            assert target['sourceHash']==renderer.inventory['sourceHash']
            p,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
            assert p==target['sourceParams'] and audio_hash(wave)==target['audioHash']
            directory=out/target['id'];directory.mkdir();sf.write(directory/'target.wav',wave,44100,subtype='FLOAT')
            pitch=descriptor_pitch(wave);objective=MatchObjective(wave);pools={};errors={}
            for arm,count in (('control',8),('expanded',4)):
                proposals=predict_temporal(*models[arm],wave,renderer,count=count)
                actual,failures=rendered_candidates(proposals,renderer,objective)
                failures += [dict(error='Missing proposal slot') for _ in range(count-len(proposals))]
                saved=[]
                for i,c in enumerate(actual):
                    path=directory/f'{arm}-{i}.wav';sf.write(path,c['wave'],44100,subtype='FLOAT')
                    decoded,sr=sf.read(path,dtype='float32');assert sr==44100 and np.array_equal(decoded,c['wave'])
                    cp=descriptor_pitch(c['wave'])
                    saved.append(dict(**serializable(c),origin='old' if arm=='control' else 'expanded',
                        waveFile=str(path.resolve()),waveFileSha256=file_hash(path),audioHash=audio_hash(c['wave']),
                        pitch=cp,pitchComparison=compare_descriptor_pitch(pitch,cp)))
                pools[arm]=saved;errors[arm]=failures
            # First four ranks from an eight-wide beam must match the actual four-wide baseline.
            small=predict_temporal(*models['control'],wave,renderer,count=4)
            assert [(c['params'],c['seed']) for c in small]==[(c['params'],c['seed']) for c in pools['control'][:4]]
            assert len(pools['control'])==8 and len(pools['expanded'])==4 and not any(errors.values())
            row=dict(target=target,targetPitch=pitch,pools=pools,failures=errors,
                selections=selections(pitch,pools['control'][:4],pools['expanded'],pools['control']))
            report['fresh'].append(row);_json_write(out/'results.json',report)
            print(json.dumps(dict(id=target['id'],scores={a:c['score'] for a,c in row['selections'].items()})),flush=True)
    report['freshSummary']=summarize(report['fresh']);s=report['freshSummary']
    report['checks']=dict(fivePercentOverOldFour=s['guarded-ensemble']['meanObjective']<=.95*s['old-four']['meanObjective'],
        beatsOldEight=s['guarded-ensemble']['meanObjective']<s['old-eight']['meanObjective'],
        individualGuards=s['guarded-ensemble']['individualGuardRegressions']==0)
    report.update(complete=True,numericalGatePassed=all(report['checks'].values()))
    _json_write(out/'results.json',report)
    print(json.dumps(dict(freshSummary=s,checks=report['checks'])),flush=True)


if __name__=='__main__':run()
