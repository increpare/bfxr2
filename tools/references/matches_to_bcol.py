#!/usr/bin/env python3
"""Turn matcher outputs into a Bfxr template collection (.bcol) of reference varieties.

    python tools/references/matches_to_bcol.py <verb> <templates/Bfxr/reference_<verb>.bcol> <match_dir>... [--max-score 1.6]

Each match directory holds report.json and match*.bfxr from `python -m match.match`. Matches at
or under --max-score become one variety each, named after the directory. A variety gets two
exemplars: the matched parameters and a copy nudged by a few percent of each control's range, so
Bfxr generates a small family around the reference rather than one fixed sound. Run
`node insert_templates.js` afterwards to regenerate js/synths/templates.js.
"""
import json, sys, random
from pathlib import Path

CONTINUOUS = {  # name: (min, max) for the controls worth nudging; discrete controls stay fixed
    'sustainTime':(0,1),'decayTime':(0.03,1),'sustainPunch':(0,1),'frequency_start':(0,1),'frequency_slide':(-0.5,0.5),
    'frequency_acceleration':(-1,1),'vibratoDepth':(0,1),'vibratoSpeed':(0,1),'pitch_jump_amount':(-1,1),'pitch_jump_onset_percent':(0,1),
    'squareDuty':(0,0.99),'dutySweep':(-1,1),'lpFilterCutoff':(0.01,1),'lpFilterCutoffSweep':(-1,1),'lpFilterResonance':(0,1),
    'hpFilterCutoff':(0,1),'attackTime':(0,1),'repeatSpeed':(0,1),'flangerOffset':(-1,1),'overtones':(0,1),'overtoneFalloff':(0,1)}

def nudge(params, amount, rng):
    out = dict(params)
    for name, (lo, hi) in CONTINUOUS.items():
        if name in out and isinstance(out[name], (int, float)):
            delta = (hi - lo) * amount * (rng.random() * 2 - 1)
            out[name] = min(hi, max(lo, out[name] + delta))
            if out[name] == 0 and params[name] == 0: out[name] = 0
    return out

def main(argv):
    max_score = 1.6
    if '--max-score' in argv:
        i = argv.index('--max-score'); max_score = float(argv[i+1]); argv = argv[:i] + argv[i+2:]
    verb, target, dirs = argv[0], Path(argv[1]), [Path(d) for d in argv[2:]]
    rng = random.Random(20261003)
    files, used = [], []
    for d in dirs:
        report = json.loads((d/'report.json').read_text())
        best = min(report['results'], key=lambda r: r['score'])
        if best['score'] > max_score:
            print(f'skip {d.name}: score {best["score"]:.2f}'); continue
        params = json.loads((d/best['file']).read_text())['params']
        params['masterVolume'] = 0.5
        slug = ''.join(c for c in d.name.lower() if c.isalnum())
        for suffix, p in (('a', params), ('b', nudge(params, 0.05, rng))):
            text = json.dumps(p)
            files.append([f'{slug}_{suffix}', text, text])
        used.append((d.name, best['score'], best['wave_type_name']))
    if not files:
        print('nothing under the score threshold'); return 1
    collection = {'Bfxr': {'files': files, 'selected_file_index': 0, 'create_new_sound': True, 'play_on_change': True, 'locked_params': {}}, 'active_tab_name': 'Bfxr'}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(collection, indent=1) + '\n')
    print(f'{target}: {len(used)} varieties for {verb}:', ', '.join(f'{n} ({s:.2f} {w})' for n, s, w in used))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
