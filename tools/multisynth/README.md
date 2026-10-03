# Multi-synth inverse model

An offline **nonparametric inverse model**: render examples from the app's
preset distributions, encode their audio, retrieve plausible parameters for
each synth, refine several synths independently, then automatically select the
closest result. This is a working baseline for expanding reachable game SFX,
not a newly trained neural network or a validated human preference predictor.

The default model spans **22 active synths**. The headless adapter supports 31,
but nine retired engines cannot be opened through normal collection import,
so matching excludes them. Chattr's text controls and Mixr/Stackr compositions
need separate search representations. Jinglr searches instrument, tuning,
tempo, envelope and timbre while keeping the retrieved phrase intact.

## Run

From `tools/`, with the existing Python environment (`uv sync --group dev`):

```sh
uv run python -m multisynth.cli build \
  -o multisynth/runs/library-v1 --per-preset 16 --jobs 4

uv run python -m multisynth.cli match path/to/sound.wav \
  --library multisynth/runs/library-v1 \
  -o multisynth/runs/my-sound --budget 128 --experts 5

uv run python -m multisynth.cli benchmark /path/to/targets_non_bfxr_big \
  --library multisynth/runs/library-v1 \
  -o multisynth/runs/real-v1 --count 40 --max-seconds 4 --budget 64
```

Open the output `index.html` to compare references, winners and alternatives.
Load `matches.bcol` or the benchmark's `winners.bcol` through the app's collection
import. Parameters remain editable. The gallery's WAVs are peak-normalized and
silence-trimmed for comparison; imported presets retain their natural timing
and volume. Bfxr/Footsteppr's browser noise RNG can vary on playback; their exact
search render seeds are recorded in JSON and replayable through this tool.
Generated libraries, reports and source audio stay local under ignored `runs/`.

All commands use deterministic seeds. `--synths Bfxr` provides a single-engine
baseline. `--budget` is the number of additional renders **per expert**; Bfxr is
always added if present in the eligible library, so five experts can mean six
searches. Each finalist also needs one final export replay, separately counted.
The CLI prints progress and writes benchmark results after each completed target.

## Model and objective

The library stores canonical controls, recipe identity, render seed and an audio
descriptor. A fingerprint covers every loaded synth dependency, browser globals,
active-tab registration and adapter implementation; changed synthesis code
requires rebuilding the library. A feature version similarly guards against
incompatible descriptors. No target files are used to build the library.

The compact representation uses 40 mel bands over 32 relative-time frames,
relative and absolute amplitude envelopes, pitch/voicing/noisiness contours,
duration and motion summaries. Weighted L1 distance gives a cheap common
objective for retrieval and refinement. Overall gain and leading/trailing
silence are removed; timing and event order inside a sound remain significant.
The weights are engineering choices, not learned from listening judgments.

Retrieval preserves up to four seeds per synth. The top synths undergo bounded
mixed discrete/continuous mutation, with decreasing step size, multiple elites,
and an initial duration proposal. Actual browser setters clamp/round controls.
The incumbent is retained on every step, so search cannot worsen its objective.
Categorical values and Transfxr endpoints/curves are supported. Texture seeds
remain fixed rather than becoming a way to optimize individual noise samples.

This implementation deliberately leaves the old Bfxr matcher and neural model
unchanged. It also avoids the earlier pitch-structure penalty whose improved
synthetic tests did not translate into a listening win.

## Evaluation and limitations

The benchmark shuffles files deterministically inside source collections and
round-robins those collections. It rejects silence, invalid audio, exact
normalized duplicates and files longer than the configured limit. It does not
silently truncate recordings. Filenames are used for display and source
balancing only; the model sees audio, not tags. Manifests include source paths,
SHA-256 hashes, settings and library identity.

The Bfxr comparison uses the same per-preset sampling count and per-expert
search budget. **Multi-synth search uses more total candidates and renders.**
Its score advantage is a search-space comparison under its own objective, not
an equal-compute comparison, nor proof of improvement over the old neural-seeded
matcher. Scores are not percentages of audible likeness. Speech, several
simultaneous sources, precise note sequences and long evolving textures remain
hard. A human A/B listening pass is necessary before calling a preset convincing
or fun. Keep alternate synth results: the numerical winner need not be the most
useful game sound.

## Tests

```sh
node --test ../tests/multisynth-render.test.js
uv run pytest tests/test_multisynth.py
```

Tests cover seeded rendering and replay, every Footsteppr terrain, inventory and
schema, worker error recovery, perceptual orderings, gain/onset invariance,
invalid audio, stale-library rejection, parameter bounds, search budget,
incumbent preservation and editable export round trips.

## First measured run

See [RESULTS.md](RESULTS.md) for the 40-target experiment, independent metric
check, noise-seed audit and local deliverables. To audit another completed run:

```sh
uv run python -m multisynth.audit multisynth/runs/real-v1
```

The audit verifies reference SHA-256 hashes, feature version and DSP source
fingerprint before re-scoring. It reports disagreement with the previous
contour metric rather than concealing it.

The benchmark gallery provides reference/model/Bfxr audio for each target, with
independent 1–5 likeness ratings and optional notes. Ratings persist in browser
local storage, scoped to the experiment and candidate identities. When the
model selected Bfxr itself, both controls share a rating. The bottom-of-page
JSON includes only rated/noted targets, with provenance for matching feedback
back to saved results. Use **Copy feedback JSON** to share it in chat; nothing
is submitted automatically.
