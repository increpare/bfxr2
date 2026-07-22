"""Human-verification report: audio players + spectrograms, self-contained HTML."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from .audio import SAMPLE_RATE


def _wav_data_uri(wave: np.ndarray) -> str:
    buf = io.BytesIO()
    sf.write(buf, wave, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return "data:audio/wav;base64," + base64.b64encode(buf.getvalue()).decode()


def _spectrogram_data_uri(wave: np.ndarray) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import torch
    import torchaudio

    x = np.array(wave, dtype=np.float32, copy=True)
    if len(x) < 4096:  # reflect padding needs len > n_fft // 2
        x = np.pad(x, (0, 4096 - len(x)))
    mel = torchaudio.transforms.MelSpectrogram(
        sample_rate=SAMPLE_RATE, n_fft=2048, hop_length=256, n_mels=128,
        f_min=30.0, f_max=18000.0, power=2.0,
    )(torch.from_numpy(x).unsqueeze(0))[0]
    logmel = torch.log(mel + 1e-5).numpy()

    fig, ax = plt.subplots(figsize=(5, 2.2), dpi=100)
    vmin = -11.5
    vmax = float(max(logmel.max(), vmin + 1e-3))
    ax.imshow(logmel, origin="lower", aspect="auto", cmap="magma",
              vmin=vmin, vmax=vmax)
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(pad=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def write_html_report(
    path: Path | str,
    target_name: str,
    target_wave: np.ndarray,
    matches: list[dict],  # {"name", "wave", "score", "params"}
) -> None:
    """Write a self-contained report.html; requires matplotlib
    (uv sync --extra report)."""
    rows = [_row(f"target: {target_name}", target_wave, None, None)]
    for m in matches:
        rows.append(_row(m["name"], m["wave"], m["score"], m["params"]))
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>bfxr match: {target_name}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2em; background: #1b1b1f; color: #e8e8ea; }}
.row {{ display: flex; align-items: center; gap: 1.5em; margin-bottom: 1.2em;
        background: #26262c; border-radius: 8px; padding: 1em; }}
.row img {{ border-radius: 4px; }}
.label {{ min-width: 16em; }}
.label b {{ display: block; margin-bottom: 0.3em; }}
.score {{ color: #ffb454; }}
details {{ font-size: 0.8em; margin-top: 0.4em; color: #9a9aa4; }}
pre {{ white-space: pre-wrap; }}
</style></head><body>
<h1>wav&rarr;bfxr match: {target_name}</h1>
{''.join(rows)}
</body></html>"""
    Path(path).write_text(html)


def _row(name: str, wave: np.ndarray, score: float | None, params: dict | None) -> str:
    score_html = f'<span class="score">score {score:.4f}</span>' if score is not None else ""
    params_html = ""
    if params is not None:
        params_html = (f"<details><summary>params</summary><pre>"
                       f"{json.dumps(params, indent=1)}</pre></details>")
    return f"""<div class="row">
<div class="label"><b>{name}</b>{score_html}{params_html}</div>
<audio controls src="{_wav_data_uri(wave)}"></audio>
<img src="{_spectrogram_data_uri(wave)}">
</div>"""
