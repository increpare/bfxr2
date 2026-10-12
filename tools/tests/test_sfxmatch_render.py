"""The fast worker must reproduce the vm-context renderer exactly."""
import numpy as np
import pytest

from multisynth.renderer import Renderer
from sfxmatch.render import FastRenderer, RenderAnd, RenderPool, active_synths


def _rms(wave):
    return float(np.sqrt(np.mean(wave**2)))


def test_fast_renderer_is_bit_identical():
    with Renderer() as slow, FastRenderer() as fast:
        assert fast.inventory == slow.inventory
        for name in active_synths(slow):
            presets = slow.specs[name]['presets']
            for i in range(3):
                preset = presets[(i*5) % len(presets)]
                params = slow.sample(name, preset, 100+i)
                assert fast.sample(name, preset, 100+i) == params
                slow_params, slow_wave = slow.render(name, params, 7+i)
                fast_params, fast_wave = fast.render(name, params, 7+i)
                assert fast_params == slow_params, name
                assert np.array_equal(fast_wave, slow_wave), name


def test_pool_matches_single_renderer_and_reports_failures():
    with FastRenderer() as renderer:
        params = renderer.sample('Transfxr', renderer.specs['Transfxr']['presets'][0], 3)
        expected = _rms(renderer.render('Transfxr', params, 5)[1])
    with RenderPool(RenderAnd(_rms), jobs=2) as pool:
        results = pool.map([('Transfxr', params, 5)]*3 + [('NoSuchSynth', {}, 1)])
    assert [r[1] for r in results[:3]] == [expected]*3
    assert results[3][0] is None and 'NoSuchSynth' in results[3][1]


def test_mix_is_real_mixr_output_and_identical_in_both_renderers():
    with Renderer() as slow, FastRenderer() as fast:
        a = {'synth': 'Boomr', 'params': fast.sample('Boomr', fast.specs['Boomr']['presets'][0], 3), 'seed': .25}
        b = {'synth': 'Birdr', 'params': fast.sample('Birdr', fast.specs['Birdr']['presets'][1], 4), 'seed': .75}
        sources, balance, wave, _ = fast.mix([a, b], .3)
        oracle = slow.request(op='mix', sources=[a, b], balance=.3)
        import base64
        assert np.array_equal(wave, np.frombuffer(base64.b64decode(oracle['audio']), dtype='<f4'))
        assert balance == .3 and [s['synth'] for s in sources] == ['Boomr', 'Birdr']
        # Sanitised controls are stable: mixing them again gives the same sound.
        assert np.array_equal(fast.mix(sources, .3)[2], wave)
        # Balance is Mixr's linear crossfade of the two sources rendered alone.
        alone_a, alone_b = fast.mix([a])[2], fast.mix([b])[2]
        count = min(len(alone_a), len(alone_b), len(wave)) - 200          # stay clear of each end fade
        expected = .7*alone_a[:count] + .3*alone_b[:count]
        assert np.allclose(wave[:count], np.clip(expected, -1, 1), atol=1e-6)
        # offset_db picks the balance that sets the level ratio.
        _, chosen, _, _ = fast.mix([a, b], offset_db=6.)
        rms = lambda x: float(np.sqrt(np.mean(x**2)))
        ratio = (chosen*rms(alone_b))/((1-chosen)*rms(alone_a))
        assert 20*np.log10(ratio) == pytest.approx(6., abs=.05)


def test_slow_render_times_out_and_the_renderer_recovers():
    with FastRenderer() as renderer:
        params = renderer.specs['Choirr']['defaults']
        renderer.timeout = .0005
        with pytest.raises(ValueError, match='exceeded'):
            renderer.render('Choirr', params, 1)
        renderer.timeout = 30.
        assert len(renderer.render('Choirr', params, 1)[1]) > 0
