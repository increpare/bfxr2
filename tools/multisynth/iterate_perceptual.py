"""Tagged v5 development comparisons, with equal search budgets and exact baselines."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import time

import numpy as np
import soundfile as sf
import torch

from . import features, perceptual
from .big_run import history, latest_best
from .coverage import copy_archived_audio, digest
from .coverage_feedback import export_coverage
from .paired_search import load_banks, search_pair, V4Metric
from .refine import board_specs
from .renderer import Renderer
from .soundboard import BoardRenderer, REVISION
from .train_perceptual import PerceptualMetric


def run(args):
    if args.output.exists():
        raise ValueError('Use a fresh output directory; listening runs are immutable')
    if min(args.jobs,args.starts,args.budget)<1:
        raise ValueError('Jobs, starts, and budget must be positive')
    torch.set_num_threads(1)
    sources=json.loads(args.targets.read_text())['targets']
    if args.limit:sources=sources[:args.limit]
    old=history(args.archives)
    with Renderer() as renderer:legacy_hash=renderer.inventory['sourceHash']
    with BoardRenderer(args.snapshot) as renderer:board_hash=renderer.inventory['sourceHash']
    rows,descriptors=load_banks(args.library,args.board_library,legacy_hash,board_hash,args.legacy_base,args.board_base)
    specs=board_specs(args.snapshot)
    metadata={'experiment':'multisynth-perceptual-v5','featureVersion':perceptual.VERSION,
              'objectiveVersion':'perceptual-v5','modelHash':digest(args.model),'v4ModelHash':digest(args.v4_model),
              'sourceHashes':{'legacy':legacy_hash,'board':board_hash},'boardRevision':REVISION,
              'libraryRows':len(rows),'featureDimension':perceptual.DIM,
              'libraryHashes':{name:{'rows':digest(path/'library.json'),'descriptors':digest(path/'descriptors.npz')}
                               for name,path in [('legacy',args.library),('board',args.board_library)]},
              'codeHashes':{name:digest(Path(__file__).with_name(name+'.py')) for name in
                            ('iterate_perceptual','paired_search','refine','perceptual','train_perceptual','features','gesture','preference','coverage_feedback')},
              'trainingArchives':[{'path':str(a),'manifestHash':digest(a/'manifest.json')} for a in args.archives],
              'targetManifestHash':digest(args.targets),'targetCount':len(sources),'budgetPerStart':args.budget,
              'startsPerObjective':args.starts,'seed':args.seed,'complete':False,
              'selection':'Frozen alternating tagged manifest rows, chosen before v5 scores. All are supervised development references.',
              'galleryTitle':'Multi-synth reproduction · gestures and texture',
              'galleryIntro':[
                  'Please compare the new recreations with the reference and Previous best. Rate likeness from 1 (far off) to 5 (very close), judging gesture, movement, texture and overall feel. Useful/fun is optional.',
                  'Both scorers are retrained on all four saved rating rounds. Event/texture model adds attacks, gaps, repetition and texture cues; Refitted old model keeps the previous feature set. Both get equal search budgets and select from the same proposals; Previous best replays your strongest earlier rated choice.',
                  'These are familiar tagged development references, not an unseen test. The new model is experimental; listening will determine whether the changes help. Identical audio is merged into one card. Ratings save in this browser; copy the JSON when you stop.'],
              'humanSeeds':'Up to two historical candidates, identical for both searches; no rating used as a distance term.'}
    args.output.mkdir(parents=True)
    for path,name in [(args.model,'model.json'),(args.v4_model,'v4-model.json')]:shutil.copyfile(path,args.output/name)
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')

    def one(item):
        index,source=item;started=time.monotonic()
        if digest(source['path'])!=source['sha256']:raise ValueError('Frozen target changed')
        observations=old.get(source['sha256'],[])
        if not observations:raise ValueError('Tagged development target lacks a rated baseline')
        previous=latest_best(observations)
        folder=f'{index+1:03d}';dest=args.output/folder;dest.mkdir()
        copy_archived_audio(previous['archive']/previous['target']['referenceAudio']['file'],dest/'target.wav')
        wave,rate=sf.read(dest/'target.wav',dtype='float32')
        if rate!=44100:raise ValueError('Unexpected reference rate')
        reference=perceptual.describe(wave)
        v5=PerceptualMetric.load(args.model);v4=V4Metric(args.v4_model)
        anchored={}
        for observation in sorted(observations,key=lambda o:o['session']):
            anchored[observation['candidate']['audio']['pcmSha256']]=observation
        seeds=[]
        for observation in sorted(anchored.values(),key=lambda o:(-o['rating'],-o['session']))[:2]:
            c=observation['candidate'];backend='board' if c['synth']=='Soundboard' else 'legacy'
            if observation['sourceHash']!=metadata['sourceHashes'][backend]:continue
            row={key:deepcopy(c[key]) for key in ('synth','params','seed')}
            row.update(backend=backend,sourceHash=observation['sourceHash'],preset='human-preferred seed',
                       humanSeed={'experimentId':observation['experimentId'],'candidateId':c['id'],'likeness':observation['rating']})
            seeds.append(row)
        with Renderer() as legacy,BoardRenderer(args.snapshot) as board:
            if legacy.inventory['sourceHash']!=legacy_hash or board.inventory['sourceHash']!=board_hash:
                raise ValueError('DSP changed during search')
            def render(row):
                return board.render(row['params'],row['seed']) if row['backend']=='board' else legacy.render(row['synth'],row['params'],row['seed'])
            result=search_pair(rows,descriptors,reference,v5,v4,render,legacy.specs,specs,
                               starts=args.starts,budget=args.budget,seed=args.seed+index*1009,human_seeds=seeds)
            cards=[];audios={}
            for role,label in [('v5','Event/texture model'),('v4','Refitted old model')]:
                c=result['choices'][role];params,wave=render(c);descriptor=perceptual.describe(wave)
                for name,metric in [('v5',v5),('v4',v4)]:
                    if abs(float(metric.distances(reference,descriptor[None])[0])-c[name+'Score'])>1e-5:
                        raise ValueError('Selected candidate score changed on replay')
                filename=role+'.wav';sf.write(dest/filename,features.prepare(wave)*.5,44100,subtype='PCM_16')
                audio_hash=digest(dest/filename)
                if audio_hash in audios:
                    audios[audio_hash]['label']='Both new selectors agree'
                    audios[audio_hash]['provenance']['selectors'].append(role)
                    continue
                card={'role':role,'label':label,'synth':c['synth'],'params':params,'seed':c['seed'],
                      'sourceHash':c['sourceHash'],'file':filename,
                      'provenance':{'backend':c['backend'],'selectors':[role],'modelHash':metadata['modelHash'],
                                    'v4ModelHash':metadata['v4ModelHash'],'v5Score':c['v5Score'],'v4Score':c['v4Score'],
                                    'humanSeed':c.get('humanSeed'),'sourceRevision':REVISION if c['backend']=='board' else None}}
                cards.append(card);audios[audio_hash]=card
            c=previous['candidate'];copy_archived_audio(previous['archive']/c['audio']['file'],dest/'baseline.wav')
            baseline={'role':'baseline','label':'Previous best','synth':c['synth'],'params':c['params'],'seed':c['seed'],
                      'sourceHash':previous['sourceHash'],'file':'baseline.wav',
                      'provenance':{'experimentId':previous['experimentId'],'candidateId':c['id'],
                                    'archivedPcmSha256':c['audio']['pcmSha256'],'previousLikeness':previous['rating']}}
            baseline_hash=digest(dest/'baseline.wav')
            if baseline_hash in audios:
                audios[baseline_hash]['label']+=' (same audio as previous best)'
                audios[baseline_hash]['provenance']['baselineAlias']=baseline['provenance']
            else:cards.append(baseline)
        record={'folder':folder,'source':dict(source,previouslyRatedReference=True),'candidates':cards,
                'note':'Previously rated tagged reference — development comparison.',
                'unchangedOnly':len(audios)==1 and baseline_hash in audios,
                'search':{'starts':len(result['traces']),'evaluations':result['evaluations'],'traces':result['traces'],
                          'seconds':time.monotonic()-started,'finalPoolSize':len(result['pool']),
                          'humanSeedStarts':2*len(seeds)}}
        (dest/'report.json').write_text(json.dumps(record,indent=2)+'\n')
        print(f'COMPLETE {folder}/{len(sources)} {source["tag"]}: '+', '.join(c['label']+'='+c['synth'] for c in cards),flush=True)
        return record

    records=[];started=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for future in as_completed([executor.submit(one,item) for item in enumerate(sources)]):records.append(future.result())
    records.sort(key=lambda r:r['folder'])
    metadata.update(complete=True,elapsedSeconds=time.monotonic()-started,
                    refinementProposals=sum(r['search']['evaluations'] for r in records),
                    unchangedOnlyFolders=[r['folder'] for r in records if r['unchangedOnly']])
    shown=[r for r in records if not r['unchangedOnly']]
    (args.output/'all-results.json').write_text(json.dumps({'metadata':metadata,'results':records},indent=2)+'\n')
    model=export_coverage(args.output,shown,metadata)
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return {'targets':len(shown),'candidates':sum(len(r['candidates']) for r in shown),
            'experimentId':model['experimentId'],'seconds':metadata['elapsedSeconds']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','library','board-library','legacy-base','board-base','targets','model','v4-model','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--archives',nargs='+',type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=4);parser.add_argument('--starts',type=int,default=8)
    parser.add_argument('--budget',type=int,default=64);parser.add_argument('--seed',type=int,default=10521)
    parser.add_argument('--limit',type=int,default=0)
    print(json.dumps(run(parser.parse_args()),indent=2))


if __name__=='__main__':main()
