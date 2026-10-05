"""Frozen validation renders for the fine-onset input experiment."""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from .benchmark import audio_hash
from .data import _json_write, file_hash
from .evaluate import rendered_candidates, serializable
from .onset_train import load, predict
from .pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from .temporal import load_temporal, predict_temporal

GATE = {'minimumMeanObjectiveReduction':.05,'maximumAdditionalMissing':0,
        'maximumAdditionalFailedRenders':0,'maximumStaticPitchPassLoss':0,
        'meaning':'synthetic candidate-generation gate for listening, not perceptual adequacy'}


def gate(control, onset):
    mean = (control['meanObjective'] is not None and onset['meanObjective'] is not None
            and onset['meanObjective'] <= control['meanObjective']*.95)
    complete = control['targets']==onset['targets'] and control['targets']>0 and onset['missing']==0
    renders = onset['failedRenders'] <= control['failedRenders']
    pitch = onset['staticPass'] >= control['staticPass']
    return {'passed':bool(mean and complete and renders and pitch),'objectivePassed':bool(mean),
            'coveragePassed':bool(complete),'rendersPassed':bool(renders),'pitchPassed':bool(pitch),'policy':GATE}


def freeze(source, output, per_stratum=16, seed=20261015):
    source,output=Path(source).resolve(),Path(output)
    if output.exists(): raise FileExistsError('Frozen target list exists')
    rng=np.random.default_rng(seed)
    rows=[]
    manifest=json.loads((source/'manifest.json').read_text())
    for name in ('Bfxr','Transfxr'):
        meta=json.loads((source/(name+'.json')).read_text())
        train_hashes={meta['rows'][i]['parameterHash'] for i in meta['train']}
        for structured in (False,True):
            pool=[i for i in meta['val'] if bool(meta['rows'][i].get('structured'))==structured]
            rng.shuffle(pool)
            chosen=[]; seen=set()
            for i in pool:
                row=meta['rows'][i]
                assert row['parameterHash'] not in train_hashes
                if row['parameterHash'] not in seen:
                    chosen.append(i);seen.add(row['parameterHash'])
                if len(chosen)==per_stratum: break
            if len(chosen)!=per_stratum: raise ValueError('Insufficient distinct validation groups')
            for i in chosen:
                row=meta['rows'][i]
                rows.append({'id':f'{name}-val-{i:05d}','sourceSynth':name,'sourceParams':row['params'],
                             'sourceSeed':row['seed'],'audioHash':row['audioHash'],'parameterHash':row['parameterHash'],
                             'sourceRow':i,'stratum':'structured' if structured else 'native',
                             'sourceHash':manifest['sourceHash']})
    _json_write(output,{'schemaVersion':1,'sourcePath':str(source),'sourceManifestSha256':file_hash(source/'manifest.json'),
                       'seed':seed,'perStratum':per_stratum,'policy':GATE,'rows':rows,
                       'scope':'Never-trained control groups from checkpoint validation split; development evidence, not an untouched test set.'})


def summary(rows, arm):
    best=[r['arms'][arm]['selected'] for r in rows]
    scores=[r['score'] for r in best if r]
    return {'targets':len(rows),'missing':sum(r is None for r in best),
            'failedRenders':sum(len(r['arms'][arm]['failures']) for r in rows),
            'meanObjective':float(np.mean(scores)) if scores else None,
            'staticTotal':sum(r['staticDiagnostic'] for r in rows),
            'staticPass':sum(r['staticDiagnostic'] and c is not None and c['pitchComparison']['medianErrorSemitones'] is not None
                             and c['pitchComparison']['medianErrorSemitones']<=1 for r,c in zip(rows,best))}


def evaluate(targets, models, frozen, output):
    targets,models,frozen,output=map(Path,(targets,models,frozen,output))
    if output.exists(): raise FileExistsError('Evaluation output exists')
    source=json.loads(targets.read_text())
    if file_hash(Path(source['sourcePath'])/'manifest.json')!=source['sourceManifestSha256']:
        raise ValueError('Source target data changed')
    torch.set_num_threads(1)
    names=sorted({r['sourceSynth'] for r in source['rows']})
    experts={name:{arm:load(models/name/arm) for arm in ('control','onset')} for name in names}
    old={name:load_temporal(frozen/name) for name in names}
    for name in names:
        a,b=experts[name]['control'][1],experts[name]['onset'][1]
        for key in ('initialWeightsHash','splitHash','normalization','seed','epochs','batchSize','dataManifestSha256'):
            if a[key]!=b[key]: raise ValueError('Paired arms differ in '+key)
    output.mkdir(parents=True)
    report={'complete':False,'targetsSha256':file_hash(targets),'codeSha256':file_hash(__file__),
            'scope':'Known-source-engine inversion; equal four-candidate budgets, no refinement. Not routing or perceptual accuracy.',
            'rows':[]}
    with Renderer() as renderer:
        for target in source['rows']:
            name=target['sourceSynth']
            if target['sourceHash']!=renderer.inventory['sourceHash']:
                raise ValueError('Target DSP mismatch')
            params,wave=renderer.render(name,target['sourceParams'],target['sourceSeed'])
            if params!=target['sourceParams'] or audio_hash(wave)!=target['audioHash']:
                raise ValueError('Target replay mismatch')
            directory=output/target['id'];directory.mkdir()
            sf.write(directory/'target.wav',wave,44100,subtype='FLOAT')
            target_pitch=descriptor_pitch(wave)
            row={**target,'targetPitch':target_pitch,
                 'staticDiagnostic':bool(target_pitch['reliable'] and target_pitch['spanSemitones']<=1),
                 'arms':{}}
            objective=MatchObjective(wave)
            for arm in ('control','onset','frozen-v3'):
                proposals=(predict_temporal(*old[name],wave,renderer,count=4) if arm=='frozen-v3'
                           else predict(*experts[name][arm],wave,renderer,count=4))
                accepted,failures=rendered_candidates(proposals,renderer,objective)
                saved=[]
                for i,c in enumerate(accepted):
                    if not np.isfinite(c['score']): raise ValueError('Nonfinite candidate objective')
                    path=directory/f'{arm}-{i}.wav'
                    sf.write(path,c['wave'],44100,subtype='FLOAT')
                    saved.append({**serializable(c),'waveFile':str(path.resolve()),'audioHash':audio_hash(c['wave']),
                                  'waveFileSha256':file_hash(path),
                                  'pitchComparison':compare_descriptor_pitch(target_pitch,descriptor_pitch(c['wave']))})
                # Unfilled categorical slots count as failures rather than disappearing.
                failures += [{'error':'missing proposal slot'} for _ in range(4-len(proposals))]
                row['arms'][arm]={'selected':min(saved,key=lambda x:x['score']) if saved else None,
                                  'candidates':saved,'failures':failures,'proposed':len(proposals)}
            report['rows'].append(row)
            _json_write(output/'results.json',report)
            print(json.dumps({'target':target['id'],'scores':{a:v['selected']['score'] if v['selected'] else None for a,v in row['arms'].items()}}),flush=True)
    report['summaries']={name:{arm:summary([r for r in report['rows'] if r['sourceSynth']==name],arm)
                             for arm in ('control','onset','frozen-v3')} for name in names}
    report['gates']={name:gate(s['control'],s['onset']) for name,s in report['summaries'].items()}
    report['complete']=True
    _json_write(output/'results.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    f=sub.add_parser('freeze');f.add_argument('--source',required=True);f.add_argument('--output',required=True)
    e=sub.add_parser('evaluate');e.add_argument('--targets',required=True);e.add_argument('--models',required=True)
    e.add_argument('--frozen',required=True);e.add_argument('--output',required=True)
    a=p.parse_args()
    if a.action=='freeze':freeze(a.source,a.output)
    else:evaluate(a.targets,a.models,a.frozen,a.output)
