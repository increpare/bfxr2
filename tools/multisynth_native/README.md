# Native multi-synth renderer (C++17)

C++ ports of the `js/audio/<Name>_DSP.js` engines for fast offline rendering.
The Node renderer (`tools/render/multisynth_*`) stays the oracle: it owns the
inventory, preset sampling and canonical controls. This worker only turns
canonical controls into PCM.

Ported: Birdr, Boomr, Bouncr, Breathr, Choirr, Clonkr, Crittr, Fractr, Glitchr,
Jinglr, Machinr, Pluckr, Riftr, Rustlr, Signlr, Squishr, Swarmr, Transfxr,
Whooshr, Zappr. Not ported: Footsteppr (a PureData graph compiled at run time),
Bfxr (it has its own port in `bfxr_native`) and the synths retired from the app.

## Build

```sh
make -C tools/multisynth_native
```

Produces `build/multisynth_worker`. Do **not** add `-ffast-math` or drop
`-ffp-contract=off`; both change results against the JS engines. On macOS the
batched `sin`/`exp`/`pow`/`tanh` calls go through Accelerate; `make SCALAR=1`
(and every other platform) uses scalar libm instead, which is slower.

## Worker protocol

Same framing as `bfxr_native`:

```
stdin   NDJSON: {"id":0,"synth":"Boomr","params":{...}}
stdout  uint32 id | int32 status | uint32 n | n x float32LE
stderr  one ready line: {"ready":true,"sampleRate":44100,"synths":[...]}
```

Status: 0 ok, 1 render failed, 2 bad request, 3 no native engine for that synth.
`params` must be the canonical controls the Node renderer returns from
`sample`/`render` (complete, clamped, `masterVolume` 0.5). None of these engines
reads `Math.random`, so the request seed does not affect the audio.

## From Python

Run from `tools/`.

```python
from multisynth_native.client import NativeRenderer, NativeWorker

with NativeRenderer() as renderer:          # drop-in for sfxmatch.render.FastRenderer
    params = renderer.sample('Boomr', 'generate_grenade', 1)
    canonical, wave = renderer.render('Boomr', params, 1)

with NativeWorker() as native:              # the bare worker
    wave = native.render('Boomr', canonical)
```

`NativeRenderer` asks Node only to canonicalise the controls (the `canonical`
op of `render/multisynth_fast_worker.js`), renders natively, and falls back to
Node for a synth with no native engine.

## Parity and speed

```sh
cd tools
uv run pytest tests/test_multisynth_native.py -s      # parity, 36 cases per engine
uv run python -m multisynth_native.bench              # parity and speedup table
```

Renders are not guaranteed bit-identical: V8 has its own `sin`, `exp`, `tan`
and `tanh`, which round a fraction of calls differently from libm and
Accelerate. Most renders still come out identical after rounding to float32.
The largest difference seen in any test or fuzz run is 3e-8; the tests allow
1e-6.

Measured with `multisynth_native.bench` (36 preset cases per engine, best of 3,
Node 25, Apple Silicon, machine busy with unrelated jobs; times are per render
as seen from Python, and the ratio is steadier than the milliseconds):

| Engine | max \|diff\| | bit-exact | Node ms | native ms | speedup |
|---|---|---|---|---|---|
| Birdr | 3.7e-09 | 33/36 | 28.2 | 6.9 | 4.1x |
| Boomr | 0 | 36/36 | 97.5 | 23.3 | 4.2x |
| Bouncr | 0 | 36/36 | 84.7 | 9.9 | 8.6x |
| Breathr | 0 | 36/36 | 52.8 | 8.3 | 6.3x |
| Choirr | 4.7e-10 | 33/36 | 251.9 | 41.6 | 6.1x |
| Clonkr | 1.5e-11 | 35/36 | 18.9 | 2.9 | 6.4x |
| Crittr | 1.5e-08 | 31/36 | 26.1 | 4.8 | 5.5x |
| Fractr | 0 | 36/36 | 16.2 | 4.4 | 3.7x |
| Glitchr | 0 | 36/36 | 21.8 | 5.8 | 3.7x |
| Jinglr | 0 | 36/36 | 60.9 | 6.6 | 9.3x |
| Machinr | 0 | 36/36 | 32.7 | 3.5 | 9.3x |
| Pluckr | 0 | 36/36 | 22.7 | 5.7 | 4.0x |
| Riftr | 3.7e-09 | 35/36 | 53.2 | 7.4 | 7.1x |
| Rustlr | 0 | 36/36 | 15.6 | 3.2 | 4.9x |
| Signlr | 0 | 36/36 | 40.6 | 4.5 | 9.1x |
| Squishr | 7.3e-12 | 35/36 | 26.1 | 3.5 | 7.4x |
| Swarmr | 0 | 36/36 | 416.6 | 65.3 | 6.4x |
| Transfxr | 2.3e-10 | 33/36 | 20.3 | 4.5 | 4.5x |
| Whooshr | 0 | 36/36 | 10.1 | 2.2 | 4.7x |
| Zappr | 0 | 36/36 | 59.1 | 9.0 | 6.6x |
| all 20, one render each | | | 1356 | 223 | 6.1x |

## Porting an engine

Add `src/engines/<name>.cpp` with a `render_<name>(const Params&)` and an
`MSN_ENGINE("<Name>", render_<name>);` line; the Makefile and the tests pick it
up. `boomr.cpp` is a plain port, `choirr.cpp` a batched one. The rules that
keep a port sample-exact:

- Every JS number is a `double`. Keep each expression's operator order and
  grouping exactly; never simplify algebra. Watch integer division
  (`note / 12.0`) and int-to-double conversions.
- A `Float32Array` store rounds to `float` at that moment: `static_cast<float>`
  on every write, `add(slot, x)` for `+=`. Plain JS arrays and locals stay
  `double`.
- `Math.pow`/`**` is `jspow` (V8 returns `x*x` for exponent 2 and `sqrt` for
  0.5; everything else is libm `pow`). `Math.round` is `jsround`, `%` is
  `std::fmod`, `SoundDSP.rng` is `Rng`, `SoundDSP.finish` is `finish`.
- `random()` calls must happen in JS order. JS evaluates operands, call
  arguments and object-literal fields left to right; C++ does not, so give
  each call its own statement.
- Reads the JS makes out of bounds (`undefined`, so `NaN`) must not become
  C++ out-of-bounds reads.
- Loops dominated by `sin`/`exp`/`pow`/`tanh` can be split into passes over
  `kBlock` samples and use the batch helpers in `vmath.h` (Accelerate's vForce
  on macOS, several times faster than scalar libm). Port the loop one-to-one
  first, check parity, then batch.
