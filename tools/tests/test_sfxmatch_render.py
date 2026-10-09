"""The fast worker must reproduce the vm-context renderer exactly."""
import numpy as np

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
