from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from match.bfxr_io import ParamSpace

from .constants import SQUARE_ONLY
from .dataset import InvertShardDataset
from .model import InverseModel
from .sampler import wave_type_index_map


def invert_loss(
    out: dict[str, torch.Tensor],
    unit_tgt: torch.Tensor,
    wave_types: torch.Tensor,
    class_idx: torch.Tensor,
    space: ParamSpace,
    version: int = 1,
) -> tuple[torch.Tensor, dict[str, float]]:
    if version == 1:
        unit_pred = out["unit"]
    elif version == 2:
        b = torch.arange(unit_tgt.shape[0], device=unit_tgt.device)
        unit_pred = out["unit_per_class"][b, class_idx]
    else:
        raise ValueError(version)

    mask = torch.ones_like(unit_tgt)
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        mask[:, j] = (wave_types == 0).float()

    unit_mse = ((unit_pred - unit_tgt) ** 2 * mask).sum() / mask.sum().clamp(min=1)
    ce = F.cross_entropy(out["wavetype_logits"], class_idx.long())
    loss = unit_mse + ce
    parts = {
        "unit_mse": float(unit_mse.detach()),
        "ce": float(ce.detach()),
    }
    return loss, parts


def _default_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _split_indices(n: int, val_ratio: float = 0.05) -> tuple[list[int], list[int]]:
    n_val = max(1, int(math.ceil(n * val_ratio))) if n > 1 else 0
    n_train = n - n_val
    train_idx = list(range(n_train))
    val_idx = list(range(n_train, n))
    return train_idx, val_idx


def _run_epoch(
    model: InverseModel,
    loader: DataLoader,
    space: ParamSpace,
    device: torch.device,
    *,
    optimizer: torch.optim.Optimizer | None,
) -> dict[str, float]:
    train = optimizer is not None
    model.train(train)
    total_loss = 0.0
    total_unit = 0.0
    total_ce = 0.0
    n_batches = 0
    for batch in loader:
        x = batch["features"].to(device)
        log_dur = batch["log_duration"].to(device)
        unit = batch["unit"].to(device)
        wt = batch["wave_type"].to(device)
        cls = batch["class_idx"].to(device)

        if train:
            optimizer.zero_grad(set_to_none=True)

        out = model(x, log_dur)
        loss, parts = invert_loss(out, unit, wt, cls, space, version=model.version)

        if train:
            loss.backward()
            optimizer.step()

        total_loss += float(loss.detach())
        total_unit += parts["unit_mse"]
        total_ce += parts["ce"]
        n_batches += 1

    denom = max(n_batches, 1)
    return {
        "loss": total_loss / denom,
        "unit_mse": total_unit / denom,
        "ce": total_ce / denom,
    }


def train(
    data: Path,
    out: Path,
    *,
    epochs: int = 10,
    batch_size: int = 64,
    lr: float = 1e-3,
    version: int = 1,
    device: str | None = None,
    val_ratio: float = 0.05,
) -> Path:
    device_s = device or _default_device()
    device_t = torch.device(device_s)
    space = ParamSpace()
    _, cls_to_id = wave_type_index_map(space)
    wave_types_order = [cls_to_id[i] for i in range(len(cls_to_id))]

    ds = InvertShardDataset(data)
    train_idx, val_idx = _split_indices(len(ds), val_ratio=val_ratio)
    train_ds = Subset(ds, train_idx)
    val_ds = Subset(ds, val_idx) if val_idx else None

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = (
        DataLoader(val_ds, batch_size=batch_size, shuffle=False) if val_ds is not None else None
    )

    model = InverseModel(version=version).to(device_t)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "train_log.jsonl"
    best_path = out / "best.pt"
    best_val = float("inf")

    with log_path.open("w", encoding="utf-8") as log_f:
        for epoch in range(1, epochs + 1):
            train_metrics = _run_epoch(
                model, train_loader, space, device_t, optimizer=opt
            )
            if val_loader is not None:
                val_metrics = _run_epoch(
                    model, val_loader, space, device_t, optimizer=None
                )
                val_loss = val_metrics["loss"]
            else:
                val_metrics = train_metrics
                val_loss = train_metrics["loss"]

            row = {
                "epoch": epoch,
                "train": train_metrics,
                "val": val_metrics,
            }
            log_f.write(json.dumps(row) + "\n")
            log_f.flush()

            if val_loss < best_val:
                best_val = val_loss
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "version": version,
                        "space_names": list(space.names),
                        "wave_types_order": wave_types_order,
                        "best_val": best_val,
                    },
                    best_path,
                )

    return best_path


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Train InverseModel on invert shards")
    p.add_argument("--data", type=Path, required=True, help="Directory of shard_*.pt")
    p.add_argument("--out", type=Path, required=True, help="Output run directory")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--version", type=int, choices=(1, 2), default=1)
    p.add_argument(
        "--device",
        type=str,
        choices=("cpu", "mps", "cuda"),
        default=None,
        help="Default: mps if available else cpu",
    )
    args = p.parse_args(argv)
    best = train(
        args.data,
        args.out,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        version=args.version,
        device=args.device,
    )
    print(f"wrote {best}")


if __name__ == "__main__":
    main()
