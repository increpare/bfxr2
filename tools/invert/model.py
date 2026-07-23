from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .constants import N_CHANNELS, N_PARAMS, N_WAVETYPES


class InverseModel(nn.Module):
    def __init__(self, version: int = 1, width: int = 128):
        super().__init__()
        if version not in (1, 2):
            raise ValueError(version)
        self.version = version
        self.encoder = nn.Sequential(
            nn.Conv1d(N_CHANNELS, width, 5, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv1d(width * 2, width * 2, 5, padding=2, stride=2),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        enc_dim = width * 2 + 1  # + log_duration
        self.wavetype_head = nn.Linear(enc_dim, N_WAVETYPES)
        if version == 1:
            self.unit_head = nn.Linear(enc_dim, N_PARAMS)
        else:
            self.unit_heads = nn.ModuleList(
                [nn.Linear(enc_dim, N_PARAMS) for _ in range(N_WAVETYPES)]
            )

    def encode(self, x: torch.Tensor, log_duration: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x).squeeze(-1)
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
