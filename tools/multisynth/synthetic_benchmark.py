"""Held-out synthetic reconstruction diagnostics; never human training labels.

Seed holdout measures new draws of known generators. The optional legacy-only
preset condition removes the exact generator label, not every semantic alias.
"""
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
from .paired_search import load_banks, search_pair, V4Metric
from .perceptual_library import audition_hash, digest, feature_hash
from .refine import board_specs
from .renderer import Renderer
from .soundboard import BoardRenderer, REVISION
from .train_perceptual import PerceptualMetric


def stable_seed(namespace, *parts):
    data = json.dumps([namespace, *parts], separators=(',', ':')).encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:4], 'little')


def parameter_key(synth, params):
    # Deliberately excludes external rendering seed and backend name.
    return json.dumps([synth, params], sort_keys=True, separators=(',', ':'), allow_nan=False)


def row_parameter_keys(row):
    keys = {parameter_key(row['synth'], row['params'])}
    if row.get('backend') == 'board':
        for source in json.loads(row['params'].get('sources', '[]')):
            keys.add(parameter_key(source['synth'], source['params']))
    return keys


class HoldoutIndex:
    def __init__(self, rows):
        self.params, self.pcm = set(), set()
        for row in rows:
            self.params.update(row_parameter_keys(row))
            if not row.get('auditionPcmSha256'):
                raise ValueError('Every cached row needs an audition PCM hash')
            self.pcm.add(row['auditionPcmSha256'])

    def reason(self, synth, params, pcm_hash):
        if parameter_key(synth, params) in self.params:
            return 'canonical_parameters_present_ignoring_render_seed'
        if pcm_hash in self.pcm:
            return 'normalized_audition_pcm_present'
        return None

    def add(self, synth, params, pcm_hash):
        self.params.add(parameter_key(synth, params))
        self.pcm.add(pcm_hash)


class TargetGenerationError(ValueError):
    def __init__(self, message, targets, rejected):
        super().__init__(message)
        self.targets, self.rejected = targets, rejected


def scope_indices(rows, target, condition):
    if condition not in ('known_engine', 'unrestricted', 'leave_preset_out'):
        raise ValueError('Unknown synthetic condition')
    selected = []
    for i, row in enumerate(rows):
        # Defensive exclusion even when generation already checked all banks.
        if (parameter_key(target['synth'], target['params']) in row_parameter_keys(row)
                or row.get('auditionPcmSha256') == target['auditionPcmSha256']):
            continue
        if condition == 'known_engine' and (row['backend'] != 'legacy' or row['synth'] != target['synth']):
            continue
        if condition == 'leave_preset_out':
            if row['backend'] != 'legacy':
                continue
            if row['synth'] == target['synth'] and row.get('preset') == target['preset']:
                continue
        selected.append(i)
    return np.asarray(selected, dtype=int)


def generate_targets(renderer, rows, namespace, recipes=2, samples=2, attempts=32, limit=0):
    """Generate balanced targets; deterministic failures stay in the manifest."""
    heldout = HoldoutIndex(rows)
    targets, rejected = [], []
    engines = sorted(name for name, spec in renderer.specs.items() if spec.get('collectionCompatible'))
    for synth in engines:
        presets = sorted(renderer.specs[synth]['presets'], key=lambda p: (stable_seed(namespace, synth, p), p))
        # Footsteppr has only one exposed generator. Keep engine weight equal
        # with more disjoint draws, rather than inventing a second recipe.
        recipe_count = min(recipes, len(presets))
        slots = [recipes*samples//recipe_count + (i < recipes*samples % recipe_count)
                 for i in range(recipe_count)] if recipe_count else []
        completed = 0
        for preset in presets:
            accepted = []
            for slot in range(slots[completed]):
                for attempt in range(attempts):
                    sampling_seed = stable_seed(namespace, synth, preset, slot, attempt, 'sample')
                    render_seed = stable_seed(namespace, synth, preset, slot, attempt, 'render')
                    if render_seed == sampling_seed:
                        render_seed = (render_seed + 1) % 2**32
                    identity = dict(synth=synth, preset=preset, slot=slot, attempt=attempt,
                                    samplingSeed=sampling_seed, seed=render_seed)
                    try:
                        params = renderer.sample(synth, preset, sampling_seed)
                        params, wave = renderer.render(synth, params, render_seed)
                        pcm_hash = audition_hash(wave)
                        reason = heldout.reason(synth, params, pcm_hash)
                    except (ValueError, RuntimeError) as exc:
                        rejected.append({**identity, 'reason':'render_or_audio_failure', 'error':str(exc)})
                        continue
                    if reason:
                        rejected.append({**identity, 'params':params, 'auditionPcmSha256':pcm_hash, 'reason':reason})
                        continue
                    heldout.add(synth, params, pcm_hash)
                    accepted.append({**identity, 'params':params, 'auditionPcmSha256':pcm_hash,
                                     'sourceHash':renderer.inventory['sourceHash']})
                    break
                else:
                    rejected.append(dict(synth=synth, preset=preset, slot=slot, reason='attempt_limit_exhausted'))
                    break
            if len(accepted) != slots[completed]:
                rejected.extend({**row, 'reason':'discarded_incomplete_recipe_group'} for row in accepted)
                continue
            targets.extend(accepted)
            completed += 1
            if limit and len(targets) >= limit:
                return targets[:limit], rejected, engines
            if completed == recipe_count:
                break
        if not recipe_count or completed < recipe_count:
            raise TargetGenerationError(
                f'{synth}: only {completed}/{recipe_count} recipes yielded distinct held-out targets; '
                f'{len(rejected)} rejected draws', targets, rejected)
    return targets, rejected, engines


def summarize(records):
    def aggregate(items):
        result = {}
        conditions = sorted({name for row in items for name in row['conditions']})
        for condition in conditions:
            pairs = [r['conditions'][condition] for r in items if condition in r['conditions']]
            result[condition] = {}
            for objective in ('v4', 'v5'):
                values = [p['selectors'][objective] for p in pairs]
                result[condition][objective] = {
                    'targets':len(values),
                    'meanAuditoryV1Before':float(np.mean([v['before']['auditoryV1'] for v in values])),
                    'meanAuditoryV1After':float(np.mean([v['after']['auditoryV1'] for v in values])),
                    'medianAuditoryV1After':float(np.median([v['after']['auditoryV1'] for v in values])),
                    'sameSourceEngine':sum(v['sameSourceEngine'] for v in values),
                }
            differences = [p['selectors']['v4']['after']['auditoryV1'] - p['selectors']['v5']['after']['auditoryV1'] for p in pairs]
            result[condition]['auditoryV1Comparison'] = {
                'v5Lower':sum(d > 1e-5 for d in differences), 'ties':sum(abs(d) <= 1e-5 for d in differences),
                'v4Lower':sum(d < -1e-5 for d in differences)}
        return result
    return {'aggregate':aggregate(records), 'perEngine':{
        name:aggregate([r for r in records if r['target']['synth'] == name])
        for name in sorted({r['target']['synth'] for r in records})}}


def load_metrics(model_path, v4_path):
    # Both scorers cache target representations. Never share them across
    # concurrently processed references, even when their weights are frozen.
    return PerceptualMetric.load(model_path), V4Metric(v4_path)


def replayed_candidate(row, params, pcm_hash):
    """Snapshot replay identity, replacing any inherited library audio hash."""
    return {**deepcopy(row), 'params':deepcopy(params), 'auditionPcmSha256':pcm_hash}


def run(args):
    if min(args.jobs, args.starts, args.recipes, args.samples, args.attempts) < 1 or args.budget < 0 or args.limit < 0:
        raise ValueError('Counts must be positive; budget and limit must be nonnegative')
    if args.output.exists():
        raise ValueError('Use a fresh immutable output directory')
    torch.set_num_threads(1)
    with Renderer() as renderer:
        legacy_hash = renderer.inventory['sourceHash']
    with BoardRenderer(args.snapshot) as renderer:
        board_hash = renderer.inventory['sourceHash']
    rows, descriptors = load_banks(args.library, args.board_library, legacy_hash, board_hash,
                                   args.legacy_base, args.board_base)
    load_metrics(args.model, args.v4_model)  # Validate checkpoints before output creation.
    source_specs = board_specs(args.snapshot)
    frozen_features = feature_hash()
    hashes = {name:digest(path) for name,path in [('v5',args.model),('v4',args.v4_model)]}
    with Renderer() as renderer:
        if renderer.inventory['sourceHash'] != legacy_hash:
            raise ValueError('DSP changed before target generation')
        try:
            targets, rejected, engines = generate_targets(renderer, rows, args.namespace, args.recipes,
                                                           args.samples, args.attempts, args.limit)
        except TargetGenerationError as exc:
            args.output.mkdir(parents=True)
            (args.output/'generation-failure.json').write_text(json.dumps({
                'complete':False,'error':str(exc),'sourceHash':legacy_hash,'namespace':args.namespace,
                'targets':exc.targets,'rejections':exc.rejected},indent=2,allow_nan=False)+'\n')
            raise
    metadata = {'experiment':'synthetic-inversion-v5', 'complete':False, 'namespace':args.namespace,
                'featureVersion':perceptual.VERSION, 'featureHash':frozen_features,
                'sourceHashes':{'legacy':legacy_hash,'board':board_hash}, 'boardRevision':REVISION,
                'modelHashes':hashes, 'libraryHashes':{name:{'manifest':digest(path/'library.json'),
                    'descriptors':digest(path/'descriptors.npz')} for name,path in
                    [('legacy',args.library),('board',args.board_library)]},
                'engines':engines, 'targetCount':len(targets), 'recipesPerEngine':args.recipes,
                'samplesPerRecipe':args.samples, 'smokeLimit':args.limit,
                'holdoutPolicy':'Reject canonical target parameters found in any full bank row or stored Soundboard constituent, ignoring external rendering seeds. Reject normalized audition PCM matching any full bank row or accepted target; standalone Soundboard-constituent PCM is not separately rendered or compared.',
                'actualEngineCoverage':{name:{'targets':sum(t['synth']==name for t in targets),
                    'recipes':sorted({t['preset'] for t in targets if t['synth']==name})} for name in engines},
                'limitedRecipePolicy':'Engines with fewer exposed generators use extra disjoint draws to retain equal target count; Footsteppr exposes only randomize_params.',
                'startsPerObjective':args.starts, 'budgetPerStart':args.budget, 'jobs':args.jobs,
                'startPolicy':'At most the configured number of distinct recipe starts per objective. Engines with fewer recipes use fewer starts; actual per-objective counts and renders are recorded for each condition.',
                'seed':args.seed, 'rejections':rejected, 'targets':targets,
                'conditions':['known_engine','unrestricted'] + (['leave_preset_out'] if args.leave_preset_out else []),
                'interpretation':'Synthetic reconstruction diagnostic, not neural inverse training or human likeness evidence. '
                'Known-engine search uses the engine label; unrestricted search uses audio only. Both selectors use the same '
                'union of equally budgeted proposals. Auditory-v1 is not directly optimized here but shares features with both scorers. '
                'Source-engine identity is secondary: alternative synths can recreate equivalent audio. '
                'Optional leave-preset-out excludes exact generator labels within legacy only, not semantic recipe families. '
                'No target parameters seed search; synthetic labels never enter human preference training.',
                'codeHashes':{name:digest(Path(__file__).with_name(name+'.py')) for name in
                              ('synthetic_benchmark','paired_search','refine','perceptual','train_perceptual','preference')}}
    args.output.mkdir(parents=True)
    for path, name in [(args.model,'model-v5.json'),(args.v4_model,'model-v4.json')]:
        shutil.copyfile(path,args.output/name)
    def save(records):
        (args.output/'results.json').write_text(json.dumps({'metadata':metadata,'summary':summarize(records),
                                                          'results':records},indent=2,allow_nan=False)+'\n')
    save([])

    def one(item):
        index, target = item
        v5, v4 = load_metrics(args.output/'model-v5.json', args.output/'model-v4.json')
        folder = f'{index+1:03d}'
        dest = args.output/folder
        dest.mkdir()
        started = time.monotonic()
        with Renderer() as legacy, BoardRenderer(args.snapshot) as board:
            if legacy.inventory['sourceHash'] != legacy_hash or board.inventory['sourceHash'] != board_hash:
                raise ValueError('DSP changed during benchmark')
            _, wave = legacy.render(target['synth'],target['params'],target['seed'])
            if audition_hash(wave) != target['auditionPcmSha256']:
                raise ValueError('Synthetic target changed on replay')
            reference = perceptual.describe(wave)
            if args.save_audio:
                sf.write(dest/'target.wav', features.prepare(wave)*.5,44100,subtype='PCM_16')
            renders = 0
            def render(row):
                nonlocal renders
                renders += 1
                return (board.render(row['params'],row['seed']) if row['backend']=='board' else
                        legacy.render(row['synth'],row['params'],row['seed']))
            def measure(row, metric, filename):
                params, audio = render(row)
                d = perceptual.describe(audio)
                pcm_hash = audition_hash(audio)
                result = {'candidate':replayed_candidate(row,params,pcm_hash),
                          'score':float(metric.distances(reference,d[None])[0]),
                          'auditoryV1':float(features.distances(reference[:features.DIM],d[None,:features.DIM])[0]),
                          'auditionPcmSha256':pcm_hash}
                if args.save_audio:
                    sf.write(dest/filename,features.prepare(audio)*.5,44100,subtype='PCM_16')
                    result['file'] = filename
                return result
            conditions = {}
            for condition in metadata['conditions']:
                indices = scope_indices(rows,target,condition)
                if not len(indices):
                    raise ValueError('No eligible candidates for '+condition)
                subset = [rows[i] for i in indices]
                subset_desc = descriptors[indices]
                before = {name:measure(subset[int(np.argmin(metric.distances(reference,subset_desc)))],metric,
                                       condition+'-'+name+'-before.wav') for name,metric in [('v5',v5),('v4',v4)]}
                start_renders = renders
                result = search_pair(subset,subset_desc,reference,v5,v4,render,legacy.specs,source_specs,
                                     starts=args.starts,budget=args.budget,
                                     seed=stable_seed(str(args.seed),index,condition))
                search_renders = renders-start_renders
                selectors = {}
                for name,metric in [('v5',v5),('v4',v4)]:
                    selected = result['choices'][name]
                    after = measure(selected,metric,condition+'-'+name+'-after.wav')
                    if abs(after['score']-selected[name+'Score']) > 1e-5:
                        raise ValueError('Selected score changed on replay')
                    selectors[name] = {'before':before[name],'after':after,
                                       'sameSourceEngine':selected['backend']=='legacy' and selected['synth']==target['synth']}
                conditions[condition] = {'eligibleRows':len(subset),'selectors':selectors,'traces':result['traces'],
                                         'evaluations':result['evaluations'],'searchRendersIncludingStarts':search_renders,
                                         'actualStartsPerObjective':{name:sum(t['objective']==name for t in result['traces'])
                                                                    for name in ('v4','v5')},
                                         'finalPoolSize':len(result['pool'])}
                if condition == 'leave_preset_out':
                    remaining = sum(row['synth']==target['synth'] for row in subset)
                    conditions[condition].update(sourceEngineRowsRemaining=remaining,
                        interpretation=('Generator-label holdout within legacy only; semantic aliases may remain.'
                                        if remaining else 'No source-engine generator remains; this condition is cross-engine approximation.'))
            record = {'target':target,'folder':folder,'conditions':conditions,'renderCalls':renders+1,
                      'seconds':time.monotonic()-started}
            (dest/'report.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
            print(f'SYNTHETIC {index+1}/{len(targets)} {target["synth"]}/{target["preset"]}',flush=True)
            return record
    records, started = [], time.monotonic()
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for future in as_completed([executor.submit(one,item) for item in enumerate(targets)]):
            records.append(future.result())
            records.sort(key=lambda r:r['folder'])
            metadata['elapsedSeconds'] = time.monotonic()-started
            save(records)
    if (feature_hash()!=frozen_features or digest(args.model)!=hashes['v5'] or digest(args.v4_model)!=hashes['v4']):
        raise ValueError('Feature code or model changed during benchmark')
    metadata['complete'] = True
    save(records)
    return {'targets':len(records),'engines':len({t['synth'] for t in targets}),
            'complete':True,'output':str(args.output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library','board-library','legacy-base','board-base','snapshot','model','v4-model','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--jobs',type=int,default=4)
    parser.add_argument('--starts',type=int,default=2)
    parser.add_argument('--budget',type=int,default=24)
    parser.add_argument('--recipes',type=int,default=2)
    parser.add_argument('--samples',type=int,default=2)
    parser.add_argument('--attempts',type=int,default=32)
    parser.add_argument('--seed',type=int,default=10529)
    parser.add_argument('--namespace',default='all-active-synth-holdout-v5-2026-10-04')
    parser.add_argument('--limit',type=int,default=0,help='Smoke run only; first N generated targets, not balanced evidence')
    parser.add_argument('--leave-preset-out',action='store_true',help='Extra legacy-only generator-label holdout condition')
    parser.add_argument('--save-audio',action='store_true',help='Save target and before/after PCM16 auditions')
    print(json.dumps(run(parser.parse_args()),indent=2))


if __name__ == '__main__':
    main()
