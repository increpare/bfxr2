import numpy as np
import soundfile as sf

from match.headroom import make_preset_targets


class _FakeRenderer:
    def render_batch(self, params_list, seeds=0):
        return [np.full(2000, 0.2, dtype=np.float32) for _ in params_list]


def test_writes_one_wav_per_preset(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "match.headroom.harvest_preset_params",
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
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
        lambda n, seed: [{"waveType": 0} for _ in range(n)],
    )
    a = make_preset_targets(tmp_path / "a", n=3, renderer=_FakeRenderer())
    b = make_preset_targets(tmp_path / "b", n=3, renderer=_FakeRenderer())
    assert [p.name for p in a] == [p.name for p in b]
