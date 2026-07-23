from __future__ import annotations

import warnings
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from .constants import CHANNEL_MEAN, CHANNEL_STD, N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES
from .dataset import InvertShardDataset
from .features_pack import normalize_channels


class SurrogateSynth(nn.Module):
    """Differentiable approximation of params -> normalized feature stack.

    Trained to imitate the (renderer -> pack_features -> normalize) pipeline on
    the existing shards, then frozen to supply a spectral/audio loss to the
    inverse model (bfxr's real DSP is not differentiable).
    """

    def __init__(self, width: int = 128):
        super().__init__()
        self.width = width
        self.n0 = N_FRAMES // 8  # 16 -> upsample x8 -> 128
        in_dim = N_PARAMS + N_WAVETYPES + 1
        self.fc = nn.Sequential(
            nn.Linear(in_dim, width * 2 * self.n0),
            nn.ReLU(inplace=True),
        )
        self.deconv = nn.Sequential(
            nn.ConvTranspose1d(width * 2, width * 2, 4, stride=2, padding=1),  # 16->32
            nn.ReLU(inplace=True),
            nn.ConvTranspose1d(width * 2, width, 4, stride=2, padding=1),      # 32->64
            nn.ReLU(inplace=True),
            nn.ConvTranspose1d(width, width, 4, stride=2, padding=1),          # 64->128
            nn.ReLU(inplace=True),
            nn.Conv1d(width, N_CHANNELS, 5, padding=2),
        )

    def forward(
        self,
        unit: torch.Tensor,
        wavetype_onehot: torch.Tensor,
        log_duration: torch.Tensor,
    ) -> torch.Tensor:
        x = torch.cat([unit, wavetype_onehot, log_duration.unsqueeze(-1)], dim=-1)
        h = self.fc(x).view(-1, self.width * 2, self.n0)
        return self.deconv(h)


def _default_device() -> str:
    return "mps" if torch.backends.mps.is_available() else "cpu"


def train_surrogate(
    data: Path,
    out: Path,
    *,
    epochs: int = 10,
    batch_size: int = 64,
    lr: float = 1e-3,
    width: int = 128,
    device: str | None = None,
) -> Path:
    device_t = torch.device(device or _default_device())
    manifest = Path(data) / "manifest.json"
    ds_version = None
    if manifest.is_file():
        import json
        ds_version = json.loads(manifest.read_text()).get("dataset_version")
    ds = InvertShardDataset(data, dataset_version=ds_version)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)

    model = SurrogateSynth(width=width).to(device_t)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ckpt = out / "surrogate.pt"

    for epoch in range(1, epochs + 1):
        model.train()
        total, nb = 0.0, 0
        for batch in loader:
            feats = normalize_channels(batch["features"].to(device_t).float())
            unit = batch["unit"].to(device_t).float()
            onehot = F.one_hot(batch["class_idx"].to(device_t), N_WAVETYPES).float()
            log_dur = batch["log_duration"].to(device_t).float()
            opt.zero_grad(set_to_none=True)
            pred = model(unit, onehot, log_dur)
            loss = F.mse_loss(pred, feats)
            loss.backward()
            opt.step()
            total += float(loss.detach())
            nb += 1
        import sys
        print(f"surrogate epoch {epoch}: mse {total / max(nb,1):.4f}", file=sys.stderr)

    torch.save(
        {
            "model_state": model.state_dict(),
            "width": width,
            "channel_mean": list(CHANNEL_MEAN),
            "channel_std": list(CHANNEL_STD),
        },
        ckpt,
    )
    return ckpt


def _channel_stats_mismatch(stored: list[float], current: tuple[float, ...], tol: float = 1e-4) -> bool:
    if len(stored) != len(current):
        return True
    return any(abs(a - b) > tol for a, b in zip(stored, current))


def load_surrogate(path: Path, device: torch.device) -> SurrogateSynth:
    ck = torch.load(Path(path), weights_only=False)
    model = SurrogateSynth(width=ck["width"]).to(device)
    model.load_state_dict(ck["model_state"])
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)

    if "channel_mean" in ck and "channel_std" in ck:
        mismatched = _channel_stats_mismatch(
            ck["channel_mean"], CHANNEL_MEAN
        ) or _channel_stats_mismatch(ck["channel_std"], CHANNEL_STD)
        if mismatched:
            warnings.warn(
                "Surrogate checkpoint was trained under different channel_mean/"
                "channel_std than invert.constants.CHANNEL_MEAN/CHANNEL_STD. "
                "The spectral loss computed against this surrogate may be "
                "miscalibrated.",
                stacklevel=2,
            )

    return model


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Train the differentiable surrogate synth")
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--device", choices=("cpu", "mps", "cuda"), default=None)
    args = p.parse_args(argv)
    out = train_surrogate(
        args.data, args.out, epochs=args.epochs, batch_size=args.batch_size,
        lr=args.lr, width=args.width, device=args.device,
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
