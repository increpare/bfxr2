"""Actual-render native-mixture comparison with unchanged transfer references."""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .coverage_mixture import load, DATA, BASE
from .coverage_train import load as load_base
from .data import file_hash, _json_write
from .evaluate import rendered_candidates, serializable
from .pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from .temporal import predict_temporal

TRANSFER=Path('tools/multisynth/runs/transfxr-transfer-v1/results.json')
EXCLUSIONS=[Path('tools/multisynth/runs/native-coverage-v1/models/fresh-targets.json'),
            Path('tools/multisynth/runs/coverage-selection-v1/targets.json')]


def fresh_targets(meta, excluded, count=32, seed=20261104):
    rows=meta['rows'];splits=meta['splits']
    training={rows[i]['parameterHash'] for i in splits['oldTrain']+splits['newTrain']}
    if any(rows[i]['parameterHash'] in training for i in splits['newVal']):
        raise ValueError('Training/validation control leakage')
    seen=set(excluded);chosen=[]
    for i in np.random.default_rng(seed).permutation(splits['newVal']):
        r=rows[int(i)]
        if r['parameterHash'] in seen:continue
        seen.add(r['parameterHash'])
        chosen.append(dict(id=f'Transfxr-mixture-{int(i):05d}', group='fresh-native',sourceSynth='Transfxr',
                           sourceParams=r['params'],sourceSeed=r['seed'],audioHash=r['audioHash'],
                           parameterHash=r['parameterHash'],sourceRow=int(i)))
        if len(chosen)==count:break
    if len(chosen)!=count:raise ValueError('Not enough distinct unused validation controls')
    return chosen


def write_wave(path, wave):
    sf.write(path,wave,44100,subtype='FLOAT')
    decoded,rate=sf.read(path,dtype='float32')
    assert rate==44100 and np.array_equal(wave,decoded)
    return dict(waveFile=str(path.resolve()),waveFileSha256=file_hash(path),audioHash=audio_hash(wave))


def read_wave(c):
    if file_hash(c['waveFile'])!=c['waveFileSha256']:raise ValueError('Changed source WAV')
    wave,rate=sf.read(c['waveFile'],dtype='float32')
    if rate!=44100 or audio_hash(wave)!=c['audioHash']:raise ValueError('Changed source PCM')
    return wave


def summarize(rows):
    groups={}
    for r in rows:
        key=r['target']['group']
        if r['target'].get('variant'):key='self/'+r['target']['variant']
        groups.setdefault(key,[]).append(r)
    result={}
    for key,group in groups.items():
        arms={}
        for arm in ('baseline','single','mixture'):
            selected=[r['selected'][arm] for r in group]
            if any(c is None for c in selected):
                arms[arm]=dict(count=len(group),missing=sum(c is None for c in selected));continue
            arms[arm]=dict(count=len(group),meanDistance=float(np.mean([c['score'] for c in selected])),
                pairedWithBaseline=sum(r['selected']['baseline'] is not None for r in group),
                pairedWithSingle=sum(r['selected']['single'] is not None for r in group),
                winsOverBaseline=sum(c['score']<r['selected']['baseline']['score']-1e-8 for r,c in zip(group,selected)
                                     if r['selected']['baseline'] is not None),
                winsOverSingle=sum(c['score']<r['selected']['single']['score']-1e-8 for r,c in zip(group,selected)
                                   if r['selected']['single'] is not None),
                reliableTargets=sum(r['targetPitch']['reliable'] for r in group),
                pitchWithinSemitone=sum(r['targetPitch']['reliable'] and c['pitchComparison']['medianErrorSemitones'] is not None
                    and c['pitchComparison']['medianErrorSemitones']<=1 for r,c in zip(group,selected)),
                meanDistinctNumericPredictions=float(np.mean([r['numericDiversity'][arm] for r in group])))
        result[key]=arms
    return result


def run(models, out):
    torch.set_num_threads(1);out=Path(out)
    if out.exists():raise FileExistsError('Fresh evaluation required')
    previous=json.loads(TRANSFER.read_text());assert previous['complete']
    excluded={r['parameterHash'] for path in EXCLUSIONS for r in json.loads(path.read_text())['rows']}
    meta=json.loads((DATA/'Transfxr.json').read_text())
    chosen=fresh_targets(meta,excluded)
    out.mkdir(parents=True)
    manifest=dict(fresh=chosen,transferTargets=[r['target']['id'] for r in previous['rows']],seed=20261104,
                  sourceReportSha256=file_hash(TRANSFER),dataManifestSha256=file_hash(DATA/'manifest.json'),
                  exclusions={str(p):file_hash(p) for p in EXCLUSIONS},scriptSha256=file_hash(__file__))
    _json_write(out/'targets.json',manifest)
    trained={a:load(Path(models)/a) for a in ('single','mixture')};trained['baseline']=load_base(BASE)
    report=dict(complete=False,manifestSha256=file_hash(out/'targets.json'),scriptSha256=file_hash(__file__),
                checkpoints={a:m['checkpointHash'] for a,(_,m) in trained.items()},
                codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/temporal.py'),Path('tools/neural_invert/features.py'),
                            *Path('tools/match').glob('*.py'),*Path('tools/neural_invert').glob('pitch_v5*.py')]},
                scope='Four proposals per arm, no search. Native holdout controls share training preset families; transfer cases are development.',rows=[])
    with Renderer() as renderer:
        work=[(r['target'],r) for r in previous['rows']]+[(t,None) for t in chosen]
        for index,(target,prior) in enumerate(work):
            folder=out/f'{index:03d}';folder.mkdir()
            if prior:wave=read_wave(target)
            else:
                p,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
                assert p==target['sourceParams'] and audio_hash(wave)==target['audioHash']
            target={**target,**write_wave(folder/'target.wav',wave)}
            pitch=descriptor_pitch(wave);objective=MatchObjective(wave);pools={};errors={};diversity={}
            for arm in ('baseline','single','mixture'):
                if arm=='baseline' and prior:
                    pool=prior['pools']['expanded'];assert len(pool)==4 and not prior['failures']['expanded']
                    actual=[dict(c,wave=read_wave(c)) for c in pool];failures=[]
                    assert report['checkpoints']['baseline']==previous['checkpoints']['expanded']
                else:
                    proposals=predict_temporal(*trained[arm],wave,renderer,count=4)
                    actual,failures=rendered_candidates(proposals,renderer,objective)
                    failures += [dict(error='Missing proposal slot') for _ in range(4-len(proposals))]
                saved=[]
                for i,c in enumerate(actual):
                    audio=c['wave'];cp=descriptor_pitch(audio)
                    score=float(objective.score_batch([audio])[0]);assert abs(score-c['score'])<1e-7
                    saved.append({**serializable(c),'origin':arm,'pitch':cp,'pitchComparison':compare_descriptor_pitch(pitch,cp),
                                  **write_wave(folder/f'{arm}-{i}.wav',audio)})
                pools[arm]=saved;errors[arm]=failures
                from .schema import ControlSchema
                schema=ControlSchema(renderer.specs['Transfxr'])
                diversity[arm]=len({tuple(schema.encode(c['params'])[0].tolist()) for c in saved})
            selected={a:min(pool,key=lambda c:c['score']) if pool else None for a,pool in pools.items()}
            report['rows'].append(dict(target=target,targetPitch=pitch,pools=pools,failures=errors,
                                       numericDiversity=diversity,selected=selected))
            _json_write(out/'results.json',report)
            print(json.dumps(dict(done=index+1,total=len(work),id=target['id'],scores={a:c['score'] if c else None for a,c in selected.items()})),flush=True)
    report.update(complete=True,summary=summarize(report['rows']));_json_write(out/'results.json',report)
    print(json.dumps(report['summary']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--models',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.models,a.output)
