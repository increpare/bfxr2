"""Reversible automated proposals, kept separate from source metadata/reviews."""
import json
from pathlib import Path
import warnings

REFINABLE_STATUSES = {'source element', 'context only', 'tentative proposal'}


def load_proposals(root, ucs):
    path = Path(root) / '_catalogue' / 'automated-proposals.jsonl'
    proposals = {}
    categories = {u['category'] for u in ucs.values()}
    if not path.exists():
        return proposals
    for line, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
            ident = item.get('description_id') or item.get('id')
            if not isinstance(ident, str) or not item.get('sha256') or not item.get('path'):
                raise ValueError('Missing source identity')
            catid = item.get('catid')
            if catid and catid not in ucs:
                raise ValueError('Unknown UCS leaf')
            category = ucs[catid]['category'] if catid else item.get('category')
            if category not in categories:
                raise ValueError('Unknown UCS category')
            if item.get('method') not in {'audio-model', 'exact-duplicate', 'exact-excerpt', 'signal-analysis'}:
                raise ValueError('Unknown proposal method')
            if item.get('confidence') not in {'low', 'medium', 'high'}:
                raise ValueError('Invalid confidence')
            if ident in proposals:
                raise ValueError('Repeated description identity')
            proposals[ident] = item | {'category': category}
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.warn(f'Ignored automated proposal line {line}: {exc}', RuntimeWarning)
    return proposals


def apply_proposal(item, proposals, ucs):
    """Preserve event labels, refine asset-kind groups, reject changed sources."""
    proposal = proposals.get(item['id'])
    if (item.get('category') and item.get('classification_status') not in REFINABLE_STATUSES) or not proposal:
        return
    if proposal['path'] != item['path'] or proposal['sha256'] != item['sha256']:
        return
    catid = proposal.get('catid')
    method = proposal['method']
    item.update(category=proposal['category'], catid=catid,
                subcategory=ucs[catid]['subcategory'] if catid else None,
                confidence=proposal['confidence'], reason=proposal.get('reason', ''),
                classification_method=method, review_needed=True,
                classification_status={'audio-model': 'audio proposal', 'exact-duplicate': 'duplicate proposal', 'exact-excerpt': 'excerpt proposal', 'signal-analysis': 'quality exclusion'}[method])
    if proposal.get('decision_strength') == 'tentative' and method == 'audio-model':
        item['classification_status'] = 'tentative proposal'
    item['extra'] = (item.get('extra') or {}) | {'automated_proposal': proposal,
                                                'audio_verified': False, 'training_eligible': False}


def duplicate_proposals(rows):
    """Transfer unanimous metadata labels between exact full-recording copies.

    Multi-description tracks are excluded: their labels refer to different
    unsegmented events, not necessarily the entire identical recording.
    """
    from collections import Counter, defaultdict
    path_counts = Counter(r['path'] for r in rows)
    groups = defaultdict(list)
    for row in rows:
        key = ('pcm', row['pcm_hash']) if row.get('pcm_hash') else ('bytes', row.get('sha256'))
        if key[1] and path_counts[row['path']] == 1:
            groups[key].append(row)
    output = []
    for group in groups.values():
        donors = [r for r in group if r.get('category') and r.get('classification_status') not in REFINABLE_STATUSES and r.get('classification_method', 'metadata') in {'metadata', 'reviewed'}]
        if not donors or len({r['category'] for r in donors}) != 1:
            continue
        leaves = {r.get('catid') for r in donors if r.get('catid')}
        leaf = next(iter(leaves)) if len(leaves) == 1 else None
        for row in group:
            if (row.get('category') and row.get('classification_status') not in REFINABLE_STATUSES) or row.get('reviewed'):
                continue
            output.append(dict(description_id=row['id'], path=row['path'], sha256=row['sha256'],
                               category=donors[0]['category'], catid=leaf, confidence='medium',
                               method='exact-duplicate', review_needed=True, audio_verified=False,
                               reason='Exact decoded recording matches labelled copies; their category agrees. Listening review still required.',
                               source_descriptions=[{'id': r['id'], 'path': r['path'], 'description': r['description'], 'catid': r.get('catid')} for r in donors]))
    return output


def assemble(root, audio_path=None):
    """Rebuild the overlay from current metadata and optional audio predictions."""
    from collections import Counter
    from .core import records
    root = Path(root)
    rows = records(root, use_proposals=False)
    current = {row['id']: row for row in rows}
    selected = {item['description_id']: item for item in duplicate_proposals(rows)}
    skipped = Counter()
    if audio_path:
        for raw in Path(audio_path).read_text(encoding='utf8').splitlines():
            if not raw.strip():
                continue
            candidate = json.loads(raw)
            if candidate.get('accepted') is not True:
                skipped['diagnostic_only_prediction'] += 1
                continue
            ident = candidate.get('description_id') or candidate.get('id')
            row = current.get(ident)
            if row is None or candidate.get('path') != row['path'] or candidate.get('sha256') != row['sha256']:
                skipped['stale_or_unknown_source'] += 1
                continue
            if (row.get('category') and row.get('classification_status') not in REFINABLE_STATUSES) or row.get('reviewed'):
                skipped['metadata_or_manual_decision_wins'] += 1
                continue
            if ident in selected:
                skipped['exact_copy_evidence_wins'] += 1
                continue
            selected[ident] = candidate | {'description_id': ident, 'method': candidate['method'] if candidate.get('method') in {'signal-analysis', 'exact-excerpt'} else 'audio-model',
                                           'review_needed': True, 'audio_verified': False,
                                           'training_eligible': False}
    taxonomy = {item['catid']: item for item in json.loads((root / '_catalogue' / 'ucs.json').read_text(encoding='utf8'))}
    categories = {item['category'] for item in taxonomy.values()}
    for item in selected.values():
        catid = item.get('catid')
        if catid:
            if catid not in taxonomy:
                raise ValueError(f'Invalid model CatID: {catid}')
            item['category'] = taxonomy[catid]['category']
        if item.get('category') not in categories or item.get('confidence') not in {'low', 'medium', 'high'}:
            raise ValueError('Invalid proposal category or confidence')
    output = root / '_catalogue' / 'automated-proposals.jsonl'
    temporary = output.with_suffix('.jsonl.tmp')
    temporary.write_text(''.join(json.dumps(item, ensure_ascii=False)+'\n' for _, item in sorted(selected.items())), encoding='utf8')
    temporary.replace(output)
    report = {'proposals': len(selected), 'methods': dict(Counter(item['method'] for item in selected.values())),
              'skipped': dict(skipped),
              'unclassified_after': sum(not row.get('category') and row['id'] not in selected for row in rows)}
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--audio-proposals', type=Path)
    args = parser.parse_args()
    assemble(args.root, args.audio_proposals)
