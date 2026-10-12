"""Sort renders into species: a local page where the listener files what each render is.

    uv run python -m sfxmatch.sort                 # then open http://127.0.0.1:8766
    uv run python -m sfxmatch.sort --pool 300000   # cap the embedded renders held in memory

Vocabulary: a *patch* is a point in a synth's parameter space and a *render*
its audio; a *species* is a perceptual kind defined only by its *specimens*,
the renders filed under it; the listener-confirmed ones are its *specimen
exemplars*. Each item plays the mix and each source alone. Labels are
appended to labels/*.jsonl, one file per session, and species live in
labels/species.json; renaming a species rewrites the names, never the ids.

Queues decide what to hear next: `discovery` is the render farthest from
everything labelled (the most typical render first), `typical` walks cluster
centres so the common mass gets named too, `alternate` takes turns, and three
probes test whether a species is a region in projection space: `verify`
serves propagated specimens nearest its boundary, `chord` the render nearest
the midpoint of two exemplars, `edge` walks outward from an exemplar until
the listener says no.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

import numpy as np

from . import benchmark

HERE = Path(__file__).resolve().parent
LABELS = HERE/'labels'
DATA = HERE/'runs/mix-1m'
CACHE = HERE/'runs/sort-cache'
SCOPES = ('mix', 'a', 'b')
NEGATIVES = ('mute', 'terrible', 'incoherent', 'skip')
KINDS = ('role', 'character')
QUEUES = ('alternate', 'discovery', 'typical', 'random', 'verify', 'chord', 'edge', 'revisit')
MIN_SECONDS = .05       # blips shorter than this are not worth a listener's time
CHUNK = 65536
EDGE_STEP = .08         # cosine distance per step of an edge walk, a little above the nearest-neighbour gap


def unit(x):
    x = np.asarray(x, np.float32)
    return x/max(float(np.linalg.norm(x)), 1e-9)


class Pool:
    """The embedded renders: a projection per row plus what each row is (pair, generators, balance, length)."""

    def __init__(self, vectors, seconds, pairs=None, generators=None, balance=None, names=None, generator_names=None,
                 dataset='mix-1m', audioset=None, audioset_names=None, clap=None, patches=None):
        self.vectors = vectors
        self.seconds = np.asarray(seconds, np.float32)
        n = len(vectors)
        self.pairs = np.asarray(pairs) if pairs is not None else np.full((n, 2), -1)
        self.generators = np.asarray(generators) if generators is not None else np.full((n, 2), -1)
        self.balance = np.asarray(balance, np.float32) if balance is not None else np.full(n, .5, np.float32)
        self.names, self.generator_names = names or [], generator_names or {}
        self.dataset = dataset
        self.audioset, self.audioset_names = audioset, audioset_names   # audioset: (top indices (n,3), probabilities (n,3))
        self.clap = clap                                              # (tag names, text vectors, mean, std)
        self.patches = patches                                        # id -> patch, when the data is on disk
        self.ids = [f'{dataset}:{i}' for i in range(n)]
        self._index = {id: i for i, id in enumerate(self.ids)}
        self.usable = (self._nonzero() > 0) & (self.seconds >= MIN_SECONDS)

    def _nonzero(self):
        out = np.zeros(len(self.vectors), np.float32)
        for start in range(0, len(self.vectors), CHUNK):
            out[start:start+CHUNK] = np.abs(self.vectors[start:start+CHUNK].astype(np.float32)).sum(1)
        return out

    def __len__(self):
        return len(self.vectors)

    def index(self, id):
        if id not in self._index:
            raise ValueError(f'Unknown render {id}')
        return self._index[id]

    def vector(self, row):
        return np.asarray(self.vectors[row], np.float32)

    def matrix(self):
        return np.asarray(self.vectors, np.float32)

    def similarity(self, vector):
        """Cosine similarity of every row to `vector`, in chunks so a million float16 rows stay small."""
        vector = np.asarray(vector, np.float32)
        out = np.empty(len(self.vectors), np.float32)
        for start in range(0, len(self.vectors), CHUNK):
            out[start:start+CHUNK] = self.vectors[start:start+CHUNK].astype(np.float32) @ vector
        return out

    def synths(self, row):
        return [self.names[p] if self.names else str(p) for p in self.pairs[row] if p >= 0]

    def describe(self, row):
        row = int(row)
        synths = self.synths(row)
        generators = []
        for synth, g in zip(synths, self.generators[row]):
            table = self.generator_names.get(synth, [])
            generators.append(table[g] if 0 <= g < len(table) else None)
        return {'id': self.ids[row], 'row': row, 'synths': synths, 'generators': generators,
                'balance': float(self.balance[row]) if len(synths) == 2 else None,
                'seconds': float(self.seconds[row]), 'pair': ' + '.join(synths)}

    def hints(self, row):
        out = {}
        if self.audioset is not None and self.audioset_names:
            top, prob = self.audioset
            out['audioset'] = [[self.audioset_names[int(i)], round(float(p), 2)] for i, p in zip(top[row], prob[row]) if p > .02]
        if self.clap is not None:
            tags, text, mean, std = self.clap
            z = (text @ self.vector(row) - mean)/std
            best = np.argsort(-z)[:3]
            out['clap'] = [[tags[int(i)], round(float(z[i]), 1)] for i in best]
        return out

    def cluster(self, k, seed=0, sample=60000, iterations=10):
        """Spherical k-means on a subsample; centres ordered by cluster size, largest first."""
        rng = np.random.default_rng(seed)
        rows = np.flatnonzero(self.usable)
        rows = rng.choice(rows, min(sample, len(rows)), replace=False)
        X = np.asarray(self.vectors[np.sort(rows)], np.float32)
        k = min(k, len(X))
        # k-means++ seeding: each new centre is drawn with probability proportional to its distance
        # from the centres so far, so a small distinct cluster is not swallowed by a big one.
        centres = X[[int(rng.integers(len(X)))]]
        nearest = 1-X @ centres[0]
        while len(centres) < k:
            weights = np.clip(nearest, 0, None)**2
            pick = int(rng.choice(len(X), p=weights/weights.sum())) if weights.sum() > 0 else int(rng.integers(len(X)))
            centres = np.vstack([centres, X[pick]])
            nearest = np.minimum(nearest, 1-X @ X[pick])
        for _ in range(iterations):
            owner = (X @ centres.T).argmax(1)
            for c in range(k):
                mine = X[owner == c]
                if len(mine):
                    centres[c] = unit(mine.sum(0))
        sizes = np.bincount((X @ centres.T).argmax(1), minlength=k)
        return centres[np.argsort(-sizes)]

    @classmethod
    def load(cls, data=DATA, count=None, log=print):
        """Rows of a mixdata directory that have cached projections (`tags.py encode`)."""
        from .tags import Sounds, TAGS, store
        data = Path(data)
        meta = json.loads((data/'meta.json').read_text())
        names = list(meta['specs'])
        generator_names = {name: list(spec['presets']) for name, spec in meta['specs'].items()}
        cache = store(data)
        vectors, pairs, generators, balance, seconds, top, prob = [], [], [], [], [], [], []
        total = 0
        for shard in sorted(data.glob('mix-*.npz')):
            if shard.name.endswith('.tmp.npz'):
                continue
            index = shard.stem.split('-')[1]
            clap_file, audioset_file = cache/f'clap-{index}.npy', cache/f'audioset-{index}.npy'
            if not (clap_file.exists() and audioset_file.exists()):
                break
            with np.load(shard) as z:
                pairs.append(z['synth'].astype(np.int16)); generators.append(z['generator'].astype(np.int16))
                balance.append(z['balance'].astype(np.float32)); seconds.append((2.**z['duration']).astype(np.float32))
            v = np.load(clap_file)
            vectors.append(v if v.dtype == np.float16 else v.astype(np.float16))
            p = np.load(audioset_file).astype(np.float32)
            best = np.argpartition(-p, 3, axis=1)[:, :3]
            best = np.take_along_axis(best, np.argsort(-np.take_along_axis(p, best, 1), axis=1), 1)
            top.append(best.astype(np.int16)); prob.append(np.take_along_axis(p, best, 1).astype(np.float16))
            total += len(v)
            if count and total >= count:
                break
        if not vectors:
            raise FileNotFoundError(f'No projections cached for {data}; run `python -m sfxmatch.tags encode --data {data}` first')
        n = min(total, count or total)
        cat = lambda parts: np.concatenate(parts)[:n]
        audioset_names = None
        labels_file = HERE/'runs/EfficientAT/metadata/class_labels_indices.csv'
        if labels_file.exists():
            import csv
            audioset_names = [row[2] for row in list(csv.reader(labels_file.open()))[1:]]
        clap = None
        text_file = cache.parent/'clap-text.npy'
        if text_file.exists():
            text = np.load(text_file).astype(np.float32)
            if len(text) == len(TAGS):
                sample = cat(vectors)[np.random.default_rng(0).choice(n, min(n, 20000), replace=False)].astype(np.float32)
                sims = sample @ text.T
                clap = ([tag for _, tag, _ in TAGS], text, sims.mean(0), sims.std(0)+1e-6)
        sounds = Sounds(data, n)
        pool = cls(cat(vectors), cat(seconds), cat(pairs), cat(generators), cat(balance), names, generator_names,
                   dataset=data.name, audioset=(cat(top), cat(prob)), audioset_names=audioset_names, clap=clap,
                   patches=lambda id: sounds.patch(int(id.split(':')[1])))
        log(f'{len(pool)} embedded renders from {data.name}'
            + ('' if clap else '; no CLAP tag hints (runs/tags/clap-text.npy missing: `python -m sfxmatch.sort text`)'))
        return pool


class Labels:
    """Append-only label records, one JSONL file per session, plus the species registry."""

    def __init__(self, directory=LABELS, session=None):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session = session or time.strftime('%Y-%m-%d-%H%M%S')
        self.file = self.dir/f'{self.session}.jsonl'
        self.registry = self.dir/'species.json'

    def species(self):
        return json.loads(self.registry.read_text()) if self.registry.exists() else {}

    def _write_species(self, species):
        self.registry.write_text(json.dumps(species, indent=1, sort_keys=True))

    @staticmethod
    def normalise(name):
        name = ' '.join(str(name).split()).lower()
        if not name:
            raise ValueError('A species needs a name')
        return name

    def create_species(self, name, kind):
        if kind not in KINDS:
            raise ValueError(f'kind must be one of {KINDS}')
        species = self.species()
        name = self.normalise(name)
        if name in species:
            return name
        species[name] = {'kind': kind, 'created': time.strftime('%Y-%m-%dT%H:%M:%S')}
        self._write_species(species)
        return name

    def add(self, record):
        species = self.species()
        record = dict(record)
        if not isinstance(record.get('id'), str):
            raise ValueError('A label needs a render id')
        if record.get('scope', 'mix') not in SCOPES:
            raise ValueError(f'scope must be one of {SCOPES}')
        record['scope'] = record.get('scope', 'mix')
        record['species'] = [self.normalise(s) for s in record.get('species', [])]
        unknown = [s for s in record['species'] if s not in species]
        if unknown:
            raise ValueError(f'Unknown species {unknown}; create it first')
        record['negatives'] = list(record.get('negatives', []))
        bad = [n for n in record['negatives'] if n not in NEGATIVES]
        if bad:
            raise ValueError(f'negatives must be among {NEGATIVES}, not {bad}')
        record['time'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        record['session'] = self.session
        with self.file.open('a') as f:
            f.write(json.dumps(record)+'\n')
        return record

    def records(self):
        out = []
        for file in sorted(self.dir.glob('*.jsonl')):
            out.extend(json.loads(line) for line in file.read_text().splitlines() if line.strip())
        return out

    def effective(self):
        """The latest record per render id; a later label for the same render replaces the earlier one."""
        latest = {}
        for record in self.records():
            latest[record['id']] = record
        return list(latest.values())

    def labelled(self):
        return {r['id'] for r in self.effective() if self.counts(r)}

    def revisit(self):
        """Renders whose latest label is an old accidental one-source label, oldest first."""
        return [r['id'] for r in self.effective() if not self.counts(r)]

    @staticmethod
    def counts(record):
        """A record is an opinion unless it is an old one-source label the page let through by accident."""
        return record['scope'] == 'mix' or record.get('explicit', False)

    def exemplars(self):
        """Specimen exemplars per species as (id, scope); scope 'a' or 'b' means the source alone."""
        out = {}
        for record in self.effective():
            if 'skip' in record['negatives'] or not self.counts(record):
                continue
            for name in record['species']:
                out.setdefault(name, []).append((record['id'], record['scope']))
        return out

    def rename(self, old, new):
        old, new = self.normalise(old), self.normalise(new)
        species = self.species()
        if old not in species:
            raise ValueError(f'No species {old}')
        if old == new:
            return
        species.setdefault(new, species[old])
        del species[old]
        self._write_species(species)
        for file in sorted(self.dir.glob('*.jsonl')):
            lines = []
            for line in file.read_text().splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                record['species'] = list(dict.fromkeys(new if s == old else s for s in record['species']))
                if record.get('probe') and record['probe'].get('species') == old:
                    record['probe']['species'] = new
                lines.append(json.dumps(record))
            file.write_text('\n'.join(lines)+'\n')


class Queues:
    """What to hear next. Stateful: the farthest-point frontier, cluster centres, chord memory, edge walks."""

    def __init__(self, pool, labels, seed=0, clusters=150, edge_step=EDGE_STEP):
        self.pool, self.labels = pool, labels
        self.rng = np.random.default_rng(seed)
        self.clusters, self.edge_step = clusters, edge_step
        self.open = pool.usable.copy()
        self.nearest = None
        self.centres, self.cursor, self.turn = None, 0, 0
        self._centre_lock = threading.Lock()
        self.chords, self.edges = {}, {}
        for id in labels.labelled():
            self._absorb(id)

    def _absorb(self, id):
        if id not in self.pool._index:
            return
        row = self.pool.index(id)
        self.open[row] = False
        s = self.pool.similarity(self.pool.vector(row))
        self.nearest = s if self.nearest is None else np.maximum(self.nearest, s)

    def observe(self, record):
        if Labels.counts(record):
            self._absorb(record['id'])
        probe = record.get('probe') or {}
        if probe.get('kind') == 'edge':
            species = probe['species']
            if species in record['species']:
                self.edges[species] = {'exemplar': probe['exemplar'], 'step': probe['step']+1, 'distance': probe['distance']}
            else:
                self.edges.pop(species, None)

    def _pick(self, score, mask=None):
        """Row with the highest score among open rows (and `mask`)."""
        allowed = self.open if mask is None else self.open & mask
        if not allowed.any():
            raise ValueError('Nothing left to hear in this queue')
        return int(np.where(allowed, score, -np.inf).argmax())

    def _exemplar_rows(self, species):
        rows = [self.pool.index(id) for id, scope in self.labels.exemplars().get(species, [])
                if scope == 'mix' and id in self.pool._index]
        return list(dict.fromkeys(rows))

    def next(self, mode, species=None):
        if mode not in QUEUES:
            raise ValueError(f'queue must be one of {QUEUES}')
        if mode == 'alternate':
            mode = ('discovery', 'typical')[self.turn % 2]
            self.turn += 1
        probe = None
        if mode == 'discovery':
            if self.nearest is None:
                row = self._pick(self.pool.similarity(unit(self.pool.matrix().mean(0)) if len(self.pool) < CHUNK else self._mean()))
            else:
                row = self._pick(-self.nearest)
        elif mode == 'typical':
            centre = self.ensure_centres()[self.cursor % len(self.centres)]
            self.cursor += 1
            row = self._pick(self.pool.similarity(centre))
        elif mode == 'random':
            row = int(self.rng.choice(np.flatnonzero(self.open)))
        elif mode == 'revisit':
            waiting = [id for id in self.labels.revisit() if id in self.pool._index]
            if not waiting:
                raise ValueError('Nothing to revisit')
            row = self.pool.index(waiting[0])
        else:
            if not species:
                raise ValueError(f'The {mode} queue needs a species')
            if species == '*':
                species = self.rotate(mode)
            row, probe = getattr(self, mode)(self.labels.normalise(species))
        item = self.pool.describe(row)          # serving is not an opinion: only a label closes a render
        item['queue'], item['probe'] = mode, probe
        return item

    def ensure_centres(self):
        """Cluster centres for the typical queue; a few seconds on a big pool, so the app starts it early."""
        with self._centre_lock:
            if self.centres is None:
                self.centres = self.pool.cluster(self.clusters, seed=int(self.rng.integers(2**31)))
        return self.centres

    def rotate(self, mode):
        """'*' as the species: take every species with enough exemplars in turn, biggest first."""
        need = 2 if mode == 'chord' else 1
        names = [n for n, m in sorted(self.labels.exemplars().items(), key=lambda kv: -len(kv[1]))
                 if len(self._exemplar_rows(n)) >= need]
        if not names:
            raise ValueError(f'No species has enough exemplars for a {mode} probe yet')
        self.rotation = getattr(self, 'rotation', 0)
        name = names[self.rotation % len(names)]
        self.rotation += 1
        return name

    def _mean(self):
        total = np.zeros(self.pool.vectors.shape[1], np.float32)
        for start in range(0, len(self.pool), CHUNK):
            total += self.pool.vectors[start:start+CHUNK].astype(np.float32).sum(0)
        return unit(total)

    def verify(self, species):
        mine = self._exemplar_rows(species)
        if not mine:
            raise ValueError(f'"{species}" has no exemplars yet')
        others = [r for name in self.labels.exemplars() if name != species for r in self._exemplar_rows(name)]
        sim_mine = np.max([self.pool.similarity(self.pool.vector(r)) for r in mine], axis=0)
        sim_other = np.max([self.pool.similarity(self.pool.vector(r)) for r in others], axis=0) if others else None
        if len(mine) >= 2:
            within = [max(float(self.pool.vector(a) @ self.pool.vector(b)) for b in mine if b != a) for a in mine]
            floor = float(np.clip(np.median(within)-.1, .5, .95))
        else:
            floor = .8
        margin = sim_mine - (sim_other if sim_other is not None else floor)
        inside = (sim_mine > floor) & (margin > 0)
        if (inside & self.open).any():
            row = self._pick(-np.abs(margin), inside)
        else:
            row = self._pick(sim_mine)
        return row, {'kind': 'verify', 'species': species, 'guess': species, 'margin': round(float(margin[row]), 4)}

    def chord(self, species):
        mine = self._exemplar_rows(species)
        if len(mine) < 2:
            raise ValueError(f'"{species}" needs two exemplars for a chord')
        tried = self.chords.setdefault(species, set())
        pairs = [(a, b) for i, a in enumerate(mine) for b in mine[i+1:]]
        fresh = [p for p in pairs if frozenset(p) not in tried] or pairs
        a, b = fresh[int(self.rng.integers(len(fresh)))]
        tried.add(frozenset((a, b)))
        va, vb = self.pool.vector(a), self.pool.vector(b)
        mid = unit(va+vb)
        row = self._pick(self.pool.similarity(mid))
        return row, {'kind': 'chord', 'species': species, 'ends': [self.pool.ids[a], self.pool.ids[b]],
                     'chord': round(1-float(va @ vb), 4), 'gap': round(1-float(mid @ self.pool.vector(row)), 4)}

    def edge(self, species):
        mine = self._exemplar_rows(species)
        if not mine:
            raise ValueError(f'"{species}" has no exemplars yet')
        state = self.edges.get(species)
        if state is None or self.pool.index(state['exemplar']) not in mine:
            state = {'exemplar': self.pool.ids[mine[int(self.rng.integers(len(mine)))]], 'step': 1, 'distance': 0.}
        centre = unit(np.sum([self.pool.vector(r) for r in mine], axis=0))
        ve = self.pool.vector(self.pool.index(state['exemplar']))
        distance = 1-self.pool.similarity(ve)
        outward = self.pool.similarity(centre) < float(ve @ centre)
        beyond = distance > state['distance']+1e-6
        target = state['step']*self.edge_step
        mask = outward & beyond
        if not (mask & self.open).any():
            mask = beyond
        row = self._pick(-np.abs(distance-target), mask)
        return row, {'kind': 'edge', 'species': species, 'exemplar': state['exemplar'], 'step': state['step'],
                     'distance': round(float(distance[row]), 4)}


def stats(labels, pool=None):
    """Counts per species, probe outcomes, and how often each pair of synths cohered."""
    registry = labels.species()
    records = [r for r in labels.effective() if 'skip' not in r['negatives']]
    skipped = sum('skip' in r['negatives'] for r in labels.effective())
    species = {}
    for name, info in registry.items():
        mine = [r for r in records if name in r['species'] and Labels.counts(r)]
        chords = [r for r in records if (r.get('probe') or {}).get('kind') == 'chord' and r['probe'].get('species') == name]
        verifies = [r for r in records if (r.get('probe') or {}).get('kind') == 'verify' and r['probe'].get('species') == name]
        edges = [r for r in records if (r.get('probe') or {}).get('kind') == 'edge' and r['probe'].get('species') == name
                 and name not in r['species']]
        species[name] = {'kind': info['kind'], 'exemplars': len(mine), 'mix': sum(r['scope'] == 'mix' for r in mine),
                         'chord_pass': (sum(name in r['species'] for r in chords)/len(chords)) if chords else None,
                         'chord_probes': len(chords),
                         'verify_agree': (sum(name in r['species'] for r in verifies)/len(verifies)) if verifies else None,
                         'verify_probes': len(verifies),
                         'edge_radii': [r['probe']['distance'] for r in edges]}
    pairs = {}
    if pool is not None:
        for r in records:
            if r['id'] not in pool._index or not (r['species'] or r['negatives']):
                continue                      # "not that species" says nothing about whether the pair cohered
            key = pool.describe(pool.index(r['id']))['pair']
            if not Labels.counts(r):
                continue                      # an old accidental one-source label is waiting to be filed again
            entry = pairs.setdefault(key, {'judged': 0, 'one_source': 0, 'terrible': 0, 'incoherent': 0, 'coherent': 0})
            entry['judged'] += 1
            if r['scope'] != 'mix':
                entry['one_source'] += 1
            elif 'terrible' in r['negatives'] or 'mute' in r['negatives']:
                entry['terrible'] += 1
            elif 'incoherent' in r['negatives']:
                entry['incoherent'] += 1
            else:
                entry['coherent'] += 1
    return {'total': len(records), 'skipped': skipped, 'species': species, 'pairs': pairs}


class Audio:
    """Renders a saved mix, or one of its sources alone through Mixr, as WAV bytes; cached on disk."""

    def __init__(self, renderer, patch_of, cache=CACHE):
        self.renderer, self.patch_of, self.cache = renderer, patch_of, Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def wav(self, id, scope):
        if scope not in SCOPES:
            raise ValueError(f'scope must be one of {SCOPES}')
        file = self.cache/f'{id.replace(":", "-")}-{scope}.wav'
        if file.exists():
            return file.read_bytes()
        patch = self.patch_of(id)
        sources = patch['sources']
        with self.lock:
            if scope == 'mix':
                wave = self.renderer.mix(sources, patch['balance'])[2]
            else:
                slot = SCOPES.index(scope)-1
                if slot >= len(sources):
                    raise ValueError(f'{id} has no source {scope}')
                wave = self.renderer.mix([sources[slot]], .5)[2]
        data = benchmark.wav_bytes(wave[:44100*6])
        file.write_bytes(data)
        return data


def wave_of(wav):
    import io
    import soundfile as sf
    return sf.read(io.BytesIO(wav), dtype='float32')[0]


class App:
    def __init__(self, pool, labels, audio=None, seed=0, clusters=150):
        self.pool, self.labels, self.audio = pool, labels, audio
        self.queues = Queues(pool, labels, seed=seed, clusters=clusters)
        self.pending = None        # the served render that has not been answered yet
        self.lock = threading.Lock()
        if len(pool) > CHUNK:
            threading.Thread(target=self.queues.ensure_centres, daemon=True).start()

    def warm(self, id, sources):
        """Render the mix and each source now, so the page's first play does not wait."""
        if self.audio is None:
            return
        def run():
            for scope in SCOPES[:1+sources]:
                try:
                    self.audio.wav(id, scope)
                except Exception:
                    pass
        threading.Thread(target=run, daemon=True).start()

    def nearby(self, row):
        """Each species' nearest exemplar to this render, as cosine similarity, highest first."""
        v = self.pool.vector(row)
        out = {}
        for name, members in self.labels.exemplars().items():
            rows = [self.pool.index(id) for id, scope in members if scope == 'mix' and id in self.pool._index and self.pool.index(id) != row]
            if rows:
                out[name] = round(max(float(v @ self.pool.vector(r)) for r in rows), 4)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    def item(self, row):
        item = self.pool.describe(row)
        item['hints'] = self.pool.hints(row)
        item['nearby'] = self.nearby(row)
        latest = {r['id']: r for r in self.labels.records()}.get(item['id'])
        item['previous'] = latest
        return item

    def handle(self, path, body):
        with self.lock:
            if path == '/api/species':
                if body.get('create'):
                    self.labels.create_species(body['create'], body.get('kind', 'character'))
                if body.get('rename'):
                    self.labels.rename(body['rename'], body['to'])
                return {'species': self.labels.species(), 'stats': stats(self.labels, self.pool)}
            if path == '/api/next':
                if body.get('resume') and self.pending:
                    return self.pending       # a reload shows the same unanswered render
                item = self.queues.next(body.get('queue', 'alternate'), body.get('species'))
                full = self.item(item['row'])
                full.update({k: item[k] for k in ('queue', 'probe')})
                self.warm(full['id'], len(full['synths']))
                self.pending = full
                return full
            if path == '/api/item':
                return self.item(self.pool.index(body['id']))
            if path == '/api/label':
                self.pool.index(body['id'])
                record = self.labels.add({k: body[k] for k in ('id', 'scope', 'species', 'negatives', 'queue', 'probe', 'note', 'seconds')
                                          if k in body} | {'explicit': True})
                self.queues.observe(record)
                if self.pending and self.pending['id'] == record['id']:
                    self.pending = None
                return {'saved': record, 'stats': stats(self.labels, self.pool)}
            if path == '/api/stats':
                return {'stats': stats(self.labels, self.pool), 'species': self.labels.species()}
            if path == '/api/exemplars':
                name = self.labels.normalise(body['species'])
                out = []
                for id, scope in self.labels.exemplars().get(name, []):
                    if id in self.pool._index:
                        entry = self.pool.describe(self.pool.index(id)); entry['scope'] = scope; out.append(entry)
                return {'species': name, 'exemplars': out}
            if path == '/api/preset':
                patch = self.pool.patches(body['id']) if self.pool.patches else None
                if patch is None:
                    raise ValueError('No patches on disk for this pool')
                sources = patch['sources']
                scope = body.get('scope', 'mix')
                if scope == 'mix':
                    preset = {'synth': 'Mixr', 'params': {'masterVolume': .5, 'seed': .5, 'balance': patch['balance'], 'sources': json.dumps(
                        [{'synth': s['synth'], 'name': s['synth'], 'params': s['params'], 'renderSeed': s['seed']} for s in sources])}}
                else:
                    s = sources[SCOPES.index(scope)-1]
                    preset = {'synth': s['synth'], 'params': s['params']}
                from multisynth.report import add_preset
                collection = {}
                add_preset(collection, preset, f'{body["id"]} {scope}')
                return collection
        raise ValueError(f'Unknown endpoint {path}')


def serve(port, pool, labels, audio, host='127.0.0.1'):
    app = App(pool, labels, audio)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, kind, data):
            self.send_response(status)
            self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store'); self.send_header('Accept-Ranges', 'bytes')
            self.end_headers(); self.wfile.write(data)

        def run(self, body):
            try:
                self.reply(200, 'application/json', json.dumps(app.handle(self.path.split('?')[0], body)).encode())
            except Exception as error:
                self.reply(500, 'application/json', json.dumps({'error': f'{type(error).__name__}: {error}'}).encode())

        def do_GET(self):
            path = self.path.split('?')[0]
            if path in ('/', '/index.html'):
                return self.reply(200, 'text/html; charset=utf-8', page().encode())
            if path.startswith('/audio/'):
                try:
                    id, name = path[len('/audio/'):].split('/')
                    data = audio.wav(id, name.removesuffix('.wav'))
                except Exception as error:
                    return self.reply(500, 'text/plain', f'{type(error).__name__}: {error}'.encode())
                return self.send_audio(data)
            self.run({})

        def send_audio(self, data):
            span = self.headers.get('Range', '')
            if span.startswith('bytes='):
                # Safari will not play audio from a server that ignores range requests.
                first, _, last = span[6:].split(',')[0].partition('-')
                start = int(first) if first else max(0, len(data)-int(last))
                end = min(int(last), len(data)-1) if first and last else len(data)-1
                chunk = data[start:end+1]
                self.send_response(206)
                self.send_header('Content-Type', 'audio/wav'); self.send_header('Content-Length', str(len(chunk)))
                self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}'); self.send_header('Accept-Ranges', 'bytes')
                self.end_headers(); self.wfile.write(chunk)
                return
            self.reply(200, 'audio/wav', data)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            self.run(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    print(f'Sorting page on http://{host}:{port}', flush=True)
    server.serve_forever()


def page():
    return (HERE/'sort_page.html').read_text()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('command', nargs='?', default='serve', choices=['serve', 'text'])
    parser.add_argument('--data', default=DATA)
    parser.add_argument('--labels', default=LABELS)
    parser.add_argument('--pool', type=int, default=None, help='cap on embedded renders held in memory')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if args.command == 'text':
        from .tags import text_vectors, store
        out = store(args.data).parent/'clap-text.npy'
        np.save(out, text_vectors())
        print(f'CLAP tag vectors saved to {out}')
        return
    from .render import FastRenderer
    pool = Pool.load(args.data, args.pool)
    with FastRenderer() as renderer:
        serve(args.port, pool, Labels(args.labels), Audio(renderer, pool.patches), host=args.host)


if __name__ == '__main__':
    main()
