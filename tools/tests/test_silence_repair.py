import numpy as np

from match.bfxr_io import ParamSpace
from match.optimizer import SILENCE_PEAK, repair_silent_params


class _StubRenderer:
    """Renders silence while the low-pass is nearly closed, a tone once it
    opens past `open_at` — mimics the observed lpFilterCutoff->silence bug."""

    def __init__(self, open_at: float = 0.2):
        self.open_at = open_at
        self.calls = 0

    def render(self, params, seed=0):
        self.calls += 1
        if params["lpFilterCutoff"] < self.open_at:
            return np.zeros(4096, dtype=np.float32)
        return np.full(4096, 0.4, dtype=np.float32)


def _params(lp: float) -> dict:
    p = {n: float(d) for n, d in zip(ParamSpace().names, ParamSpace().defaults)}
    p["lpFilterCutoff"] = lp
    return p


def test_audible_render_is_untouched():
    space = ParamSpace()
    r = _StubRenderer()
    params = _params(0.5)
    wave = np.full(4096, 0.4, dtype=np.float32)
    out_params, out_wave = repair_silent_params(params, wave, r, space)
    assert out_params is params  # no repair attempted
    assert r.calls == 0
    assert float(np.max(np.abs(out_wave))) >= SILENCE_PEAK


def test_silent_render_is_opened_until_audible():
    space = ParamSpace()
    r = _StubRenderer(open_at=0.2)
    params = _params(0.01)  # near-closed low-pass -> silence
    silent = np.zeros(4096, dtype=np.float32)
    out_params, out_wave = repair_silent_params(params, silent, r, space)
    assert out_params["lpFilterCutoff"] >= 0.2
    assert float(np.max(np.abs(out_wave))) >= SILENCE_PEAK


def test_gives_up_gracefully_when_nothing_helps():
    space = ParamSpace()
    # never opens: every render is silent regardless of cutoff
    r = _StubRenderer(open_at=99.0)
    params = _params(0.01)
    silent = np.zeros(4096, dtype=np.float32)
    out_params, out_wave = repair_silent_params(params, silent, r, space)
    # falls back to the original params/wave rather than raising
    assert out_params == params
    assert float(np.max(np.abs(out_wave))) < SILENCE_PEAK
