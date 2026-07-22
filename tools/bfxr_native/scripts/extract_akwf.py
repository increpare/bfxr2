#!/usr/bin/env python3
"""Extract AKWF wavetable arrays from js/audio/AKWF.js into C++ sources."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AKWF_JS = ROOT / "js" / "audio" / "AKWF.js"
OUT_H = Path(__file__).resolve().parents[1] / "include" / "akwf_tables.h"
OUT_CC = Path(__file__).resolve().parents[1] / "src" / "akwf_tables.cpp"

TABLES = ("granular_0044", "fmsynth_0012", "hvoice_0012")


def extract(name: str, text: str) -> list[int]:
    m = re.search(rf"static {name} = \[([\s\S]*?)\];", text)
    if not m:
        raise SystemExit(f"table {name} not found in {AKWF_JS}")
    nums = [int(x) for x in re.findall(r"-?\d+", m.group(1))]
    if len(nums) != 256:
        raise SystemExit(f"{name}: expected 256 samples, got {len(nums)}")
    return nums


def main() -> None:
    text = AKWF_JS.read_text()
    tables = {name: extract(name, text) for name in TABLES}

    OUT_H.parent.mkdir(parents=True, exist_ok=True)
    OUT_CC.parent.mkdir(parents=True, exist_ok=True)

    OUT_H.write_text(
        "#pragma once\n"
        "#include <cstdint>\n\n"
        "namespace bfxr {\n\n"
        "constexpr int kAkwfLen = 256;\n\n"
        + "".join(
            f"extern const int16_t {name}[kAkwfLen];\n" for name in TABLES
        )
        + "\n}  // namespace bfxr\n"
    )

    lines = [
        '#include "akwf_tables.h"\n',
        "namespace bfxr {\n",
    ]
    for name, nums in tables.items():
        lines.append(f"const int16_t {name}[kAkwfLen] = {{")
        for i in range(0, 256, 16):
            chunk = ", ".join(str(n) for n in nums[i : i + 16])
            lines.append(f"  {chunk},")
        lines.append("};\n")
    lines.append("}  // namespace bfxr\n")
    OUT_CC.write_text("\n".join(lines))
    print(f"wrote {OUT_H.relative_to(ROOT)} and {OUT_CC.relative_to(ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
