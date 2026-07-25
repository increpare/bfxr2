import numpy as np
import pytest
import soundfile as sf

pytest.importorskip("matplotlib")

from invert.eval_targets import _safe_stem as eval_targets_safe_stem
from match.audio import SAMPLE_RATE
from match.listen_compare import HARD_SLICE, _safe_stem, main, write_compare_page

MODES = ("one_shot", "model_seeded")


def _const(amplitude: float = 0.3, seconds: float = 0.05) -> np.ndarray:
    # Keep fixture audio very short so spectrogram rendering stays fast.
    n = int(round(seconds * SAMPLE_RATE))
    return np.full(n, amplitude, dtype=np.float32)


def _write(path, x: np.ndarray) -> None:
    sf.write(path, x, SAMPLE_RATE, subtype="FLOAT")


def _build_roots(tmp_path, stems, modes=MODES):
    """Eval-root-shaped fixture: targets with spaces/parens in their stems
    (the real-world case that broke an earlier _safe_stem), plus matching
    baseline/candidate renders under every mode."""
    targets_dir = tmp_path / "targets"
    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    targets_dir.mkdir()

    for stem in stems:
        _write(targets_dir / f"{stem}.wav", _const())
        safe = _safe_stem(stem)
        for mode in modes:
            for root in (baseline_root, candidate_root):
                d = root / safe / mode
                d.mkdir(parents=True)
                _write(d / "match.wav", _const())

    return targets_dir, baseline_root, candidate_root


def test_page_has_audio_for_every_cell_and_shows_target_names(tmp_path):
    stems = ["Mario 3 - jump (nes)", "Mario Break Brick"]
    targets_dir, baseline_root, candidate_root = _build_roots(tmp_path, stems)

    out = tmp_path / "compare.html"
    write_compare_page(out, targets_dir, baseline_root, candidate_root, modes=MODES)
    html = out.read_text()

    for stem in stems:
        assert stem in html  # row label, exercising spaces/parens verbatim

    # Every row: target original + (baseline, candidate) x len(MODES) cells.
    expected_audio_tags = len(stems) * (1 + 2 * len(MODES))
    assert html.count("<audio") == expected_audio_tags
    assert "<td class='miss'>-</td>" not in html
    # Column headers must unambiguously distinguish baseline vs candidate.
    for mode in MODES:
        assert f"baseline {mode}" in html
        assert f"candidate {mode}" in html


def test_missing_render_yields_placeholder_cell_not_crash(tmp_path):
    stems = ["Mario Break Brick"]
    targets_dir, baseline_root, candidate_root = _build_roots(tmp_path, stems)

    # Knock out one specific render to simulate a genuine eval gap.
    safe = _safe_stem("Mario Break Brick")
    missing = candidate_root / safe / "model_seeded" / "match.wav"
    missing.unlink()

    out = tmp_path / "compare.html"
    write_compare_page(out, targets_dir, baseline_root, candidate_root, modes=MODES)
    html = out.read_text()

    assert "Mario Break Brick" in html
    assert "<td class='miss'>-</td>" in html
    # The other three match cells for this target should still have audio,
    # so a real gap shows up as one missing cell, not a wiped-out row.
    expected_audio_tags = 1 + 3  # target original + 3 present match cells
    assert html.count("<audio") == expected_audio_tags


def test_hard_slice_filters_to_annotated_subset(tmp_path, capsys):
    stems = [HARD_SLICE[0], HARD_SLICE[2], "Some Other Target"]
    targets_dir, baseline_root, candidate_root = _build_roots(tmp_path, stems)

    out = tmp_path / "compare.html"
    rc = main([
        "--targets", str(targets_dir),
        "--baseline", str(baseline_root),
        "--candidate", str(candidate_root),
        "-o", str(out),
        "--hard-slice",
    ])
    html = out.read_text()

    assert rc == 0
    assert HARD_SLICE[0] in html
    assert HARD_SLICE[2] in html
    assert "Some Other Target" not in html


def test_main_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--baseline" in out
    assert "--candidate" in out
    assert "--hard-slice" in out


def test_safe_stem_agrees_with_eval_targets():
    """invert.eval_targets._safe_stem is what actually names an eval run's
    per-target output directory. If this module's _safe_stem diverges,
    write_compare_page silently renders every match cell as a placeholder --
    see the task brief for the real-world case this caught: target stems
    with spaces/parens, e.g. "Mario 3 - jump (nes)"."""
    stems = [
        "Mario 3 - jump (nes)",
        "Mario 3 - jump (snes)",
        "Mario Break Brick",
        "mario 2 - jump",
        "chrono_trigger_leeneBell",
        "mega_man_iii_wily-fortress-appear",
        "foo.v2",
        "back\\slash",
        "a/b",
    ]
    for stem in stems:
        assert _safe_stem(stem) == eval_targets_safe_stem(stem), stem
