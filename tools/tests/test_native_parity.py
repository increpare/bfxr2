"""Parity checks: native C++ renderer vs Node oracle.

Skips if `tools/bfxr_native/build/bfxr_worker` is missing.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
from pathlib import Path

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[1]
NATIVE_WORKER = TOOLS / "bfxr_native" / "build" / "bfxr_worker"
NODE_WORKER = TOOLS / "render" / "render_worker.js"
FIXTURES = TOOLS / "tests" / "fixtures"
TESTDATA = TOOLS / "bfxr_native" / "testdata"

# Plan bound: max|Δ| ≤ 1e-5. Observed tan-path diffs are ~1e-15 on macOS.
ATOL = 1e-5

pytestmark = pytest.mark.skipif(
    not (NATIVE_WORKER.is_file() and os.access(NATIVE_WORKER, os.X_OK)),
    reason="native bfxr_worker not built (make -C tools/bfxr_native)",
)


def _render(cmd: list[str], params: dict, seed: int) -> np.ndarray:
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.stderr.readline()
    line = json.dumps({"id": 1, "seed": seed, "params": params}, separators=(",", ":"))
    proc.stdin.write((line + "\n").encode())
    proc.stdin.close()
    hdr = proc.stdout.read(12)
    _id, status, n = struct.unpack("<IiI", hdr)
    data = proc.stdout.read(n * 4) if n else b""
    proc.wait(timeout=30)
    assert status == 0, f"render failed status={status} cmd={cmd}"
    return np.frombuffer(data, dtype="<f4")


def _params_from_fixture(path: Path) -> dict:
    doc = json.loads(path.read_text())
    return doc["params"] if "params" in doc else doc


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("*.bfxr")), ids=lambda p: p.stem)
def test_fixture_parity_vs_node(fixture: Path):
    params = _params_from_fixture(fixture)
    node = _render(["node", str(NODE_WORKER)], params, seed=1)
    native = _render([str(NATIVE_WORKER)], params, seed=1)
    assert len(native) == len(node)
    np.testing.assert_allclose(native, node, atol=ATOL, rtol=0)


@pytest.mark.parametrize("wave_type", range(12))
def test_wave_type_grid_parity(wave_type: int):
    params = {
        "waveType": wave_type,
        "frequency_start": 0.4,
        "sustainTime": 0.2,
        "decayTime": 0.3,
    }
    node = _render(["node", str(NODE_WORKER)], params, seed=42)
    native = _render([str(NATIVE_WORKER)], params, seed=42)
    assert len(native) == len(node)
    np.testing.assert_allclose(native, node, atol=ATOL, rtol=0)


def test_dump_info_shape_matches_node():
    native_cli = TOOLS / "bfxr_native" / "build" / "bfxr_render"
    node_info = json.loads(
        subprocess.check_output(
            ["node", str(TOOLS / "render" / "render_cli.js"), "--dump-info"],
            text=True,
        )
    )
    native_info = json.loads(
        subprocess.check_output([str(native_cli), "--dump-info"], text=True)
    )
    assert native_info["version"] == node_info["version"]
    assert native_info["sampleRate"] == node_info["sampleRate"]
    assert native_info["permalocked"] == node_info["permalocked"]
    assert [p["name"] for p in native_info["params"]] == [p["name"] for p in node_info["params"]]
    assert native_info["waveTypes"] == node_info["waveTypes"]
