"""Generate a frozen tagged iteration with old/new/Bfxr listening comparisons."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import time

import torch

from match.audio import load_audio
from .features import VERSION, describe, distances, prepare
from .gesture import GestureMetric, model_hash
from .library import Library
from .renderer import Renderer
from .report import export_match, export_benchmark
from .search import approximate

DEFAULT_TAGS = ('attack','bell','carbeep','card','chains','click','collect','door',
                'explode','hit','jump','laser','magic','power_up','shoot','slime','step','sword')


def select_batch(manifest_path, tags):
    manifest = json.loads(Path(manifest_path).read_text())
    missing = set(tags)-{t['tag'] for t in manifest['targets']}
    if missing:
        raise ValueError('Missing tags: '+', '.join(sorted(missing)))
    selected = [t for t in manifest['targets'] if t['tag'] in tags]
    if len({t['path'] for t in selected}) != len(selected):
        raise ValueError('Repeated target path in frozen manifest')
    for target in selected:
        if hashlib.sha256(Path(target['path']).read_bytes()).hexdigest() != target['sha256']:
            raise ValueError('Frozen target changed: '+target['path'])
    return selected


def run(args):
    if args.jobs < 1 or args.budget < 0 or args.experts < 1:
        raise ValueError('jobs/experts must be positive and budget nonnegative')
    torch.set_num_threads(1)
    targets = select_batch(args.targets,args.tags.split(',') if args.tags else DEFAULT_TAGS)
    with Renderer() as renderer:
        source_hash = renderer.inventory['sourceHash']
    old_library = Library.load(args.previous_library,source_hash)
    library = Library.load(args.library,source_hash)
    metric = GestureMetric.load(args.model)
    checkpoint_hash = model_hash(args.model)
    metadata = {'featureVersion':VERSION,'objectiveVersion':metric.version,
                'modelHash':checkpoint_hash,'sourceHash':source_hash,
                'libraryManifestHash':model_hash(args.library/'library.json'),
                'libraryRows':len(library.rows),'seed':args.seed,'budgetPerExpert':args.budget,
                'experts':args.experts,'previousLibraryManifestHash':model_hash(args.previous_library/'library.json'),
                'previousLibraryRows':len(old_library.rows),'previousBudgetPerExpert':64,'previousExperts':5,
                'targetManifestSha256':model_hash(args.targets),'targets':targets,
                'selection':'Preselected 18 game-SFX tags; no filtering by new scores or listening outcomes',
                'trainingReferenceOverlap':sum(t.get('previouslyRatedReference',False) for t in targets),
                'comparisonLimits':'The new model searches twice as many starting examples and spends longer refining sounds. The Bfxr sample uses the new matching method too; the previous-model sample uses the original method. This compares the complete new setup, so a win will not tell us which individual change helped.',
                'jobs':args.jobs}
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    shutil.copyfile(args.model,args.output/'model.json')

    def one(item):
        index, source = item
        folder = f'{index+1:03d}'
        target = prepare(load_audio(Path(source['path'])))
        with Renderer() as renderer:
            if renderer.inventory['sourceHash'] != source_hash:
                raise ValueError('DSP changed during iteration')
            old = approximate(renderer,old_library,target,experts=5,budget=64,seed=args.seed)
            previous = export_match(args.output/'previous'/folder,target,old,source)
            new = approximate(renderer,library,target,experts=args.experts,budget=args.budget,
                              seed=args.seed,metric=metric,seed_candidates=old['candidates'])
            new.update(objectiveVersion=metric.version,modelHash=checkpoint_hash)
            record = export_match(args.output/folder,target,new,source)
            old_winner = previous['candidates'][0]
            previous_file = 'previous-'+old_winner['file']
            shutil.copyfile(args.output/'previous'/folder/old_winner['file'],args.output/folder/previous_file)
            record.update(folder=folder,previous={**old_winner,'file':previous_file,'objectiveVersion':VERSION},
                          previousRun={'search_evaluations':old['search_evaluations'],
                                       'seconds':old['seconds'],'export_renders':old['export_renders']})
            ref = describe(target)
            comparison_descriptors = [describe(old['candidates'][0]['wave']),describe(new['candidates'][0]['wave'])]
            record['comparisonScores'] = {'oldAndNewUnderGesture':metric.distances(ref,comparison_descriptors).tolist(),
                                          'oldAndNewUnderAuditoryV1':distances(ref,comparison_descriptors).tolist()}
            (args.output/folder/'report.json').write_text(json.dumps(record,indent=2)+'\n')
            print(f'COMPLETE {folder}/{len(targets)} {source["tag"]}: {old_winner["synth"]} -> {record["candidates"][0]["synth"]}',flush=True)
            return record

    started = time.monotonic()
    records = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(one,item) for item in enumerate(targets)]
        for future in as_completed(futures):
            records.append(future.result())
            records.sort(key=lambda r:r['folder'])
            metadata['elapsedSeconds'] = time.monotonic()-started
            metadata['complete'] = len(records) == len(targets)
            export_benchmark(args.output,records,metadata)
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    return {'targets':len(records),'seconds':metadata['elapsedSeconds'],'output':str(args.output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets',type=Path,required=True)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--previous-library',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tags',help='Comma-separated tags; default 18 varied game-SFX tags')
    parser.add_argument('--jobs',type=int,default=3)
    parser.add_argument('--budget',type=int,default=96)
    parser.add_argument('--experts',type=int,default=8)
    parser.add_argument('--seed',type=int,default=1234)
    args = parser.parse_args()
    print(json.dumps(run(args),indent=2))


if __name__ == '__main__':
    main()
