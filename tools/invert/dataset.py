from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from match.bfxr_io import ParamSpace
from match.optimizer import RENDER_SEED
from match.renderer import BfxrRenderer

from .augment import maybe_augment
from .constants import (
    DATASET_VERSION,
    FEATURES_MEL_SCALE_IDX,
    N_CHANNELS,
    N_FRAMES,
    SILENCE_PEAK,
)
from .features_pack import pack_features
from .sampler import sample_example

FEATURE_NOTE = f"contours+blurred_logmel_scale{FEATURES_MEL_SCALE_IDX}"


def write_shard(path: Path | str, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def read_shard(path: Path | str) -> dict:
    return torch.load(Path(path), weights_only=False)


class InvertShardDataset(Dataset):
    """Loads shard_*.pt files into RAM and indexes examples across them."""

    def __init__(self, root: Path | str, *, max_shards: int | None = None):
        root = Path(root)
        paths = sorted(root.glob("shard_*.pt"))
        if max_shards is not None:
            paths = paths[:max_shards]
        if not paths:
            raise FileNotFoundError(f"no shard_*.pt under {root}")

        features: list[torch.Tensor] = []
        log_duration: list[torch.Tensor] = []
        unit: list[torch.Tensor] = []
        wave_type: list[torch.Tensor] = []
        class_idx: list[torch.Tensor] = []
        for p in paths:
            shard = read_shard(p)
            features.append(shard["features"])
            log_duration.append(shard["log_duration"])
            unit.append(shard["unit"])
            wave_type.append(shard["wave_type"])
            class_idx.append(shard["class_idx"])

        self.features = torch.cat(features, dim=0)
        self.log_duration = torch.cat(log_duration, dim=0)
        self.unit = torch.cat(unit, dim=0)
        self.wave_type = torch.cat(wave_type, dim=0)
        self.class_idx = torch.cat(class_idx, dim=0)

    def __len__(self) -> int:
        return int(self.features.shape[0])

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "features": self.features[idx],
            "log_duration": self.log_duration[idx],
            "unit": self.unit[idx],
            "wave_type": self.wave_type[idx],
            "class_idx": self.class_idx[idx],
        }


def _is_bad_wave(wave: np.ndarray | None) -> bool:
    if wave is None or len(wave) == 0:
        return True
    return float(np.max(np.abs(wave))) < SILENCE_PEAK


def _stratified_wave_types(space: ParamSpace, n: int, rng: np.random.Generator) -> list[int]:
    wave_types = sorted(space.wave_types)
    base, rem = divmod(n, len(wave_types))
    wt_list: list[int] = []
    for i, wt in enumerate(wave_types):
        wt_list.extend([wt] * (base + (1 if i < rem else 0)))
    rng.shuffle(wt_list)
    return wt_list


def _render_accepted(
    space: ParamSpace,
    rng: np.random.Generator,
    renderer: BfxrRenderer,
    force_wave_type: int,
) -> tuple[dict, np.ndarray]:
    for _ in range(8):
        ex = sample_example(space, rng=rng, force_wave_type=force_wave_type)
        params = space.params_dict(ex["unit"], ex["wave_type"])
        wave = renderer.render(params, seed=RENDER_SEED)
        if not _is_bad_wave(wave):
            assert wave is not None
            return ex, wave
    raise RuntimeError(f"could not render accepted wave for wave_type={force_wave_type}")


def generate_shards(
    out_dir: Path | str,
    n: int,
    seed: int,
    jobs: int | None,
    shard_size: int = 2048,
    augment_p: float = 0.5,
) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    space = ParamSpace()
    rng = np.random.default_rng(seed)
    wt_list = _stratified_wave_types(space, n, rng)

    print(f"rendering {n} invert examples…", file=sys.stderr)
    examples: list[dict] = []
    waves: list[np.ndarray | None] = [None] * n
    params_list: list[dict] = []

    for wt in wt_list:
        ex = sample_example(space, rng=rng, force_wave_type=wt)
        examples.append(ex)
        params_list.append(space.params_dict(ex["unit"], ex["wave_type"]))

    with BfxrRenderer(jobs=jobs) as renderer:
        waves = renderer.render_batch(params_list, seeds=RENDER_SEED)
        failed = [i for i, w in enumerate(waves) if _is_bad_wave(w)]
        if failed:
            print(f"  {len(failed)} failed/silent, resampling…", file=sys.stderr)
            for i in failed:
                ex, wave = _render_accepted(space, rng, renderer, wt_list[i])
                examples[i] = ex
                waves[i] = wave

    feat_buf: list[np.ndarray] = []
    log_dur_buf: list[float] = []
    unit_buf: list[np.ndarray] = []
    wave_type_buf: list[int] = []
    class_idx_buf: list[int] = []
    shard_idx = 0
    written = 0

    def flush() -> None:
        nonlocal shard_idx, written, feat_buf, log_dur_buf, unit_buf, wave_type_buf, class_idx_buf
        if not feat_buf:
            return
        m = len(feat_buf)
        payload = {
            "features": torch.from_numpy(np.stack(feat_buf)).half(),
            "log_duration": torch.tensor(log_dur_buf, dtype=torch.float32),
            "unit": torch.from_numpy(np.stack(unit_buf).astype(np.float32)),
            "wave_type": torch.tensor(wave_type_buf, dtype=torch.long),
            "class_idx": torch.tensor(class_idx_buf, dtype=torch.long),
            "meta": {
                "dataset_version": DATASET_VERSION,
                "n": m,
                "feature_note": FEATURE_NOTE,
                "render_seed": RENDER_SEED,
            },
        }
        write_shard(out_dir / f"shard_{shard_idx:04d}.pt", payload)
        written += m
        shard_idx += 1
        feat_buf = []
        log_dur_buf = []
        unit_buf = []
        wave_type_buf = []
        class_idx_buf = []

    for i in range(n):
        wave = waves[i]
        assert wave is not None
        aug = maybe_augment(wave, rng=rng, p=augment_p)
        feat, log_dur = pack_features(aug)
        assert feat.shape == (N_CHANNELS, N_FRAMES)
        feat_buf.append(feat)
        log_dur_buf.append(log_dur)
        unit_buf.append(examples[i]["unit"])
        wave_type_buf.append(int(examples[i]["wave_type"]))
        class_idx_buf.append(int(examples[i]["class_idx"]))
        if len(feat_buf) >= shard_size:
            flush()
    flush()

    manifest = {
        "n": written,
        "seed": seed,
        "dataset_version": DATASET_VERSION,
        "feature_note": FEATURE_NOTE,
        "render_seed": RENDER_SEED,
        "shard_size": shard_size,
        "augment_p": augment_p,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate invert training feature shards")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--jobs", type=int, default=None)
    p.add_argument("--shard-size", type=int, default=2048)
    p.add_argument("--augment-p", type=float, default=0.5)
    args = p.parse_args(argv)
    generate_shards(
        args.out,
        n=args.n,
        seed=args.seed,
        jobs=args.jobs,
        shard_size=args.shard_size,
        augment_p=args.augment_p,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
