import numpy as np
import pytest
import soundfile as sf

from match.headroom import (
    HELDOUT_RENDER_SEED,
    PRESET_TARGET_RENDER_SEED,
    make_preset_targets,
)
from match.optimizer import RENDER_SEED


def _harvest_rows(n, seed, wave_types=None):
    """The real `harvest_preset_params` output shape.

    preset_cli.js emits `{"preset", "seed", "params"}` records, NOT bare param
    dicts. Fakes shaped as bare param dicts let a caller that forgets to unwrap
    `row["params"]` pass every test while rendering N copies of the default
    sound in production.
    """
    wave_types = list(range(n)) if wave_types is None else wave_types
    return [
        {"preset": "fake", "seed": seed + i,
         "params": {"waveType": wt, "frequency_start": 0.1 * (i + 1)}}
        for i, wt in enumerate(wave_types)
    ]


class _FakeRenderer:
    """Healthy fake renderer: returns distinct waves per preset."""

    def __init__(self):
        self.seeds = []
        self.params_seen = []

    def render_batch(self, params_list, seeds=0):
        self.seeds.append(seeds)
        self.params_seen.append(list(params_list))
        return [
            np.full(2000, 0.1 * (i + 1), dtype=np.float32) for i in range(len(params_list))
        ]


class _SilentFakeRenderer:
    """Degenerate fake renderer: all silent."""

    def render_batch(self, params_list, seeds=0):
        return [np.zeros(2000, dtype=np.float32) for _ in params_list]


class _IdenticalFakeRenderer:
    """Degenerate fake renderer: all identical."""

    def render_batch(self, params_list, seeds=0):
        return [np.full(2000, 0.2, dtype=np.float32) for _ in params_list]


class _NoneFakeRenderer:
    """Degenerate fake renderer: returns None."""

    def render_batch(self, params_list, seeds=0):
        return [None] + [np.full(2000, 0.2, dtype=np.float32) for _ in params_list[1:]]


def test_writes_one_wav_per_preset(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed),
    )
    paths = make_preset_targets(tmp_path, n=3, renderer=_FakeRenderer())
    assert len(paths) == 3
    for p in paths:
        assert p.suffix == ".wav" and p.is_file()
        data, _ = sf.read(p)
        assert len(data) > 0


def test_names_are_stable_across_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed),
    )
    a = make_preset_targets(tmp_path / "a", n=3, renderer=_FakeRenderer())
    b = make_preset_targets(tmp_path / "b", n=3, renderer=_FakeRenderer())
    assert [p.name for p in a] == [p.name for p in b]


def test_raises_on_all_silent_waves(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed, wave_types=[0] * n),
    )
    with pytest.raises(RuntimeError, match="silent"):
        make_preset_targets(tmp_path, n=3, renderer=_SilentFakeRenderer())


def test_raises_on_identical_waves(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed, wave_types=[0] * n),
    )
    with pytest.raises(RuntimeError, match="identical"):
        make_preset_targets(tmp_path, n=2, renderer=_IdenticalFakeRenderer())


def test_raises_on_none_wave(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed, wave_types=[0] * n),
    )
    with pytest.raises(RuntimeError, match="None"):
        make_preset_targets(tmp_path, n=3, renderer=_NoneFakeRenderer())


def test_the_three_render_seeds_are_pairwise_distinct():
    """Critical: if the control targets were rendered on HELDOUT_RENDER_SEED,
    a well-recovered noisy preset would reproduce the target's own noise
    realization on the held-out re-score, collapsing the in-domain floor (more
    so for the better-recovering big arm) and firing the reachability-ceiling
    branch of the decision rule for a reason unrelated to reachability. And on
    RENDER_SEED the search would be handed the target's noise for free."""
    seeds = [RENDER_SEED, HELDOUT_RENDER_SEED, PRESET_TARGET_RENDER_SEED]
    assert len(set(seeds)) == 3


def test_preset_targets_render_on_their_own_seed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed),
    )
    renderer = _FakeRenderer()
    make_preset_targets(tmp_path, n=3, renderer=renderer)
    assert renderer.seeds == [PRESET_TARGET_RENDER_SEED]
    assert PRESET_TARGET_RENDER_SEED != HELDOUT_RENDER_SEED


def test_raises_when_the_harvest_returns_too_few_params(tmp_path, monkeypatch):
    """A short preset_cli output must not silently shrink the control set."""
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n - 1, seed, wave_types=[0] * (n - 1)),
    )
    with pytest.raises(RuntimeError, match="expected 5"):
        make_preset_targets(tmp_path, n=5, renderer=_FakeRenderer())


def test_renderer_receives_the_inner_params_not_the_harvest_records(
    tmp_path, monkeypatch
):
    """The bug this pins rendered 10 identical default sounds, not 10 presets.

    The renderer worker merges whatever dict it is handed over the bfxr
    defaults, so a `{"preset", "seed", "params"}` record contributes no known
    keys and renders as the default sound. Ten distinct presets then collapse
    to one wave -- caught only by the all-identical degeneracy guard, at
    runtime, after the harness had already been declared ready.
    """
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed),
    )
    renderer = _FakeRenderer()
    make_preset_targets(tmp_path, n=3, renderer=renderer)
    sent = renderer.params_seen[0]
    assert [p["waveType"] for p in sent] == [0, 1, 2]
    assert all("params" not in p and "preset" not in p for p in sent)


def test_raises_when_a_harvest_row_is_not_a_params_record(tmp_path, monkeypatch):
    """A bare param dict (no "params" key) must fail loudly, not render defaults."""
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": i} for i in range(n)],
    )
    with pytest.raises(RuntimeError, match="no 'params' dict"):
        make_preset_targets(tmp_path, n=3, renderer=_FakeRenderer())


def test_jobs_is_threaded_into_the_owned_renderer(tmp_path, monkeypatch):
    seen = {}

    class _OwnedRenderer(_FakeRenderer):
        def __init__(self, jobs=None):
            super().__init__()
            seen["jobs"] = jobs

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: _harvest_rows(n, seed),
    )
    monkeypatch.setattr("match.headroom.BfxrRenderer", _OwnedRenderer)
    make_preset_targets(tmp_path, n=2, jobs=3)
    assert seen["jobs"] == 3
