"""Bfxr parameter metadata and serialization.

Single source of truth for parameter names/ranges is the JS side
(render_cli.js --dump-info); nothing is duplicated here.
"""
from __future__ import annotations

import functools
import json
import subprocess
from pathlib import Path

import numpy as np

TOOLS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = TOOLS_DIR.parent
RENDER_CLI = TOOLS_DIR / "render" / "render_cli.js"
RENDER_WORKER = TOOLS_DIR / "render" / "render_worker.js"


@functools.cache
def param_info() -> dict:
    out = subprocess.run(
        ["node", str(RENDER_CLI), "--dump-info"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


class ParamSpace:
    """The searchable parameter space: all RANGE params except the
    permalocked masterVolume, mapped to/from [0,1] vectors. waveType is
    handled separately (categorical)."""

    def __init__(self):
        info = param_info()
        excluded = set(info["permalocked"])
        self.range_params = [
            p for p in info["params"]
            if p["type"] == "RANGE" and p["name"] not in excluded
        ]
        self.names = [p["name"] for p in self.range_params]
        self.mins = np.array([p["min"] for p in self.range_params])
        self.maxs = np.array([p["max"] for p in self.range_params])
        self.defaults = np.array([p["default"] for p in self.range_params])
        self.wave_types = [w["value"] for w in info["waveTypes"]]
        self.wave_type_names = {w["value"]: w["name"] for w in info["waveTypes"]}
        self.version = info["version"]
        self.sample_rate = info["sampleRate"]

    @property
    def dim(self) -> int:
        return len(self.names)

    def to_unit(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mins) / (self.maxs - self.mins)

    def from_unit(self, unit: np.ndarray) -> np.ndarray:
        return self.mins + np.clip(unit, 0.0, 1.0) * (self.maxs - self.mins)

    def defaults_unit(self) -> np.ndarray:
        return self.to_unit(self.defaults)

    def params_dict(self, unit: np.ndarray, wave_type: int) -> dict:
        values = self.from_unit(np.asarray(unit, dtype=float))
        params = {name: float(v) for name, v in zip(self.names, values)}
        params["waveType"] = int(wave_type)
        params["masterVolume"] = 0.5
        return params

    def unit_from_params(self, params: dict) -> tuple[np.ndarray, int]:
        values = np.array([params[name] for name in self.names], dtype=float)
        return self.to_unit(values), int(params["waveType"])


def write_bfxr(path: Path | str, params: dict, file_name: str) -> None:
    """Write an app-loadable .bfxr file (same shape as Tab.serialize_params)."""
    doc = {
        "synth_type": "Bfxr",
        "version": param_info()["version"],
        "file_name": file_name,
        "params": params,
    }
    Path(path).write_text(json.dumps(doc, indent=1))


def read_bfxr(path: Path | str) -> dict:
    doc = json.loads(Path(path).read_text())
    return doc["params"] if "params" in doc else doc
