from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES


class InverseModel(nn.Module):
    def __init__(
        self,
        version: int = 1,
        width: int = 128,
        readout: str = "flatten",
        dilated: bool = False,
    ):
        super().__init__()
        if version not in (1, 2):
            raise ValueError(version)
        if readout not in ("gap", "flatten"):
            raise ValueError(readout)
        self.version = version
        self.readout = readout
        self.width = width
        self.dilated = dilated
        self.encoder = nn.Sequential(
            nn.Conv1d(N_CHANNELS, width, 5, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width * 2, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
        )
        if dilated:
            self.dilated_conv = nn.Sequential(
                nn.Conv1d(width * 2, width * 2, 5, padding=4, dilation=2),
                nn.ReLU(inplace=True),
            )
        n_out_frames = N_FRAMES // 8  # three stride-2 convs: 128 -> 16
        if readout == "gap":
            feat_dim = width * 2
        else:
            self.proj = nn.Sequential(
                nn.Linear(width * 2 * n_out_frames, 512),
                nn.ReLU(inplace=True),
            )
            feat_dim = 512
        enc_dim = feat_dim + 1  # + log_duration
        self.wavetype_head = nn.Linear(enc_dim, N_WAVETYPES)
        if version == 1:
            self.unit_head = nn.Linear(enc_dim, N_PARAMS)
        else:
            self.unit_heads = nn.ModuleList(
                [nn.Linear(enc_dim, N_PARAMS) for _ in range(N_WAVETYPES)]
            )

    def encode(self, x: torch.Tensor, log_duration: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x)
        if self.dilated:
            h = self.dilated_conv(h)
        if self.readout == "gap":
            h = h.mean(dim=-1)
        else:
            h = self.proj(h.flatten(1))
        return torch.cat([h, log_duration.unsqueeze(-1)], dim=-1)

    def forward(self, x: torch.Tensor, log_duration: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.encode(x, log_duration)
        logits = self.wavetype_head(h)
        if self.version == 1:
            unit = torch.sigmoid(self.unit_head(h))
            return {"unit": unit, "wavetype_logits": logits}
        units = torch.stack(
            [torch.sigmoid(head(h)) for head in self.unit_heads], dim=1
        )
        return {"unit_per_class": units, "wavetype_logits": logits}
