# Native Bfxr renderer (C++17)

Fast headless port of `js/audio/Bfxr_DSP.js` for offline matching / training.
Drop-in replacement for `tools/render/` (same CLI flags and worker protocol).

## Build

```sh
make -C tools/bfxr_native
```

Produces:

- `build/bfxr_render` — one-shot CLI
- `build/bfxr_worker` — persistent batch worker

Do **not** enable `-ffast-math`; it breaks parity with the JS oracle.

## Usage

```sh
./build/bfxr_render --dump-info
./build/bfxr_render --in sound.bfxr --out out.wav --seed 1

# Worker protocol (identical to render/render_worker.js):
# stdin NDJSON: {"id":0,"seed":1,"params":{...}}
# stdout: uint32 id | int32 status | uint32 n | n×float32LE
./build/bfxr_worker
```

Regenerate AKWF tables after editing `js/audio/AKWF.js`:

```sh
python3 scripts/extract_akwf.py
```

## Parity

Renders aim for near bit-identical float32 output vs the Node renderer for the
same `(params, seed)`. Noise paths use the same mulberry32 PRNG as
`tools/render/bfxr_context.js`. Wave type 6 (`tan`) may differ slightly across
libm implementations; the parity tests document the measured bound.
