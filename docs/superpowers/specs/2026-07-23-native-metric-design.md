# Native “current” metric (C++) — design

## Goal

Port the matcher’s **current** perceptual metric (contour features + multi-scale log-mel) from Python/PyTorch into C++ so match, refine, and library bakeoff scoring are much faster. Python keeps driving search; scoring goes through a persistent native worker. Absolute score parity with the old torch path is **not** required.

## Context

- Today’s score path: `tools/match/features.py` (contours) + `tools/match/objective.py` (blurred multi-scale mel + weighted sum). Implemented with torch/torchaudio as a DSP library, not a neural net.
- Consumers: `match.match` / `StagedOptimizer`, `match.refine`, `match.metric_bakeoff` (`current` only).
- Rendering already has a native persistent worker (`bfxr_native/build/bfxr_worker`). Metric should follow the same pattern.
- Alternate bakeoff metrics (harmonic / zimtohrli / clap) were judged useless for product use; out of scope.

## Decisions

| Topic | Choice |
|-------|--------|
| Scope | Contours **and** full multi-scale mel (same structure as today’s `MatchObjective`) |
| Consumers | Matcher/refine **and** library analyze + score-against-cache |
| Parity | Behavioral / ranking quality only — not bit-exact vs torchaudio |
| Integration | Persistent `metric_worker` (stdin/stdout), not ctypes/pybind |
| Python torch scorer | **Replaced** — C++ is the only score path |

## Non-goals

- Bit-exact or near-exact numerical match to PyTorch/torchaudio scores.
- Porting clap, zimtohrli, or harmonic metrics.
- Fusing render + score into one process (revisit later if IPC dominates).
- SIMD/GPU optimization in v1.
- Changing CMA / refine algorithms (only the scorer backend).

## Architecture

Add metric code under `tools/bfxr_native` (same Makefile / C++17 toolchain as the renderer):

| Piece | Role |
|-------|------|
| `features.{h,cpp}` | Contour extraction: env dB, f0/voiced/clarity, active, centroid, noisiness; `feature_distance` + weights |
| `mel.{h,cpp}` | Multi-scale log-mel + frequency-axis Gaussian blur; pair distance with optional stretch/shift |
| `objective.{h,cpp}` | Target state, candidate cache, combine contour terms + mel term |
| Vendored real-FFT | e.g. pocketfft or kissfft — no system FFTW |
| `metric_worker` | Persistent binary exposing the protocol below |
| Python `MatchObjective` | Thin client over the worker; same public methods as today |

Mel filterbank is **our own** (HTK-style or similar), tuned to the same scales as Python today — not required to match torchaudio bin-for-bin.

### Scales / constants (port from Python)

Keep the same knobs unless profiling forces a change:

- Sample rate 44100; feature frame 2048 / hop 512; pitch frame 1024; ACF size 2048.
- Mel scales: `(n_fft, hop, n_mels)` = `(2048,512,128)`, `(1024,256,96)`, `(512,128,64)`, `(256,64,32)`; `f_min=30`, `f_max=18000`.
- `MIN_WAVE_LEN=4096`, `TAIL_PAD=2048`, peak normalize, mel blur σ≈2 bins on the 128-band scale.
- Default `FeatureWeights` including `mel=0.35`; optional `allow_pitch_shift` / `allow_time_stretch`.

## Worker protocol

Pattern mirrors `bfxr_worker`: stderr ready-line JSON; then request/response. PCM is binary float32 LE (not JSON).

**Commands**

1. **`set_target`** — peak-normalize, extract target features + mels into worker memory. Payload includes flags (`allow_pitch_shift`, `allow_time_stretch`) and optional weight overrides.
2. **`score_batch`** — NDJSON header `{id, n, lengths:[…]}` followed by `n` concatenated float32 waves. Reply: binary `id | status | n | n×f64 scores`. Optional later: per-term breakdown for debugging.
3. **`analyze_library`** — same waveform framing; build and retain a candidate cache (per-clip features + mels).
4. **`score_library`** — score cached library vs current target without re-analysis; reply scores.

Python `MatchObjective` maps:

- ctor / target change → `set_target`
- `score` / `score_batch` → `score_batch`
- `precompute_candidates` → `analyze_library`
- `score_candidates` → `score_library`

Batching semantics (pad to max length in batch + tail pad; slice features by true length) stay conceptually the same so refine’s “score probes alone” discipline still matters.

## Python cutover

- Replace implementations in `match/objective.py` (and retire torch `match/features.py` from the hot path).
- Wire match / refine / bakeoff `current` through the worker; require `bfxr_native/build/metric_worker` like the render worker.
- Remove torch/torchaudio from the **match score** dependency path. Keep torch only where still needed (e.g. optional HTML spectrograms under the `report` extra, and any remaining resample helper — prefer replacing resample with a small non-torch path if easy).
- Dead bakeoff metrics that force torch may be deleted or left unused; no obligation to keep them working.

## Testing

- Preserve the **intent** of `tests/test_metric_rankings.py` and `tests/test_objective.py` (e.g. rising vs falling sweep, silence expensive, monotone-ish frequency distance). Update absolute thresholds if scores shift.
- Worker smoke: `set_target` + `score_batch` roundtrip.
- No golden “must equal old Python float” tests.

## Success criteria

- Match, refine, and `current` bakeoff score without torch on the hot path.
- Clear speedup on library analyze and per-eval scoring vs the torch implementation.
- Ranking-oriented tests still pass after threshold retune if needed.
- `make -C tools/bfxr_native` builds `metric_worker` alongside existing binaries.

## Out of scope for v1

- Combined render+metric worker.
- Exact torchaudio mel parity.
- Shipping metric code into the web app.
