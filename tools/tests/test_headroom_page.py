import json

import numpy as np
import soundfile as sf

from match.audio import SAMPLE_RATE
from match.listen_compare import write_arms_page


def _wav(path, value=0.1):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, np.full(1000, value, dtype=np.float32), SAMPLE_RATE)


def _setup(tmp_path):
    targets = tmp_path / "targets"
    _wav(targets / "Mario 1 - Jump.wav")
    arms = []
    for name in ("baseline_seeded", "big_seeded", "big_unseeded"):
        root = tmp_path / name
        _wav(root / "Mario 1 - Jump" / "model_seeded" / "match.wav")
        arms.append((name, root))
    return targets, arms


def test_key_records_every_arm_and_page_hides_names(tmp_path):
    targets, arms = _setup(tmp_path)
    out = tmp_path / "page.html"
    key_out = tmp_path / "key.json"

    write_arms_page(out, key_out, targets, arms, only={"Mario 1 - Jump"})

    html = out.read_text()
    for name, _ in arms:
        assert name not in html  # labels must not leak into the page

    key = json.loads(key_out.read_text())
    assert sorted(key["Mario 1 - Jump"]) == ["A", "B", "C"]
    assert sorted(key["Mario 1 - Jump"].values()) == sorted(n for n, _ in arms)


def test_shuffle_is_deterministic_for_a_given_seed(tmp_path):
    targets, arms = _setup(tmp_path)
    keys = []
    for i in range(2):
        out = tmp_path / f"page{i}.html"
        key_out = tmp_path / f"key{i}.json"
        write_arms_page(out, key_out, targets, arms,
                        only={"Mario 1 - Jump"}, shuffle_seed=7)
        keys.append(json.loads(key_out.read_text()))
    assert keys[0] == keys[1]
