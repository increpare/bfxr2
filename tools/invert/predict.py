"""Checkpoint → ranked .bfxr guesses for a target wav.

    cd tools && uv run python -m invert.predict target.wav --ckpt runs/v1/best.pt -o guesses/ --top-k 3
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F

from match.audio import prepare_target
from match.bfxr_io import ParamSpace, write_bfxr

from .constants import SQUARE_ONLY
from .features_pack import pack_features
from .model import InverseModel


def load_checkpoint(path: Path | str, device: str = "cpu") -> tuple[InverseModel, dict[str, Any]]:
    ckpt = torch.load(path, map_location=device, weights_only=False)
    version = int(ckpt["version"])
    model = InverseModel(version=version)
    model.load_state_dict(ckpt["model_state"])
    model.to(device)
    model.eval()
    meta = {
        "version": version,
        "wave_types_order": list(ckpt["wave_types_order"]),
        "space_names": list(ckpt["space_names"]),
    }
    return model, meta


def _pin_square_only(unit: np.ndarray, wave_type: int, space: ParamSpace) -> np.ndarray:
    out = np.asarray(unit, dtype=np.float64).copy()
    if wave_type != 0:
        defaults = space.defaults_unit()
        for name in SQUARE_ONLY:
            j = space.names.index(name)
            out[j] = float(defaults[j])
    return out


@torch.no_grad()
def predict_wave(
    model: InverseModel,
    meta: dict[str, Any],
    wave: np.ndarray,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    space = ParamSpace()
    if list(space.names) != list(meta["space_names"]):
        raise ValueError("checkpoint space_names do not match current ParamSpace")

    feat, log_dur = pack_features(wave)
    device = next(model.parameters()).device
    x = torch.from_numpy(feat).unsqueeze(0).to(device)
    log_duration = torch.tensor([log_dur], dtype=torch.float32, device=device)

    out = model(x, log_duration)
    probs = F.softmax(out["wavetype_logits"][0], dim=0)
    k = min(top_k, probs.numel())
    top_probs, top_idx = torch.topk(probs, k)

    wave_types_order = list(meta["wave_types_order"])
    version = int(meta["version"])
    guesses: list[dict[str, Any]] = []

    if version == 1:
        unit_shared = out["unit"][0].detach().cpu().numpy()
        for i in range(k):
            class_idx = int(top_idx[i].item())
            wave_type = int(wave_types_order[class_idx])
            unit = _pin_square_only(unit_shared, wave_type, space)
            guesses.append(
                {
                    "unit": unit.astype(np.float64),
                    "wave_type": wave_type,
                    "class_idx": class_idx,
                    "prob": float(top_probs[i].item()),
                }
            )
    elif version == 2:
        units = out["unit_per_class"][0].detach().cpu().numpy()
        for i in range(k):
            class_idx = int(top_idx[i].item())
            wave_type = int(wave_types_order[class_idx])
            unit = _pin_square_only(units[class_idx], wave_type, space)
            guesses.append(
                {
                    "unit": unit.astype(np.float64),
                    "wave_type": wave_type,
                    "class_idx": class_idx,
                    "prob": float(top_probs[i].item()),
                }
            )
    else:
        raise ValueError(version)

    return guesses


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Predict ranked bfxr guesses from a wav")
    p.add_argument("target", type=Path, help="target audio file")
    p.add_argument("--ckpt", type=Path, required=True, help="checkpoint .pt")
    p.add_argument("-o", "--out", type=Path, required=True, help="output directory")
    p.add_argument("--top-k", type=int, default=3)
    p.add_argument(
        "--device",
        type=str,
        choices=("cpu", "mps", "cuda"),
        default="cpu",
    )
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    model, meta = load_checkpoint(args.ckpt, device=args.device)
    wave = prepare_target(args.target)
    space = ParamSpace()
    guesses = predict_wave(model, meta, wave, top_k=args.top_k)

    for rank, g in enumerate(guesses, start=1):
        params = space.params_dict(g["unit"], g["wave_type"])
        stem = f"guess_{rank}"
        write_bfxr(args.out / f"{stem}.bfxr", params, file_name=f"{args.target.stem}_{stem}")
        print(
            f"{stem}.bfxr wave_type={g['wave_type']} "
            f"({space.wave_type_names[g['wave_type']]}) prob={g['prob']:.4f}"
        )


if __name__ == "__main__":
    main()
