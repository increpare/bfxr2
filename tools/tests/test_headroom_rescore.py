from pathlib import Path

import numpy as np

from match.headroom import HELDOUT_RENDER_SEED, rescore_heldout
from match.optimizer import RENDER_SEED

FIXTURE = Path(__file__).parent / "fixtures" / "square_blip.bfxr"


class _RecordingRenderer:
    def __init__(self):
        self.seeds = []

    def render_batch(self, params_list, seeds=0):
        self.seeds.append(seeds)
        return [np.ones(16, dtype=np.float32) for _ in params_list]


class _FakeObjective:
    def score_batch(self, waves):
        return np.array([0.5 for _ in waves])


def test_heldout_seed_differs_from_search_seed():
    assert HELDOUT_RENDER_SEED != RENDER_SEED


def test_rescore_renders_with_the_heldout_seed():
    renderer = _RecordingRenderer()
    score = rescore_heldout(FIXTURE, _FakeObjective(), renderer)
    assert renderer.seeds == [HELDOUT_RENDER_SEED]
    assert score == 0.5
