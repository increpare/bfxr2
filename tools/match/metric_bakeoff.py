"""Fixed-library multi-metric nearest-neighbor bake-off.

    # 1) build short-biased library of N bfxr renders (C++ worker)
    uv run python -m match.metric_bakeoff build-lib -o metric_lib/ --n 5000

    # 2) rank every target against the library under each metric
    uv run python -m match.metric_bakeoff rank targets/ --lib metric_lib/ -o metric_compare/

    open metric_compare/index.html
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from .alt_metrics import ZimtohrliMetric, make_metric
from .audio import SAMPLE_RATE, prepare_target
from .bfxr_io import ParamSpace, write_bfxr
from .objective import MatchObjective
from .optimizer import ENVELOPE_PARAMS, ENVELOPE_SAMPLES_PER_UNIT, RENDER_SEED, SQUARE_ONLY_PARAMS
from .renderer import BfxrRenderer
from .report import _spectrogram_data_uri, _wav_data_uri

AUDIO_EXTS = {".wav", ".flac", ".ogg", ".aif", ".aiff", ".mp3"}
METRICS = ("current", "harmonic", "zimtohrli", "clap")
# hard cap on envelope length for short-biased library (~0.55s)
LIB_CAP_SAMPLES = 0.55 * SAMPLE_RATE


# ---------------------------------------------------------------------------
# Library sampling / I/O
# ---------------------------------------------------------------------------

def sample_short_unit(rng: np.random.Generator, space: ParamSpace) -> np.ndarray:
    """Uniform unit cube with short-biased envelopes (Beta toward zero)."""
    unit = rng.random(space.dim)
    for name in ENVELOPE_PARAMS:
        i = space.names.index(name)
        unit[i] = float(rng.beta(1.2, 6.0))  # peaks near 0
    return unit


def params_for_lib(space: ParamSpace, unit: np.ndarray, wave_type: int) -> dict:
    params = space.params_dict(unit, wave_type)
    if wave_type != 0:
        for name in SQUARE_ONLY_PARAMS:
            i = space.names.index(name)
            params[name] = float(space.defaults[i])
    total = sum(params[n] ** 2 * ENVELOPE_SAMPLES_PER_UNIT for n in ENVELOPE_PARAMS)
    if total > LIB_CAP_SAMPLES:
        scale = float(np.sqrt(LIB_CAP_SAMPLES / total))
        for n in ENVELOPE_PARAMS:
            params[n] *= scale
    return params


def build_lib(out: Path, n: int, seed: int, jobs: int | None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    space = ParamSpace()
    rng = np.random.default_rng(seed)
    wave_types = sorted(space.wave_types)
    # stratify by wave type
    base, rem = divmod(n, len(wave_types))
    wt_list: list[int] = []
    for i, wt in enumerate(wave_types):
        wt_list.extend([wt] * (base + (1 if i < rem else 0)))
    rng.shuffle(wt_list)

    units = np.stack([sample_short_unit(rng, space) for _ in range(n)])
    params_list = [params_for_lib(space, units[i], wt_list[i]) for i in range(n)]

    print(f"rendering {n} library sounds…", file=sys.stderr)
    t0 = time.perf_counter()
    with BfxrRenderer(jobs=jobs) as renderer:
        waves = renderer.render_batch(params_list, seeds=RENDER_SEED)
    # drop failed renders by resampling replacements
    failed = [i for i, w in enumerate(waves) if w is None or len(w) == 0]
    if failed:
        print(f"  {len(failed)} failed, resampling…", file=sys.stderr)
        with BfxrRenderer(jobs=jobs) as renderer:
            for i in failed:
                for _ in range(8):
                    units[i] = sample_short_unit(rng, space)
                    params_list[i] = params_for_lib(space, units[i], wt_list[i])
                    w = renderer.render(params_list[i], seed=RENDER_SEED)
                    if w is not None and len(w) > 0:
                        waves[i] = w
                        break
                if waves[i] is None or len(waves[i]) == 0:
                    raise RuntimeError(f"could not render library slot {i}")

    # pack audio
    lengths = np.array([len(w) for w in waves], dtype=np.int32)
    offsets = np.zeros(n + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lengths)
    audio = np.concatenate([np.asarray(w, dtype=np.float32) for w in waves])
    np.save(out / "units.npy", units.astype(np.float64))
    np.save(out / "wave_types.npy", np.asarray(wt_list, dtype=np.int32))
    np.save(out / "lengths.npy", lengths)
    np.save(out / "offsets.npy", offsets)
    audio.tofile(out / "audio.f32")
    (out / "params.jsonl").write_text(
        "\n".join(json.dumps(p, separators=(",", ":")) for p in params_list) + "\n"
    )
    meta = {
        "n": n,
        "seed": seed,
        "render_seed": RENDER_SEED,
        "sample_rate": SAMPLE_RATE,
        "cap_seconds": LIB_CAP_SAMPLES / SAMPLE_RATE,
        "envelope_bias": "beta(1.2, 6.0) + cap",
        "dim": space.dim,
        "wave_types": wave_types,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
        "mean_seconds": float(lengths.mean() / SAMPLE_RATE),
        "p95_seconds": float(np.percentile(lengths, 95) / SAMPLE_RATE),
    }
    (out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"wrote {out}  mean={meta['mean_seconds']:.3f}s  "
          f"p95={meta['p95_seconds']:.3f}s  in {meta['elapsed_seconds']}s",
          file=sys.stderr)
    return 0


def load_library(lib: Path) -> tuple[list[np.ndarray], list[dict], np.ndarray, dict]:
    meta = json.loads((lib / "manifest.json").read_text())
    n = meta["n"]
    lengths = np.load(lib / "lengths.npy")
    offsets = np.load(lib / "offsets.npy")
    audio = np.fromfile(lib / "audio.f32", dtype=np.float32)
    waves = [audio[offsets[i] : offsets[i + 1]].copy() for i in range(n)]
    params = [json.loads(line) for line in (lib / "params.jsonl").read_text().splitlines() if line]
    wave_types = np.load(lib / "wave_types.npy")
    return waves, params, wave_types, meta


def _pack_waves(waves: list[np.ndarray], audio_path: Path, offsets_path: Path) -> None:
    lengths = np.array([len(w) for w in waves], dtype=np.int32)
    offsets = np.zeros(len(waves) + 1, dtype=np.int64)
    offsets[1:] = np.cumsum(lengths)
    np.concatenate([np.asarray(w, dtype=np.float32) for w in waves]).tofile(audio_path)
    np.save(offsets_path, offsets)


def _unpack_waves(audio_path: Path, offsets_path: Path) -> list[np.ndarray]:
    offsets = np.load(offsets_path)
    audio = np.fromfile(audio_path, dtype=np.float32)
    return [audio[offsets[i] : offsets[i + 1]].copy() for i in range(len(offsets) - 1)]


def load_or_build_48k(lib: Path, waves: list[np.ndarray]) -> list[np.ndarray]:
    audio_path, offsets_path = lib / "audio_48k.f32", lib / "offsets_48k.npy"
    if audio_path.exists() and offsets_path.exists():
        print("  loaded cached audio_48k.f32", file=sys.stderr)
        return _unpack_waves(audio_path, offsets_path)
    print("  resampling library → 48k (once, disk-cached)…", file=sys.stderr)
    lib_48k = ZimtohrliMetric.resample_library(waves)
    _pack_waves(lib_48k, audio_path, offsets_path)
    return lib_48k


# ---------------------------------------------------------------------------
# Ranking + HTML
# ---------------------------------------------------------------------------

def list_targets(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        f for f in path.iterdir()
        if f.suffix.lower() in AUDIO_EXTS
        and not f.name.startswith(".")
        and not f.name.lower().endswith(".bfxr.wav")
    )


def rank_targets(
    targets_dir: Path,
    lib: Path,
    out: Path,
    metrics: list[str],
    top_k: int,
) -> int:
    waves, params, wave_types, meta = load_library(lib)
    space = ParamSpace()
    out.mkdir(parents=True, exist_ok=True)
    targets = list_targets(targets_dir)
    if not targets:
        print("no targets", file=sys.stderr)
        return 1

    # Shared / per-metric library caches — compute once, reuse for every target.
    need_48k = any(m in metrics for m in ("zimtohrli", "clap"))
    lib_48k: list[np.ndarray] | None = None
    lib_48k_len: int | None = None
    if need_48k:
        print("init shared 48k library…", file=sys.stderr)
        lib_48k = load_or_build_48k(lib, waves)

    lib_side: dict = {}
    metric_objs = {}
    for name in metrics:
        print(f"init metric {name}…", file=sys.stderr)
        m = make_metric(name)
        metric_objs[name] = m
        cache = lib / f"emb_{name}.npy"
        if name == "current":
            pt = lib / "cache_current.pt"
            if pt.exists():
                import torch
                lib_side[name] = torch.load(pt, weights_only=False)
                print(f"  loaded cached {pt.name}", file=sys.stderr)
            else:
                print("  analyzing library (current)…", file=sys.stderr)
                lib_side[name] = MatchObjective.precompute_candidates(waves)
                import torch
                torch.save(lib_side[name], pt)
        elif name in ("clap", "harmonic") and cache.exists():
            lib_side[name] = np.load(cache)
            print(f"  loaded cached {cache.name}", file=sys.stderr)
        elif name == "clap":
            emb = m.embed_library(waves, lib_48k=lib_48k)
            np.save(cache, emb)
            lib_side[name] = emb
        elif name == "harmonic":
            print("  embedding library (harmonic)…", file=sys.stderr)
            emb = m.embed_library(waves)
            np.save(cache, emb)
            lib_side[name] = emb
        elif name == "zimtohrli":
            assert lib_48k is not None
            print("  padding library to equal length…", file=sys.stderr)
            padded, lib_48k_len = ZimtohrliMetric.pad_library_equal(lib_48k)
            lib_side[name] = padded
            lib_48k = padded  # reuse padded form for any later consumer
        else:
            lib_side[name] = None

    index_rows = []
    for ti, tpath in enumerate(targets):
        print(f"\n=== [{ti + 1}/{len(targets)}] {tpath.name} ===", file=sys.stderr)
        target = prepare_target(tpath)
        stem = tpath.stem
        sub = out / stem
        sub.mkdir(parents=True, exist_ok=True)
        report_path = sub / "report.json"
        html_path = sub / "index.html"
        if report_path.exists() and set(json.loads(report_path.read_text()).get("metrics", {})) >= set(metrics):
            report = json.loads(report_path.read_text())
            if not html_path.exists():
                print("  regenerating HTML from cached report…", file=sys.stderr)
                write_compare_html(html_path, stem, target, waves, report["metrics"], space)
            else:
                print("  skip (already ranked)", file=sys.stderr)
            index_rows.append(report)
            continue

        sf.write(sub / "target.wav", target, SAMPLE_RATE, subtype="PCM_16")

        per_metric = {}
        for name in metrics:
            m = metric_objs[name]
            t0 = time.perf_counter()
            if name == "current":
                dists = m.distances_to_library(target, waves, lib_cache=lib_side[name])
            elif name in ("clap", "harmonic"):
                dists = m.distances_to_library(target, waves, lib_emb=lib_side[name])
            elif name == "zimtohrli":
                dists = m.distances_to_library(
                    target, waves, lib_48k=lib_side[name], lib_len=lib_48k_len
                )
            else:
                dists = m.distances_to_library(target, waves)
            order = np.argsort(dists)
            best = []
            for rank, idx in enumerate(order[:top_k], start=1):
                idx = int(idx)
                stem_m = f"{name}_match" if rank == 1 else f"{name}_match_{rank}"
                wave = waves[idx]
                sf.write(sub / f"{stem_m}.wav", wave, SAMPLE_RATE, subtype="PCM_16")
                write_bfxr(sub / f"{stem_m}.bfxr", params[idx], file_name=f"{stem}_{stem_m}")
                best.append({
                    "rank": rank,
                    "lib_index": idx,
                    "distance": float(dists[idx]),
                    "wave_type": int(wave_types[idx]),
                    "wave_type_name": space.wave_type_names[int(wave_types[idx])],
                    "file": f"{stem_m}.wav",
                    "bfxr": f"{stem_m}.bfxr",
                })
            per_metric[name] = {
                "elapsed_seconds": round(time.perf_counter() - t0, 2),
                "best": best,
            }
            print(f"  {name}: best={best[0]['distance']:.4f} "
                  f"({best[0]['wave_type_name']}) in {per_metric[name]['elapsed_seconds']}s",
                  file=sys.stderr)

        report = {
            "target": str(tpath),
            "stem": stem,
            "lib": str(lib),
            "lib_n": meta["n"],
            "metrics": per_metric,
        }
        (sub / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        write_compare_html(sub / "index.html", stem, target, waves, per_metric, space)
        index_rows.append(report)

    write_index_html(out / "index.html", index_rows)
    (out / "summary.json").write_text(json.dumps(index_rows, indent=2) + "\n")
    print(f"\nwrote {out / 'index.html'}", file=sys.stderr)
    return 0


def write_compare_html(
    path: Path,
    stem: str,
    target: np.ndarray,
    library: list[np.ndarray],
    per_metric: dict,
    space: ParamSpace,
) -> None:
    def block(title: str, wave: np.ndarray, meta: str) -> str:
        return f"""
<section class="card">
  <div class="head"><h2>{title}</h2><div class="meta">{meta}</div></div>
  <audio controls src="{_wav_data_uri(wave)}"></audio>
  <img src="{_spectrogram_data_uri(wave)}" alt="">
</section>"""

    sections = [block("Original", target, stem)]
    for name in METRICS:
        if name not in per_metric:
            continue
        b = per_metric[name]["best"][0]
        wave = library[b["lib_index"]]
        meta = (f"distance {b['distance']:.4f} · {b['wave_type_name']} · "
                f"lib#{b['lib_index']}")
        sections.append(block(f"Best — {name}", wave, meta))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{stem} — metric compare</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: "IBM Plex Sans", system-ui, sans-serif; margin: 0;
        background: #12141a; color: #e6e8ef; }}
header {{ padding: 1.5rem 2rem; border-bottom: 1px solid #2a2e3a; }}
header a {{ color: #8eb4ff; }}
h1 {{ margin: 0 0 .3rem; font-size: 1.4rem; font-weight: 600; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
         gap: 1rem; padding: 1.5rem 2rem 3rem; }}
.card {{ background: #1a1d27; border: 1px solid #2a2e3a; border-radius: 6px;
         padding: 1rem; display: flex; flex-direction: column; gap: .7rem; }}
.card h2 {{ margin: 0; font-size: 1rem; font-weight: 600; }}
.meta {{ color: #9aa3b5; font-size: .8rem; }}
.card img {{ width: 100%; border-radius: 3px; background: #0d0f14; }}
audio {{ width: 100%; }}
</style></head><body>
<header>
  <h1>{stem}</h1>
  <div><a href="../index.html">← all targets</a> · same 5000-sound library, nearest under each metric</div>
</header>
<div class="grid">
{''.join(sections)}
</div>
</body></html>"""
    path.write_text(html)


def write_index_html(path: Path, rows: list[dict]) -> None:
    trs = []
    for r in rows:
        cells = [f"<td><a href='{r['stem']}/index.html'>{r['stem']}</a></td>"]
        for name in METRICS:
            if name not in r["metrics"]:
                cells.append("<td>—</td>")
                continue
            b = r["metrics"][name]["best"][0]
            cells.append(
                f"<td>{b['wave_type_name']}<br>"
                f"<span class='d'>{b['distance']:.3f}</span></td>"
            )
        trs.append("<tr>" + "".join(cells) + "</tr>")
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>metric compare</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: "IBM Plex Sans", system-ui, sans-serif; margin: 2rem;
        background: #12141a; color: #e6e8ef; }}
h1 {{ font-size: 1.5rem; font-weight: 600; }}
p {{ color: #9aa3b5; max-width: 42rem; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1.5rem; }}
th, td {{ text-align: left; padding: .55rem .7rem; border-bottom: 1px solid #2a2e3a;
          vertical-align: top; font-size: .92rem; }}
th {{ color: #9aa3b5; font-weight: 500; }}
a {{ color: #8eb4ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.d {{ color: #c4a35a; font-variant-numeric: tabular-nums; }}
</style></head><body>
<h1>Metric compare</h1>
<p>Each target is matched against the same fixed library of short-biased bfxr
renders. Columns show the nearest library sound under each metric (wave type +
distance). Click a target to listen.</p>
<table>
<tr><th>target</th>{''.join(f'<th>{m}</th>' for m in METRICS)}</tr>
{''.join(trs)}
</table>
</body></html>"""
    path.write_text(html)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="metric_bakeoff")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-lib", help="sample + render short-biased library")
    b.add_argument("-o", "--out", type=Path, default=Path("metric_lib"))
    b.add_argument("--n", type=int, default=5000)
    b.add_argument("--seed", type=int, default=0)
    b.add_argument("--jobs", type=int, default=None)

    r = sub.add_parser("rank", help="nearest-neighbor each target under each metric")
    r.add_argument("targets", type=Path)
    r.add_argument("--lib", type=Path, default=Path("metric_lib"))
    r.add_argument("-o", "--out", type=Path, default=Path("metric_compare"))
    r.add_argument("--metrics", type=str, default=",".join(METRICS))
    r.add_argument("--top-k", type=int, default=1)

    args = p.parse_args(argv)
    if args.cmd == "build-lib":
        return build_lib(args.out, args.n, args.seed, args.jobs)
    metrics = [m.strip() for m in args.metrics.split(",") if m.strip()]
    return rank_targets(args.targets, args.lib, args.out, metrics, args.top_k)


if __name__ == "__main__":
    raise SystemExit(main())
