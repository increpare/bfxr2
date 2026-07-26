import numpy as np
import pytest
import soundfile as sf

from invert.eval_targets import _safe_stem as eval_targets_safe_stem
from match.audio import SAMPLE_RATE
from match.length_report import _read, _safe_stem, length_ratios, main

FRAME = int(SAMPLE_RATE * 10 / 1000)  # 441 samples/frame; keep test signals as
# exact multiples of this so trim_silence never clips a partial trailing frame.


def _const(amplitude: float, seconds: float) -> np.ndarray:
    n = int(round(seconds * SAMPLE_RATE))
    assert n % FRAME == 0, "keep test durations frame-aligned"
    return np.full(n, amplitude, dtype=np.float32)


def _write(path, x: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    # Explicit FLOAT subtype: sf.write's default WAV subtype is 16-bit PCM,
    # which quantizes our known amplitudes enough to break exact assertions.
    sf.write(path, x, rate, subtype="FLOAT")


def _build_eval_root(tmp_path, mode="one_shot"):
    """Eval-root/targets fixture with three known cases:

    - "exact": candidate identical to target -> duration x1.0, energy x1.0.
    - "partial": candidate 0.7x the duration at half amplitude -> duration
      x0.7, energy x0.175 (not a collapse).
    - "collapse": candidate 0.2x the duration at double amplitude -> duration
      x0.2 (COLLAPSE), energy x0.8 (looks "acceptable" despite collapsing;
      this is exactly the failure mode the tool exists to surface).
    """
    targets_dir = tmp_path / "targets"
    eval_root = tmp_path / "eval_root"
    targets_dir.mkdir()

    cases = {
        "exact": (0.5, 1.0, 0.5, 1.0),
        "partial": (0.4, 1.0, 0.2, 0.7),
        "collapse": (0.3, 1.0, 0.6, 0.2),
    }
    for stem, (t_amp, t_dur, c_amp, c_dur) in cases.items():
        _write(targets_dir / f"{stem}.wav", _const(t_amp, t_dur))
        cand_dir = eval_root / _safe_stem(stem) / mode
        cand_dir.mkdir(parents=True)
        _write(cand_dir / "match.wav", _const(c_amp, c_dur))

    return targets_dir, eval_root, cases


def test_length_ratios_computes_known_duration_and_energy_ratios(tmp_path):
    targets_dir, eval_root, _ = _build_eval_root(tmp_path)

    rows = length_ratios(eval_root, targets_dir, "one_shot")
    by_stem = {stem: (dur, energy) for stem, dur, energy in rows}

    assert set(by_stem) == {"exact", "partial", "collapse"}

    dur, energy = by_stem["exact"]
    assert dur == pytest.approx(1.0, abs=1e-6)
    assert energy == pytest.approx(1.0, abs=1e-6)

    dur, energy = by_stem["partial"]
    assert dur == pytest.approx(0.7, abs=1e-6)
    assert energy == pytest.approx(0.175, abs=1e-6)  # (0.2/0.4)**2 * 0.7

    dur, energy = by_stem["collapse"]
    assert dur == pytest.approx(0.2, abs=1e-6)
    assert energy == pytest.approx(0.8, abs=1e-6)  # (0.6/0.3)**2 * 0.2
    assert dur < 0.5  # exercises the COLLAPSE flag / histogram's [0, 0.5) bucket


def test_length_ratios_only_reads_requested_mode(tmp_path):
    targets_dir, eval_root, _ = _build_eval_root(tmp_path, mode="one_shot")

    # No renders exist under "model_seeded" for any target.
    rows = length_ratios(eval_root, targets_dir, "model_seeded")
    assert rows == []


def test_length_ratios_skips_targets_with_no_render(tmp_path):
    targets_dir = tmp_path / "targets"
    eval_root = tmp_path / "eval_root"
    targets_dir.mkdir()
    _write(targets_dir / "orphan.wav", _const(0.5, 1.0))
    # eval_root has no subdirectory for "orphan" at all.

    rows = length_ratios(eval_root, targets_dir, "one_shot")
    assert rows == []


def test_main_reports_no_matched_renders_clearly(tmp_path, capsys):
    targets_dir = tmp_path / "targets"
    eval_root = tmp_path / "eval_root"
    targets_dir.mkdir()
    eval_root.mkdir()
    _write(targets_dir / "lonely.wav", _const(0.5, 1.0))

    rc = main([
        "--eval-root", str(eval_root),
        "--targets", str(targets_dir),
        "--mode", "one_shot",
    ])
    out = capsys.readouterr().out

    assert rc == 1
    assert "no matched renders found" in out
    # The empty-result message must not look like a clean "0 collapsed" table.
    assert "collapsed" not in out


def test_main_prints_histogram_and_collapse_flag(tmp_path, capsys):
    targets_dir, eval_root, _ = _build_eval_root(tmp_path)

    rc = main([
        "--eval-root", str(eval_root),
        "--targets", str(targets_dir),
        "--mode", "one_shot",
    ])
    out = capsys.readouterr().out

    assert rc == 0
    assert "COLLAPSE" in out
    assert "collapsed (<0.5x): 1/3" in out


def test_read_resamples_to_sample_rate(tmp_path):
    other_rate = 22050
    seconds = 1.0
    x = np.full(int(other_rate * seconds), 0.4, dtype=np.float32)
    path = tmp_path / "low_rate.wav"
    _write(path, x, rate=other_rate)

    mono = _read(path)
    assert len(mono) == pytest.approx(SAMPLE_RATE * seconds, abs=1)
    assert float(mono.mean()) == pytest.approx(0.4, abs=1e-3)


def test_safe_stem_agrees_with_eval_targets():
    """invert.eval_targets._safe_stem is what actually names an eval run's
    per-target output directory. If this module's _safe_stem diverges,
    length_ratios silently finds zero renders (looks like "no data", is
    actually a bug) -- see task brief for the real-world case this caught:
    target stems with spaces/parens, e.g. "Mario 3 - jump (nes)"."""
    stems = [
        "Mario 3 - jump (nes)",
        "Mario World - Jump (reverb)",
        "chrono_trigger_leeneBell",
        "mega_man_iii_wily-fortress-appear",
        "foo.v2",
        "back\\slash",
        "a/b",
    ]
    for stem in stems:
        assert _safe_stem(stem) == eval_targets_safe_stem(stem), stem
