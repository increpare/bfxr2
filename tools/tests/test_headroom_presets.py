import numpy as np
import pytest
import soundfile as sf

from match.headroom import make_preset_targets


class _FakeRenderer:
    """Healthy fake renderer: returns distinct waves per preset."""

    def render_batch(self, params_list, seeds=0):
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
        lambda n, seed: [{"waveType": i} for i in range(n)],
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
        lambda n, seed: [{"waveType": i} for i in range(n)],
    )
    a = make_preset_targets(tmp_path / "a", n=3, renderer=_FakeRenderer())
    b = make_preset_targets(tmp_path / "b", n=3, renderer=_FakeRenderer())
    assert [p.name for p in a] == [p.name for p in b]


def test_raises_on_all_silent_waves(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    with pytest.raises(RuntimeError, match="silent"):
        make_preset_targets(tmp_path, n=3, renderer=_SilentFakeRenderer())


def test_raises_on_identical_waves(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    with pytest.raises(RuntimeError, match="identical"):
        make_preset_targets(tmp_path, n=2, renderer=_IdenticalFakeRenderer())


def test_raises_on_none_wave(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    with pytest.raises(RuntimeError, match="None"):
        make_preset_targets(tmp_path, n=3, renderer=_NoneFakeRenderer())
