"""Exact blocked CLAP coverage measurements and reusable hole targets.

Midpoint coverage uses a quarter of endpoint cosine distance; the report also
keeps the stricter quarter Euclidean endpoint chord as an explicit diagnostic.

    uv run python -m sfxmatch.covereval holes --data sfxmatch/runs/mix-1m --limit-shards 91 --out sfxmatch/runs/cover-holes.npz
    uv run python -m sfxmatch.covereval evaluate --data sfxmatch/runs/mix-1m --targets sfxmatch/runs/cover-holes.npz --new sfxmatch/runs/mix-cover --out sfxmatch/runs/cover-report.json
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from . import tags


def normalize(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    norm = np.linalg.norm(vectors, axis=1, keepdims=True)
    valid = np.isfinite(vectors).all(1) & (norm[:, 0] > 1e-8)
    result = np.zeros_like(vectors); result[valid] = vectors[valid]/norm[valid]
    return result, valid


def load(data, limit_shards=None, shard_names=None):
    """Never splice truncated encodings onto recipe rows, or silently shift row IDs."""
    data = Path(data); cache = tags.store(data)
    vectors, labels, pairs, seconds, files, skipped = [], [], [], [], [], Counter()
    shards = sorted(s for s in data.glob('mix-*.npz') if not s.name.endswith('.tmp.npz'))
    if shard_names is not None:
        shards = [data/name for name in shard_names]
    elif limit_shards is not None:
        shards = shards[:limit_shards]
    for shard in shards:
        index = shard.stem.split('-')[1]; encoded = cache/f'clap-{index}.npy'; recipes = shard.with_suffix('.jsonl')
        if not encoded.exists() or not shard.exists() or not recipes.exists():
            skipped['missing_encoding'] += 1; continue
        with np.load(shard) as z:
            count = len(z['synth']); shape = np.load(encoded, mmap_mode='r').shape
            if shape[0] != count or len(recipes.read_text().splitlines()) != count:
                skipped['unaligned'] += 1; continue
            audioset = cache/f'audioset-{index}.npy'
            probability = np.load(audioset, mmap_mode='r') if audioset.exists() else None
            if probability is not None and len(probability) != count:
                skipped['unaligned'] += 1; continue
            vectors.append(np.load(encoded).astype(np.float32)); pairs.append(z['synth'].copy())
            seconds.append(2.**z['duration']); files.append(shard)
            labels.append(probability.argmax(1) if probability is not None else None)
    if not vectors:
        raise ValueError(f'No fully aligned encoded shards for {data}')
    vector, valid = normalize(np.concatenate(vectors))
    if all(label is not None for label in labels):
        label = np.concatenate(labels); label_kind = 'audioset'
    else:
        # Fixed CLAP vocabulary is sufficient when AudioSet has not been encoded.
        text = tags.text_vectors(); similarity = vector @ text.T
        spread = np.maximum(similarity[valid].std(0), 1e-8)
        label = ((similarity-similarity[valid].mean(0))/spread).argmax(1); label_kind = 'clap'
    return {'vectors': vector, 'valid': valid, 'labels': label, 'labelKind': label_kind,
            'pairs': np.concatenate(pairs), 'seconds': np.concatenate(seconds), 'files': files,
            'starts': np.cumsum([0]+[len(v) for v in vectors]), 'shards': [s.name for s in files],
            'skipped': dict(skipped), 'data': data}


def patch(bank, row, cache):
    shard = int(np.searchsorted(bank['starts'], row, side='right'))-1
    if shard not in cache:
        cache[shard] = bank['files'][shard].with_suffix('.jsonl').read_text().splitlines()
    return json.loads(cache[shard][row-bank['starts'][shard]])


def nearest(query, reference, exclude=None, query_block=256, reference_block=16384, device='auto'):
    """Exact cosine NN with bounded QxR blocks; exclusion applies to every query."""
    query, alive = normalize(query); reference, usable = normalize(reference)
    if exclude is not None:
        usable[np.asarray(exclude, dtype=int)] = False
    if query_block < 1 or reference_block < 1:
        raise ValueError('Block sizes must be positive')
    use_torch = False
    if device != 'cpu':
        import torch
        use_torch = torch.backends.mps.is_available()
        if device == 'mps' and not use_torch:
            raise ValueError('MPS unavailable')
    best = np.full(len(query), -np.inf, np.float32); ids = np.full(len(query), -1, np.int64)
    for q0 in range(0, len(query), query_block):
        q = query[q0:q0+query_block]
        if use_torch:
            qt = torch.from_numpy(q).to('mps')
        for r0 in range(0, len(reference), reference_block):
            r = reference[r0:r0+reference_block]; valid = usable[r0:r0+len(r)]
            if not valid.any():
                continue
            if use_torch:
                score = (qt @ torch.from_numpy(r).to('mps').T).cpu().numpy()
            else:
                score = q @ r.T
            score[:, ~valid] = -np.inf
            local = score.argmax(1); value = score[np.arange(len(q)), local]
            moved = value > best[q0:q0+len(q)]
            best[q0:q0+len(q)][moved] = value[moved]; ids[q0:q0+len(q)][moved] = r0+local[moved]
    ids[~alive] = -1; best[~alive] = -np.inf
    return np.maximum(0, 1-best), ids


def chords(vectors, labels, count, rng, exclude=(), structure=None):
    vectors, valid = normalize(vectors); valid[np.asarray(exclude, dtype=int)] = False
    if structure is None:
        groups = [np.flatnonzero(valid & (labels == label)) for label in np.unique(labels)]
    else:
        keys = [(int(label), *tuple(pair)) for label, pair in zip(labels, structure)]
        buckets = {}
        for row in np.flatnonzero(valid):
            buckets.setdefault(keys[row], []).append(row)
        groups = [np.asarray(rows) for rows in buckets.values()]
    groups = [group for group in groups if len(group) > 1]
    pairs, midpoint, seen = [], [], set()
    if not groups:
        return np.empty((0, 2), np.int64), np.empty((0, vectors.shape[1]), np.float32)
    for _ in range(max(100, count*40)):
        group = groups[int(rng.integers(len(groups)))]; a, b = rng.choice(group, 2, replace=False)
        endpoints = tuple(sorted((int(a), int(b))))
        if endpoints in seen:
            continue
        cosine = float(vectors[a] @ vectors[b])
        if .5 < cosine < .999999:
            target = vectors[a]+vectors[b]; target /= np.linalg.norm(target)
            pairs.append((int(a), int(b))); midpoint.append(target); seen.add(endpoints)
            if len(pairs) == count:
                break
    return np.asarray(pairs, dtype=np.int64).reshape(-1, 2), np.asarray(midpoint, dtype=np.float32).reshape(-1, vectors.shape[1])


def audio_recipe_key(recipe):
    return json.dumps({'sources': recipe.get('sources', []), 'balance': recipe.get('balance', .5)},
                      sort_keys=True, separators=(',', ':'))


def unique_counts(targets, pairs, recipes=None):
    out = {'uniqueTargets': len(np.unique(targets, axis=0)),
           'uniqueEndpointPairs': len(np.unique(np.sort(pairs, axis=1), axis=0))}
    if recipes is not None:
        keys = []
        for index, recipe in enumerate(recipes):
            if 'left' in recipe and 'right' in recipe:
                keys.append(tuple(sorted(audio_recipe_key(recipe[side]) for side in ('left', 'right'))))
            else:
                keys.append(tuple(sorted(int(row) for row in pairs[index])))
        out['uniqueRecipes'] = len(set(keys))
    return out


def holes(data, output, queries=3000, candidates=6000, seed=1, limit_shards=None, device='auto'):
    from .mixcover import interpolate
    bank = load(data, limit_shards); rng = np.random.default_rng(seed)
    valid = bank['valid'] & (bank['seconds'] >= .05) & (bank['seconds'] <= 4)
    held = rng.choice(np.flatnonzero(valid), min(queries, valid.sum()), replace=False)
    # The independent test chords remain fixed even when the target bank is filtered.
    excluded = np.union1d(held, np.flatnonzero(~valid))
    test_pairs, test_targets = chords(bank['vectors'], bank['labels'], queries, rng, excluded)
    single_excluded = np.union1d(excluded, np.flatnonzero(bank['pairs'][:, 1] >= 0))
    single_pairs, single_targets = chords(bank['vectors'], bank['labels'], max(1, candidates//3), rng, single_excluded, bank['pairs'])
    pair_excluded = np.union1d(excluded, np.flatnonzero(bank['pairs'][:, 1] < 0))
    pair_pairs, pair_targets = chords(bank['vectors'], bank['labels'], candidates-len(single_pairs), rng, pair_excluded)
    pairs = np.concatenate((single_pairs, pair_pairs)); target = np.concatenate((single_targets, pair_targets))
    gap, _ = nearest(target, bank['vectors'], held, device=device)
    specs = json.loads((Path(data)/'meta.json').read_text())['specs']
    cache, recipes, selected, reasons = {}, [], [], Counter()
    for index, ((a, b), distance) in enumerate(zip(pairs, gap)):
        if distance <= .11:
            reasons['gap_below_threshold'] += 1; continue
        left, right = patch(bank, a, cache), patch(bank, b, cache)
        if len(left['sources']) != len(right['sources']):
            reasons['different_source_count'] += 1; continue
        if interpolate(left, right, specs, .5, rng) is None:
            reasons['disjoint_pairs'] += 1; continue
        recipes.append(json.dumps({'id': len(recipes), 'left': left, 'right': right,
                                   'label': int(bank['labels'][a]), 'endpoints': [int(a), int(b)]}))
        selected.append(index)
    if not recipes:
        raise ValueError(f'No compatible holes; rejection counts {dict(reasons)}')
    selected = np.asarray(selected, int)
    meta = {'seed': seed, 'data': str(Path(data).resolve()), 'shards': bank['shards'], 'referenceRows': len(bank['vectors']),
            'queryRows': len(held), 'labelKind': bank['labelKind'], 'cosineDistanceBelow': .5, 'gapAbove': .11,
            'rejections': dict(reasons), 'loadSkipped': bank['skipped']}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output, meta=json.dumps(meta), heldout=held, queries=bank['vectors'][held],
             test_pairs=test_pairs, test_targets=test_targets, pairs=pairs[selected], targets=target[selected],
             gaps=gap[selected], recipes=np.asarray(recipes))
    report = {'targets': len(recipes), **unique_counts(target[selected], pairs[selected], [json.loads(r) for r in recipes]),
              'uniqueMidpoints': len(np.unique(test_targets, axis=0)), 'singleTargets': sum(len(json.loads(r)['left']['sources']) == 1 for r in recipes), **meta}
    print(json.dumps(report), flush=True); return report


def summary(gap, radius=None):
    finite = gap[np.isfinite(gap)]
    out = {'count': len(gap), 'meanGap': float(finite.mean()) if len(finite) else None,
           'medianGap': float(np.median(finite)) if len(finite) else None,
           'p90Gap': float(np.quantile(finite, .9)) if len(finite) else None}
    if radius is not None:
        out.update(covered=int((gap <= radius).sum()), coverageRate=float((gap <= radius).mean()) if len(gap) else None)
    return out


def evaluate(data, targets, new, output, device='auto'):
    with np.load(targets) as z:
        meta = json.loads(str(z['meta'])); held = z['heldout'].copy(); query = z['queries'].copy()
        midpoint = z['test_targets'].copy(); pairs = z['test_pairs'].copy()
        hole_targets = z['targets'].copy(); recipes = [json.loads(v) for v in z['recipes']]
        endpoint_pairs = z['pairs'].copy()
    if str(Path(data).resolve()) != meta['data']:
        raise ValueError('Targets belong to another reference dataset')
    bank = load(data, shard_names=meta['shards']); fresh = load(new)
    if bank['shards'] != meta['shards'] or len(bank['vectors']) != meta['referenceRows']:
        raise ValueError('Reference snapshot no longer fully aligned')
    usable = np.flatnonzero(fresh['valid'] & (fresh['seconds'] >= .05) & (fresh['seconds'] <= 4))
    added = fresh['vectors'][usable]
    before, _ = nearest(query, bank['vectors'], held, device=device)
    added_query, _ = nearest(query, added, device=device)
    after = np.minimum(before, added_query)
    chord_cosine = np.sum(bank['vectors'][pairs[:, 0]]*bank['vectors'][pairs[:, 1]], axis=1)
    radius = (1-chord_cosine)/4
    euclidean_radius = (1-chord_cosine)/16
    mid_before, _ = nearest(midpoint, bank['vectors'], held, device=device)
    mid_new, _ = nearest(midpoint, added, device=device)
    novelty, _ = nearest(added, bank['vectors'], device=device)
    target_before, _ = nearest(hole_targets, bank['vectors'], held, device=device)
    target_added, _ = nearest(hole_targets, added, device=device)
    recipe_cache = {}; intended = []; audio_keys = set(); modes = []; strategy_keys = {}
    id_map = {int(r['id']): index for index, r in enumerate(recipes)}
    for row in usable:
        recipe = patch(fresh, row, recipe_cache); key = audio_recipe_key(recipe); audio_keys.add(key)
        mode = str(recipe.get('mode') or 'unknown'); modes.append(mode)
        strategy_keys.setdefault(mode, set()).add(key)
        hole = recipe.get('hole')
        if hole is None or int(hole['id']) not in id_map:
            continue
        index = id_map[int(hole['id'])]
        intended.append(float(max(0, 1-fresh['vectors'][row] @ hole_targets[index])))
    mode_labels = np.asarray(modes, dtype=str)
    novelty_by_strategy = {}
    standard_modes = ('both-uniform', 'generator-uniform', 'hole', 'unknown')
    for mode in dict.fromkeys((*standard_modes, *modes)):
        gaps = novelty[mode_labels == mode]; rows = len(gaps)
        unique = len(strategy_keys.get(mode, ()))
        novelty_by_strategy[mode] = {**summary(gaps), 'rows': rows, 'abovePoint1': int((gaps > .1).sum()),
                                    'rateAbovePoint1': float((gaps > .1).mean()) if rows else 0.,
                                    'uniqueAudioRecipes': unique, 'exactDuplicateAudioRecipes': rows-unique}
    merged = np.concatenate((bank['vectors'], fresh['vectors']))
    active = np.concatenate((bank['valid'] & (bank['seconds'] >= .05) & (bank['seconds'] <= 4),
                             fresh['valid'] & (fresh['seconds'] >= .05) & (fresh['seconds'] <= 4)))
    active[held] = False
    picks = min(100, int(active.sum()))
    chosen, gaps, share = tags.spread(merged, picks, active) if picks else ([], [], [])
    spread = [{'dataset': 'new' if row >= len(bank['vectors']) else 'reference',
               'row': int(row-len(bank['vectors']) if row >= len(bank['vectors']) else row),
               'gap': float(gap), 'share': float(weight)} for row, gap, weight in zip(chosen, gaps, share)]
    statsfile = Path(new)/'report.json'
    rejection = json.loads(statsfile.read_text()).get('statistics', {}) if statsfile.exists() else {}
    far = int((np.minimum(target_before, target_added) > .11).sum())
    rates = {}
    for key, value in rejection.items():
        if not key.endswith('/attempt'):
            continue
        prefix = key[:-len('/attempt')]
        accepted_key = prefix + ('/accepted' if prefix.endswith('/row') else '/source_accepted')
        accepted = rejection.get(accepted_key, 0)
        rates[prefix] = {'attempts': value, 'accepted': accepted,
                         'rejected': value-accepted, 'rejectionRate': 1-accepted/value if value else None}
    report = {'referenceRows': len(bank['vectors']), 'encodedNewRows': len(fresh['vectors']),
              'usableNewRows': len(usable), 'failedEncodingRows': int((~fresh['valid']).sum()),
              'heldout': {'count': len(query), 'before': summary(before), 'after': summary(after)},
              'midpoints': {'count': len(midpoint), **unique_counts(midpoint, pairs), 'radius': 'quarter endpoint cosine distance=(1-cos endpoints)/4',
                            'before': summary(mid_before, radius), 'after': summary(np.minimum(mid_before, mid_new), radius),
                            'quarterEuclidean': {'radius': 'cosine radius=(1-cos endpoints)/16, quarter Euclidean endpoint chord',
                                                 'before': summary(mid_before, euclidean_radius),
                                                 'after': summary(np.minimum(mid_before, mid_new), euclidean_radius)}},
              'novelty': {**summary(novelty), 'abovePoint1': int((novelty > .1).sum()),
                          'rateAbovePoint1': float((novelty > .1).mean()) if len(novelty) else None},
              'noveltyByStrategy': novelty_by_strategy,
              'holes': {'count': len(hole_targets), **unique_counts(hole_targets, endpoint_pairs, recipes), 'farMisses': far, 'farMissRate': far/len(hole_targets),
                        'targetedRows': len(intended), 'targetedFarMisses': int((np.asarray(intended) > .11).sum()),
                        'targetedFarMissRate': float((np.asarray(intended) > .11).mean()) if intended else None},
              'audioRecipes': {'count': len(usable), 'unique': len(audio_keys), 'exactDuplicates': len(usable)-len(audio_keys)},
              'loadSkipped': fresh['skipped'], 'rejections': rejection, 'rejectionRates': rates, 'spread100': spread,
              'newSpreadPicks': sum(item['dataset'] == 'new' for item in spread)}
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2)); print(json.dumps(report), flush=True)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    h = sub.add_parser('holes'); h.add_argument('--data', required=True); h.add_argument('--out', required=True)
    h.add_argument('--queries', type=int, default=3000); h.add_argument('--candidates', type=int, default=6000)
    h.add_argument('--seed', type=int, default=1); h.add_argument('--limit-shards', type=int)
    h.add_argument('--device', choices=['auto', 'cpu', 'mps'], default='auto')
    e = sub.add_parser('evaluate'); e.add_argument('--data', required=True); e.add_argument('--targets', required=True)
    e.add_argument('--new', required=True); e.add_argument('--out', required=True)
    e.add_argument('--device', choices=['auto', 'cpu', 'mps'], default='auto')
    a = p.parse_args()
    if a.command == 'holes':
        holes(a.data, a.out, a.queries, a.candidates, a.seed, a.limit_shards, a.device)
    else:
        evaluate(a.data, a.targets, a.new, a.out, a.device)


if __name__ == '__main__':
    main()
