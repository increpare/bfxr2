"""Unlabeled real-audio manifests + feature dataset for spectral finetune."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from match.audio import load_audio, normalize_peak, trim_silence

from .features_pack import pack_features

AUDIO_EXTS = {".wav", ".ogg", ".flac", ".mp3"}

DEFAULT_CAPS: dict[str, int] = {
    "minecraft_legends_units": 2000,
    "RAREVGSFX 1+2": 2000,
    "kenney_voiceover-pack": 100,
    "kenney_voiceover-pack-fighter": 100,
}


def iter_audio_files(root: Path) -> list[Path]:
    root = Path(root)
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            out.append(p)
    return sorted(out)


def _pack_name(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(path.name)
    parts = rel.parts
    return parts[0] if len(parts) > 1 else root.name


def _stable_holdout(path: Path, holdout_frac: float) -> bool:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()
    # first 8 hex chars → [0, 1)
    u = int(digest[:8], 16) / 0xFFFFFFFF
    return u < holdout_frac


def _cap_for_pack(pack: str, caps: dict[str, int]) -> int | None:
    if pack in caps:
        return caps[pack]
    if "voiceover" in pack.lower():
        return caps.get("kenney_voiceover-pack", 100)
    return None


def build_manifest(
    roots: list[Path],
    *,
    out_json: Path,
    seed: int = 0,
    holdout_frac: float = 0.1,
    caps: dict[str, int] | None = None,
    exclude_roots: list[Path] | None = None,
) -> Path:
    """Enumerate audio, cap per pack, split train/holdout by path hash."""
    caps = dict(DEFAULT_CAPS if caps is None else caps)
    exclude_resolved = [Path(p).resolve() for p in (exclude_roots or [])]
    rng = np.random.default_rng(seed)

    by_pack: dict[str, list[tuple[Path, Path]]] = {}
    for root in roots:
        root = Path(root)
        for path in iter_audio_files(root):
            resolved = path.resolve()
            if any(
                resolved == ex or ex in resolved.parents for ex in exclude_resolved
            ):
                continue
            pack = _pack_name(path, root)
            by_pack.setdefault(pack, []).append((path, root))

    rows: list[dict] = []
    for pack, items in sorted(by_pack.items()):
        lim = _cap_for_pack(pack, caps)
        if lim is not None and len(items) > lim:
            idx = rng.choice(len(items), size=lim, replace=False)
            items = [items[i] for i in sorted(idx.tolist())]
        for path, _root in items:
            split = "holdout" if _stable_holdout(path, holdout_frac) else "train"
            rows.append(
                {
                    "path": str(path.resolve()),
                    "pack": pack,
                    "split": split,
                }
            )

    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return out_json


def load_wave(path: Path | str) -> np.ndarray:
    return normalize_peak(trim_silence(load_audio(path)))


class RealAudioFeatureDataset(Dataset):
    """Feature-only dataset from a real-audio manifest split."""

    def __init__(self, rows: list[dict], *, split: str = "train"):
        self.rows = [r for r in rows if r.get("split") == split]
        if not self.rows:
            raise ValueError(f"no rows with split={split!r}")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        n = len(self.rows)
        last_err: Exception | None = None
        for offset in range(n):
            row = self.rows[(idx + offset) % n]
            try:
                wave = load_wave(row["path"])
                feat, log_dur = pack_features(wave)
                return {
                    "features": torch.from_numpy(np.asarray(feat)).float(),
                    "log_duration": torch.tensor(float(log_dur), dtype=torch.float32),
                }
            except Exception as exc:  # noqa: BLE001 — skip bad files
                last_err = exc
                continue
        raise RuntimeError(f"failed to load any audio near index {idx}: {last_err}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Build real-audio finetune manifest")
    p.add_argument(
        "--roots",
        type=Path,
        nargs="+",
        required=True,
        help="Audio tree roots (e.g. targets_non_bfxr_big/tags)",
    )
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--holdout-frac", type=float, default=0.1)
    p.add_argument(
        "--exclude",
        type=Path,
        nargs="*",
        default=[],
        help="Paths to exclude (e.g. product tools/targets)",
    )
    args = p.parse_args(argv)
    path = build_manifest(
        args.roots,
        out_json=args.out,
        seed=args.seed,
        holdout_frac=args.holdout_frac,
        exclude_roots=list(args.exclude),
    )
    rows = json.loads(path.read_text())
    n_train = sum(1 for r in rows if r["split"] == "train")
    n_hold = sum(1 for r in rows if r["split"] == "holdout")
    print(f"wrote {path} ({len(rows)} files: {n_train} train / {n_hold} holdout)")


if __name__ == "__main__":
    main()
