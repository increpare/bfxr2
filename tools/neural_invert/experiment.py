"""Independent reconstruction checks and tagged listening with original Bfxr."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf
import torch

from match.audio import prepare_target, normalize_peak
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.renderer import Renderer
from multisynth.coverage_feedback import export_coverage
from multisynth.big_run import history, latest_best
from multisynth.coverage import copy_archived_audio
from .evaluate import OriginalBfxr, approximate, digest, serializable, pitch_summary


def _write_wave(path,wave):
    sf.write(path,normalize_peak(np.asarray(wave,dtype=np.float32)),44100,subtype='PCM_16')


_WORKER = None


def _init_worker(args,old,provenance):
    # CMA uses NumPy's global RNG: independent processes isolate each target.
    global _WORKER
    from .predict import load_model
    torch.set_num_threads(1)
    model,metadata=load_model(args.model)
    _WORKER=(args,model,metadata,old,provenance)


def _tagged_one(item):
    args,model,metadata,old,provenance=_WORKER
    index,source=item; started=time.monotonic();folder=f'{index+1:03d}'
    if digest(source['path']) != source['sha256']:raise ValueError('Frozen source changed')
    dest=args.output/folder;dest.mkdir()
    previous=latest_best(old[source['sha256']]) if old.get(source['sha256']) else None
    if previous:
        copy_archived_audio(previous['archive']/previous['target']['referenceAudio']['file'],dest/'target.wav')
        wave,rate=sf.read(dest/'target.wav',dtype='float32')
        if rate!=44100:raise ValueError('Reference rate differs')
    else:
        wave=prepare_target(source['path']);_write_wave(dest/'target.wav',wave)
    # Match the exact reference audition, including its trim and duration.
    wave,_=sf.read(dest/'target.wav',dtype='float32')
    with Renderer() as renderer,BfxrRenderer(jobs=1) as original_renderer:
        if renderer.inventory['sourceHash']!=metadata['sourceHash']:raise ValueError('Training DSP differs')
        original=OriginalBfxr(args.bfxr_checkpoint,original_renderer)
        result=approximate(model,metadata,wave,renderer,original,starts=args.starts,
                   budget=args.budget,bfxr_budget=args.bfxr_budget,seed=args.seed+index*1009)
        cards=[]
        for role,label in [('raw','Raw neural prediction'),('selected','Automatic expert choice'),('original','Original Bfxr')]:
            c=result[role]
            if c is None:continue
            filename=role+'.wav';_write_wave(dest/filename,c['wave'])
            card={**serializable(c),'role':role,'label':label,'file':filename,
                'sourceHash':metadata['sourceHash'],
                'provenance':{**c['provenance'],'matchObjectiveScore':c['score'],
                    'modelSha256':provenance['modelSha256'],'backend':'original-bfxr' if c.get('expert') else 'neural',
                    'pitchDiagnostic':pitch_summary(c['wave'])}}
            cards.append(card)
        if previous:
            c=previous['candidate'];filename='previous.wav'
            copy_archived_audio(previous['archive']/c['audio']['file'],dest/filename)
            cards.append({'role':'previous','label':'Previous best','synth':c['synth'],'params':c['params'],
                'seed':c['seed'],'sourceHash':previous['sourceHash'],'file':filename,
                'provenance':{'experimentId':previous['experimentId'],'candidateId':c['id'],
                    'archivedPcmSha256':c['audio']['pcmSha256'],'previousLikeness':previous['rating']}})
    record={'folder':folder,'source':source,'candidates':cards,
        'note':'Previously reviewed development reference. No target category is given to inference.',
        'diagnostics':{'referencePitch':pitch_summary(wave),
            'neuralBest':serializable(result['neural']),
            'allRaw':[{**serializable(r),'pitchDiagnostic':pitch_summary(r['wave'])} for r in result['allRaw']],
            'failures':result['failures'],'evaluations':result['evaluations'],
            'seconds':time.monotonic()-started}}
    (dest/'report.json').write_text(json.dumps(record,indent=2)+'\n')
    raw_name=result['raw']['synth'] if result['raw'] else 'unavailable'
    print(f'TAGGED {folder}/{provenance["targetCount"]} {source["name"]}: selected={result["selected"]["synth"]} raw={raw_name}',flush=True)
    return record


def _synthetic_one(target):
    args,model,metadata,old,provenance=_WORKER
    dest=args.output/target['folder'];wave,_=sf.read(dest/'target.wav',dtype='float32')
    with Renderer() as renderer,BfxrRenderer(jobs=1) as old_renderer:
        original=OriginalBfxr(args.bfxr_checkpoint,old_renderer)
        result=approximate(model,metadata,wave,renderer,original,args.starts,args.budget,args.bfxr_budget,
                           seed=args.seed+int(target['folder'])*71)
    known=[r for r in result['allRaw'] if r['synth']==target['synth']]
    known=min(known,key=lambda r:r['score']) if known else None
    roles={'known_raw':known,'unrestricted_raw':result['raw'],
           'neural_refined':result['neural'],'selected':result['selected'],'original':result['original']}
    record={'target':target,'referencePitch':pitch_summary(wave),'candidates':{},
            'failures':result['failures'],'evaluations':result['evaluations']}
    for role,c in roles.items():
        if c is None:
            record['candidates'][role]=None
            continue
        _write_wave(dest/(role+'.wav'),c['wave'])
        record['candidates'][role]={**serializable(c),'pitchDiagnostic':pitch_summary(c['wave'])}
    (dest/'report.json').write_text(json.dumps(record,indent=2)+'\n')
    raw_score=f'{known["score"]:.3f}' if known else 'unavailable'
    print(f'SYNTHETIC {target["folder"]}/{provenance["targetCount"]} {target["synth"]}: raw={raw_score} selected={result["selected"]["score"]:.3f}',flush=True)
    return record

def tagged(args):
    from .predict import load_model
    if args.output.exists():
        raise ValueError('Use a fresh listening output directory')
    model,metadata=load_model(args.model)
    sources=json.loads(args.targets.read_text())['targets']
    if args.limit:sources=sources[:args.limit]
    old=history(args.archives)
    args.output.mkdir(parents=True)
    provenance={'experiment':'neural-multisynth-v1','modelSha256':digest(args.model),
        'targetCount':len(sources),
        'bfxrCheckpointSha256':digest(args.bfxr_checkpoint),'targetManifestSha256':digest(args.targets),
        'trainedEngines':metadata['engines'],'complete':False,
        'galleryTitle':'Learned multisynth inversion · first training run',
        'galleryIntro':[
          'These candidates come from trained audio-to-control experts for every listed instrument. The original Bfxr neural model and optimizer are restored as a separate baseline.',
          'Raw neural prediction shows the best rendered prediction before refinement. Automatic expert choice compares refined learned predictions with Original Bfxr. Previous best is the exact audio from your earlier ratings.',
          'Rate likeness independently from useful/fun. These are familiar tagged development references; this first trained model has not yet established a human quality improvement. Ratings save here and can be copied as JSON.'],
        'sourceHash':metadata['sourceHash'],'starts':args.starts,'refinementBudgetPerStart':args.budget,
        'originalBfxrBudget':args.bfxr_budget,
        'scope':'Individual numeric engines; Jinglr editable phrase structure comes from predicted generator, not note transcription.'}
    (args.output/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')


    started=time.monotonic();records=[]
    with ProcessPoolExecutor(max_workers=args.jobs,initializer=_init_worker,initargs=(args,old,provenance)) as executor:
        for future in as_completed([executor.submit(_tagged_one,item) for item in enumerate(sources)]):records.append(future.result())
    records.sort(key=lambda r:r['folder'])
    provenance.update(complete=True,seconds=time.monotonic()-started)
    result=export_coverage(args.output,records,provenance)
    (args.output/'manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return {'targets':len(records),'experimentId':result['experimentId'],'seconds':provenance['seconds']}


def synthetic(args):
    from .predict import load_model
    from .schema import ControlSchema
    if args.output.exists():raise ValueError('Use a fresh synthetic output directory')
    model,metadata=load_model(args.model)
    if digest(args.data/'manifest.json') != metadata['dataManifestHash']:
        raise ValueError('Synthetic holdout data differs from checkpoint training data')
    from .data import verify_dataset_files
    verify_dataset_files(args.data,json.loads((args.data/'manifest.json').read_text()))
    # Dataset rows, including validation, are excluded from fresh target draws.
    exclusions={}
    for name in metadata['engines']:
        path=args.data/(name+'.json')
        payload=json.loads(path.read_text())
        rows=payload['rows']
        schema=ControlSchema(metadata['specs'][name])
        exclusions[name]={json.dumps(schema.encode(row['params'])[0].tolist())+'|'+
                          json.dumps(schema.encode(row['params'])[1].tolist())+'|'+
                          row['params'].get('phrase','') for row in rows}
    args.output.mkdir(parents=True)
    targets=[]
    with Renderer() as renderer:
        if renderer.inventory['sourceHash']!=metadata['sourceHash']:raise ValueError('Training DSP changed')
        for engine in metadata['engines']:
            schema=ControlSchema(renderer.specs[engine]);presets=renderer.specs[engine]['presets']
            for index in range(args.per_synth):
                for retry in range(500):
                    seed=int.from_bytes(__import__('hashlib').sha256(f'neural-independent:{args.seed}:{engine}:{index}:{retry}'.encode()).digest()[:4],'little')
                    preset=presets[(index*len(presets)//args.per_synth)%len(presets)]
                    params=renderer.sample(engine,preset,seed)
                    params,wave=renderer.render(engine,params,seed^0xA591)
                    unit,cats=schema.encode(params)
                    key=json.dumps(unit.tolist())+'|'+json.dumps(cats.tolist())+'|'+params.get('phrase','')
                    if key in exclusions[engine] or np.max(np.abs(wave))<1e-5:continue
                    exclusions[engine].add(key)
                    folder=f'{len(targets)+1:03d}';dest=args.output/folder;dest.mkdir()
                    _write_wave(dest/'target.wav',wave)
                    targets.append({'folder':folder,'synth':engine,'preset':preset,'params':params,
                                    'seed':seed^0xA591,'sampleSeed':seed,'sourceHash':metadata['sourceHash']})
                    break
                else:raise ValueError('Unable to draw independent target '+engine)
    provenance={'experiment':'neural-v1-independent-synthetic','modelSha256':digest(args.model),
        'targetCount':len(targets),
        'bfxrCheckpointSha256':digest(args.bfxr_checkpoint),'sourceHash':metadata['sourceHash'],
        'scope':'Fresh generator draws and numeric/categorical parameter holdout; not held-out generator families.',
        'perSynth':args.per_synth,'complete':False}
    (args.output/'manifest.json').write_text(json.dumps({'metadata':provenance,'targets':targets},indent=2)+'\n')


    records=[];started=time.monotonic()
    with ProcessPoolExecutor(max_workers=args.jobs,initializer=_init_worker,initargs=(args,{},provenance)) as executor:
        for f in as_completed([executor.submit(_synthetic_one,t) for t in targets]):records.append(f.result())
    records.sort(key=lambda r:r['target']['folder'])
    summary={}
    for role in records[0]['candidates']:
        scores=[r['candidates'][role]['score'] for r in records if r['candidates'][role] is not None]
        summary[role]={'mean':float(np.mean(scores)) if scores else None,
            'median':float(np.median(scores)) if scores else None,'available':len(scores),'missing':len(records)-len(scores)}
    summary['directEngineRecovery']=sum(r['candidates']['unrestricted_raw'] is not None and
        r['candidates']['unrestricted_raw']['synth']==r['target']['synth'] for r in records)
    provenance.update(complete=True,seconds=time.monotonic()-started)
    report={'metadata':provenance,'summary':summary,'results':records}
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'manifest.json').write_text(json.dumps({'metadata':provenance,'targets':targets},indent=2)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['tagged','synthetic'])
    for name in ('model','bfxr-checkpoint','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--data',type=Path);parser.add_argument('--targets',type=Path)
    parser.add_argument('--archives',type=Path,nargs='+',default=[])
    parser.add_argument('--limit',type=int,default=0);parser.add_argument('--per-synth',type=int,default=2)
    parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--starts',type=int,default=4)
    parser.add_argument('--budget',type=int,default=128);parser.add_argument('--bfxr-budget',type=int,default=2000)
    parser.add_argument('--seed',type=int,default=20261004)
    args=parser.parse_args()
    if min(args.jobs,args.starts,args.budget,args.bfxr_budget,args.per_synth)<1:parser.error('Budgets and counts must be positive')
    if args.mode=='synthetic' and args.data is None:parser.error('--data is required for synthetic evaluation')
    if args.mode=='tagged' and args.targets is None:parser.error('--targets is required for tagged evaluation')
    torch.set_num_threads(1)
    print(json.dumps((tagged if args.mode=='tagged' else synthetic)(args),indent=2))


if __name__=='__main__':main()
