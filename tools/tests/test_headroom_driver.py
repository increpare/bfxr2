import json

from match.headroom import ARMS, run_arm


def test_arm_matrix_matches_the_spec():
    assert set(ARMS) == {
        "baseline_seeded", "big_seeded", "baseline_unseeded", "big_unseeded",
    }
    assert ARMS["baseline_seeded"] == {
        "budget": 2000, "seed_model": True, "restarts": False
    }
    assert ARMS["big_seeded"] == {
        "budget": 200000, "seed_model": True, "restarts": True
    }
    assert ARMS["baseline_unseeded"] == {
        "budget": 2000, "seed_model": False, "restarts": False
    }
    assert ARMS["big_unseeded"] == {
        "budget": 200000, "seed_model": False, "restarts": True
    }


def test_run_arm_builds_the_expected_argv(tmp_path, monkeypatch):
    seen = {}

    def _fake_match_main(argv):
        seen["argv"] = argv
        out = tmp_path / "out"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "evals": 123, "elapsed_seconds": 4.5, "trace": [[64, 3.0]],
            "results": [{"file": "match.bfxr", "score": 1.5,
                         "wave_type": 0, "wave_type_name": "Square"}],
        }))
        return 0

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr("match.headroom.heldout_for_run",
                        lambda *a, **k: 1.9)

    row = run_arm(tmp_path / "t.wav", tmp_path / "out", "big_seeded",
                  ckpt=tmp_path / "best.pt", jobs=2, rng_seed=0)

    argv = seen["argv"]
    assert "--restarts" in argv
    assert argv[argv.index("--budget") + 1] == "200000"
    assert "--seed-model" in argv
    assert row["score"] == 1.5
    assert row["heldout_score"] == 1.9
    assert row["evals"] == 123


def test_baseline_unseeded_omits_the_model(tmp_path, monkeypatch):
    seen = {}

    def _fake_match_main(argv):
        seen["argv"] = argv
        out = tmp_path / "out2"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "evals": 1, "elapsed_seconds": 1.0, "trace": [],
            "results": [{"file": "match.bfxr", "score": 2.0,
                         "wave_type": 0, "wave_type_name": "Square"}],
        }))
        return 0

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr("match.headroom.heldout_for_run", lambda *a, **k: 2.2)

    run_arm(tmp_path / "t.wav", tmp_path / "out2", "baseline_unseeded",
            ckpt=tmp_path / "best.pt", jobs=None, rng_seed=0)

    assert "--seed-model" not in seen["argv"]
    assert "--restarts" not in seen["argv"]
