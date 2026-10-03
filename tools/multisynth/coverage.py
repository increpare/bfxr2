"""Six-reference development diagnostic of human-curated Soundboard coverage."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import quote

import soundfile as sf
import torch

from .coverage_feedback import export_coverage
from .features import VERSION, describe, distances, prepare
from .library import Library
from .report import add_preset
from .soundboard import BoardRenderer, REVISION, choose_candidates

TAGS = {'collect':'coin', 'hit':'hit', 'jump':'jump', 'step':'step', 'door':'door', 'magic':'cast'}
LABELS = {'automatic':'Automatic match', 'guided':'Category-guided diagnostic',
          'diverse':'Different ingredients', 'baseline':'Best previously rated'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def best_previous(target,candidates):
    # Stable ties prefer the original auditory-v1 result.
    roles = [(role,target[role]) for role in ('previous','selected','bfxr')
             if role in target and candidates[target[role]].get('rating') is not None]
    if not roles:
        raise ValueError('Reference has no prior likeness rating')
    return max(roles,key=lambda item:candidates[item[1]]['rating'])


def copy_archived_audio(source,destination):
    info = sf.info(source)
    if info.subtype != 'PCM_16' or info.samplerate != 44100 or info.channels != 1:
        raise ValueError('Expected archived mono 44.1 kHz PCM16 audio')
    wave,rate = sf.read(source,dtype='int16')
    sf.write(destination,wave,rate,subtype='PCM_16')


def verify_archived_audio(archive,info):
    path = (archive/info['file']).resolve()
    if not path.is_relative_to(archive.resolve()):
        raise ValueError('Archived audio path escapes archive')
    wave,rate = sf.read(path,dtype='int16',always_2d=True)
    actual = hashlib.sha256(str((rate,wave.shape)).encode()+wave.astype('<i2').tobytes()).hexdigest()
    if actual != info['pcmSha256']:
        raise ValueError('Archived PCM checksum differs: '+info['file'])


def run(snapshot,library_dir,archive,output):
    snapshot,library_dir,archive,output = map(Path,(snapshot,library_dir,archive,output))
    if output.exists():
        raise ValueError('Use a new output directory; listening experiments are immutable')
    torch.set_num_threads(1)
    manifest = json.loads((archive/'manifest.json').read_text())
    if digest(archive/'feedback.json') != manifest['feedbackSha256']:
        raise ValueError('Archived feedback checksum differs')
    prior = {c['id']:c for c in manifest['candidates']}
    targets = []
    for tag in TAGS:
        matches = [t for t in manifest['targets'] if t['source'].get('tag')==tag]
        if len(matches)!=1:
            raise ValueError('Expected exactly one archived reference for '+tag)
        targets.append(matches[0])
    for target in targets:
        verify_archived_audio(archive,target['referenceAudio'])
        _,candidate_id = best_previous(target,prior)
        verify_archived_audio(archive,prior[candidate_id]['audio'])
    records,collection = [],{}
    with BoardRenderer(snapshot) as renderer:
        source_hash = renderer.inventory['sourceHash']
        library = Library.load(library_dir,source_hash)
        if library.metadata['sourceRevision']!=REVISION:
            raise ValueError('Library revision mismatch')
        metadata = {
            'experiment':'soundboard-coverage-v3','evaluationType':'development / previously rated references',
            'featureVersion':VERSION,'objectiveVersion':VERSION,'sourceRevision':REVISION,
            'sourceHash':source_hash,'libraryManifestHash':digest(library_dir/'library.json'),
            'descriptorFileHash':digest(library_dir/'descriptors.npz'),
            'libraryRows':len(library.rows),'catalogueEntries':library.metadata['entries'],
            'takesPerEntry':library.metadata['takesPerEntry'],
            'excludedEntries':library.metadata['excludedEntries'],
            'priorExperimentId':manifest['experimentId'],'priorManifestHash':digest(archive/'manifest.json'),
            'selection':'Fixed six reviewed references: coin, punch, jump, step, door, magic; no score filtering',
            'automatic':'Global auditory-v1 retrieval across all verbs, no reference tags or human ratings',
            'guided':'Known tag filters candidates; choose next distinct recipe signature, then a second distinct recipe',
            'baseline':'Highest existing human likeness rating, ties prefer previous auditory-v1 result; exact archived PCM',
            'branchEvidence':'Pinned curated recipes and commit notes; no raw target-likeness ratings imported from other branch',
            'collectionUrl':'soundboard-choices.bcol',
        }
        output.mkdir(parents=True)
        for index,target in enumerate(targets):
            folder = f'{index+1:03d}'
            destination = output/folder
            destination.mkdir()
            copy_archived_audio(archive/target['referenceAudio']['file'],destination/'target.wav')
            reference,rate = sf.read(destination/'target.wav',dtype='float32')
            descriptor = describe(reference)
            scores = distances(descriptor,library.descriptors)
            verb = TAGS[target['source']['tag']]
            choices = choose_candidates(library.rows,scores,verb)
            candidates = []
            for order,(role,row_index) in enumerate(choices.items()):
                row = library.rows[row_index]
                params,wave = renderer.render(row['params'],row['seed'])
                if params != row['params']:
                    raise ValueError('Saved parameters are not canonical')
                filename = f'{order+1:02d}-{role}.wav'
                sf.write(destination/filename,prepare(wave)*.5,44100,subtype='PCM_16')
                name = target['source']['name']+' · '+LABELS[role]
                payload = json.dumps({'filename':name,'params':params},separators=(',',':')).replace('~','\\u007e')
                editor = os.path.relpath(snapshot,output).replace(os.sep,'/')+'/?sfx='+quote('Soundboard~@2~'+payload,safe='')
                candidate = {'label':LABELS[role],'role':role,'synth':'Soundboard','params':params,
                             'seed':row['seed'],'sourceHash':source_hash,'file':filename,
                             'score':float(scores[row_index]),'ingredients':row['ingredients'],'editUrl':editor,
                             'provenance':{'sourceRevision':REVISION,'libraryManifestHash':metadata['libraryManifestHash'],
                                           'libraryIndex':row_index,'verb':row['verb'],'entry':row['entry'],
                                           'signature':row['signature'],'composite':row['composite']}}
                candidates.append(candidate)
                add_preset(collection,candidate,name)
            old_role,old_id = best_previous(target,prior)
            old = prior[old_id]
            copy_archived_audio(archive/old['audio']['file'],destination/'04-baseline.wav')
            candidates.append({'label':LABELS['baseline'],'role':'baseline','synth':old['synth'],
                               'params':old['params'],'seed':old['seed'],
                               'sourceHash':manifest['provenance']['sourceHash'],'file':'04-baseline.wav',
                               'provenance':{'experimentId':manifest['experimentId'],'candidateId':old_id,
                                             'originalRole':old_role,'previousLikenessRating':old['rating'],
                                             'archivedPcmSha256':old['audio']['pcmSha256']}})
            records.append({'folder':folder,'source':target['source'],'candidates':candidates})
            print(f'{folder} {target["source"]["name"]}: '+', '.join(
                role+'='+library.rows[i]['signature'] for role,i in choices.items()),flush=True)
        (output/'soundboard-choices.bcol').write_text(json.dumps(collection,indent=2)+'\n')
        model = export_coverage(output,records,metadata)
    return {'targets':len(records),'candidates':sum(len(r['candidates']) for r in records),
            'experimentId':model['experimentId'],'output':str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','library','archive','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.snapshot,args.library,args.archive,args.output),indent=2))


if __name__=='__main__':
    main()
