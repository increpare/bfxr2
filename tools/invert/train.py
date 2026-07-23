from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset

from match.bfxr_io import ParamSpace

from .constants import CHANNEL_MEAN, CHANNEL_STD, SQUARE_ONLY
from .dataset import InvertShardDataset
from .features_pack import normalize_channels
from .model import InverseModel
from .sampler import wave_type_index_map


def select_unit_pred(
    out: dict[str, torch.Tensor], class_idx: torch.Tensor, version: int
) -> torch.Tensor:
    if version == 1:
        return out["unit"]
    if version == 2:
        b = torch.arange(class_idx.shape[0], device=class_idx.device)
        return out["unit_per_class"][b, class_idx]
    raise ValueError(version)


def per_param_r2(
    pred: torch.Tensor, tgt: torch.Tensor, names: list[str]
) -> dict[str, float]:
    """1 - MSE/Var per param. ~0 = predicting the mean; 1 = perfect."""
    mse = ((pred - tgt) ** 2).mean(dim=0)
    var = tgt.var(dim=0, unbiased=False).clamp_min(1e-8)
    r2 = 1.0 - mse / var
    return {n: float(r2[i]) for i, n in enumerate(names)}


def wavetype_topk_accuracy(
    logits: torch.Tensor, class_idx: torch.Tensor, k: int
) -> float:
    topk = logits.topk(k, dim=1).indices
    return float((topk == class_idx[:, None]).any(dim=1).float().mean())


def invert_loss(
    out: dict[str, torch.Tensor],
    unit_tgt: torch.Tensor,
    wave_types: torch.Tensor,
    class_idx: torch.Tensor,
    space: ParamSpace,
    version: int = 1,
    unit_weight: float = 10.0,
    ce_weight: float = 0.5,
) -> tuple[torch.Tensor, dict[str, float]]:
    unit_pred = select_unit_pred(out, class_idx, version)

    mask = torch.ones_like(unit_tgt)
    for name in SQUARE_ONLY:
        j = space.names.index(name)
        mask[:, j] = (wave_types == 0).float()

    unit_mse = ((unit_pred - unit_tgt) ** 2 * mask).sum() / mask.sum().clamp(min=1)
    ce = F.cross_entropy(out["wavetype_logits"], class_idx.long())
    loss = unit_weight * unit_mse + ce_weight * ce
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
    unit_weight: float = 10.0,
    ce_weight: float = 0.5,
) -> dict[str, float]:
    train = optimizer is not None
    collect = optimizer is None
    model.train(train)
    total_loss = 0.0
    total_unit = 0.0
    total_ce = 0.0
    n_batches = 0
    preds, tgts, all_logits, all_cls = [], [], [], []
    for batch in loader:
        # float16 shards → float32; z-score channels before the CNN
        x = normalize_channels(batch["features"].to(device).float())
        log_dur = batch["log_duration"].to(device).float()
        unit = batch["unit"].to(device).float()
        wt = batch["wave_type"].to(device)
        cls = batch["class_idx"].to(device)

        if train:
            optimizer.zero_grad(set_to_none=True)

        out = model(x, log_dur)
        loss, parts = invert_loss(
            out,
            unit,
            wt,
            cls,
            space,
            version=model.version,
            unit_weight=unit_weight,
            ce_weight=ce_weight,
        )

        if train:
            loss.backward()
            optimizer.step()

        total_loss += float(loss.detach())
        total_unit += parts["unit_mse"]
        total_ce += parts["ce"]
        n_batches += 1

        if collect:
            preds.append(select_unit_pred(out, cls, model.version).detach().cpu())
            tgts.append(unit.detach().cpu())
            all_logits.append(out["wavetype_logits"].detach().cpu())
            all_cls.append(cls.detach().cpu())

    denom = max(n_batches, 1)
    metrics: dict[str, float | dict[str, float]] = {
        "loss": total_loss / denom,
        "unit_mse": total_unit / denom,
        "ce": total_ce / denom,
    }
    if collect and preds:
        pred_cat, tgt_cat = torch.cat(preds), torch.cat(tgts)
        logit_cat, cls_cat = torch.cat(all_logits), torch.cat(all_cls)
        metrics["r2"] = per_param_r2(pred_cat, tgt_cat, list(space.names))
        metrics["wavetype_top1"] = wavetype_topk_accuracy(logit_cat, cls_cat, 1)
        metrics["wavetype_top3"] = wavetype_topk_accuracy(logit_cat, cls_cat, 3)
    return metrics


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
    unit_weight: float = 10.0,
    ce_weight: float = 0.5,
    width: int = 128,
    dilated: bool = False,
) -> Path:
    device_s = device or _default_device()
    device_t = torch.device(device_s)
    space = ParamSpace()
    _, cls_to_id = wave_type_index_map(space)
    wave_types_order = [cls_to_id[i] for i in range(len(cls_to_id))]

    # Historical dirs (e.g. invert/data/v1) may carry an older dataset_version.
    manifest_path = Path(data) / "manifest.json"
    ds_version = None
    if manifest_path.is_file():
        import json
        ds_version = json.loads(manifest_path.read_text()).get("dataset_version")
    ds = InvertShardDataset(data, dataset_version=ds_version)
    train_idx, val_idx = _split_indices(len(ds), val_ratio=val_ratio)
    train_ds = Subset(ds, train_idx)
    val_ds = Subset(ds, val_idx) if val_idx else None

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = (
        DataLoader(val_ds, batch_size=batch_size, shuffle=False) if val_ds is not None else None
    )

    model = InverseModel(version=version, width=width, dilated=dilated).to(device_t)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "train_log.jsonl"
    best_path = out / "best.pt"
    best_val = float("inf")

    with log_path.open("w", encoding="utf-8") as log_f:
        for epoch in range(1, epochs + 1):
            train_metrics = _run_epoch(
                model,
                train_loader,
                space,
                device_t,
                optimizer=opt,
                unit_weight=unit_weight,
                ce_weight=ce_weight,
            )
            if val_loader is not None:
                val_metrics = _run_epoch(
                    model,
                    val_loader,
                    space,
                    device_t,
                    optimizer=None,
                    unit_weight=unit_weight,
                    ce_weight=ce_weight,
                )
            else:
                val_metrics = train_metrics

            if "r2" in val_metrics:
                worst = sorted(val_metrics["r2"].items(), key=lambda kv: kv[1])[:3]
                print(
                    f"epoch {epoch}: val unit_mse {val_metrics['unit_mse']:.4f} "
                    f"top3 {val_metrics['wavetype_top3']:.2%} "
                    f"worst r2: " + ", ".join(f"{n}={v:.2f}" for n, v in worst),
                    file=sys.stderr,
                )

            row = {
                "epoch": epoch,
                "train": train_metrics,
                "val": val_metrics,
            }
            log_f.write(json.dumps(row) + "\n")
            log_f.flush()

            val_metric = val_metrics["unit_mse"]
            if val_metric < best_val:
                best_val = val_metric
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "version": version,
                        "readout": model.readout,
                        "width": model.width,
                        "dilated": model.dilated,
                        "space_names": list(space.names),
                        "wave_types_order": wave_types_order,
                        "best_val": best_val,
                        "selection_metric": "val_unit_mse",
                        "channel_mean": list(CHANNEL_MEAN),
                        "channel_std": list(CHANNEL_STD),
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
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--dilated", action="store_true")
    p.add_argument("--unit-weight", type=float, default=10.0)
    p.add_argument("--ce-weight", type=float, default=0.5)
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
        unit_weight=args.unit_weight,
        ce_weight=args.ce_weight,
        width=args.width,
        dilated=args.dilated,
    )
    print(f"wrote {best}")


if __name__ == "__main__":
    main()
