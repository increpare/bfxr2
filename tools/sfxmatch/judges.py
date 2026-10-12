"""Which automatic judge agrees with the ratings we already have? No listening needed.

    uv run --with transformers --with torchvision python -m sfxmatch.judges

Every rated clip in ratings/ is paired with its reference audio (kept beside
each listening page). Each judge scores how alike candidate and reference are.
A judge is measured the way it would be used: within one target, when the
listener rated two candidates differently, does the judge prefer the same one?
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from . import benchmark
from .objective import Objective

HERE = Path(__file__).resolve().parent


def rated_clips():
    """-> [{'page','target','system','rating','reference','candidate','domain'}] with audio as arrays."""
    clips, cache = [], {}

    def audio(path):
        if path not in cache:
            cache[path] = sf.read(path, dtype='float32', always_2d=True)[0][:, 0]
        return cache[path]

    for file in sorted((HERE/'ratings').glob('*.json')):
        data = json.loads(file.read_text())
        page = HERE/'runs/pages'/data['page']
        text = (page/'index.html').read_text()
        listed = json.loads(text[text.index('const DATA=')+11:text.index(", KEY='sfxmatch-'")])
        files = {(t['id'], c['system']): c['file'] for t in listed['targets'] for c in t['candidates']}
        for row in data['ratings']:
            target = row['target']
            domain = 'recording' if target.startswith('ext') else 'mix' if target.startswith('mix') else 'native'
            clips.append({'page': data['page'], 'target': target, 'system': row['system'], 'rating': row['rating'], 'domain': domain,
                          'reference': audio(page/'audio'/f'{target}-ref.wav'),
                          'candidate': audio(page/'audio'/files[(target, row['system'])])})
    return clips


def clap_likeness(clips):
    import torch
    import torchaudio
    from .tags import RATE, clap, vector
    model, processor = clap()

    def embed(waves):
        ready = [torchaudio.functional.resample(torch.from_numpy(w/max(float(np.abs(w).max()), 1e-9)), 44100, RATE).numpy()[:RATE*10]
                 for w in waves]
        with torch.no_grad():
            parts = [vector(model.get_audio_features(**processor(audio=ready[at:at+32], sampling_rate=RATE, return_tensors='pt')))
                     for at in range(0, len(ready), 32)]
        return torch.nn.functional.normalize(torch.cat(parts), dim=-1).numpy()

    a, b = embed([c['reference'] for c in clips]), embed([c['candidate'] for c in clips])
    return (a*b).sum(1)


def audioset_likeness(clips):
    """Cosine between the two sounds' AudioSet label profiles (log-odds)."""
    import torch
    import torchaudio
    from .tags import efficientat
    model = efficientat()[0]
    from models.preprocess import AugmentMelSTFT       # importable once efficientat() has run
    mel = AugmentMelSTFT(n_mels=128, sr=32000, win_length=800, hopsize=320).eval()

    def profile(waves):
        out = []
        with torch.no_grad():
            for w in waves:
                x = torchaudio.functional.resample(torch.from_numpy(w/max(float(np.abs(w).max()), 1e-9)), 44100, 32000)[:320000]
                x = torch.nn.functional.pad(x, (0, 320000-len(x)))[None]
                out.append(model(mel(x).unsqueeze(0))[0].float().flatten().numpy())
        z = np.stack(out)
        z = z-z.mean(1, keepdims=True)
        return z/np.linalg.norm(z, axis=1, keepdims=True)

    return (profile([c['reference'] for c in clips])*profile([c['candidate'] for c in clips])).sum(1)


def objective_parts(clips):
    gesture, spectrum, cache = [], [], {}
    for c in clips:
        key = (c['page'], c['target'])
        if key not in cache:
            cache[key] = Objective(c['reference'])
        parts = cache[key].components(c['candidate'])
        gesture.append(-parts['gesture']); spectrum.append(-parts['spectrum'])
    return np.asarray(gesture), np.asarray(spectrum)


def agreement(clips, score, domain=None):
    """Share of strictly ordered pairs (same page and target) the judge orders the same way; and how many pairs."""
    groups = {}
    for i, c in enumerate(clips):
        if domain in (None, c['domain']):
            groups.setdefault((c['page'], c['target']), []).append(i)
    right = total = 0
    for members in groups.values():
        for n, i in enumerate(members):
            for j in members[n+1:]:
                if clips[i]['rating'] != clips[j]['rating']:
                    total += 1
                    right += (score[i] > score[j]) == (clips[i]['rating'] > clips[j]['rating'])
    return (right/total if total else float('nan')), total


def standard(x):
    return (x-x.mean())/x.std()


def robust(x, low, high):
    return np.clip(x, low, high)


class Predictor:
    """Rating expected for a (reference, candidate) pair, from the three judges.

    Not a trained metric: each judge is clipped and standardised with constants
    taken from the rated clips, the three are added, and the sum is mapped to a
    rating by the average rating of rated recording clips with a similar sum.
    """

    NAMES = ('objective (gesture + spectrum)', 'CLAP likeness', 'AudioSet profile likeness')

    def __init__(self, table, rating, keep):
        self.stats = []
        for name in self.NAMES:
            low, high = np.percentile(table[name], [2, 98])
            clipped = np.clip(table[name], low, high)
            self.stats.append((low, high, clipped.mean(), clipped.std()))
        total = self.combine(*[table[name] for name in self.NAMES])[keep]
        order = np.argsort(total)
        bins = np.array_split(order, 10)
        self.x = np.array([total[b].mean() for b in bins])
        self.y = np.maximum.accumulate(np.array([rating[keep][b].mean() for b in bins]))    # keep it monotone

    def combine(self, objective, clap, audioset):
        parts = [(np.clip(v, low, high)-mean)/std for v, (low, high, mean, std) in zip((objective, clap, audioset), self.stats)]
        return parts[0]+parts[1]+parts[2]

    def rating(self, objective, clap, audioset):
        return np.interp(self.combine(objective, clap, audioset), self.x, self.y)


def profile(logits):
    z = logits-logits.mean(-1, keepdims=True)
    return z/np.linalg.norm(z, axis=-1, keepdims=True)


def predict(data, shortlist=300, jobs=None):
    """For every benchmark recording: the library sound the three judges like best, and the rating they expect for it."""
    import torch
    import torchaudio
    from .objective import Score
    from .render import FastRenderer, RenderPool
    from .tags import RATE, Sounds, clap, efficientat, scores, vector
    saved = np.load(HERE/'runs/judges.npz')
    clips = rated_clips()
    recording = np.array([c['domain'] == 'recording' for c in clips])
    everything = np.ones(len(clips), bool)
    narrow = Predictor(saved, saved['rating'], recording)       # calibrated on recordings only: cannot say more than they ever got
    wide = Predictor(saved, saved['rating'], everything)        # calibrated on all clips: assumes a score means the same everywhere
    columns = [saved[k] for k in Predictor.NAMES]
    total = wide.combine(*columns)
    print('combined judge score by what the clip was rated (all clips): ' +
          ', '.join(f'{r}: {total[saved["rating"] == r].mean():+.2f}' for r in (1, 2, 3, 4, 5)))
    print(f'recording clips: mean score {total[recording].mean():+.2f}, best 5% above {np.percentile(total[recording], 95):+.2f}; '
          f'the wide map over-predicts their ratings by {(wide.rating(*columns)[recording]-saved["rating"][recording]).mean():+.2f} on average')
    library_clap = scores('clap', data)
    library_set = scores('audioset', data)[:len(library_clap)]
    library_clap = library_clap[:len(library_set)]
    odds = np.clip(library_set, 1e-4, 1-1e-4)
    library_profile = profile(np.log(odds/(1-odds)))
    sounds = Sounds(data, len(library_clap))
    model, processor = clap()
    tagger = efficientat()[0]
    from models.preprocess import AugmentMelSTFT
    mel = AugmentMelSTFT(n_mels=128, sr=32000, win_length=800, hopsize=320).eval()
    rows = []
    with FastRenderer() as renderer, torch.no_grad():
        for target in benchmark.targets('external'):
            wave = benchmark.reference(target, renderer)
            unit = torch.from_numpy(wave/np.max(np.abs(wave)))
            query = torch.nn.functional.normalize(vector(model.get_audio_features(**processor(
                audio=[torchaudio.functional.resample(unit, 44100, RATE).numpy()[:RATE*10]], sampling_rate=RATE, return_tensors='pt'))), dim=-1).numpy()[0]
            x = torchaudio.functional.resample(unit, 44100, 32000)[:320000]
            mine = profile(tagger(mel(torch.nn.functional.pad(x, (0, 320000-len(x)))[None]).unsqueeze(0))[0].float().flatten().numpy())
            likeness, kinship = library_clap @ query, library_profile @ mine
            first = np.argsort(-(likeness/likeness.std()+kinship/kinship.std()))[:shortlist]
            patches = [sounds.patch(int(i)) for i in first]
            with RenderPool(Score(wave), jobs) as pool:
                objective = np.array([-score if canonical is not None else -99. for canonical, score in
                                      pool.map([('__mix__', p, 0) for p in patches])])
            args = (objective, likeness[first], kinship[first])
            expected, combined = wide.rating(*args), wide.combine(*args)
            best = int(np.argmax(combined))
            rows.append({'target': target['id'], 'file': target['file'], 'row': int(first[best]), 'expected': float(expected[best]),
                         'score': float(combined[best]), 'narrow': float(narrow.rating(*[a[best:best+1] for a in args])[0]),
                         'synths': ' + '.join(s['synth'] for s in patches[best]['sources']),
                         'top': [{'row': int(first[i]), 'expected': float(expected[i])} for i in np.argsort(-expected)[:3]]})
            print(f'{target["id"]} {target["file"][:40]:40s} best of {len(library_clap):,}: {rows[-1]["synths"]:24s} score {combined[best]:+.2f}', flush=True)
    score = np.array([r['score'] for r in rows])
    print(f'{len(rows)} recordings, best library sound each: mean score {score.mean():+.2f} (min {score.min():+.2f}, max {score.max():+.2f}). '
          f'Expected rating: {np.mean([r["narrow"] for r in rows]):.2f} if a score means what it meant for recordings so far, '
          f'{np.mean([r["expected"] for r in rows]):.2f} if it means what it means across all clips; '
          f'{sum(r["expected"] >= 3.5 for r in rows)} of {len(rows)} reach 3.5 on the generous reading')
    (HERE/'runs/predicted.json').write_text(json.dumps(rows, indent=1))


def main():
    clips = rated_clips()
    gesture, spectrum = objective_parts(clips)
    judges = {'objective (gesture + spectrum)': gesture+spectrum, '  gesture part': gesture, '  spectrum part': spectrum,
              'CLAP likeness': clap_likeness(clips), 'AudioSet profile likeness': audioset_likeness(clips)}
    judges['objective + CLAP (equal weight)'] = standard(judges['objective (gesture + spectrum)'])+standard(judges['CLAP likeness'])
    judges['objective + CLAP + AudioSet'] = judges['objective + CLAP (equal weight)']+standard(judges['AudioSet profile likeness'])
    np.savez(HERE/'runs/judges.npz', rating=[c['rating'] for c in clips], **{k.strip(): v for k, v in judges.items()})
    domains = (None, 'recording', 'native', 'mix')
    print(f'{len(clips)} rated clips. Agreement with the listener on strictly ordered pairs:')
    print(f'{"":36s}' + ''.join(f'{(d or "all"):>18s}' for d in domains))
    for name, score in judges.items():
        cells = [agreement(clips, score, d) for d in domains]
        print(f'{name:36s}' + ''.join(f'{a*100:11.1f}% {n:5d}' for a, n in cells))


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['predict']:
        predict(sys.argv[2])
    else:
        main()
