"""Attach hash-checked waveform measurements without inferring sound sources."""
import json
from pathlib import Path
import warnings

FACETS = {'brief', 'tonal_dominant', 'broadband_noisy', 'dominant_frequency_moves'}


def load_traits(root):
    path = Path(root) / '_catalogue' / 'acoustic-traits.jsonl'
    output = {}
    if not path.exists():
        return output
    for line, raw in enumerate(path.read_text(encoding='utf8').splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
            if not item.get('path') or not item.get('sha256') or item.get('error'):
                continue
            facets = item.get('facets', [])
            if not isinstance(facets, list) or any(value not in FACETS for value in facets):
                raise ValueError('Unknown measured trait')
            output[(item['path'], item['sha256'])] = item
        except (ValueError, TypeError, AttributeError) as exc:
            warnings.warn(f'Ignored acoustic trait line {line}: {exc}', RuntimeWarning)
    return output


def apply_traits(row, measurements):
    item = measurements.get((row['path'], row['sha256']))
    row['acoustic_traits'] = list(item.get('facets', [])) if item else []
    if item:
        row['extra'] = (row.get('extra') or {}) | {'waveform_measurements': item}
