## About
[Bfxr2](https://www.bfxr.net/) a tool for making sound effects for games, a rewrite/refresh of the flash tool Bfxr in javascript.

![image](https://github.com/user-attachments/assets/1701bccc-82d6-47e1-881c-ec6ca228dc89)

It's currently BETA, and new things should be coming to it, but the main addition right now is Obiwannabe's subtly wonderful footstep generator, ported from puredata to javsacript:

![image](https://github.com/user-attachments/assets/1f338401-d2e4-4100-ad4d-471ad6e56f6f)

## Transfxr

Transfxr moves a sound between two states, with independent curves for pitch, filter, wobble and level. A waveform morph can carry the sound into noise. Its 15 preset families use 228 curated states from a 512-sound survey, refined by listening feedback. Taps and chirps stay short, wavering voices sustain a quiver, soft pips use a gentle sine voice, and sand and air have distinct textures. Each family varies complete sound states while respecting locks. See [the revised listening catalogue](examples/Transfxr/survey/index.html) and [the example collection and controls](examples/Transfxr/README.md).

## Chattr

Chattr makes playful speech for game characters, from loose Animal Crossing-like chatter to connected formant speech. Type English words, choose a creature, and press **Say it!** (or Ctrl/Cmd+Enter). It runs locally and exports real WAV audio.

- **Articulation** moves from simplified vowel chirps to full consonants, vowel glides and connected speech. **Clear Speaker** provides a neutral reference alongside the eight creature voices. Pronunciation stays the same as you change character or articulation: “phone” starts with /f/, and “ship” and “sheep” have different vowels.
- **Babble / Squeak / Bleep** change the voice's source color while retaining the speaking mouth.
- **Pitch** and **Mouth size** independently shape the voice; **Chatter speed**, **Expression**, **Inflection** and **Word spacing** shape delivery. Questions rise, exclamations perk up, and punctuation adds pauses.
- Add **Wobble**, **Breath** and **Grit**, or change **Personality** for another repeatable reading. Character presets, Randomize and Mutate keep your text. Parameter locks keep favorite voice settings.
- Text (up to 160 characters) and voice settings travel together in sounds, collections, and share links. Use the usual WAV export for dialogue clips. Existing Chattr files and links load with the new articulation default.

The engine uses [klattsch](https://github.com/tgies/klattsch)'s glottal source, noise and three moving formants, with stressed pronunciations from [CMUdict](https://github.com/cmusphinx/cmudict). The synthesis is deliberately artificial; extreme voice settings trade clarity for character. Unfamiliar names use approximate spelling rules, homographs use the dictionary's first pronunciation, and other languages are not supported. Number expansion is bounded to 96 words, 512 phonemes and 60 seconds; playback reports a shortened line. Source revisions and complete licenses are in [THIRD_PARTY_CHATTR.md](THIRD_PARTY_CHATTR.md). Everything ships locally; the compact dictionary adds about 715 KB gzipped.

Run `node tools/render/chattr_examples.js` to render a listening comparison of the same sentence at 0%, 50% and 100% articulation, plus Village Mouse. Open `examples/Chattr/listen.html`; the accompanying `.bfxr` files are editable in the app. Automated tests check phonemes, synthesis, bounds and persistence; intelligibility still benefits from listening feedback.

## More sound makers

Six more tabs keep the Bfxr pattern: click a category to get a fresh sound, lock the controls you like, then Randomize or Mutate.

| Tab | What it makes | Random categories |
| --- | --- | --- |
| Clonkr | Material impacts, scrapes and rattles | 10 |
| Machinr | Motors, mechanisms and start/stop events | 8 |
| Weathr | Seamless rain, wind, fire, water and electrical loops | 9 |
| Jinglr | Musical cues with a combined seed and separate reseed controls | 8 |
| Squishr | Bubbles, suction, slime and elastic goo | 10 |
| Stackr | Layered events built from copies of sounds in other tabs | 8 |

Weathr has loop playback and a Stop button. Jinglr combines melody and instrument character in one ten-digit seed. Reseed either independently, with eight instrument families to audition against the same tune. Stackr provides a six-layer timeline with start time, level and pitch controls; source settings travel inside saved sounds and collections. All six save repeatable audio, including their random texture variations.

Try the [53-sound example collection and listening reel](examples/SoundCabinet/README.md), or compare [sixteen Jinglr voices playing the same tune](examples/Jinglr/README.md).

## Exotic game sounds

Five more tabs each have eight randomized preset categories, plus Randomize, Mutate and parameter locks:

| Tab | What it makes |
| --- | --- |
| Crittr | Nonverbal creatures with changing throats, segmented calls and growls |
| Signlr | Alien packets, coded transmissions, broken radios and beacons |
| Fractr | Glass, ice, crystal, armor and pixel objects breaking into bouncing pieces |
| Riftr | Portals, time reversal, gravity wells and dispersive force fields |
| Swarmr | Flocks, nanobots, fireflies, drone formations and seeking missiles |

All five save repeatable audio and can be copied into Stackr. Try the [40 editable examples and short listening reel](examples/Exotic/README.md). Rebuild them with `node tools/render/exotic_examples.js`.

## Interface sounds

Five tabs for the small interactions players hear throughout a game. Each has eight randomized preset buttons, plus the usual locks, Randomize and Mutate.

| Tab | What it makes |
| --- | --- |
| Tappr | Focus, selection, toggles and tactile press/release contacts |
| Rustlr | Cards, pages, bags, equipment, fabric and zips |
| Notifr | Messages, quest updates, warnings and success/failure alerts |
| Tickr | Reward counters, filling bars, countdowns and accelerating progress |
| Holor | Holographic cursors, map pings, target locks and panel gestures |

All five save exact variations and work as Stackr sources. Try the [40 editable examples and listening reel](examples/Interface/README.md). Rebuild with `node tools/render/interface_examples.js`.

## The tab deluge

Twelve more tabs, each with eight randomized categories:

| Tab | Sounds |
| --- | --- |
| Boomr | Pressure blasts, shockwaves and scattered debris. |
| Pewpr | Staged weapon pulses, charge, recoil and ricochets. |
| Zappr | Electrical arcs, crackles, hum and sparks. |
| Whooshr | Moving air, whistles and Doppler swishes. |
| Bouncr | Material contacts with shrinking bounce flights. |
| Rollr | Continuous rolling contacts, surfaces and wheel motion. |
| Breathr | Breathing, exertion and turbulent airflow. |
| Choirr | Detuned vowel ensembles and harmonic swells. |
| Pluckr | Feedback strings with excitation and damping. |
| Glitchr | Repeated, corrupted and missing digital fragments. |
| Pulser | Double pressure beats and turbulent body rhythms. |
| Rumblr | Low structural modes, shuddering pressure and grit. |

[96 editable examples and a listening reel](examples/Deluge/README.md). All support parameter locks, repeatable saved audio and Stackr copies. Rebuild with `node tools/render/deluge_examples.js`.

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

## Sound quality pass

Transfxr and Chattr offer Bfxr's twelve waveform choices; Chattr also retains its original vocal source. Character buttons vary the speaker as well as the delivery. Notifr has independent instrument reseeding, with different bell constructions sharing the same alert pattern.

Fractr, Boomr, Rustlr and Rollr now emphasize fractures, turbulent pressure and continuous material contact. Tappr presets make single interface gestures; a second contact remains optional. Breathr offers Airflow, Retro and Snore, and Pluckr offers Nylon, Steel, Gut, Rubber, Glass and Gravity strings.

To combine sounds, open Stackr and choose **New empty stack**, then click **Layer in Stackr** from any sound tab. Layers start together; change **Start (s)** to sequence them. Their copied settings remain independent of the originals.

[32 editable examples and a 26.5-second listening reel](examples/Quality/README.md) compare the revised engines, three bell seeds with the same alert pattern, and six string materials at the same tuning. Rebuild with `node tools/render/quality_examples.js`.
