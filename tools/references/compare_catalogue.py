#!/usr/bin/env python3
"""Compare tagged reference measurements with the Soundboard catalogue, verb by verb.

    python tools/references/compare_catalogue.py <tags.json> <files.json> <catalogue_inventory.json> <out.md>

tags.json / files.json come from measure_tagged.py; catalogue_inventory.json from
`node tools/render/verb_inventory.js --json`. Produces a Markdown table per verb: reference
duration spread against the catalogue's measured spread and the vocabulary's class, plus the
tonal share and brightness of the references, so presets can be steered by numbers.
"""
import json, re, sys
from pathlib import Path
import numpy as np

tags, files, inventory, out = (json.loads(Path(p).read_text()) if i < 3 else Path(p) for i, p in enumerate(sys.argv[1:5]))
verbs = {v['id']: v for v in inventory['verbs']} if 'verbs' in inventory else {}
report = inventory.get('report', inventory)
by_verb = {}
for row in files:
    if row.get('verb'): by_verb.setdefault(row['verb'], []).append(row)
lines = ['# References versus catalogue, by verb', '',
         'Reference numbers come from the tagged collection (library and game sounds, measured after trimming silence). Catalogue numbers are the measured active durations of every Soundboard ingredient over four seeded takes. Class is the vocabulary bound used by the tests.', '',
         '| verb | refs | ref active p10 / p50 / p90 | ref tonal | ref centroid Hz | catalogue min / median / max | class | reading |', '|---|---|---|---|---|---|---|---|']
findings = []
for verb_id, entries in report['verbs'].items():
    refs = by_verb.get(verb_id, [])
    cls = verbs.get(verb_id, {}).get('duration', ['?', '?'])
    cat = [e['range'] for e in entries]
    cmin, cmax = min(r[0] for r in cat), max(r[1] for r in cat)
    cmed = float(np.median([np.mean(r) for r in cat]))
    if refs:
        act = np.array([r['active'] for r in refs]); p10, p50, p90 = np.percentile(act, [10, 50, 90])
        tonal = np.mean([r['voiced_fraction'] > 0.5 for r in refs]); cent = 2 ** np.median([r['centroid_log2'] for r in refs])
        reading = []
        if p50 > cmed * 1.6: reading.append('references run longer than the catalogue')
        if p50 < cmed / 1.6: reading.append('references run shorter than the catalogue')
        if p90 > cls[1] * 1.1: reading.append(f'{int(np.mean(act > cls[1]) * 100)}% of references exceed the class')
        if p10 < cls[0] * 0.9: reading.append(f'{int(np.mean(act < cls[0]) * 100)}% of references are shorter than the class')
        text = '; '.join(reading) or 'in agreement'
        lines.append(f"| {verb_id} | {len(refs)} | {p10:.2f} / {p50:.2f} / {p90:.2f} | {tonal:.2f} | {cent:.0f} | {cmin:.2f} / {cmed:.2f} / {cmax:.2f} | {cls[0]}–{cls[1]} | {text} |")
        if reading: findings.append((verb_id, text))
    else:
        lines.append(f"| {verb_id} | 0 | – | – | – | {cmin:.2f} / {cmed:.2f} / {cmax:.2f} | {cls[0]}–{cls[1]} | no references tagged |")
lines += ['', '## Findings', ''] + [f'- **{v}**: {t}.' for v, t in findings]
out.write_text('\n'.join(lines) + '\n'); print('\n'.join(lines))
