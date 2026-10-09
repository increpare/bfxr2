# bfxrlib

Copy `bfxrlib.min.js` to your project. It includes all 23 current synths, preset generators and waveform data. It creates one global, `bfxr`, and needs no other files, npm, module loader or initialization. `bfxrlib.js` is the readable version. Open `example.html` directly in a browser to try it.

```html
<script src="bfxrlib.min.js"></script>
<script>
  var jump = bfxr.preset("Bfxr", "jump", 12345);
</script>
<button onclick="bfxr.play(jump)">Jump</button>
<button onclick="bfxr.playMutated(jump)">Varied jump</button>
```

Call playback from a click, keypress or another user gesture to satisfy browser autoplay rules. The library creates and resumes its AudioContext automatically. If playback is attempted before a gesture, it also tries to unlock audio on the next gesture.

## Presets and exported sounds

```js
bfxr.synths();                   // ["Bfxr", "Footsteppr", "Transfxr", ...]
bfxr.presets("Bfxr");            // ["pickup_coin", "laser_shoot", ...]
bfxr.presets("Jinglr");          // ["confirm", "message", ...]
var cue = bfxr.preset("Jinglr", "confirm", "menu-confirm");
```

Synth and preset IDs are case-sensitive strings. They come from the existing preset generators, so there are no numeric preset enums to keep synchronized. Footsteppr's categories are `snow`, `grass`, `dirt`, `gravel` and `wood`.

An optional finite number or string seed reproduces the generated settings and noise. Omit it for a fresh sound. The result is ordinary data:

```js
{
  synth_type: "Bfxr",
  version: "1.0.4",              // Engine version, not the library version.
  params: { /* sound controls */ },
  renderSeed: 0.2922589511       // Repeatable noise used by legacy engines.
}
```

Save it with `JSON.stringify(sound)`. `play`, `playMutated`, `render` and the cache functions accept either this object or a JSON string exported from the editor as a `.bfxr` file. No filename is needed. Older exports without `renderSeed` use 0.5. Known controls are normalized through the same bounds and migrations as Mixr's saved sounds. Unknown synths and preset IDs throw descriptive errors; retired synths are unsupported.

## Playback

```js
var voice = bfxr.play(cue);
voice.stop();

var quieter = bfxr.play(cue, {volume: 0.5, pitch: -12, loop: true});
quieter.stop();
bfxr.stopAll();
```

Each call creates an independent voice, so repeated calls overlap. `stop()` is safe to call again or after a voice finishes. Finished voices disconnect automatically.

Options are `volume` (nonnegative gain, default 1), `pitch` (−96 to 96 semitones, default 0), and `loop` (boolean, default false). Changing these playback options reuses the same rendered buffer. Pitch shifts use playback speed, so they also change duration.

## Mutations and caching

```js
bfxr.playMutated(cue);                       // amount 0.05, pool of 15
bfxr.playMutated(cue, 0.03, 8, {volume: 0.5});

await bfxr.cache(cue);
await bfxr.cacheMutations(cue, 0.03, 8);
bfxr.clearCache();
```

The first 15 default mutated plays each create and cache one variation; later calls pick from that pool. Changing the sound, amount or count selects a separate pool. Amount is 0–1, as a fraction of each numeric control's range; count is an integer from 1–256. Amount 0 plays the original.

Every variation starts from the original; mutations never drift or edit your sound object. Waveforms, discrete instrument choices, master volume, texture/instrument seeds, transition curves and edited musical notes remain fixed. Mixr keeps its source choices and mutates numeric controls inside their saved sounds.

The two prewarm functions return Promises and create no AudioContext. They yield before rendering and between variations so a UI can update; individual renders still run on the main thread. Playback normally fills caches on demand, so prewarming is optional. `clearCache()` also cancels outstanding prewarming and leaves playing voices alone.

Equivalent normalized settings reuse buffers even if supplied as different objects or JSON strings. Filenames and object property order do not affect cache keys. PCM and AudioBuffers share a 32 MiB LRU budget; mutation definitions have a separate 4 MiB/256-pool limit. Older entries can be evicted and reproduced when needed. Active voices retain their buffers until they finish, independently of those cache limits.

## Use with your own audio system

```js
var samples = bfxr.render(cue); // A fresh mono Float32Array copy.
var rate = bfxr.sampleRate;     // 44100.
```

Rendering needs no browser DOM or AudioContext. You own the returned array; editing it cannot change cached sounds. `bfxr.version` identifies the library API version.

## Build and redistribute

Run `node tools/build-library.js` from the repository, or `npm run build:lib`. Node and uglify-js are build-time dependencies only. The editor and library use the same synthesis sources. PureData terrain patches compile at build time, so the delivered scripts use no runtime `eval`, `Function` compilation, fetches or asset downloads.

The complete minified build, including license texts, is approximately **326 kB**, or **106 kB gzip**. Gzip describes compressed network delivery; the file you include is still `bfxrlib.min.js`. The build command prints exact current sizes.

Both JS files embed license and attribution notices. Preserve those when redistributing. The library contains MIT-licensed Bfxr2 code, Apache-2.0 SfxrSynth-derived DSP, and CC0 Adventure Kid waveform data.
