"""Native multi-synth engines must reproduce the Node renderer.

Skips when tools/multisynth_native/build/multisynth_worker is not built.
"""
import os

import numpy as np
import pytest

from multisynth_native.bench import NodeRenderer, compare
from multisynth_native.client import WORKER, NativeRenderer, NativeWorker

BUILT = WORKER.is_file() and os.access(WORKER, os.X_OK)
pytestmark = pytest.mark.skipif(not BUILT, reason='native worker not built (make -C tools/multisynth_native)')

# libm and V8 round a few transcendental calls differently, so renders are
# not always bit-identical. The largest difference measured is 3e-8.
TOLERANCE = 1e-6


def _engines():
    if not BUILT:
        return []
    with NativeWorker() as native:
        return sorted(native.synths)


ENGINES = _engines()


@pytest.fixture(scope='module')
def backends():
    with NodeRenderer() as node, NativeWorker() as native:
        yield node, native


def test_priority_engines_are_ported():
    assert {'Boomr', 'Choirr', 'Pluckr', 'Riftr', 'Squishr', 'Swarmr', 'Transfxr'} <= set(ENGINES)


@pytest.mark.parametrize('synth', ENGINES)
def test_native_matches_node(backends, synth):
    worst, exact, _, _ = compare(*backends, synth, 36)
    print(f'{synth}: max |difference| {worst:.1e}, {exact}/36 bit-exact')
    assert worst <= TOLERANCE


def test_worker_reports_bad_requests(backends):
    native = backends[1]
    with pytest.raises(ValueError, match='no native engine'):
        native.render('NoSuchSynth', {})
    with pytest.raises(ValueError, match='no usable audio'):
        native.render('Transfxr', {})
    # The worker keeps serving after a failed request.
    assert len(native.render('Boomr', {'duration': 0.2})) == 8820


def test_native_renderer_is_a_drop_in(backends):
    node = backends[0]
    with NativeRenderer() as renderer:
        # Out-of-range and partial controls are canonicalised by Node either way.
        for synth, params in [('Boomr', {'duration': 0.3, 'size': 7, 'mechanism': 2.5}),
                              ('Transfxr', {'duration': 0.2, 'pitch': {'start': 2, 'end': 0.1, 'curve': 'Nope'}})]:
            expected_params, expected = node.render(synth, params, 3)
            actual_params, actual = renderer.render(synth, params, 3)
            assert actual_params == expected_params
            assert len(actual) == len(expected) and np.max(np.abs(actual-expected)) <= TOLERANCE
        # A synth without a native engine still renders, through Node.
        fallback = next(name for name in sorted(node.specs) if name not in renderer.native.synths)
        params = node.sample(fallback, node.specs[fallback]['presets'][0], 5)
        assert np.array_equal(renderer.render(fallback, params, 9)[1], node.render(fallback, params, 9)[1])
