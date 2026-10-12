import json

import numpy as np
import pytest
import torch

from neural_invert.schema import ControlSchema
from sfxmatch import benchmark, mel
from sfxmatch.dataset import MODES, perturb, quotas
from sfxmatch.model import BINS, InverseModel, expected_unit, proposals, soft_bins
from sfxmatch.objective import INFEASIBLE, Objective
from sfxmatch.render import FastRenderer
from sfxmatch.search import Space


@pytest.fixture(scope='module')
def renderer():
    with FastRenderer() as r:
        yield r


def tone(hz, seconds=.4, decay=6.):
    t = np.arange(int(44100*seconds))/44100
    return (np.sin(2*np.pi*hz*t)*np.exp(-decay*t)).astype(np.float32)


def test_describe_shape_and_silence_invariance():
    wave = tone(440)
    absolute, relative, duration = mel.describe(wave)
    assert absolute.shape == (mel.BANDS, mel.FRAMES) and absolute.dtype == np.uint8
    assert relative.shape == (mel.BANDS, mel.REL_FRAMES)
    padded = np.concatenate([np.zeros(5000, np.float32), wave*.2, np.zeros(9000, np.float32)])
    again = mel.describe(padded)
    assert np.array_equal(again[0], absolute) and again[2] == duration
    with pytest.raises(ValueError):
        mel.describe(np.zeros(1000, np.float32))


def test_objective_orders_sounds_and_ignores_padding():
    target = tone(440)
    objective = Objective(target)
    same = objective.score(target)
    assert same < 1e-3
    assert objective.score(np.concatenate([target, np.zeros(44100, np.float32)])) == pytest.approx(same, abs=1e-3)
    near, far = objective.score(tone(466)), objective.score(tone(1760, seconds=.1, decay=40))
    assert same < near < far
    assert objective.score(np.zeros(4000, np.float32)) == INFEASIBLE


def test_objective_penalises_wrong_spectral_balance_and_cannot_be_diluted_by_a_quiet_tail():
    rng = np.random.default_rng(0)
    noise = rng.standard_normal(22050).astype(np.float32)*np.exp(-np.arange(22050)/6000).astype(np.float32)
    bright = np.diff(noise, prepend=0).astype(np.float32)          # same envelope, low end removed
    objective = Objective(bright)
    assert objective.components(noise)['spectrum'] > .8            # roughly a 10 dB mean error
    assert objective.components(bright)['spectrum'] < 1e-6
    # A nearly silent tail with a faint late blip must not shrink the error.
    tail = np.zeros(88200, np.float32); tail[-200:] = .002
    stretched = np.concatenate([noise, tail])
    assert objective.components(stretched)['spectrum'] > .9*objective.components(noise)['spectrum']


def test_model_loss_and_proposals_decode_to_renderable_controls(renderer):
    specs = {name: renderer.specs[name] for name in ('Transfxr', 'Zappr')}
    model = InverseModel(specs)
    assert model.C == 15 and model.K == 7
    batch = 6
    synth = torch.tensor([0, 0, 0, 1, 1, 1])
    embedding = model.encode(torch.randint(0, 255, (batch, mel.BANDS, mel.FRAMES)),
                             torch.randint(0, 255, (batch, mel.BANDS, mel.REL_FRAMES)), torch.zeros(batch))
    out = model.controls_for(embedding, synth, [3, 3])
    loss = model.control_loss(out, synth, torch.rand(batch, 32), torch.zeros(batch, 8, dtype=torch.long),
                              torch.zeros(batch, dtype=torch.long))
    assert torch.isfinite(loss)
    # Zappr has no categoricals and fewer controls; padding must never be chosen.
    assert out['options'][3:].max() <= -1e4+1 and out['generator'][3:, len(specs['Zappr']['presets']):].max() <= -1e4+1
    for index, name in enumerate(specs):
        schema = ControlSchema(specs[name])
        unit, cats, gens = proposals(model, model.controls_for(embedding[:1], index), index, 4)
        assert unit.shape == (4, len(schema.continuous)) and cats.shape == (4, len(schema.categorical))
        anchor = renderer.sample(name, specs[name]['presets'][int(gens[1])], 1)
        _, wave = renderer.render(name, schema.decode(unit[1], cats[1], anchor), 1)
        assert len(wave) > 0


def test_soft_bins_round_trip():
    unit = torch.tensor([[.03, .5, .97]])
    assert torch.allclose(expected_unit(torch.log(soft_bins(unit)+1e-9)), unit, atol=1/BINS)


def test_space_round_trip_and_perturb(renderer):
    spec = renderer.specs['Transfxr']
    schema = ControlSchema(spec)
    params = renderer.sample('Transfxr', spec['presets'][0], 4)
    space = Space(spec, params)
    assert schema.encode(space.decode(space.encode(params)))[1].tolist() == schema.encode(params)[1].tolist()
    assert np.allclose(schema.encode(space.decode(space.encode(params)))[0], schema.encode(params)[0], atol=1e-6)
    rng = np.random.default_rng(0)
    for mode in MODES:
        renderer.render('Transfxr', perturb(schema, params, rng, mode), 1)


def test_quotas_weight_by_controls(renderer):
    plan = quotas(renderer.specs, ['Bfxr', 'Footsteppr'], 1000)
    assert sum(plan.values()) == pytest.approx(1000, abs=2) and plan['Bfxr'] > plan['Footsteppr']


def test_benchmark_is_frozen_and_wavs_start_and_end_at_zero(tmp_path):
    data = json.loads(benchmark.BENCHMARK.read_text())
    ids = [t['id'] for t in data['external']+data['native']]
    assert len(data['external']) == 50 and len(ids) == len(set(ids))
    assert not any(t['tag'] in benchmark.SKIP_TAGS for t in data['external'])
    benchmark.write_wav(tmp_path/'x.wav', np.ones(2000, np.float32))
    import soundfile as sf
    wave, _ = sf.read(tmp_path/'x.wav')
    assert wave[0] == 0 and wave[-1] == 0 and abs(wave).max() == pytest.approx(.5, abs=1e-3)


def test_guided_variations_are_local_and_choices_are_plausible_and_distinct(renderer):
    from sfxmatch.guided import pick_diverse, variations
    spec = renderer.specs['Transfxr']
    schema = ControlSchema(spec)
    parent = {'synth': 'Transfxr', 'params': renderer.sample('Transfxr', spec['presets'][0], 4), 'seed': 1}
    base, base_cat = schema.encode(parent['params'])
    rng = np.random.default_rng(0)
    moved = []
    for params in variations(parent, spec, rng, 40, .1):
        renderer.render('Transfxr', params, 1)
        unit, cat = schema.encode(params)
        moved.append(int((np.abs(unit-base) > 1e-6).sum() + (cat != base_cat).sum()))
    assert 1 <= np.median(moved) <= 4 and max(moved) <= len(base)//4+len(base_cat)+1
    # Six fake candidates: spectra differ along one axis, two score far worse than the parent.
    spectrum = lambda v: np.full(8, v, np.uint8)
    rows = [({'n': n}, score, spectrum(v), 0.) for n, (score, v) in
            enumerate([(1.0, 10), (1.05, 12), (1.05, 200), (1.08, 100), (3.0, 255), (4.0, 0)] + [(1.09, 11)]*9)]
    shown = pick_diverse(({'n': 'parent'}, 1.0, spectrum(10), 0.), rows, 3)
    assert [r[0]['n'] for r in shown] == [0, 2, 3]      # objective's best, then the most different plausible ones


def test_mix_draw_and_model_treat_a_mix_as_an_unordered_set(renderer):
    from sfxmatch.mixdata import COLUMNS, MixDraw
    from sfxmatch.mixmodel import PAIR, SINGLE, TWIN, MixModel, prepare
    from sfxmatch.render import active_synths
    names = active_synths(renderer)
    draw, rows, seed = MixDraw(names), [], 0
    while len(rows) < 24:
        seed += 1
        try:
            rows.append(draw(renderer, [9, seed]))
        except ValueError:
            pass
    data = {key: torch.from_numpy(np.stack([row[1][i] for row in rows])) for i, key in enumerate(COLUMNS)}
    synth = data['synth']
    assert ((synth[:, 1] < 0) | (synth[:, 0] <= synth[:, 1])).all()          # stored in synth order
    for patch, _ in rows[:4]:                                                # labels replay through Mixr
        assert len(renderer.mix(patch['sources'], patch['balance'])[2]) > 0
    # Force one single, one pair and one twin so every branch of the loss runs.
    synth[0, 1] = -1
    synth[1] = torch.tensor([2, 5]); synth[2] = torch.tensor([4, 4])
    data['synths'] = len(names)
    model = MixModel({name: renderer.specs[name] for name in names}).eval()
    batch, counts = prepare(data, torch.arange(len(rows)), 'cpu')
    assert batch['kind'][:3].tolist() == [SINGLE, PAIR, TWIN] and sum(counts) == len(batch['item_row'])
    embedding = model.encode(batch['mel'], batch['rel'], batch['duration'])
    loss, _ = model.loss(batch, counts, embedding)
    assert torch.isfinite(loss)
    # Listing a twin's two sources the other way round (and flipping the balance) is the same mix.
    for key in ('continuous', 'categorical', 'generator'):
        data[key][2] = data[key][2].flip(0)
    data['balance'][2] = 1-data['balance'][2]
    batch, counts = prepare(data, torch.arange(len(rows)), 'cpu')
    assert model.loss(batch, counts, embedding)[0].item() == pytest.approx(loss.item(), rel=1e-5)


def test_cover_uniform_preserves_text_and_transitions(renderer):
    from sfxmatch import mixcover
    schema = ControlSchema(renderer.specs['Transfxr'])
    anchor = renderer.sample('Transfxr', renderer.specs['Transfxr']['presets'][0], 7)
    params = mixcover.uniform(schema, anchor, np.random.default_rng(4))
    unit, cats = schema.encode(params)
    assert np.allclose(unit, np.random.default_rng(4).random(len(unit)), atol=1e-6)
    assert all(params[name] == anchor.get(name, schema.spec['defaults'][name]) for name in schema.fixed_text)
    assert any('.start' in control['name'] for control in schema.continuous)
    assert all(0 <= label < len(control['values']) for label, control in zip(cats, schema.categorical))


def test_cover_caps_envelope_and_gates_audible_duration():
    from sfxmatch import mixcover
    source = {'synth': 'Bfxr', 'params': {'attackTime': 1., 'sustainTime': 1., 'decayTime': 1.}, 'seed': .2}
    capped = mixcover.cap_source(source)
    assert sum(capped['params'][key]**2 for key in ('attackTime', 'sustainTime', 'decayTime'))*100000+10 <= 4*44100
    assert source['params']['attackTime'] == 1.
    assert mixcover.audio_reason(tone(440), [0.1]) is None
    assert mixcover.audio_reason(tone(440, .01), [.1]) == 'duration'
    assert mixcover.audio_reason(tone(440), [1e-6]) == 'source_rms'
    assert mixcover.audio_reason(tone(440)*1e-6, [.1]) == 'mix_rms'


def test_cover_interpolates_shared_controls_and_counts_disjoint(renderer):
    from sfxmatch import mixcover
    def source(name, seed):
        return {'synth': name, 'params': renderer.sample(name, renderer.specs[name]['presets'][0], seed), 'seed': .2}
    a, b = source('Transfxr', 1), source('Transfxr', 2)
    schema = ControlSchema(renderer.specs['Transfxr'])
    left, right = {'sources': [a], 'balance': .5}, {'sources': [b], 'balance': .5}
    result = mixcover.interpolate(left, right, renderer.specs, .25, np.random.default_rng(1))
    assert np.allclose(schema.encode(result['sources'][0]['params'])[0], .75*schema.encode(a['params'])[0]+.25*schema.encode(b['params'])[0])
    assert mixcover.interpolate(left, {'sources': [source('Zappr', 1)], 'balance': .5}, renderer.specs, .5, np.random.default_rng(1)) is None
    crossed = mixcover.interpolate({'sources': [a, source('Zappr', 2)], 'balance': .2}, {'sources': [b, source('Footsteppr', 3)], 'balance': .8}, renderer.specs, .5, np.random.default_rng(4))
    assert len(crossed['sources']) == 2 and crossed['balance'] == pytest.approx(.5)


def test_cover_draw_modes_replay_and_keep_generator_labels(renderer):
    from sfxmatch.mixcover import CoverDraw, COLUMNS
    draw = CoverDraw(['Transfxr', 'Zappr'], [], source_retries=3)
    successes = []
    for index in range(40):
        patch, values, stats = draw(renderer, {'seed': [3, index], 'mode': 'both-uniform', 'single': index % 5 == 0})
        assert stats and sum(value for key, value in stats.items() if key.endswith('/attempt')) >= 1
        if patch is not None:
            successes.append(patch)
            row = dict(zip(COLUMNS, values))
            assert np.all(row['generator'] == -1) and row['mode'] == 'both-uniform'
            assert len(patch['sources']) == (1 if index % 5 == 0 else 2)
            assert renderer.mix(patch['sources'], patch['balance'])[3]
    assert successes


def test_covereval_blocked_nn_normalizes_excludes_zero_and_self():
    from sfxmatch.covereval import nearest
    reference = np.array([[2., 0., 0.], [0., 3., 0.], [0., 0., 0.], [1., 1., 0.]], np.float32)
    query = np.array([[1., 0., 0.], [0., 1., 0.]], np.float32)
    gap, row = nearest(query, reference, exclude=[0, 1], query_block=1, reference_block=2, device='cpu')
    assert row.tolist() == [3, 3]
    assert np.allclose(gap, 1-1/np.sqrt(2))
    gap, row = nearest([[0., 0., 0.]], reference, device='cpu')
    assert row.tolist() == [-1] and np.isinf(gap).all()


def test_covereval_loads_only_fully_aligned_available_shards(tmp_path, monkeypatch):
    from sfxmatch.covereval import load
    from sfxmatch import tags
    data, cache = tmp_path/'data', tmp_path/'cache'; data.mkdir(); cache.mkdir()
    (data/'meta.json').write_text('{}')
    for n in range(3):
        np.savez(data/f'mix-{n:04d}.npz', synth=np.zeros((2, 2), np.int8), duration=np.zeros(2))
        (data/f'mix-{n:04d}.jsonl').write_text('{}\n{}\n')
    np.save(cache/'clap-0000.npy', np.array([[2., 0.], [0., 0.]], np.float16))
    np.save(cache/'clap-0002.npy', np.ones((1, 2), np.float16))
    monkeypatch.setattr(tags, 'store', lambda path: cache)
    monkeypatch.setattr(tags, 'text_vectors', lambda: np.eye(2, dtype=np.float32))
    bank = load(data)
    assert len(bank['vectors']) == 2 and bank['valid'].tolist() == [True, False]
    assert bank['shards'] == ['mix-0000.npz']
    assert bank['skipped']['missing_encoding'] == 1 and bank['skipped']['unaligned'] == 1


def test_covereval_same_label_chords_exclude_heldout():
    from sfxmatch.covereval import chords
    vectors = np.array([[1., 0., 0.], [.7, .7, 0.], [0., 0., 1.], [-1., 0., 0.]], np.float32)
    labels = np.array([0, 0, 1, 0])
    pairs, targets = chords(vectors, labels, 20, np.random.default_rng(1), exclude=[3])
    assert len(pairs) > 0 and set(pairs.flatten()) == {0, 1}
    assert np.allclose(targets, np.array([1+1/np.sqrt(2), 1/np.sqrt(2), 0.])/np.linalg.norm([1+1/np.sqrt(2), 1/np.sqrt(2), 0.]))


def test_cover_model_loads_diagnostic_mode_and_unlabelled_generators(renderer, tmp_path):
    from sfxmatch.mixmodel import MixModel, load_dataset, prepare
    from sfxmatch.mixcover import CoverDraw, COLUMNS
    names = ['Transfxr', 'Zappr']; specs = {n: renderer.specs[n] for n in names}
    draw = CoverDraw(names, [], 10); rows = []
    for index in range(30):
        patch, values, _ = draw(renderer, {'seed': [71, index], 'mode': 'both-uniform', 'single': index % 5 == 0})
        if patch is not None:
            rows.append(values)
        if len(rows) == 3:
            break
    np.savez(tmp_path/'mix-0000.npz', **{k: np.stack([r[i] for r in rows]) for i, k in enumerate(COLUMNS)})
    (tmp_path/'meta.json').write_text(json.dumps({'specs': specs}))
    _, data = load_dataset(tmp_path)
    model = MixModel(specs).eval(); data['synths'] = 2
    batch, counts = prepare(data, torch.arange(len(rows)), 'cpu')
    embedding = model.encode(batch['mel'], batch['rel'], batch['duration'])
    loss = model.loss(batch, counts, embedding)[0]
    assert torch.isfinite(loss) and (data['generator'] == -1).all()
    data['synth'][2] = torch.tensor([0, 0])
    # A twin can exchange both sources and invert balance even without generator labels.
    first, counts = prepare(data, torch.arange(len(rows)), 'cpu')
    value = model.loss(first, counts, embedding)[0]
    for key in ('continuous', 'categorical', 'generator'):
        data[key][2] = data[key][2].flip(0)
    data['balance'][2] = 1-data['balance'][2]
    swapped, counts = prepare(data, torch.arange(len(rows)), 'cpu')
    assert model.loss(swapped, counts, embedding)[0].item() == pytest.approx(value.item(), rel=1e-5)
    # Missing generator targets suppress only that CE, leaving the control gradient.
    inverse = InverseModel(specs).eval()
    out = inverse.controls_for(embedding[:1, :512], 0)
    target = torch.full((1,), -1, dtype=torch.long)
    masked = inverse.row_loss(out, torch.zeros(1, dtype=torch.long), torch.zeros(1, 32), torch.zeros(1, 8, dtype=torch.long), target)
    assert torch.isfinite(masked).all()


def test_covereval_report_has_fixed_denominator_novelty_and_hole_misses(tmp_path, monkeypatch):
    from sfxmatch.covereval import evaluate
    from sfxmatch import tags
    reference, new = tmp_path/'reference', tmp_path/'new'; cache = tmp_path/'cache'; cache.mkdir()
    for path, vectors in [(reference, [[1., 0.], [0., 1.], [-1., 0.]]), (new, [[.7071, .7071]])]:
        path.mkdir(); dest = cache/path.name; dest.mkdir()
        np.savez(path/'mix-0000.npz', synth=np.zeros((len(vectors), 2), np.int8), duration=np.zeros(len(vectors)))
        (path/'mix-0000.jsonl').write_text('{}\n'*len(vectors))
        np.save(dest/'clap-0000.npy', np.array(vectors, np.float32)); np.save(dest/'audioset-0000.npy', np.ones((len(vectors), 2)))
    monkeypatch.setattr(tags, 'store', lambda p: cache/p.name)
    targets = tmp_path/'holes.npz'
    np.savez(targets, meta=json.dumps({'data': str(reference.resolve()), 'shards': ['mix-0000.npz'], 'referenceRows': 3}),
             heldout=np.array([2]), queries=np.array([[-1., 0.]]), test_pairs=np.array([[0, 1]]),
             test_targets=np.array([[.7071, .7071]]), targets=np.array([[.7071, .7071]]),
             pairs=np.array([[0, 1]]), recipes=np.array([json.dumps({'id': 0})]))
    report = evaluate(reference, targets, new, tmp_path/'report.json', device='cpu')
    assert report['heldout']['count'] == 1 and report['referenceRows'] == 3
    assert report['midpoints']['after']['covered'] == 1 and report['midpoints']['before']['covered'] == 0
    assert report['novelty']['abovePoint1'] == 1 and report['holes']['farMisses'] == 0
    assert report['holes']['uniqueTargets'] == report['holes']['uniqueRecipes'] == 1
    assert report['midpoints']['uniqueTargets'] == report['midpoints']['uniqueEndpointPairs'] == 1
    assert report['audioRecipes']['exactDuplicates'] == 0
    # A legacy bank may repeat endpoint orientation and audio recipes; expose both.
    np.savez(targets, meta=json.dumps({'data': str(reference.resolve()), 'shards': ['mix-0000.npz'], 'referenceRows': 3}),
             heldout=np.array([2]), queries=np.array([[-1., 0.]]), test_pairs=np.array([[0, 1], [1, 0]]),
             test_targets=np.array([[.7071, .7071], [.7071, .7071]]), targets=np.array([[.7071, .7071], [.7071, .7071]]),
             pairs=np.array([[0, 1], [1, 0]]), recipes=np.array([json.dumps({'id': 0}), json.dumps({'id': 1})]))
    np.savez(new/'mix-0000.npz', synth=np.zeros((2, 2), np.int8), duration=np.zeros(2))
    (new/'mix-0000.jsonl').write_text('{}\n{}\n')
    np.save(cache/'new'/'clap-0000.npy', np.array([[.7071, .7071], [.7071, .7071]], np.float32))
    np.save(cache/'new'/'audioset-0000.npy', np.ones((2, 2)))
    duplicate = evaluate(reference, targets, new, tmp_path/'report-duplicate.json', device='cpu')
    assert duplicate['holes']['count'] == 2 and duplicate['holes']['uniqueTargets'] == duplicate['holes']['uniqueRecipes'] == 1
    assert duplicate['midpoints']['count'] == 2 and duplicate['midpoints']['uniqueTargets'] == 1
    assert duplicate['audioRecipes']['exactDuplicates'] == 1
    grouped = duplicate['noveltyByStrategy']
    assert grouped['unknown']['rows'] == 2 and grouped['unknown']['abovePoint1'] == 2
    assert grouped['unknown']['uniqueAudioRecipes'] == grouped['unknown']['exactDuplicateAudioRecipes'] == 1
    assert grouped['both-uniform']['rows'] == 0 and grouped['both-uniform']['rateAbovePoint1'] == 0
    # Group by stored recipe mode without changing the same computed embeddings.
    (new/'mix-0000.jsonl').write_text(json.dumps({'mode': 'both-uniform'})+'\n'+json.dumps({'mode': 'hole'})+'\n')
    strategies = evaluate(reference, targets, new, tmp_path/'report-strategies.json', device='cpu')['noveltyByStrategy']
    assert strategies['both-uniform']['rows'] == strategies['hole']['rows'] == 1
    assert strategies['both-uniform']['abovePoint1'] == strategies['hole']['abovePoint1'] == 1
    assert strategies['hole']['meanGap'] == pytest.approx(duplicate['novelty']['meanGap'])
    assert strategies['unknown']['rows'] == strategies['generator-uniform']['rows'] == 0


def test_cover_hole_orders_inventory_slots_and_flips_balance(renderer):
    from sfxmatch.mixcover import CoverDraw, COLUMNS
    names = ['Transfxr', 'Birdr']
    def source(name, seed):
        return {'synth': name, 'params': renderer.sample(name, renderer.specs[name]['presets'][0], seed), 'seed': .2}
    left = {'sources': [source('Transfxr', 1), source('Birdr', 2)], 'balance': .3}
    right = {'sources': [source('Transfxr', 3), source('Birdr', 4)], 'balance': .7}
    hole = {'id': 0, 'label': 1, 'left': left, 'right': right}
    result = CoverDraw(names, [hole])(renderer, {'seed': 7, 'single': False, 'mode': 'hole'})
    patch, values, _ = result
    assert patch is not None
    row = dict(zip(COLUMNS, values))
    assert row['synth'].tolist() == [0, 1]
    assert [s['synth'] for s in patch['sources']] == names
    assert np.allclose(renderer.mix(patch['sources'], patch['balance'])[2], renderer.mix(patch['sources'], float(row['balance']))[2], atol=1e-6)


def test_cover_rejects_long_source_even_when_mix_is_short(renderer):
    from sfxmatch.mixcover import CoverDraw
    # Test the actual duration gate against an individually rendered source.
    class ShortMix:
        specs = renderer.specs
        sample = renderer.sample
        def mix(self, sources, balance=.5, offset_db=None):
            if len(sources) == 1:
                return sources, .5, tone(440, 5., decay=.01), [.1]
            return sources, .5, tone(440, .2), [.1, .1]
    patch, _, stats = CoverDraw(['Transfxr'], [], source_retries=2)(ShortMix(),
            {'seed': 1, 'single': False, 'mode': 'both-uniform'})
    assert patch is None and stats.get('both-uniform/Transfxr/source_duration', 0) > 0


def test_cover_generation_resume_is_identical_and_checks_metadata(tmp_path):
    from sfxmatch.mixcover import generate
    first = tmp_path/'first'; second = tmp_path/'second'
    report = generate(first, total=5, shard_rows=5, jobs=1, batch=2, seed=74)
    assert report['newRows'] == 5 and report['existingRows'] == 0
    before = (first/'mix-0000.jsonl').read_bytes()
    resumed = generate(first, total=5, shard_rows=5, jobs=1, batch=5, seed=74)
    assert resumed['existingRows'] == 5 and resumed['newRows'] == 0
    assert (first/'mix-0000.jsonl').read_bytes() == before
    generate(second, total=5, shard_rows=5, jobs=1, batch=5, seed=74)
    assert (second/'mix-0000.jsonl').read_bytes() == before
    with np.load(first/'mix-0000.npz') as a, np.load(second/'mix-0000.npz') as b:
        assert all(np.array_equal(a[key], b[key]) for key in a.files)
    with pytest.raises(ValueError, match='different settings'):
        generate(first, total=5, shard_rows=5, jobs=1, seed=75)


def test_cover_reports_worker_pool_failure(tmp_path, monkeypatch):
    from sfxmatch import mixcover
    class BrokenPool:
        def __init__(self, *args):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def map(self, tasks):
            raise RuntimeError('worker process died')
    monkeypatch.setattr(mixcover, 'RenderPool', BrokenPool)
    with pytest.raises(RuntimeError, match='worker process died'):
        mixcover.generate(tmp_path, total=1, shard_rows=1)
    stats = json.loads((tmp_path/'mix-0000.stats.json').read_text())
    assert stats['both-uniform/pool/worker_failure'] == 1


def test_cover_crosses_both_nonshared_ingredients_and_keeps_endpoint_levels(renderer):
    from sfxmatch.mixcover import interpolate
    def source(name, seed):
        return {'synth': name, 'params': renderer.sample(name, renderer.specs[name]['presets'][0], seed), 'seed': .2}
    common = source('Transfxr', 1); b = source('Birdr', 2); c = source('Zappr', 3)
    left = {'sources': [common, b], 'balance': .2}
    right = {'sources': [common, c], 'balance': .8}
    crossed = interpolate(left, right, renderer.specs, .5, np.random.default_rng(1), recipe='cross-ingredients')
    assert [s['synth'] for s in crossed['sources']] == ['Birdr', 'Zappr']
    assert crossed['sources'][0] == b and crossed['sources'][1] == c
    assert crossed['balance'] == pytest.approx(.8)
    shared = interpolate(left, right, renderer.specs, .5, np.random.default_rng(1))
    assert 'Transfxr' in [s['synth'] for s in shared['sources']]
    from sfxmatch.mixcover import CoverDraw
    hole = {'id': 0, 'label': 1, 'left': left, 'right': right}
    draw = CoverDraw(['Transfxr', 'Birdr', 'Zappr'], [hole])
    seen = set()
    for seed in range(12):
        patch, _, _ = draw(renderer, {'seed': seed, 'single': False, 'mode': 'hole'})
        if patch is not None:
            seen.add(patch['hole']['recipe'])
            if patch['hole']['recipe'] == 'cross-ingredients':
                assert [s['synth'] for s in patch['sources']] == ['Birdr', 'Zappr']
    assert seen == {'cross-ingredients', 'shared-interpolation'}


def test_covereval_chords_deduplicate_unordered_endpoints_when_pool_is_small():
    from sfxmatch.covereval import chords
    angles = np.arange(4)*.1
    vectors = np.stack((np.cos(angles), np.sin(angles)), axis=1).astype(np.float32)
    pairs, midpoint = chords(vectors, np.zeros(4, int), 100, np.random.default_rng(3))
    unordered = {tuple(sorted(pair)) for pair in pairs}
    assert len(pairs) == len(unordered) == len(midpoint) == 6
    assert all(a != b for a, b in pairs)


def test_cover_generation_rejects_total_that_omits_completed_trailing_shards(tmp_path):
    from sfxmatch.mixcover import generate
    # A completed trailing shard must not silently survive a reduced total.
    generate(tmp_path, total=1, shard_rows=1, jobs=1, seed=74)
    (tmp_path/'mix-0001.npz').write_bytes((tmp_path/'mix-0000.npz').read_bytes())
    (tmp_path/'mix-0001.jsonl').write_bytes((tmp_path/'mix-0000.jsonl').read_bytes())
    with pytest.raises(ValueError, match='trailing'):
        generate(tmp_path, total=1, shard_rows=1, jobs=1, seed=74)


def test_cover_skips_infeasible_holes_without_retrying_duplicate_endpoints(renderer):
    from sfxmatch.mixcover import CoverDraw
    def source(name):
        return {'synth': name, 'params': renderer.sample(name, renderer.specs[name]['presets'][0], 1), 'seed': .2}
    bad = {'id': 0, 'label': 1, 'endpoints': [10, 11], 'left': {'sources': [source('Bfxr')], 'balance': .5}, 'right': {'sources': [source('Bfxr')], 'balance': .5}}
    duplicate = {**bad, 'id': 1, 'endpoints': [11, 10]}
    good = {'id': 2, 'label': 1, 'endpoints': [20, 21], 'left': {'sources': [source('Transfxr')], 'balance': .5}, 'right': {'sources': [source('Transfxr')], 'balance': .5}}
    class GatedRenderer:
        specs = renderer.specs
        def mix(self, sources, balance=.5, offset_db=None):
            seconds = .012 if sources[0]['synth'] == 'Bfxr' else .2
            return sources, balance, tone(440, seconds), [.1]*len(sources)
    names = ['Bfxr', 'Transfxr']
    # Reproduce an initially selected bad chord without relying on disposable runs.
    for seed in range(100):
        rng = np.random.default_rng(seed); rng.integers(0, len(names), 1)
        if int(rng.integers(3)) < 2:
            break
    patch, _, stats = CoverDraw(names, [bad, duplicate, good], source_retries=2)(GatedRenderer(),
                {'seed': seed, 'single': True, 'mode': 'hole'})
    assert patch is not None and patch['hole']['id'] == 2 and len(patch['sources']) == 1
    assert stats['hole/Bfxr/source_duration'] == 2
    assert stats['hole/pool/skipped_infeasible'] == 1
    assert stats['hole/row/attempt'] == 3
    failed, _, exhausted = CoverDraw(names, [bad, duplicate], source_retries=2)(GatedRenderer(),
                {'seed': seed, 'single': True, 'mode': 'hole'})
    assert failed is None and exhausted['hole/row/attempt'] == 2
    assert exhausted['hole/pool/skipped_infeasible'] == 1 and exhausted['hole/pool/exhausted'] == 1
    all_bad = [{**bad, 'id': index, 'endpoints': [100+2*index, 101+2*index]} for index in range(6)]
    failed, _, bounded = CoverDraw(names, all_bad, source_retries=2)(GatedRenderer(),
                {'seed': seed, 'single': True, 'mode': 'hole'})
    assert failed is None and bounded['hole/row/attempt'] == 8
    assert bounded['hole/pool/skipped_infeasible'] == 4


def test_covereval_reports_cosine_and_euclidean_quarter_coverage_separately(tmp_path, monkeypatch):
    from sfxmatch.covereval import evaluate
    from sfxmatch import tags
    reference, new = tmp_path/'reference', tmp_path/'new'; cache = tmp_path/'cache'; cache.mkdir()
    # Endpoint cosine=.8: cosine-quarter radius=.05, Euclidean-quarter radius=.0125.
    # This existing neighbor has gap=.03 from their midpoint, distinguishing the measures.
    vectors = np.array([[np.sqrt(.9), -np.sqrt(.1), 0.], [np.sqrt(.9), np.sqrt(.1), 0.],
                        [.97, 0., np.sqrt(1-.97**2)], [-1., 0., 0.]], np.float32)
    for path, rows in [(reference, vectors), (new, np.array([[1., 0., 0.]], np.float32))]:
        path.mkdir(); dest = cache/path.name; dest.mkdir()
        np.savez(path/'mix-0000.npz', synth=np.zeros((len(rows), 2), np.int8), duration=np.zeros(len(rows)))
        (path/'mix-0000.jsonl').write_text('{}\n'*len(rows))
        np.save(dest/'clap-0000.npy', rows); np.save(dest/'audioset-0000.npy', np.ones((len(rows), 2)))
    monkeypatch.setattr(tags, 'store', lambda path: cache/path.name)
    targets = tmp_path/'holes.npz'
    np.savez(targets, meta=json.dumps({'data': str(reference.resolve()), 'shards': ['mix-0000.npz'], 'referenceRows': 4}),
             heldout=np.array([3]), queries=vectors[3:], test_pairs=np.array([[0, 1]]),
             test_targets=np.array([[1., 0., 0.]]), targets=np.array([[1., 0., 0.]]),
             pairs=np.array([[0, 1]]), recipes=np.array([json.dumps({'id': 0})]))
    report = evaluate(reference, targets, new, tmp_path/'report.json', device='cpu')
    assert report['midpoints']['before']['covered'] == 1
    assert report['midpoints']['quarterEuclidean']['before']['covered'] == 0
    assert report['midpoints']['after']['covered'] == report['midpoints']['quarterEuclidean']['after']['covered'] == 1
    assert '/4' in report['midpoints']['radius'] and '/16' in report['midpoints']['quarterEuclidean']['radius']
