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
