"""Spectral-only finetune of InverseModel on unlabeled real audio."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from match.bfxr_io import ParamSpace

from .features_pack import normalize_channels
from .model import InverseModel
from .predict import load_checkpoint
from .real_audio import RealAudioFeatureDataset
from .surrogate import load_surrogate
from .train import select_unit_pred


def _default_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _spectral_loss(
    model: InverseModel,
    surrogate,
    features: torch.Tensor,
    log_duration: torch.Tensor,
) -> tuple[torch.Tensor, float]:
    """Surrogate(pred_params) ↔ input features; wavetype from model softmax."""
    x = normalize_channels(features)
    out = model(x, log_duration)
    # Soft one-hot so wavetype gets spectral gradient; unit via hard argmax class
    # for select_unit_pred (v1 path ignores class; v2 needs an index).
    probs = F.softmax(out["wavetype_logits"], dim=-1)
    cls = probs.argmax(dim=-1)
    unit_pred = select_unit_pred(out, cls, model.version)
    pred_feat = surrogate(unit_pred, probs, log_duration)
    loss = F.mse_loss(pred_feat, x)
    return loss, float(loss.detach())


def _run_epoch(
    model: InverseModel,
    surrogate,
    loader: DataLoader,
    device: torch.device,
    *,
    optimizer: torch.optim.Optimizer | None,
    spectral_weight: float,
) -> float:
    train = optimizer is not None
    model.train(train)
    total = 0.0
    n = 0
    for batch in loader:
        feat = batch["features"].to(device).float()
        log_dur = batch["log_duration"].to(device).float()
        if train:
            optimizer.zero_grad(set_to_none=True)
        loss, _ = _spectral_loss(model, surrogate, feat, log_dur)
        loss = spectral_weight * loss
        if train:
            loss.backward()
            optimizer.step()
        total += float(loss.detach())
        n += 1
    return total / max(n, 1)


def finetune(
    *,
    init_weights: Path,
    manifest: Path,
    surrogate_path: Path,
    out: Path,
    epochs: int = 3,
    batch_size: int = 32,
    lr: float = 1e-4,
    spectral_weight: float = 1.0,
    device: str | None = None,
) -> Path:
    device_s = device or _default_device()
    device_t = torch.device(device_s)
    space = ParamSpace()

    model, meta = load_checkpoint(init_weights, device=device_s)
    model.train()
    surrogate = load_surrogate(surrogate_path, device_t)
    surrogate.eval()
    for p in surrogate.parameters():
        p.requires_grad = False

    rows = json.loads(Path(manifest).read_text(encoding="utf-8"))
    train_ds = RealAudioFeatureDataset(rows, split="train")
    hold_ds = RealAudioFeatureDataset(rows, split="holdout")
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    hold_loader = DataLoader(hold_ds, batch_size=batch_size, shuffle=False)

    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "train_log.jsonl"
    best_path = out / "best.pt"
    best_val = float("inf")

    with log_path.open("w", encoding="utf-8") as log_f:
        for epoch in range(1, epochs + 1):
            train_loss = _run_epoch(
                model,
                surrogate,
                train_loader,
                device_t,
                optimizer=opt,
                spectral_weight=spectral_weight,
            )
            val_loss = _run_epoch(
                model,
                surrogate,
                hold_loader,
                device_t,
                optimizer=None,
                spectral_weight=spectral_weight,
            )
            row = {"epoch": epoch, "train_spectral": train_loss, "hold_spectral": val_loss}
            log_f.write(json.dumps(row) + "\n")
            log_f.flush()
            print(
                f"epoch {epoch}: train_spectral {train_loss:.4f} hold_spectral {val_loss:.4f}",
                file=sys.stderr,
            )
            if val_loss < best_val:
                best_val = val_loss
                torch.save(
                    {
                        "model_state": model.state_dict(),
                        "version": int(meta["version"]),
                        "readout": str(meta["readout"]),
                        "width": int(meta["width"]),
                        "dilated": bool(meta["dilated"]),
                        "space_names": list(space.names),
                        "wave_types_order": list(meta["wave_types_order"]),
                        "best_val": best_val,
                        "selection_metric": "hold_spectral",
                        "channel_mean": list(meta["channel_mean"]),
                        "channel_std": list(meta["channel_std"]),
                        "spectral_weight": spectral_weight,
                        "surrogate": str(surrogate_path),
                        "real_manifest": str(manifest),
                    },
                    best_path,
                )
    return best_path


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Spectral finetune on unlabeled real audio")
    p.add_argument("--init-weights", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--surrogate", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--spectral-weight", type=float, default=1.0)
    p.add_argument("--device", type=str, choices=("cpu", "mps", "cuda"), default=None)
    args = p.parse_args(argv)
    best = finetune(
        init_weights=args.init_weights,
        manifest=args.manifest,
        surrogate_path=args.surrogate,
        out=args.out,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        spectral_weight=args.spectral_weight,
        device=args.device,
    )
    print(f"wrote {best}")


if __name__ == "__main__":
    main()
