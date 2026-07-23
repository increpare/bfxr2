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
    SQUARE_ONLY,
)
from .features_pack import pack_features
from .sampler import sample_example, wave_type_index_map

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
            ver = shard.get("meta", {}).get("dataset_version")
            if ver != DATASET_VERSION:
                raise ValueError(
                    f"{p}: dataset_version {ver!r} != expected {DATASET_VERSION!r}"
                )
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

        manifest_path = root / "manifest.json"
        if manifest_path.exists() and max_shards is None:
            manifest = json.loads(manifest_path.read_text())
            expected = int(manifest["n"])
            got = int(self.features.shape[0])
            if got != expected:
                raise ValueError(
                    f"{root}: loaded {got} examples but manifest.json has n={expected}"
                )

    def __len__(self) -> int:
        return int(self.features.shape[0])

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        # Shards store features as float16; model weights are float32.
        return {
            "features": self.features[idx].float(),
            "log_duration": self.log_duration[idx].float(),
            "unit": self.unit[idx].float(),
            "wave_type": self.wave_type[idx],
            "class_idx": self.class_idx[idx],
        }


def _is_acceptable_wave(wave: np.ndarray | None) -> bool:
    """True if wave is usable training audio (finite, non-silent, non-empty)."""
    if wave is None or len(wave) == 0:
        return False
    w = np.asarray(wave)
    if not np.isfinite(w).all():
        return False
    peak = float(np.max(np.abs(w)))
    if not np.isfinite(peak) or peak < SILENCE_PEAK:
        return False
    return True


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
    *,
    max_tries: int = 64,
) -> tuple[dict, np.ndarray]:
    """Resample until a non-silent render lands. Biases toward defaults after a few misses."""
    for attempt in range(max_tries):
        # Early tries keep the normal mix; later tries drop full-uniform (quieter mush).
        uniform_frac = 0.2 if attempt < 8 else 0.0
        ex = sample_example(
            space, rng=rng, force_wave_type=force_wave_type, uniform_frac=uniform_frac
        )
        params = space.params_dict(ex["unit"], ex["wave_type"])
        wave = renderer.render(params, seed=RENDER_SEED)
        if _is_acceptable_wave(wave):
            assert wave is not None
            return ex, wave

    # Last resort: pinned defaults for this wave type (almost always audible).
    unit = space.defaults_unit().copy()
    if force_wave_type != 0:
        du = space.defaults_unit()
        for name in SQUARE_ONLY:
            unit[space.names.index(name)] = float(du[space.names.index(name)])
    params = space.params_dict(unit, force_wave_type)
    wave = renderer.render(params, seed=RENDER_SEED)
    if _is_acceptable_wave(wave):
        assert wave is not None
        id_to_cls, _ = wave_type_index_map(space)
        return {
            "unit": unit.astype(np.float64),
            "wave_type": int(force_wave_type),
            "class_idx": id_to_cls[int(force_wave_type)],
        }, wave
    raise RuntimeError(f"could not render accepted wave for wave_type={force_wave_type}")


def _clear_out_dir(out_dir: Path) -> None:
    for p in out_dir.glob("shard_*.pt"):
        p.unlink()
    manifest = out_dir / "manifest.json"
    if manifest.exists():
        manifest.unlink()


def _pack_shard_payload(
    examples: list[dict],
    waves: list[np.ndarray | None],
    rng: np.random.Generator,
    augment_p: float,
) -> dict:
    """Augment + pack one chunk of waves into a shard payload (float16 features)."""
    feat_buf: list[np.ndarray] = []
    log_dur_buf: list[float] = []
    unit_buf: list[np.ndarray] = []
    wave_type_buf: list[int] = []
    class_idx_buf: list[int] = []
    for i, ex in enumerate(examples):
        wave = waves[i]
        assert wave is not None
        aug = maybe_augment(wave, rng=rng, p=augment_p)
        feat, log_dur = pack_features(aug)
        assert feat.shape == (N_CHANNELS, N_FRAMES)
        feat_buf.append(feat)
        log_dur_buf.append(log_dur)
        unit_buf.append(ex["unit"])
        wave_type_buf.append(int(ex["wave_type"]))
        class_idx_buf.append(int(ex["class_idx"]))
    m = len(feat_buf)
    return {
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


def generate_shards(
    out_dir: Path | str,
    n: int,
    seed: int,
    jobs: int | None,
    shard_size: int = 2048,
    augment_p: float = 0.5,
) -> None:
    """Sample/render/pack in shard-sized chunks so peak RAM stays O(shard_size)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    _clear_out_dir(out_dir)
    space = ParamSpace()
    rng = np.random.default_rng(seed)
    wt_list = _stratified_wave_types(space, n, rng)

    print(f"rendering {n} invert examples (chunk={shard_size})…", file=sys.stderr)
    shard_idx = 0
    written = 0

    with BfxrRenderer(jobs=jobs) as renderer:
        for chunk_start in range(0, n, shard_size):
            chunk_wts = wt_list[chunk_start : chunk_start + shard_size]
            examples: list[dict] = []
            params_list: list[dict] = []
            for wt in chunk_wts:
                ex = sample_example(space, rng=rng, force_wave_type=wt)
                examples.append(ex)
                params_list.append(space.params_dict(ex["unit"], ex["wave_type"]))

            waves = renderer.render_batch(params_list, seeds=RENDER_SEED)
            del params_list
            failed = [i for i, w in enumerate(waves) if not _is_acceptable_wave(w)]
            if failed:
                print(
                    f"  shard {shard_idx}: {len(failed)} failed/silent, resampling…",
                    file=sys.stderr,
                )
                for i in failed:
                    ex, wave = _render_accepted(space, rng, renderer, chunk_wts[i])
                    examples[i] = ex
                    waves[i] = wave

            payload = _pack_shard_payload(examples, waves, rng, augment_p)
            del waves, examples
            write_shard(out_dir / f"shard_{shard_idx:04d}.pt", payload)
            written += int(payload["meta"]["n"])
            print(
                f"  wrote shard_{shard_idx:04d}.pt ({written}/{n})",
                file=sys.stderr,
            )
            shard_idx += 1
            del payload

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
