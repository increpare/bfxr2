"""Strict human preference pairs from the archived listening sessions (read-only)."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

ARCHIVES = Path(__file__).resolve().parents[1] / 'multisynth' / 'listening_data'
# Edited copies of the reference, not synth output.
SKIP = ('cue-calibration',)


def _audio(root, entry, cache):
    key = entry['pcmSha256']
    if key not in cache:
        wave, rate = sf.read(root/entry['file'], dtype='float32', always_2d=True)
        if rate != 44100:
            raise ValueError(f'Unexpected sample rate in {root/entry["file"]}')
        cache[key] = wave[:, 0]
    return key


def load_pairs(archives=ARCHIVES):
    """-> list of dicts: reference, better, worse (waveforms), session, name.

    A pair is strict when the listener chose one candidate over another they
    actually played, or rated two candidates differently in the same session.
    Partial exports superseded by a later export of the same session are skipped.
    """
    roots = sorted(p for p in Path(archives).iterdir() if (p/'manifest.json').exists())
    names = {p.name for p in roots}
    pairs, cache = [], {}
    for root in roots:
        if any(s in root.name for s in SKIP):
            continue
        if root.name.endswith('-01') and root.name[:-1]+'2' in names:
            continue
        manifest = json.loads((root/'manifest.json').read_text())
        candidates = {c['id']: c for c in manifest['candidates']}
        for target in manifest['targets']:
            ids = ([c['id'] if isinstance(c, dict) else c for c in target['candidates']] if 'candidates' in target
                   else [target[r] for r in ('selected', 'bfxr', 'previous') if target.get(r)])
            ref = _audio(root, target['referenceAudio'], cache)
            pcm = {cid: _audio(root, candidates[cid]['audio'], cache) for cid in dict.fromkeys(ids)}
            ordered = []  # (better pcm, worse pcm)
            choice = target.get('choice')
            if choice and choice['kind'] == 'best':
                winner = choice['preferredCandidateIds'][0]
                heard = choice.get('auditionedCandidateIds', [])
                if winner in heard:
                    ordered += [(pcm[winner], pcm[cid]) for cid in heard if cid != winner]
            rated = {}
            for cid in pcm:
                value = candidates[cid].get('likeness', candidates[cid].get('rating'))
                if value is not None:
                    rated.setdefault(pcm[cid], set()).add(value)
            rated = {k: v.pop() for k, v in rated.items() if len(v) == 1}
            keys = list(rated)
            for i, a in enumerate(keys):
                for b in keys[i+1:]:
                    if rated[a] != rated[b]:
                        ordered.append((a, b) if rated[a] > rated[b] else (b, a))
            seen = set()
            for better, worse in ordered:
                if better == worse or (better, worse) in seen or (worse, better) in seen:
                    continue
                seen.add((better, worse))
                pairs.append({'reference': cache[ref], 'better': cache[better], 'worse': cache[worse],
                              'referenceId': ref, 'session': root.name,
                              'name': target['source'].get('name', '') if isinstance(target.get('source'), dict) else ''})
    return pairs
