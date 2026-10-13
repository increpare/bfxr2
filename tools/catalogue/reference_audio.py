"""Compare opaque recordings with labelled local acoustic references.

Uses cached CLAP audio embeddings. No audio leaves this computer, and metadata
labels are never replaced. Held-out diagnostics exclude identical sample families.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re


def prepare(root, per_category=30, output_path=None):
    rows = json.loads((root / '_catalogue/site/catalogue.json').read_text(encoding='utf8'))
    pilot = json.loads((root / '_catalogue/work/acoustic-pilot-input.json').read_text(encoding='utf8'))
    held_out = {r['sha256'] for r in pilot}
    path_counts = Counter(r['path'] for r in rows)
    groups = defaultdict(lambda: defaultdict(list))
    seen = set()
    for row in rows:
        key = row.get('sample_family') or row.get('pcm_hash') or row['sha256']
        clear_interface = row.get('category') in {'USER INTERFACE', 'BEEPS'} and re.search(r'beep|ui_|menu|cursor|button|interface', row['description'], re.I)
        if (not row.get('category') or (row.get('confidence') not in {'high', 'medium'} and not clear_interface)
                or row['category'] in {'ARCHIVED', 'GAMES'} or row['sha256'] in held_out
                or row.get('classification_status') == 'source element'
                or row.get('classification_method', 'metadata') not in {'metadata', 'reviewed'}
                or path_counts[row['path']] != 1 or key in seen or not 0.05 <= (row.get('duration') or 0) <= 60):
            continue
        seen.add(key)
        groups[row['category']][(row['library'], row.get('catid'))].append(row)
    rng = random.Random(20261010)
    selected = []
    for category, buckets in sorted(groups.items()):
        lists = list(buckets.values())
        for values in lists:
            rng.shuffle(values)
        rng.shuffle(lists)
        category_rows = []
        while any(lists) and len(category_rows) < per_category:
            for values in lists:
                if values and len(category_rows) < per_category:
                    category_rows.append(values.pop())
        selected.extend(category_rows)
    path = output_path or root / '_catalogue/work/acoustic-reference-input.json'
    path.write_text(json.dumps(selected, ensure_ascii=False), encoding='utf8')
    print(json.dumps({'references': len(selected), 'categories': dict(Counter(r['category'] for r in selected)), 'path': str(path)}, indent=2))


def rank(root, input_path, output_path, references_path=None):
    import numpy as np
    model = json.loads((root / '_catalogue/work/acoustic-model.json').read_text(encoding='utf8'))
    cache = root / '_catalogue/models/huggingface/audio-embeddings' / model['revision'][:12]
    references = json.loads((references_path or root / '_catalogue/work/acoustic-reference-input.json').read_text(encoding='utf8'))
    rows = json.loads(input_path.read_text(encoding='utf8'))
    refs, features = [], []
    for ref in references:
        path = cache / (ref['sha256'] + '.npz')
        if path.exists():
            values = np.load(path)
            if values['peak'].max() <= 1e-7:
                continue
            embedding = values['features'].mean(axis=0)
            features.append(embedding / max(np.linalg.norm(embedding), 1e-12))
            refs.append(ref)
    if not features:
        raise ValueError('No reference embeddings available')
    matrix = np.stack(features)
    output = []
    for row in rows:
        path = cache / (row['sha256'] + '.npz')
        if not path.exists():
            continue
        values = np.load(path)
        if values['peak'].max() <= 1e-7:
            continue
        embedding = values['features'].mean(axis=0)
        embedding /= max(np.linalg.norm(embedding), 1e-12)
        scores = matrix @ embedding
        for i, ref in enumerate(refs):
            if ref['path'] == row['path'] or ref['sha256'] == row['sha256'] or (ref.get('sample_family') and ref['sample_family'] == row.get('sample_family')):
                scores[i] = -1
        indices = np.argsort(scores)[::-1][:7]
        neighbours = [{'id': refs[i]['id'], 'path': refs[i]['path'], 'description': refs[i]['description'],
                       'category': refs[i]['category'], 'catid': refs[i].get('catid'),
                       'cosine_similarity': float(scores[i])} for i in indices]
        votes = Counter(n['category'] for n in neighbours)
        category, count = votes.most_common(1)[0]
        top = neighbours[0]
        agreement = count / len(neighbours)
        accepted = (top['category'] == category and agreement >= 5/7 and top['cosine_similarity'] >= 0.80)
        # Very close acoustic copies still remain proposals, never verified labels.
        if top['cosine_similarity'] >= 0.98:
            category, accepted = top['category'], True
        output.append(dict(description_id=row['id'], id=row['id'], path=row['path'], sha256=row['sha256'],
                           category=category, catid=None, confidence='low', accepted=accepted,
                           method='audio-model', model={'name': 'CLAP with labelled local acoustic references', 'revision': model['revision']},
                           reason=f'Local acoustic-reference proposal: {category}; nearest similarity {top["cosine_similarity"]:.3f}, {count}/7 neighbours agree. Listening review required.',
                           alternatives=neighbours, agreement=agreement, nearest_similarity=top['cosine_similarity'],
                           expected_category=row.get('category'), audio_verified=False, training_eligible=False, review_needed=True))
    output_path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in output), encoding='utf8')
    controls = [r for r in output if r.get('expected_category')]
    accepted_controls = [r for r in controls if r['accepted']]
    print(json.dumps({'references': len(refs), 'queries': len(output), 'accepted': sum(r['accepted'] for r in output),
                      'controls': len(controls), 'correct_category': sum(r['category'] == r['expected_category'] for r in controls),
                      'accepted_controls': len(accepted_controls), 'accepted_correct': sum(r['category'] == r['expected_category'] for r in accepted_controls)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'rank'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--references', type=Path)
    parser.add_argument('--per-category', type=int, default=30)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.root, args.per_category, args.output)
    else:
        rank(args.root, args.input, args.output, args.references)
