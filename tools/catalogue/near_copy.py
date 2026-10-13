"""Verify candidate acoustic matches against whole decoded waveforms."""
import argparse
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor


def verify(root, input_path=None, output_path=None):
    import numpy as np
    from scipy.signal import correlate, correlation_lags
    from .core import native_path, CREATE_NO_WINDOW, records
    work = root / '_catalogue/work'
    candidates = [json.loads(line) for line in (input_path or work / 'reference-remaining.jsonl').read_text(encoding='utf8').splitlines()]
    rows = records(root, use_proposals=False)
    by_path = {row['path']: row for row in rows}
    pairs = []
    for item in candidates:
        row = by_path.get(item['path'])
        if not row or (row.get('category') and row['classification_status'] != 'source element'):
            continue
        for donor in item['alternatives']:
            reference = by_path.get(donor['path'])
            if not reference or donor['cosine_similarity'] < .8:
                continue
            durations = [row.get('duration') or 0, reference.get('duration') or 0]
            if min(durations) < .2 or max(durations) > 60 or min(durations) / max(durations) < .95:
                continue
            pairs.append((item, donor))
    cache = {}
    def decode(path):
        if path not in cache:
            result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(native_path(root / path)),
                                     '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'],
                                    capture_output=True, check=True, timeout=60, creationflags=CREATE_NO_WINDOW)
            cache[path] = np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)
        return cache[path]
    paths = sorted({x['path'] for pair in pairs for x in pair})
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(decode, paths))
    results = []
    for item, donor in pairs:
        a, b = decode(item['path']), decode(donor['path'])
        if min(len(a), len(b)) / max(len(a), len(b)) < .95 or max(len(a), len(b)) > 60*8000:
            continue
        a, b = a - a.mean(), b - b.mean()
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm <= 1e-12:
            continue
        values = np.abs(correlate(a, b, mode='full', method='fft')) / norm
        lags = correlation_lags(len(a), len(b), mode='full')
        values[np.abs(lags) > 800] = 0  # No more than 100ms shift.
        at = int(values.argmax())
        score = float(values[at])
        if score < .995:
            continue
        results.append(item | dict(accepted=True, category=donor['category'], catid=donor['catid'],
            confidence='medium', waveform_correlation=score, waveform_lag_seconds=float(lags[at])/8000,
            reason=f'Whole decoded waveform closely matches labelled recording {donor["description"]!r} (correlation {score:.4f}, duration within 5%). Category remains provisional.',
            model={'name': 'CLAP candidate search followed by whole-waveform correlation', 'source': donor}))
    # Reject conflicting source categories even when both references correlate.
    grouped = {}
    for item in results:
        grouped.setdefault(item['id'], []).append(item)
    results = [max(group, key=lambda x: x['waveform_correlation']) for group in grouped.values()
               if len({x['category'] for x in group}) == 1]
    (output_path or work / 'verified-near-copy-proposals.jsonl').write_text(''.join(json.dumps(item, ensure_ascii=False)+'\n' for item in results), encoding='utf8')
    print(json.dumps({'candidate_pairs': len(pairs), 'waveform_verified': len(results),
                      'examples': [{'path': r['path'], 'catid': r['catid'], 'correlation': r['waveform_correlation']} for r in results]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    verify(args.root, args.input, args.output)
