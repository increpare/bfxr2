#!/usr/bin/env python3
"""Measure a folder of tagged reference sounds and compare each tag with a Soundboard verb.

    python tools/references/measure_tagged.py <wav_root> <out_dir>

<wav_root>/<tag>/*.wav are mono 16-bit WAVs (see tools/references/README.md for the ffmpeg
conversion). Writes per-file features (kept out of git), per-tag statistics, and a Markdown
report comparing each tag with the duration class and measured catalogue of its verb.
Requires NumPy only. Reuses the preset survey's feature extractor.
"""
import json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'preset_survey'))
from analyze import extract_features, read_audio  # noqa: E402

# The collection's tags, mapped to the board's verbs. None = not a board verb; still measured.
TAG_TO_VERB = {
    'jump':'jump','double_jump':'jump','fall':'land','footstep':'step','step':'step','clothes':'step',
    'attack':'swing','sword':'swing','draw_weapon':'swing','hit':'hit','shoot':'shoot','laser':'shoot',
    'explode':'explode','collect':'coin','chips':'coin','power_up':'powerup','unlock':'unlock','motiv':'confirm',
    'bell':'confirm','select':'confirm','click':'blip','card':'blip','forbidden':'alert','carbeep':'alert',
    'magic':'cast','monster':'roar','animal':'roar','voice':'hurt','door':'door','dice':'break','slime':'splash',
    'bird':None,'chains':None,'computer':None,'die':'lose','misc':None,
}

def active_duration(pcm, rate=44100, hop=256, fraction=0.03):
    n = len(pcm) // hop
    env = np.sqrt(np.mean(pcm[:n*hop].reshape(n, hop) ** 2, axis=1)) if n else np.zeros(1)
    peak = max(float(env.max()), 1e-9)
    idx = np.flatnonzero(env >= max(peak * fraction, 0.0005))
    return 0.0 if not len(idx) else float((idx[-1] - idx[0] + 1) * hop / rate)

def trim(pcm, rate=44100):
    # Library recordings carry silence at both ends; measure the sound, not the file.
    hop = 256; n = len(pcm) // hop
    if n < 2: return pcm
    env = np.sqrt(np.mean(pcm[:n*hop].reshape(n, hop) ** 2, axis=1))
    peak = env.max(); idx = np.flatnonzero(env >= max(peak * 0.01, 0.0003))
    if not len(idx): return pcm
    return pcm[max(0, idx[0]-1)*hop:min(n, idx[-1]+2)*hop]

def main(root, out):
    root, out = Path(root), Path(out); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for wav in sorted(root.rglob('*.wav')):
        tag = wav.parent.name
        try:
            pcm, rate = read_audio(wav)
            pcm = trim(pcm, rate)
            if len(pcm) < 512: continue
            feats = extract_features(pcm, rate)
        except Exception as error:  # a broken file should not stop the survey
            print('skip', wav, error); continue
        peak = float(np.max(np.abs(pcm))) if len(pcm) else 0.0
        rows.append({'tag':tag,'verb':TAG_TO_VERB.get(tag),'file':wav.name,'seconds':round(len(pcm)/rate,3),
                     'active':round(active_duration(pcm, rate),3),'peak':round(peak,3),**{k:round(float(v),4) for k,v in feats.items()}})
    (out/'files.json').write_text(json.dumps(rows, indent=1))
    tags = {}
    for row in rows: tags.setdefault(row['tag'], []).append(row)
    def q(values, p): return float(np.percentile(values, p)) if values else float('nan')
    summary = {}
    for tag, items in sorted(tags.items()):
        act = [r['active'] for r in items]; voiced = [r['voiced_fraction'] for r in items]
        summary[tag] = {'verb':TAG_TO_VERB.get(tag),'count':len(items),
            'active_p10':round(q(act,10),3),'active_p50':round(q(act,50),3),'active_p90':round(q(act,90),3),
            'tonal_share':round(float(np.mean([v>0.5 for v in voiced])),2),
            'centroid_hz_p50':round(2**q([r['centroid_log2'] for r in items],50)),
            'flatness_db_p50':round(q([r['flatness_db'] for r in items],50),1),
            'pitch_slope_oct_p50':round(q([r['pitch_slope_octaves'] for r in items],50),2),
            'attack_rise_p50':round(q([r['attack_rise'] for r in items],50),3),
            'late_energy_p50':round(q([r['late_energy'] for r in items],50),3)}
    (out/'tags.json').write_text(json.dumps(summary, indent=1))
    lines = ['# Tagged reference measurements', '', f'{len(rows)} files, {len(tags)} tags. Active duration is the span above 3% of the peak envelope. Tonal share is the fraction of files whose spectrum is dominated by a few peaks.', '',
             '| tag | verb | n | active p10 / p50 / p90 (s) | tonal | centroid Hz | flatness dB | pitch slope (oct) | attack | late energy |', '|---|---|---|---|---|---|---|---|---|---|']
    for tag, s in summary.items():
        lines.append(f"| {tag} | {s['verb'] or '–'} | {s['count']} | {s['active_p10']} / {s['active_p50']} / {s['active_p90']} | {s['tonal_share']} | {s['centroid_hz_p50']} | {s['flatness_db_p50']} | {s['pitch_slope_oct_p50']} | {s['attack_rise_p50']} | {s['late_energy_p50']} |")
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
