# `make diff_wav` — design

## Goal

From `tools/`, compare two WAV files with one Make invocation and print both sample-level distance stats and the existing match objective score.

```sh
make diff_wav A=path1.wav B=path2.wav
```

## Context

- Matching already has audio load/preprocess (`match.audio`) and scoring (`MatchObjective`).
- Native C++ tooling renders/writes WAV only; there is no C++ comparator. Comparison stays in Python for v1 (fast enough for two short SFX files).
- There is no top-level `tools/Makefile` yet.

## Non-goals

- Porting metrics or DSP comparison into C++.
- HTML reports, batch directories, or alignment search (time-shift / pitch-shift).
- Changing `MatchObjective` weights or preprocess semantics.

## Interface

| Piece | Role |
|-------|------|
| `tools/Makefile` | `diff_wav` target; requires `A` and `B`; runs `uv run python -m match.diff_wav "$(A)" "$(B)"` |
| `tools/match/diff_wav.py` | CLI: load, compare, print |

Missing `A`/`B` or unreadable paths → non-zero exit, message on stderr.

## Comparison

**Sample stats** (raw mono via `load_audio` → 44.1 kHz):

1. Zero-pad the shorter buffer to the longer length.
2. Report: `n_a`, `n_b`, `n_cmp`, `max_abs`, `rms` of `(a - b)`.

**Objective score**:

1. Run each path through `prepare_target` (trim + peak normalize — same as matching).
2. Score B against A as target: `MatchObjective(prepare_target(A)).score(prepare_target(B))`.
3. Print `objective` (lower = closer).

## Output

Human-readable key/value lines on stdout, e.g.:

```
n_a 44100
n_b 44000
n_cmp 44100
max_abs 0.0123
rms 0.00145
objective 0.82
```

## Success criteria

- `make -C tools diff_wav A=… B=…` prints both sample stats and objective for two existing WAVs.
- Identical files → `max_abs` / `rms` ≈ 0 and a low objective.
- Unit smoke test optional: two short synthetic buffers exercise pad + printed fields.

## Out of scope for v1

- Native/C++ sample differ.
- Make positional args (`make diff_wav a.wav b.wav`).
- Extra metrics (zimtohrli, clap, harmonic).
