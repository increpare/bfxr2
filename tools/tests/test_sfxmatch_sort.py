"""The sorting page: labels, queues, probes and audio for filing renders under species."""
import json

import numpy as np
import pytest

from sfxmatch import sort
from sfxmatch.render import FastRenderer

NAMES = ['Birdr', 'Machinr', 'Squishr']
GENERATORS = {'Birdr': ['generate_chirp', 'generate_trill'], 'Machinr': ['generate_ratchet'], 'Squishr': ['generate_blob']}


def unit(x):
    x = np.asarray(x, np.float32)
    return x/np.linalg.norm(x, axis=-1, keepdims=True)


def make_pool(seed=0, per_cluster=40):
    """Three tight clusters on the unit sphere in 8 dimensions, plus a few scattered rows."""
    rng = np.random.default_rng(seed)
    centres = unit(rng.normal(size=(3, 8)))
    rows = [c + rng.normal(0, .12, (per_cluster, 8)) for c in centres]
    rows.append(rng.normal(size=(6, 8)))
    vectors = unit(np.concatenate(rows))
    n = len(vectors)
    pairs = np.array([[0, 1]]*per_cluster + [[1, 1]]*per_cluster + [[0, 2]]*per_cluster + [[2, -1]]*6)
    generators = np.array([[0, 0]]*per_cluster + [[0, 0]]*per_cluster + [[1, 0]]*per_cluster + [[0, -1]]*6)
    pool = sort.Pool(vectors.astype(np.float16), seconds=np.full(n, .5, np.float32), pairs=pairs, generators=generators,
                     balance=np.full(n, .4, np.float32), names=NAMES, generator_names=GENERATORS)
    return pool, centres


def cluster_of(pool, row, centres):
    return int((centres @ pool.vector(row)).argmax())


def test_pool_describes_a_render_as_its_cell():
    pool, _ = make_pool()
    cell = pool.describe(0)
    assert cell['id'] == 'mix-1m:0' and pool.index('mix-1m:0') == 0
    assert cell['synths'] == ['Birdr', 'Machinr'] and cell['generators'] == ['generate_chirp', 'generate_ratchet']
    assert cell['balance'] == pytest.approx(.4) and cell['seconds'] == pytest.approx(.5)
    single = pool.describe(len(pool)-1)
    assert single['synths'] == ['Squishr'] and single['generators'] == ['generate_blob'] and single['balance'] is None


def test_labels_store_round_trip_rename_and_exemplars(tmp_path):
    labels = sort.Labels(tmp_path, session='one')
    labels.create_species('coin', 'role')
    saved = labels.add({'id': 'mix-1m:5', 'scope': 'mix', 'species': ['coin'], 'negatives': [], 'queue': 'discovery'})
    assert saved['time'] and json.loads((tmp_path/'one.jsonl').read_text().splitlines()[0])['id'] == 'mix-1m:5'
    later = sort.Labels(tmp_path, session='two')
    later.add({'id': 'mix-1m:7', 'scope': 'a', 'species': ['coin'], 'negatives': []})           # an old accidental one
    later.add({'id': 'mix-1m:8', 'scope': 'b', 'species': ['coin'], 'negatives': [], 'explicit': True})
    assert later.labelled() == {'mix-1m:5', 'mix-1m:8'} and later.revisit() == ['mix-1m:7']
    assert later.species() == {'coin': {'kind': 'role'}} or later.species()['coin']['kind'] == 'role'
    later.rename('coin', 'pickup')
    fresh = sort.Labels(tmp_path, session='three')
    assert fresh.exemplars() == {'pickup': [('mix-1m:5', 'mix'), ('mix-1m:8', 'b')]}
    assert 'coin' not in fresh.species() and fresh.species()['pickup']['kind'] == 'role'
    assert {r['id'] for r in fresh.records()} == {'mix-1m:5', 'mix-1m:7', 'mix-1m:8'}
    with pytest.raises(ValueError):
        fresh.add({'id': 'mix-1m:9', 'scope': 'mix', 'species': ['unknown species'], 'negatives': []})


def test_discovery_starts_typical_then_goes_far(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path)
    queues = sort.Queues(pool, labels, seed=1)
    first = queues.next('discovery')
    typical = int((pool.matrix() @ unit(pool.matrix().mean(0))).argmax())
    assert first['row'] == typical and first['queue'] == 'discovery' and first['probe'] is None
    labels.create_species('x', 'character')
    queues.observe(labels.add({'id': first['id'], 'scope': 'mix', 'species': ['x'], 'negatives': []}))
    second = queues.next('discovery')
    assert second['id'] != first['id']
    assert cluster_of(pool, second['row'], centres) != cluster_of(pool, first['row'], centres)
    skipped = labels.add({'id': second['id'], 'scope': 'mix', 'species': [], 'negatives': ['skip']})
    queues.observe(skipped)
    assert queues.next('discovery')['id'] not in {first['id'], second['id']}


def test_typical_queue_covers_every_cluster(tmp_path):
    pool, centres = make_pool()
    queues = sort.Queues(pool, sort.Labels(tmp_path), seed=1, clusters=6)
    items = [queues.next('typical') for _ in range(6)]
    assert {cluster_of(pool, item['row'], centres) for item in items} == {0, 1, 2}
    assert len({item['id'] for item in items}) == 6


def test_alternate_and_random_queues(tmp_path):
    pool, _ = make_pool()
    queues = sort.Queues(pool, sort.Labels(tmp_path), seed=1, clusters=3)
    assert [queues.next('alternate')['queue'] for _ in range(4)] == ['discovery', 'typical', 'discovery', 'typical']
    assert queues.next('random')['queue'] == 'random'


def file_cluster(pool, labels, queues, centres, cluster, species, count=3):
    rows = [r for r in range(len(pool)) if cluster_of(pool, r, centres) == cluster][:count]
    for r in rows:
        queues.observe(labels.add({'id': pool.ids[r], 'scope': 'mix', 'species': [species], 'negatives': []}))
    return rows


def test_verify_queue_serves_the_species_boundary_first(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path)
    labels.create_species('a', 'character'); labels.create_species('b', 'character')
    queues = sort.Queues(pool, labels, seed=1)
    file_cluster(pool, labels, queues, centres, 0, 'a'); file_cluster(pool, labels, queues, centres, 1, 'b')
    first, second = queues.next('verify', 'a'), queues.next('verify', 'a')
    assert first['probe']['kind'] == 'verify' and first['probe']['species'] == 'a'
    assert cluster_of(pool, first['row'], centres) == 0 and first['id'] not in labels.labelled()
    assert first['probe']['margin'] <= second['probe']['margin']


def test_chord_probe_finds_the_render_nearest_a_midpoint(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('a', 'character')
    queues = sort.Queues(pool, labels, seed=1)
    rows = file_cluster(pool, labels, queues, centres, 0, 'a')
    item = queues.next('chord', 'a')
    probe = item['probe']
    assert probe['kind'] == 'chord' and probe['species'] == 'a' and item['row'] not in rows
    ends = [pool.index(e) for e in probe['ends']]
    mid = unit(pool.vector(ends[0]) + pool.vector(ends[1]))
    assert probe['chord'] == pytest.approx(1 - float(pool.vector(ends[0]) @ pool.vector(ends[1])), abs=1e-4)
    assert probe['gap'] == pytest.approx(1 - float(mid @ pool.vector(item['row'])), abs=1e-4)
    assert probe['gap'] < probe['chord']
    assert queues.next('chord', 'a')['probe']['ends'] != probe['ends']


def test_edge_probe_walks_outward_until_told_no(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('a', 'character')
    queues = sort.Queues(pool, labels, seed=1)
    file_cluster(pool, labels, queues, centres, 0, 'a')
    one = queues.next('edge', 'a')
    assert one['probe']['kind'] == 'edge' and one['probe']['step'] == 1 and one['probe']['distance'] > 0
    queues.observe(labels.add({'id': one['id'], 'scope': 'mix', 'species': ['a'], 'negatives': [], 'probe': one['probe']}))
    two = queues.next('edge', 'a')
    assert two['probe']['step'] == 2 and two['probe']['exemplar'] == one['probe']['exemplar']
    assert two['probe']['distance'] > one['probe']['distance']
    queues.observe(labels.add({'id': two['id'], 'scope': 'mix', 'species': [], 'negatives': [], 'probe': two['probe']}))
    three = queues.next('edge', 'a')
    assert three['probe']['step'] == 1
    assert sort.stats(labels, pool)['species']['a']['edge_radii'] == [pytest.approx(two['probe']['distance'])]


def test_stats_count_coherence_by_pair_and_probe_outcomes(tmp_path):
    pool, _ = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('a', 'character'); labels.create_species('b', 'role')
    labels.add({'id': 'mix-1m:0', 'scope': 'mix', 'species': ['a'], 'negatives': []})
    labels.add({'id': 'mix-1m:1', 'scope': 'a', 'species': ['a'], 'negatives': []})
    labels.add({'id': 'mix-1m:2', 'scope': 'mix', 'species': [], 'negatives': ['terrible']})
    labels.add({'id': 'mix-1m:3', 'scope': 'mix', 'species': [], 'negatives': ['skip']})
    labels.add({'id': 'mix-1m:44', 'scope': 'mix', 'species': ['a'], 'negatives': [], 'probe': {'kind': 'chord', 'species': 'a'}})
    labels.add({'id': 'mix-1m:45', 'scope': 'mix', 'species': [], 'negatives': [], 'probe': {'kind': 'chord', 'species': 'a'}})
    labels.add({'id': 'mix-1m:46', 'scope': 'mix', 'species': ['b'], 'negatives': [], 'probe': {'kind': 'verify', 'species': 'a'}})
    s = sort.stats(labels, pool)
    assert s['total'] == 6 and s['skipped'] == 1
    assert s['species']['a'] == {'kind': 'character', 'exemplars': 2, 'mix': 2, 'chord_pass': 0.5, 'chord_probes': 2,
                                 'verify_agree': 0.0, 'verify_probes': 1, 'edge_radii': []}
    assert s['species']['b']['exemplars'] == 1
    pair = s['pairs']['Birdr + Machinr']
    assert pair == {'judged': 2, 'one_source': 0, 'terrible': 1, 'incoherent': 0, 'coherent': 1}   # the old accidental label is not a judgement
    assert s['pairs']['Machinr + Machinr']['judged'] == 2      # a bare "not a" answer is not a coherence judgement


def test_app_round_trip_serves_items_and_records_labels(tmp_path):
    pool, _ = make_pool()
    app = sort.App(pool, sort.Labels(tmp_path), audio=None)
    assert app.handle('/api/species', {'create': 'coin', 'kind': 'role'})['species']['coin']['kind'] == 'role'
    item = app.handle('/api/next', {'queue': 'discovery'})
    assert item['id'] in pool.ids and item['synths'] and 'hints' in item
    saved = app.handle('/api/label', {'id': item['id'], 'scope': 'mix', 'species': ['coin'], 'negatives': [], 'queue': 'discovery', 'seconds': 4.2})
    assert saved['stats']['species']['coin']['exemplars'] == 1
    assert app.handle('/api/next', {'queue': 'discovery'})['id'] != item['id']
    assert app.handle('/api/exemplars', {'species': 'coin'})['exemplars'][0]['id'] == item['id']
    with pytest.raises(ValueError):
        app.handle('/api/label', {'id': 'mix-1m:999999', 'scope': 'mix', 'species': [], 'negatives': []})


@pytest.fixture(scope='module')
def renderer():
    with FastRenderer() as r:
        yield r


def test_audio_renders_each_source_alone_and_caches(tmp_path, renderer):
    sources = [{'synth': 'Boomr', 'params': {}, 'seed': .3}, {'synth': 'Zappr', 'params': {}, 'seed': .7}]
    canonical, balance, mix, _ = renderer.mix(sources, balance=0.)
    patches = {'mix-1m:1': {'sources': canonical, 'balance': 0.}}
    audio = sort.Audio(renderer, patches.__getitem__, tmp_path)
    alone = sort.wave_of(audio.wav('mix-1m:1', 'a'))
    assert len(alone) == len(mix) or abs(len(alone)-len(mix)) < 64
    n = min(len(alone), len(mix))
    corr = float(np.corrcoef(alone[:n], mix[:n])[0, 1])
    assert corr > .999
    assert (tmp_path/'mix-1m:1-a.wav').exists() or any(tmp_path.glob('*a.wav'))
    assert audio.wav('mix-1m:1', 'a') == audio.wav('mix-1m:1', 'a')
    assert len(sort.wave_of(audio.wav('mix-1m:1', 'b'))) > 0 and len(sort.wave_of(audio.wav('mix-1m:1', 'mix'))) > 0


def test_item_reports_species_nearest_to_the_render(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('a', 'character'); labels.create_species('b', 'character')
    app = sort.App(pool, labels, audio=None)
    file_cluster(pool, labels, app.queues, centres, 0, 'a'); file_cluster(pool, labels, app.queues, centres, 1, 'b')
    probe = [r for r in range(len(pool)) if cluster_of(pool, r, centres) == 1 and pool.ids[r] not in labels.labelled()][0]
    near = app.handle('/api/item', {'id': pool.ids[probe]})['nearby']
    assert list(near) == ['b', 'a'] and near['b'] > near['a']


def test_reload_resumes_the_unanswered_render(tmp_path):
    pool, _ = make_pool()
    app = sort.App(pool, sort.Labels(tmp_path), audio=None)
    app.handle('/api/species', {'create': 'x'})
    first = app.handle('/api/next', {'queue': 'discovery'})
    assert app.handle('/api/next', {'queue': 'discovery', 'resume': True})['id'] == first['id']
    assert app.handle('/api/next', {'queue': 'discovery'})['id'] == first['id']      # unanswered, so still the next pick
    app.handle('/api/label', {'id': first['id'], 'scope': 'mix', 'species': ['x'], 'negatives': []})
    assert app.handle('/api/next', {'queue': 'discovery', 'resume': True})['id'] != first['id']


def test_revisit_queue_serves_half_assigned_renders_until_refiled(tmp_path):
    pool, _ = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('x', 'character')
    app = sort.App(pool, labels, audio=None)
    labels.add({'id': 'mix-1m:3', 'scope': 'b', 'species': ['x'], 'negatives': []})      # as an older version wrote it
    assert app.handle('/api/stats', {})['stats']['species']['x']['exemplars'] == 0
    assert app.handle('/api/next', {'queue': 'revisit'})['id'] == 'mix-1m:3'
    saved = app.handle('/api/label', {'id': 'mix-1m:3', 'scope': 'b', 'species': ['x'], 'negatives': []})['saved']
    assert saved['explicit'] and app.handle('/api/stats', {})['stats']['species']['x']['exemplars'] == 1
    with pytest.raises(ValueError):
        app.handle('/api/next', {'queue': 'revisit'})


def test_star_species_rotates_probes_through_every_species(tmp_path):
    pool, centres = make_pool()
    labels = sort.Labels(tmp_path); labels.create_species('a', 'character'); labels.create_species('b', 'character')
    queues = sort.Queues(pool, labels, seed=1)
    file_cluster(pool, labels, queues, centres, 0, 'a'); file_cluster(pool, labels, queues, centres, 1, 'b')
    assert [queues.next('chord', '*')['probe']['species'] for _ in range(3)] == ['a', 'b', 'a']
