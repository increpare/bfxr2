"""Build an inverse library, approximate audio, or evaluate a local corpus."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.audio import load_audio
from .features import VERSION, prepare
from .library import Library, build
from .renderer import Renderer
from .search import approximate
from .report import export_match, export_benchmark

AUDIO_SUFFIXES = {'.wav','.ogg','.flac','.aiff','.aif','.mp3'}


def benchmark_root(root, all_collections=False):
    """Prefer the curated tags subtree; also accept a directly supplied audio folder."""
    return root/'tags' if not all_collections and (root/'tags').is_dir() else root


def source_info(path, root=None):
    return {'name':str(path.relative_to(root)) if root else path.name,
            'path':str(path.resolve()), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def select_targets(root, count, seed, max_seconds):
    """Round-robin over shuffled source collections; no labels reach matching."""
    groups = defaultdict(list)
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES:
            rel = path.relative_to(root)
            groups[rel.parts[0] if len(rel.parts)>1 else '.'].append(path)
    rng = np.random.default_rng(seed)
    for paths in groups.values():
        rng.shuffle(paths)
    selected, rejected, seen = [], [], set()
    while groups and len(selected)<count:
        for group in list(groups):
            path = groups[group].pop()
            if not groups[group]:
                del groups[group]
            try:
                info = sf.info(path)
                # Skip long recordings rather than silently matching a truncated crop.
                if info.duration > max_seconds or info.duration < .025:
                    continue
                wave = prepare(load_audio(path))
                digest = hashlib.sha256(wave.tobytes()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                selected.append(path)
            except (ValueError, RuntimeError, sf.LibsndfileError) as exc:
                rejected.append({'path':str(path),'error':str(exc)})
                continue
            if len(selected)>=count:
                break
    return selected, rejected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('build')
    p.add_argument('-o','--output',type=Path,required=True)
    p.add_argument('--per-preset',type=int,default=12)
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--seed',type=int,default=1729)
    p.add_argument('--synths',help='Comma-separated synth names (default all supported)')
    for name in ('match','benchmark'):
        p = sub.add_parser(name)
        p.add_argument('target',type=Path)
        p.add_argument('--library',type=Path,required=True)
        p.add_argument('-o','--output',type=Path,required=True)
        p.add_argument('--experts',type=int,default=5)
        p.add_argument('--budget',type=int,default=96,help='Additional evaluations per expert; Bfxr is always retained')
        p.add_argument('--seed',type=int,default=1234)
        p.add_argument('--synths',help='Restrict matching to these comma-separated names')
        if name=='benchmark':
            p.add_argument('--count',type=int,default=40)
            p.add_argument('--max-seconds',type=float,default=4)
            p.add_argument('--all-collections',action='store_true',
                           help='Use the entire supplied corpus instead of preferring its tags/ directory')
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.seed < 0 or args.seed > 2**31-1:
        parser.error('seed must be between 0 and 2147483647')
    if args.command == 'benchmark' and (args.count < 1 or args.max_seconds <= 0):
        parser.error('count and max-seconds must be positive')
    synths = args.synths.split(',') if args.synths else None
    with Renderer() as renderer:
        if synths and set(synths)-renderer.specs.keys():
            parser.error('Unknown synths: '+str(set(synths)-renderer.specs.keys()))
        if args.command=='build':
            library = build(renderer,args.output,args.per_preset,args.seed,synths,args.jobs)
            print(f'Saved {len(library.rows)} exemplars to {args.output}',flush=True)
            return
        library = Library.load(args.library, renderer.inventory['sourceHash'])
        if args.command=='match':
            target = prepare(load_audio(args.target))
            result = approximate(renderer,library,target,experts=args.experts,budget=args.budget,seed=args.seed,synths=synths)
            export_match(args.output,target,result,source_info(args.target))
        else:
            root = benchmark_root(args.target,args.all_collections)
            print(f'Target directory: {root.resolve()}',flush=True)
            paths, rejected = select_targets(root,args.count,args.seed,args.max_seconds)
            if not paths:
                parser.error('No usable targets')
            args.output.mkdir(parents=True,exist_ok=True)
            metadata = {'featureVersion':VERSION,'sourceHash':renderer.inventory['sourceHash'],
                        'library':str(args.library.resolve()), 'libraryRows':len(library.rows),
                        'libraryManifestHash':hashlib.sha256((args.library/'library.json').read_bytes()).hexdigest(),
                        'seed':args.seed,'budgetPerExpert':args.budget,'experts':args.experts,
                        'synths':synths, 'maxSeconds':args.max_seconds,'selectionRejected':rejected,
                        'targetRoot':str(root.resolve()), 'allCollections':args.all_collections,
                        'targets':[source_info(p,args.target) for p in paths]}
            (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
            records, started = [], time.monotonic()
            for i,path in enumerate(paths):
                print(f'[{i+1}/{len(paths)}] {path.relative_to(args.target)}',flush=True)
                target = prepare(load_audio(path))
                result = approximate(renderer,library,target,experts=args.experts,budget=args.budget,seed=args.seed,synths=synths)
                folder = f'{i+1:03d}'
                report = export_match(args.output/folder,target,result,metadata['targets'][i])
                records.append(report | {'folder':folder})
                metadata['elapsedSeconds'] = time.monotonic()-started
                stats = export_benchmark(args.output,records,metadata)
            print(json.dumps(stats,indent=2),flush=True)


if __name__ == '__main__':
    main()
