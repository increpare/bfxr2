from __future__ import annotations

import json
import subprocess
from pathlib import Path

PRESET_CLI = Path(__file__).resolve().parent.parent / "render" / "preset_cli.js"


def harvest_preset_params(n: int, seed: int, node: str = "node") -> list[dict]:
    out = subprocess.run(
        [node, str(PRESET_CLI), "--preset", "all", "--count", str(n), "--seed", str(seed)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [json.loads(line) for line in out.splitlines() if line.strip()]
