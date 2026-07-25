import json

from match.headroom import ARMS, _safe_dir, main, run_arm


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


def test_heldout_failure_does_not_discard_the_search_result(tmp_path, monkeypatch):
    """Important 1 fix: a Node-flake in the seconds-long held-out re-score
    must not throw away a 200000-eval search that already succeeded."""

    def _fake_match_main(argv):
        out = tmp_path / "out3"
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps({
            "evals": 200000, "elapsed_seconds": 900.0,
            "trace": [[64, 3.0], [200000, 0.5]],
            "results": [{"file": "match.bfxr", "score": 0.4,
                         "wave_type": 2, "wave_type_name": "Sawtooth"}],
        }))
        return 0

    def _flaky_heldout(*a, **k):
        raise RuntimeError("renderer worker died")

    monkeypatch.setattr("match.headroom.match_main", _fake_match_main)
    monkeypatch.setattr("match.headroom.heldout_for_run", _flaky_heldout)

    row = run_arm(tmp_path / "t.wav", tmp_path / "out3", "big_seeded",
                  ckpt=tmp_path / "best.pt", jobs=None, rng_seed=0)

    # The expensive search result must survive the cheap failure.
    assert row["score"] == 0.4
    assert row["evals"] == 200000
    assert row["trace"] == [[64, 3.0], [200000, 0.5]]
    assert row["wave_type_name"] == "Sawtooth"
    assert row["heldout_score"] is None
    assert "renderer worker died" in row["heldout_error"]


def _make_targets_dir(tmp_path, names):
    d = tmp_path / "targets"
    d.mkdir()
    for name in names:
        (d / f"{name}.wav").write_bytes(b"")
    return d


def test_main_uses_the_layout_write_arms_page_reads_back(tmp_path, monkeypatch):
    """out_dir passed to run_arm must be exactly
    <out>/<arm>/<safe_stem>/model_seeded — write_arms_page reads candidates
    from that exact path, and a mismatch silently blanks the listen page."""
    name = "Mario 3 - jump (nes)"
    targets_dir = _make_targets_dir(tmp_path, [name])
    out_dir = tmp_path / "out"

    calls = []

    def _fake_run_arm(target, out_dir_arg, arm, *, ckpt, jobs, rng_seed):
        calls.append((target, out_dir_arg, arm))
        return {"arm": arm, "score": 1.0, "heldout_score": 1.0,
                "wave_type_name": "Square", "evals": 10,
                "elapsed_seconds": 1.0, "trace": []}

    monkeypatch.setattr("match.headroom.run_arm", _fake_run_arm)
    monkeypatch.setattr("match.headroom.write_arms_page", lambda *a, **k: None)

    rc = main([
        "--targets", str(targets_dir),
        "--ckpt", str(tmp_path / "best.pt"),
        "-o", str(out_dir),
        "--presets", "0",
        "--arms", "baseline_seeded",
    ])

    assert rc == 0
    assert len(calls) == 1
    _, got_out_dir, arm = calls[0]
    assert arm == "baseline_seeded"
    expected = out_dir / "baseline_seeded" / _safe_dir(name) / "model_seeded"
    assert got_out_dir == expected


def test_main_survives_one_arm_failing(tmp_path, monkeypatch):
    """A run_arm failure on one arm must not abort the run; the other arm's
    row for the same target must still land in results.json."""
    name = "Mario 3 - jump (nes)"
    targets_dir = _make_targets_dir(tmp_path, [name])
    out_dir = tmp_path / "out"

    def _fake_run_arm(target, out_dir_arg, arm, *, ckpt, jobs, rng_seed):
        if arm == "big_seeded":
            raise RuntimeError("match exited with code 1")
        return {"arm": arm, "score": 1.0, "heldout_score": 1.0,
                "wave_type_name": "Square", "evals": 10,
                "elapsed_seconds": 1.0, "trace": []}

    monkeypatch.setattr("match.headroom.run_arm", _fake_run_arm)
    monkeypatch.setattr("match.headroom.write_arms_page", lambda *a, **k: None)

    rc = main([
        "--targets", str(targets_dir),
        "--ckpt", str(tmp_path / "best.pt"),
        "-o", str(out_dir),
        "--presets", "0",
        "--arms", "baseline_seeded", "big_seeded",
    ])

    assert rc == 0
    data = json.loads((out_dir / "results.json").read_text())
    rows = data["rows"]
    assert len(rows) == 2
    by_arm = {r["arm"]: r for r in rows}
    assert "error" not in by_arm["baseline_seeded"]
    assert by_arm["baseline_seeded"]["score"] == 1.0
    assert "error" in by_arm["big_seeded"]
    assert "RuntimeError" in by_arm["big_seeded"]["error"]


def test_main_results_json_is_valid_with_one_row_per_target_arm(
    tmp_path, monkeypatch
):
    """results.json must parse as JSON and contain exactly one row per
    (target, arm) attempted, including presets, with error rows carrying
    an 'error' key."""
    real_name = "Mario 3 - jump (nes)"
    targets_dir = _make_targets_dir(tmp_path, [real_name])
    out_dir = tmp_path / "out"
    preset_paths = [tmp_path / "preset_00.wav", tmp_path / "preset_01.wav"]

    def _fake_run_arm(target, out_dir_arg, arm, *, ckpt, jobs, rng_seed):
        if target.stem == "preset_01":
            raise RuntimeError("boom")
        return {"arm": arm, "score": 1.0, "heldout_score": 1.0,
                "wave_type_name": "Square", "evals": 10,
                "elapsed_seconds": 1.0, "trace": []}

    def _fake_make_preset_targets(out_dir_arg, n=10, seed=4242, renderer=None):
        return preset_paths

    monkeypatch.setattr("match.headroom.run_arm", _fake_run_arm)
    monkeypatch.setattr("match.headroom.make_preset_targets",
                        _fake_make_preset_targets)
    monkeypatch.setattr("match.headroom.write_arms_page", lambda *a, **k: None)

    rc = main([
        "--targets", str(targets_dir),
        "--ckpt", str(tmp_path / "best.pt"),
        "-o", str(out_dir),
        "--presets", "2",
        "--arms", "baseline_seeded",
        "--preset-arms", "baseline_seeded",
    ])

    assert rc == 0
    text = (out_dir / "results.json").read_text()
    data = json.loads(text)  # must parse: proves the write was atomic/complete
    rows = data["rows"]
    # 1 real target x 1 arm + 2 presets x 1 preset-arm = 3 rows
    assert len(rows) == 3
    by_target = {r["target"]: r for r in rows}
    assert "error" not in by_target[real_name]
    assert "error" not in by_target["preset_00"]
    assert "error" in by_target["preset_01"]
