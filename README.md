## About
[Bfxr2](https://www.bfxr.net/) a tool for making sound effects for games, a rewrite/refresh of the flash tool Bfxr in javascript.

![image](https://github.com/user-attachments/assets/1701bccc-82d6-47e1-881c-ec6ca228dc89)

It's currently BETA, and new things should be coming to it, but the main addition right now is Obiwannabe's subtly wonderful footstep generator, ported from puredata to javsacript:

![image](https://github.com/user-attachments/assets/1f338401-d2e4-4100-ad4d-471ad6e56f6f)

## Transfxr

Transfxr moves a sound between two states, with independent curves for pitch, filter, wobble and level. A waveform morph can carry the sound into noise. Its 15 preset families use 228 curated states from a 512-sound survey, refined by listening feedback. Taps and chirps stay short, wavering voices sustain a quiver, soft pips use a gentle sine voice, and sand and air have distinct textures. Each family varies complete sound states while respecting locks. See [the revised listening catalogue](examples/Transfxr/survey/index.html) and [the example collection and controls](examples/Transfxr/README.md).

## Sound makers

The app has 23 synths. Preset buttons choose fresh sounds, parameter locks preserve favorite settings, and Randomize and Mutate explore variations.

| Synth | Sounds |
| --- | --- |
| Bfxr | Classic game sound effects. |
| Footsteppr | Footsteps on snow, grass, dirt, gravel and wood. |
| Mixr | Two copied sounds mixed together, with independent generators and a balance control. |
| Transfxr | Transitions between complete sound states. |
| Jinglr | Musical cues with independent melody and instrument seeds. |
| Pluckr | Plucked strings with material, damping, vibrato and tremolo controls. |
| Choirr | Detuned vowel ensembles and harmonic swells. |
| Crittr | Creature calls, changing throats and growls. |
| Birdr | Bird calls and trills. |
| Swarmr | Flocks, nanobots, fireflies and drone formations. |
| Clonkr | Material impacts, scrapes and rattles. |
| Bouncr | Material contacts with shrinking bounce flights. |
| Fractr | Glass, ice, crystal and other objects breaking into bouncing pieces. |
| Boomr | Pressure blasts, shockwaves and scattered debris. |
| Rustlr | Cards, pages, bags, equipment, fabric and zips. |
| Squishr | Bubbles, suction, slime and elastic goo. |
| Machinr | Motors, mechanisms and start/stop events. |
| Breathr | Breathing, exertion, turbulent airflow and snoring. |
| Whooshr | Moving air, whistles and Doppler swishes. |
| Signlr | Alien packets, coded transmissions, broken radios and beacons. |
| Riftr | Portals, time reversal, gravity wells and dispersive force fields. |
| Zappr | Electrical arcs, crackles, hum and sparks. |
| Glitchr | Repeated, corrupted and missing digital fragments. |

Use **Mix this sound** to copy a sound into Mixr. The copied settings stay independent of the original. Choose generators for either slot and use Regen or Regen Both to explore new combinations.

## Listening examples

- [Sound Cabinet](examples/SoundCabinet/README.md): 40 editable material, machine, musical and liquid sounds.
- [Jinglr palette](examples/Jinglr/README.md): sixteen instruments playing the same tune.
- [Exotic sounds](examples/Exotic/README.md): 40 creature, signal, fracture, field and swarm examples.
- [Inventory sounds](examples/Interface/README.md): eight Rustlr examples.
- [The tab deluge](examples/Deluge/README.md): 71 examples across eight synths.
- [Sound quality examples](examples/Quality/README.md): 18 editable examples, including string materials and waveform choices.
- [Mixr and friends](examples/Cabinet/index.html): editable mixtures and individual source comparisons.
- [Refined sounds](examples/Refined/index.html): 27 editable effects.

Example generators live in `tools/render/`. They check finite, bounded, audible output and exact replay of saved parameters. Retired engines have been removed; older collection records remain preserved when saving, but their sounds cannot be rendered.

## Embed in another app

Copy [bfxrlib.min.js](lib/bfxrlib.min.js) into your project and include it with an ordinary script tag. All 23 synths and their presets are bundled; audio setup and caching are automatic.

```html
<script src="bfxrlib.min.js"></script>
<script>
  var jump = bfxr.preset("Bfxr", "jump", 12345);
</script>
<button onclick="bfxr.play(jump)">Jump</button>
<button onclick="bfxr.playMutated(jump)">Varied jump</button>
```

See the [library API](lib/README.md) and [standalone HTML example](lib/example.html). The complete build, including license texts, is approximately 326 kB minified, 106 kB gzip. Consumers need no npm install, module loader, external assets, or setup call. Rebuild with `node tools/build-library.js` or `npm run build:lib`.

## Development
cf. [DEVELOPMENT.md](https://github.com/increpare/bfxr2/blob/master/DEVELOPMENT.md).

## Archaeology

I don't know if it's genetically related, but I believe that _why made a program called sound foley (which I haven't been able to get to work) which looks quite similar to Sfxr in design based on what I've seen of his _why's presentation of it.
The darling DrPetter made the program this is based on, Sfxr:

* http://drpetter.se/
* http://drpetter.se/article_sound.html
* http://drpetter.se/project_sfxr.html
The fabulous Tom Vian did a flash port of this, called as3sfxr
* http://www.tomvian.com/
* http://www.superflashbros.net/as3sfxr/
There's also a port of Sfxr to OS X that's quite loved by people (and was a little influential) called cfxr:
* http://thirdcog.eu/apps/cfxr
I did a mod of as3sfxr that introduced some new features, and called it as3sfxr-b:
* http://ded.increpare.com/~locus/as3sfxr-b/
After asking for feedback, I spent some time adding and changing more things, making something new. Which is Bfxr. Which is what you see on this page.

Code from
Bulk of coding of this version done by poor little me. In addition to code from Tom/DrPetter, code snippits were taken from

* http://www.firstpr.com.au/dsp/pink-noise/#Filtering for pink-noise related synthesis

Thanks + Acknolwedgements
* DrPetter, for Sfxr.
* Tom Vian, for his elegantly constructed as3sfxr port.
* @docky, @Draknek, @KommanderKlobb, @eigenbo, @GrimFang4, @nyarla, @bfod, @jasperbyrne, @draknek, @hybridmind, @RinkuHero, DustinGunn, mcc, and agj for feedback + suggestions. And Derek for some early encouragement.
The people from the #flex irc room on freenode for technical help in my hour of need, especially J_A_X.

Other software that can be software for making sounds:
* Audacity - http://audacity.sourceforge.net/
* HighC - http://highc.org/
* PXTone - http://buzinkai.net/PXTone/tutorial/
* Sound Effects Generator - http://www.windowsgames.co.uk/effects.html (windows only. I nicked a couple of things from this. )
* Freesound - http://www.freesound.org - Okay, not sound software, but a really amazing resource.
* ChipTone - https://sfbgames.itch.io/chiptone
