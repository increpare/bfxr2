"""Large mixed-backend reproduction experiment with learned/fixed comparisons."""
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

from match.audio import load_audio
from .coverage import copy_archived_audio, verify_archived_audio, digest
from .coverage_feedback import export_coverage
from .features import VERSION, describe, prepare, distances
from .library import Library
from .refine import board_specs, distinct_starts, refine
from .renderer import Renderer
from .search import approximate
from .soundboard import BoardRenderer, REVISION


class AuditoryMetric:
    distances = staticmethod(distances)


def candidate_key(row):
    return json.dumps({key:row[key] for key in ('backend','synth','seed','params')},sort_keys=True,separators=(',',':'))


def latest_best(observations):
    latest={}
    for observation in sorted(observations,key=lambda o:o['session']):
        latest[observation['candidate']['audio']['pcmSha256']]=observation
    return max(latest.values(),key=lambda o:(o['rating'],o['session']))


def history(archives):
    by_source={}
    for session,archive in enumerate(archives):
        data=json.loads((archive/'manifest.json').read_text())
        if digest(archive/'feedback.json')!=data['feedbackSha256']:
            raise ValueError('Feedback changed: '+str(archive))
        candidates={c['id']:c for c in data['candidates']}
        for target in data['targets']:
            verify_archived_audio(archive,target['referenceAudio'])
            if data.get('schemaVersion',1)>=2:
                ids=[c['id'] for c in target['candidates']]
                dimension='likeness'
            else:
                ids=[target[r] for r in ('selected','previous','bfxr') if r in target]
                dimension='rating'
            for cid in dict.fromkeys(ids):
                candidate=candidates[cid]
                if candidate.get(dimension) is None:
                    continue
                verify_archived_audio(archive,candidate['audio'])
                observation={
                    'candidate':candidate,'rating':candidate[dimension],'session':session,
                    'archive':archive,'target':target,'experimentId':data['experimentId'],
                    'sourceHash':candidate.get('sourceHash',data['provenance'].get('sourceHash'))}
                by_source.setdefault(target['source']['sha256'],[]).append(observation)
                by_source.setdefault('pcm:'+target['referenceAudio']['pcmSha256'],[]).append(observation)
    return by_source


def run(args):
    from .preference import PreferenceMetric
    if args.output.exists():
        raise ValueError('Use a new output directory; existing listening runs are immutable')
    if min(args.jobs,args.learned_starts,args.auditory_starts,args.budget)<1:
        raise ValueError('Jobs, starts, and budget must be positive')
    torch.set_num_threads(1)
    sources=json.loads(args.targets.read_text())['targets']
    if args.limit:
        sources=sources[:args.limit]
    for source in sources:
        if digest(source['path'])!=source['sha256']:
            raise ValueError('Frozen target changed: '+source['path'])
    old=history(args.archives)
    with Renderer() as renderer:
        legacy_hash=renderer.inventory['sourceHash']
    with BoardRenderer(args.snapshot) as renderer:
        board_hash=renderer.inventory['sourceHash']
    legacy=Library.load(args.library,legacy_hash)
    old_library=Library.load(args.baseline_library,legacy_hash)
    board=Library.load(args.board_library,board_hash)
    rows=[dict(row,backend='legacy',sourceHash=legacy_hash) for row in legacy.rows]+[
        dict(row,backend='board',sourceHash=board_hash) for row in board.rows]
    descriptors=np.concatenate([legacy.descriptors,board.descriptors])
    specs=board_specs(args.snapshot)
    metadata={'experiment':'multisynth-big-v4','featureVersion':VERSION,'objectiveVersion':'preference-v4',
              'modelHash':digest(args.model),'sourceHashes':{'legacy':legacy_hash,'board':board_hash},
              'boardRevision':REVISION,'libraryRows':len(rows),'legacyLibraryHash':digest(args.library/'library.json'),
              'boardLibraryHash':digest(args.board_library/'library.json'),
              'baselineLibraryHash':digest(args.baseline_library/'library.json'),
              'descriptorFileHashes':{'legacy':digest(args.library/'descriptors.npz'),
                                      'board':digest(args.board_library/'descriptors.npz'),
                                      'baseline':digest(args.baseline_library/'descriptors.npz')},
              'targetManifestHash':digest(args.targets),'targetCount':len(sources),
              'searchCodeHash':hashlib.sha256(Path(__file__).read_bytes()+Path(__file__).with_name('refine.py').read_bytes()).hexdigest(),
              'metricCodeHash':hashlib.sha256(b''.join(Path(__file__).with_name(name+'.py').read_bytes()
                                                     for name in ('features','gesture','preference'))).hexdigest(),
              'trainingArchives':[{'path':str(a),'manifestHash':digest(a/'manifest.json')} for a in args.archives],
              'budgetPerStart':args.budget,'learnedStarts':args.learned_starts,'auditoryStarts':args.auditory_starts,
              'seed':args.seed,'selection':'All frozen tagged references, no filtering by new scores; no tag-based retrieval',
              'refinement':'Fixed recipe, phrase, random seed, categorical choices and alignment; bounded continuous controls',
              'historicalSeeds':'Up to two previously rated candidates per known reference; supervised development, not unseen generalization',
              'galleryTitle':'Multi-synth reproduction · large listening run',
              'galleryIntro':[
                  'Please rate how closely each new sound recreates the reference: its gesture, movement, texture and overall feel. 1 = far off, 3 = recognizably similar, 5 = very close. Usefulness/fun is optional.',
                  'Retrained match uses all your saved likeness ratings; it remains experimental, with no validated quality win yet. Expanded original model uses the original audio distance on the same generated candidate pool. Previous best replays your strongest earlier choice; on new references, Original matcher supplies the baseline.',
                  'Some references are new to these listening rounds; others are development examples used in training. Each row says which. If two methods produce the same audio, they share one card. There is no need to finish everything at once: ratings save in this browser; copy the JSON whenever you stop.'],
              'complete':False}
    args.output.mkdir(parents=True)
    shutil.copyfile(args.model,args.output/'model.json')
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')

    def one(item):
        index,source=item
        started=time.monotonic()
        folder=f'{index+1:03d}';dest=args.output/folder;dest.mkdir()
        sf.write(dest/'target.wav',prepare(load_audio(Path(source['path'])))*.5,44100,subtype='PCM_16')
        pcm,rate=sf.read(dest/'target.wav',dtype='int16',always_2d=True)
        pcm_hash=hashlib.sha256(str((rate,pcm.shape)).encode()+pcm.astype('<i2').tobytes()).hexdigest()
        observations=old.get(source['sha256'],old.get('pcm:'+pcm_hash,[]))
        previous=latest_best(observations) if observations else None
        if previous:
            copy_archived_audio(previous['archive']/previous['target']['referenceAudio']['file'],dest/'target.wav')
        target,_=sf.read(dest/'target.wav',dtype='float32');reference=describe(target)
        learned=PreferenceMetric.load(args.model);auditory=AuditoryMetric()
        learned_scores=learned.distances(reference,descriptors)
        auditory_scores=auditory.distances(reference,descriptors)
        starts=[('learned',deepcopy(rows[i])) for i in distinct_starts(rows,learned_scores,args.learned_starts)]
        starts += [('auditory',deepcopy(rows[i])) for i in distinct_starts(rows,auditory_scores,args.auditory_starts)]
        # Human preferences are deliberately useful development seeds, never hidden test labels.
        anchored={}
        for observation in sorted(observations,key=lambda o:o['session']):
            anchored[observation['candidate']['audio']['pcmSha256']]=observation
        for observation in sorted(anchored.values(),key=lambda o:(-o['rating'],-o['session']))[:2]:
            c=observation['candidate']
            backend='board' if c['synth']=='Soundboard' else 'legacy'
            if observation['sourceHash']!=metadata['sourceHashes'][backend]:
                continue
            seedrow={k:deepcopy(c[k]) for k in ('synth','params','seed')}
            seedrow.update(backend=backend,sourceHash=observation['sourceHash'],preset='human-preferred seed',
                           humanSeed={'experimentId':observation['experimentId'],'candidateId':c['id'],'likeness':observation['rating']})
            starts.append(('learned',seedrow))
            starts.append(('auditory',seedrow))
        pool={};traces=[]
        with Renderer() as legacy_renderer,BoardRenderer(args.snapshot) as board_renderer:
            if legacy_renderer.inventory['sourceHash']!=legacy_hash or board_renderer.inventory['sourceHash']!=board_hash:
                raise ValueError('DSP source changed during run')
            def render(row):
                if row['backend']=='board':
                    return board_renderer.render(row['params'],row['seed'])
                return legacy_renderer.render(row['synth'],row['params'],row['seed'])
            for start_index,(objective,start) in enumerate(starts):
                a,b=(learned,auditory) if objective=='learned' else (auditory,learned)
                spec=legacy_renderer.specs[start['synth']] if start['backend']=='legacy' else None
                children,trace=refine(start,render,spec,specs if start['backend']=='board' else None,
                                      reference,a,b,args.budget,args.seed+index*1009+start_index*71)
                for child in children:
                    child['learnedScore']=child['score'] if objective=='learned' else child['otherScore']
                    child['auditoryScore']=child['otherScore'] if objective=='learned' else child['score']
                    pool[candidate_key(child)]=child
                traces.append({'objective':objective,'synth':start['synth'],'backend':start['backend'],
                               'preset':start.get('signature',start.get('preset')),'humanSeed':start.get('humanSeed'),**trace})
            choices=[('learned','Retrained match',min(pool.values(),key=lambda r:r['learnedScore'])),
                     ('auditory','Expanded original model',min(pool.values(),key=lambda r:r['auditoryScore']))]
            cards=[];audios={}
            for role,label,c in choices:
                params,wave=render(c)
                descriptor=describe(wave)
                if abs(float(learned.distances(reference,descriptor[None])[0])-c['learnedScore'])>1e-5:
                    raise ValueError('Candidate replay changed learned score')
                if abs(float(auditory.distances(reference,descriptor[None])[0])-c['auditoryScore'])>1e-5:
                    raise ValueError('Candidate replay changed auditory score')
                filename=role+'.wav';sf.write(dest/filename,prepare(wave)*.5,44100,subtype='PCM_16')
                audio_hash=digest(dest/filename)
                if audio_hash in audios:
                    audios[audio_hash]['label']='Both new selectors agree'
                    audios[audio_hash]['provenance']['selectors'].append(role)
                    continue
                card={'role':role,'label':label,'synth':c['synth'],'params':params,'seed':c['seed'],
                      'sourceHash':c['sourceHash'],'file':filename,'score':c['learnedScore'],
                      'provenance':{'backend':c['backend'],'sourceRevision':REVISION if c['backend']=='board' else None,
                                    'selectors':[role],
                                    'modelHash':metadata['modelHash'],'learnedScore':c['learnedScore'],
                                    'auditoryScore':c['auditoryScore'],'humanSeed':c.get('humanSeed')}}
                cards.append(card);audios[audio_hash]=card
            if previous:
                c=previous['candidate']
                copy_archived_audio(previous['archive']/c['audio']['file'],dest/'baseline.wav')
                baseline={'role':'baseline','label':'Previous best','synth':c['synth'],'params':c['params'],
                          'seed':c['seed'],'sourceHash':previous['sourceHash'],'file':'baseline.wav',
                          'provenance':{'experimentId':previous['experimentId'],'candidateId':c['id'],
                                        'archivedPcmSha256':c['audio']['pcmSha256'],'previousLikeness':previous['rating']}}
            else:
                result=approximate(legacy_renderer,old_library,target,experts=5,budget=64,seed=args.seed)
                c=result['candidates'][0]
                sf.write(dest/'baseline.wav',prepare(c['wave'])*.5,44100,subtype='PCM_16')
                baseline={'role':'baseline','label':'Original matcher','synth':c['synth'],'params':c['params'],
                          'seed':c['seed'],'sourceHash':legacy_hash,'file':'baseline.wav',
                          'provenance':{'objectiveVersion':VERSION,'libraryHash':metadata['baselineLibraryHash'],
                                        'budgetPerExpert':64,'experts':5}}
            baseline_hash=digest(dest/'baseline.wav')
            if baseline_hash in audios:
                audios[baseline_hash]['label']+=' (same audio as '+baseline['label'].lower()+')'
                audios[baseline_hash]['provenance']['baselineAlias']=baseline['provenance']
            else:
                cards.append(baseline)
        record={'folder':folder,'source':dict(source,previouslyRatedReference=bool(previous)),
                'candidates':cards,'note':'Previously rated reference — development comparison.' if previous else 'New to these listening rounds — please compare against the original matcher.',
                'search':{'starts':len(starts),'evaluations':len(starts)*args.budget,
                          'seconds':time.monotonic()-started,'traces':traces,'finalPoolSize':len(pool),
                          'humanSeedStarts':sum(bool(s.get('humanSeed')) for _,s in starts)}}
        (dest/'report.json').write_text(json.dumps(record,indent=2)+'\n')
        print(f'COMPLETE {folder}/{len(sources)} {source["tag"]}: '+', '.join(c['label']+'='+c['synth'] for c in cards),flush=True)
        return record

    records=[];started=time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures=[executor.submit(one,item) for item in enumerate(sources)]
        for future in as_completed(futures):
            records.append(future.result());records.sort(key=lambda r:r['folder'])
    metadata.update(complete=True,elapsedSeconds=time.monotonic()-started,
                    previouslyRatedReferences=sum(r['source']['previouslyRatedReference'] for r in records),
                    newReferences=sum(not r['source']['previouslyRatedReference'] for r in records),
                    refinementRenders=sum(r['search']['evaluations'] for r in records))
    model=export_coverage(args.output,records,metadata)
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return {'targets':len(records),'candidates':sum(len(r['candidates']) for r in records),
            'experimentId':model['experimentId'],'seconds':metadata['elapsedSeconds']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','library','baseline-library','board-library','targets','model','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--archives',nargs='+',type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=3)
    parser.add_argument('--budget',type=int,default=96)
    parser.add_argument('--learned-starts',type=int,default=8)
    parser.add_argument('--auditory-starts',type=int,default=8)
    parser.add_argument('--seed',type=int,default=9182)
    parser.add_argument('--limit',type=int,default=0)
    print(json.dumps(run(parser.parse_args()),indent=2))


if __name__=='__main__':
    main()
