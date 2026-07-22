#!/usr/bin/env python3
"""Render fixture/grid params via Node and write float32 golden dumps."""
from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[2]  # .../tools
ROOT = TOOLS.parent
NODE_WORKER = TOOLS / "render" / "render_worker.js"
FIXTURES = TOOLS / "tests" / "fixtures"
OUT = TOOLS / "bfxr_native" / "testdata"


def render_node(params: dict, seed: int = 1) -> np.ndarray:
    proc = subprocess.Popen(
        ["node", str(NODE_WORKER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.stderr.readline()
    req = json.dumps({"id": 1, "seed": seed, "params": params}, separators=(",", ":"))
    proc.stdin.write((req + "\n").encode())
    proc.stdin.close()
    hdr = proc.stdout.read(12)
    _id, status, n = struct.unpack("<IiI", hdr)
    data = proc.stdout.read(n * 4) if n else b""
    proc.wait()
    if status != 0:
        raise RuntimeError(f"node render failed status={status}")
    return np.frombuffer(data, dtype="<f4").copy()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cases: list[tuple[str, dict, int]] = []
    for path in sorted(FIXTURES.glob("*.bfxr")):
        doc = json.loads(path.read_text())
        cases.append((path.stem, doc.get("params", doc), 1))
    for wt in range(12):
        cases.append(
            (
                f"grid_wt{wt}",
                {
                    "waveType": wt,
                    "frequency_start": 0.4,
                    "sustainTime": 0.2,
                    "decayTime": 0.3,
                },
                42,
            )
        )

    meta = []
    for name, params, seed in cases:
        buf = render_node(params, seed)
        out_path = OUT / f"{name}.f32"
        buf.astype("<f4").tofile(out_path)
        meta.append({"name": name, "seed": seed, "params": params, "n": int(buf.size)})
        print(f"wrote {out_path.relative_to(ROOT)} ({buf.size} samples)", file=sys.stderr)

    (OUT / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
