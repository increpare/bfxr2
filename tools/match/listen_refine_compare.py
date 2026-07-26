"""Listen page: original vs raw one-shot vs refined one-shot vs seeded.

    PYTHONPATH=. uv run python -m match.listen_refine_compare \\
        --targets targets/ \\
        --raw invert/runs/tt_raw \\
        --refined invert/runs/tt_refined \\
        --seeded invert/runs/tt_seeded \\
        -o invert/runs/tt_refine_listen.html --hard-slice
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE
from .listen_compare import HARD_SLICE, _safe_stem
from .report import _spectrogram_data_uri, _wav_data_uri

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}


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


def write_page(
    out: Path,
    targets_dir: Path,
    raw_root: Path,
    refined_root: Path,
    seeded_root: Path,
    *,
    only: set[str] | None = None,
) -> None:
    rows = []
    for target_path in sorted(targets_dir.iterdir()):
        if target_path.suffix.lower() not in AUDIO_EXTS:
            continue
        if only is not None and target_path.stem not in only:
            continue
        safe = _safe_stem(target_path.stem)
        cells = [
            f"<td class='name'>{target_path.stem}</td>",
            _cell(_read(target_path)),
            _cell(_read(raw_root / safe / "one_shot" / "match.wav")),
            _cell(_read(refined_root / safe / "one_shot" / "match.wav")),
            _cell(_read(seeded_root / safe / "model_seeded" / "match.wav")),
        ]
        rows.append("<tr>" + "".join(cells) + "</tr>")

    out.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Test-time refine - raw vs refined one-shot</title>"
        "<style>"
        "body{font:14px system-ui;margin:20px}"
        "table{border-collapse:collapse}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top}"
        ".name{font-weight:600;white-space:nowrap}"
        ".miss{color:#999;text-align:center}"
        "img{display:block;width:220px}"
        "audio{width:220px}"
        "</style>"
        "<h1>Test-time refine — raw vs refined one-shot</h1>"
        "<p>Is the <b>refined</b> one-shot acceptably better than <b>raw</b>? "
        "Seeded is the ceiling reference. Scores hidden on purpose.</p>"
        "<table><tr><th>target</th><th>original</th>"
        "<th>raw one-shot</th><th>refined one-shot</th>"
        "<th>model seeded</th></tr>"
        + "".join(rows) +
        "</table>"
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="match.listen_refine_compare")
    p.add_argument("--targets", type=Path, required=True)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--refined", type=Path, required=True)
    p.add_argument("--seeded", type=Path, required=True)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--hard-slice", action="store_true")
    args = p.parse_args(argv)
    write_page(
        args.out, args.targets, args.raw, args.refined, args.seeded,
        only=set(HARD_SLICE) if args.hard_slice else None,
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
