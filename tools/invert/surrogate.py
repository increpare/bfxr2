from __future__ import annotations

import torch
import torch.nn as nn

from .constants import N_CHANNELS, N_FRAMES, N_PARAMS, N_WAVETYPES


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
