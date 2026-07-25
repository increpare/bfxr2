"""Two-way listen comparison page: baseline objective vs candidate objective.

    PYTHONPATH=. uv run python -m match.listen_compare \\
        --targets targets/ \\
        --baseline invert/runs/gateA_legacy \\
        --candidate invert/runs/gateA_new \\
        -o invert/runs/gateB_listen.html --hard-slice

Metric scores are deliberately NOT shown: the point of this page is to decide
with ears, and a visible number anchors the verdict.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE
from .report import _spectrogram_data_uri, _wav_data_uri

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}

# The annotated hard slice from the v7 listen pass.
HARD_SLICE = (
    "Mario 1 - Jump", "Mario 2 - Throw", "Mario 3 - jump (nes)",
    "Mario 3 - jump (snes)", "Mario Break Brick", "mario 2 - jump",
    "mega_man_ii_one-up", "mega_man_iii_cursor", "mega_man_ii_beam-out",
    "chrono_trigger_leeneBell",
)


def _safe_stem(stem: str) -> str:
    """Must match invert.eval_targets._safe_stem EXACTLY (see length_report.py):
    only strip path separators, KEEP spaces and parens. Real eval dirs are named
    e.g. "Mario 3 - jump (nes)"; mangling non-alnum characters silently yields a
    page with every match cell empty."""
    return stem.replace("/", "_").replace("\\", "_")


def _read(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(round(len(mono) * SAMPLE_RATE / rate))
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n), np.arange(len(mono)), mono
        ).astype(np.float32)
    return mono


def _cell(wave: np.ndarray | None) -> str:
    if wave is None or len(wave) == 0:
        return "<td class='miss'>-</td>"
    return (
        "<td>"
        f"<audio controls preload='none' src='{_wav_data_uri(wave)}'></audio>"
        f"<br><img src='{_spectrogram_data_uri(wave)}' alt=''>"
        "</td>"
    )


def write_compare_page(
    out: Path,
    targets_dir: Path,
    baseline_root: Path,
    candidate_root: Path,
    modes: tuple[str, ...] = ("one_shot", "model_seeded"),
    only: set[str] | None = None,
) -> None:
    head = "".join(
        f"<th>baseline {m}</th><th>candidate {m}</th>" for m in modes
    )
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        cells = [f"<td class='name'>{target_path.stem}</td>",
                 _cell(_read(target_path))]
        for mode in modes:
            for root in (baseline_root, candidate_root):
                cells.append(_cell(_read(root / safe / mode / "match.wav")))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Gate B - baseline vs candidate objective</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Gate B - baseline vs candidate objective</h1>"
        "<p>Is the candidate <b>acceptably better on structure failures</b> "
        "(note count, pitch direction, discrete vs glissando) without obvious "
        "new regressions or mutes? Scores are hidden on purpose.</p>"
        f"<table><tr><th>target</th><th>original</th>{head}</tr>"
        + "".join(rows) +
        "</table>"
    )


def write_arms_page(
    out: Path,
    key_out: Path,
    targets_dir: Path,
    arms: list[tuple[str, Path]],
    mode: str = "model_seeded",
    only: set[str] | None = None,
    shuffle_seed: int = 0,
) -> None:
    """Blind N-arm listen page: candidate columns are shuffled per row and
    labelled A/B/C..., with the mapping written to `key_out` instead of the
    page. Scores and arm names stay hidden so the listener cannot anchor."""
    letters = [chr(ord("A") + i) for i in range(len(arms))]
    key: dict[str, dict[str, str]] = {}
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        rng = random.Random(f"{shuffle_seed}:{target_path.stem}")
        order = list(arms)
        rng.shuffle(order)
        key[target_path.stem] = {
            letter: name for letter, (name, _) in zip(letters, order)
        }
        cells = [f"<td class='name'>{target_path.stem}</td>",
                 _cell(_read(target_path))]
        for _, root in order:
            cells.append(_cell(_read(root / safe / mode / "match.wav")))
        rows.append("<tr>" + "".join(cells) + "</tr>")

    head = "".join(f"<th>{letter}</th>" for letter in letters)
    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Headroom probe - blind arms</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Headroom probe - blind arms</h1>"
        "<p>Score each lettered column 0-5 against the original. Column order "
        "is <b>reshuffled on every row</b> and the arm names are withheld on "
        "purpose - do not guess which is which.</p>"
        f"<table><tr><th>target</th><th>original</th>{head}</tr>"
        + "".join(rows) +
        "</table>"
    )
    key_out.write_text(json.dumps(key, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.listen_compare")
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--hard-slice", action="store_true",
                   help="only the annotated hard targets from the v7 listen pass")
    args = p.parse_args(argv)

    write_compare_page(
        args.out, args.targets, args.baseline, args.candidate,
        only=set(HARD_SLICE) if args.hard_slice else None,
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
