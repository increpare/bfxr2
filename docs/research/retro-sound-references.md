# Retro game sound references, by game verb

A research catalogue for the Soundboard. For each of the 25 verbs it lists 20 or more
sound effects from actual retro games, with a short description of the acoustic character:
source waveform, pitch motion, duration, envelope. The point is not to copy any of them but
to widen the range of interpretations each verb button can produce.

**How this was made, honestly.** No audio is included or was downloaded; redistributing ripped
game audio is not something this repository should do. The entries are written from memory of
the games, so treat every description as approximate and verify by ear before relying on it.
Durations are rough. Where a description is a guess at mechanism rather than a clear memory it
says "roughly". The **Archetypes** line under each verb is what was carried into the synths:
Transfxr verb presets, engine verb preset variants and Soundboard catalogue entries. The
archetype ids are referenced from `js/synths/Transfxr.js` and the engine recipes.

Abbreviations: sq = square/pulse wave, tri = triangle, saw = sawtooth, sin = sine, N = noise.
NES/Famicom = 2A03 (two pulse, one triangle, noise, DPCM); SMS = SN76489 (three sq, one N);
C64 = SID; Genesis/MD = YM2612 FM + SN76489; GB = Game Boy (two pulse, wave, noise);
SNES = SPC700 samples; Arcade varies.

---

## Jump

1. **Super Mario Bros. (NES, 1985)** — jump: sq, fast upward sweep ~0.2 s, starts around 300 Hz and rises over an octave and a half, quick linear decay.
2. **Super Mario Bros. (NES)** — big Mario jump: same sweep starting lower (~200 Hz), slightly longer.
3. **Sonic the Hedgehog (MD, 1991)** — spin jump: FM, short rising "bwip" with a sharp attack, ~0.25 s, brighter than Mario, slight downward tail.
4. **Mega Man 2 (NES, 1988)** — jump is silent; landing clicks. (Included as a reminder that many platformers put the sound on the land, not the jump.)
5. **Castlevania (NES, 1986)** — jump is silent too; whip and landing carry the weight.
6. **Donkey Kong (Arcade, 1981)** — Jumpman jump: a low sq "boing" with a quick up-down pitch bend, ~0.3 s.
7. **Pitfall! (Atari 2600, 1982)** — jump: a short two-step sq blip rising, very dry, under 0.2 s.
8. **Prince of Persia (Apple II / DOS, 1989)** — jump: a cloth and breath "huff", noise-based, no tone.
9. **Kid Icarus (NES, 1986)** — jump: sq rising chirp similar to Mario but shorter and higher.
10. **Metroid (NES, 1986)** — Samus jump: sq rising sweep with a little vibrato, slightly longer, ~0.3 s.
11. **Duck Tales (NES, 1989)** — pogo bounce: sq quick rise then immediate fall ("boing"), ~0.25 s.
12. **Super Mario World (SNES, 1990)** — jump: sampled, rounded rising sweep with a soft attack, spin jump adds a rolled flutter.
13. **Yoshi's Island (SNES, 1995)** — Yoshi flutter jump: a repeated short rising chirp pattern, three or four pulses.
14. **Commander Keen 4 (DOS, 1991)** — jump: PC speaker rising sq, very thin, ~0.2 s, pogo adds a second higher blip.
15. **Alex Kidd in Miracle World (SMS, 1986)** — jump: sq rising sweep, shorter and more nasal than Mario.
16. **Wonder Boy (SMS/Arcade, 1986)** — jump: sq two-note hop, up a fourth, dry.
17. **Bubble Bobble (Arcade, 1986)** — jump: sq quick rising "pip" with a little vibrato on the end.
18. **Ghosts 'n Goblins (Arcade, 1985)** — jump: a short noise puff plus a low sq thump, cloth-like.
19. **Kirby's Adventure (NES, 1993)** — jump: soft sq rising sweep with a rounded attack, ~0.2 s; flying puff is a noise burst.
20. **Celeste (2018, retro style)** — jump: layered sq sweep with a small noise transient, ~0.15 s; dash is a longer noise whoosh.
21. **Super Meat Boy (2010, retro style)** — jump: short wet "splat-boing", noise plus pitch bend.
22. **Chip 'n Dale Rescue Rangers (NES, 1990)** — jump: sq rising chirp with a quick duty-cycle change, bright.

**Archetypes:** `jump_sweep` (sq rising sweep, the Mario family), `jump_boing` (up-then-down bend, Donkey Kong, Duck Tales), `jump_hop` (two discrete rising notes, Pitfall, Wonder Boy), `jump_puff` (noise breath, Prince of Persia, Ghosts 'n Goblins), `jump_flutter` (repeated rising chirps, Yoshi), `jump_chirp` (short high vibrato pip, Bubble Bobble, Kid Icarus).

## Land

1. **Mega Man (NES)** — landing: short noise tick, under 0.05 s, very dry.
2. **Castlevania (NES)** — landing: low sq thud with a noise click, ~0.1 s.
3. **Super Mario Bros. 3 (NES)** — landing is silent; stomp on enemy is a sq "boink" (see Hit).
4. **Prince of Persia (DOS)** — landing from height: a heavy "oof" grunt plus a floor thud; hard landing adds a crunch.
5. **Flashback (Amiga/MD, 1992)** — landing: sampled footfall thud with a bit of gravel.
6. **Another World (Amiga, 1991)** — landing: a deep sampled thump.
7. **Donkey Kong Country (SNES, 1994)** — landing: sampled soft thud; roll adds grass rustle.
8. **Super Metroid (SNES, 1994)** — landing: metallic boot clank, two-part (heel and toe), ~0.15 s.
9. **Sonic the Hedgehog (MD)** — landing is silent; rolling and skidding make noise sweeps.
10. **Mario 64 (N64, 1996)** — landing: sampled "thump" with Mario's grunt on hard landings.
11. **Rayman (PS1, 1995)** — landing: light sampled pat.
12. **Earthworm Jim (MD/SNES, 1994)** — landing: a sq "bonk" plus a splat.
13. **Shovel Knight (2014, NES style)** — landing: short noise burst with low sq thump, ~0.08 s.
14. **Cave Story (2004, retro style)** — landing: quick sq blip downward, very short.
15. **Spelunky (2008/2012)** — landing: sampled dirt thud; landing on spikes is a crunch.
16. **Bionic Commando (NES, 1988)** — landing: noise tick plus low sq.
17. **Contra (NES, 1987)** — landing: a short low sq "duh", and a noise tick when prone.
18. **Ninja Gaiden (NES, 1988)** — landing: metallic sq tick, bright and very short.
19. **Golden Axe (Arcade, 1989)** — landing: sampled ground thump with a dusty tail.
20. **Street Fighter II (Arcade, 1991)** — landing after a jump: a sampled "tup", short, mid-low.
21. **Super Mario World (SNES)** — ground pound: a deep sampled thud with a rumble tail, ~0.4 s.

**Archetypes:** `land_tick` (dry noise click, Mega Man), `land_thud` (low tone plus noise, Castlevania, Contra), `land_clank` (two-part metallic, Super Metroid), `land_heavy` (deep thump with rumble tail, ground pound), `land_grunt` (effort voice plus thud, Prince of Persia).

## Step

1. **Prince of Persia (DOS)** — footsteps: dry sampled stone taps, alternating two pitches.
2. **Flashback (Amiga)** — footsteps: sampled boot on metal, bright click with ring.
3. **Another World (Amiga)** — footsteps: soft stone pats, slow.
4. **Metal Gear (MSX2, 1987)** — footsteps are silent; guard footsteps are a soft sq tick pattern.
5. **Metal Gear Solid (PS1, 1998)** — footsteps: sampled per-surface taps, metal grating rings.
6. **Resident Evil (PS1, 1996)** — footsteps: sampled hard-soled taps on wood with hall echo.
7. **Silent Hill (PS1, 1999)** — footsteps: sampled scrapes on concrete, slightly gritty.
8. **Doom (DOS, 1993)** — no footsteps; the absence is part of its style.
9. **Shadow of the Beast (Amiga, 1989)** — footsteps: sampled grass swish per step.
10. **Zelda: Link's Awakening (GB, 1993)** — walking is silent; grass makes a noise rustle per step.
11. **Pokémon Red (GB, 1996)** — bump into wall: a sq "thunk", low and short; no step sound.
12. **Super Mario 64 (N64)** — footsteps: per-surface samples, sand is a soft shush, metal a clink, snow a crunch.
13. **Tomb Raider (PS1, 1996)** — footsteps: sampled per-surface taps with a slight echo.
14. **Half-Life (PC, 1998)** — footsteps: four-sample cycles per material; metal grate rings, vent booms.
15. **Thief: The Dark Project (PC, 1998)** — footsteps: carpet whisper, tile click, metal clang; the whole game is about them.
16. **Ocarina of Time (N64, 1998)** — footsteps: light sampled taps; grass swish, water splash.
17. **Little Big Adventure (DOS, 1994)** — footsteps: light sampled pats with a slight slap.
18. **Oddworld: Abe's Oddysee (PS1, 1997)** — footsteps: sampled soft pats on stone with a hollow room.
19. **Castlevania: Symphony of the Night (PS1, 1997)** — footsteps: sampled boot clacks on marble with echo.
20. **Earthbound (SNES, 1994)** — walking is silent; bumping and menus carry the taps.
21. **Super Mario World (SNES)** — footsteps are silent; the land and skid carry the feet.

**Archetypes:** `step_tap` (dry tone-less tap, stone or wood), `step_metal` (short click with a ring), `step_grass` (noise swish), `step_crunch` (gravel or snow), `step_pair` (alternating two pitches, Prince of Persia). Footsteppr already covers tap, grass, gravel, wood and snow; Clonkr and Fractr cover metal and crunch.

## Dash

1. **Mega Man X (SNES, 1993)** — dash: sampled noise whoosh with a rising start, ~0.3 s.
2. **Mega Man 3 (NES, 1990)** — slide: short sq descending blip with a noise edge.
3. **Sonic the Hedgehog 2 (MD, 1992)** — spin dash charge: repeated rising FM revs, then a release whoosh.
4. **Sonic the Hedgehog (MD)** — speed shoes / skid: sampled brake screech with falling pitch.
5. **Celeste (2018)** — dash: layered noise whoosh with a tonal "zip" rising, ~0.25 s.
6. **Super Metroid (SNES)** — speed booster: a cycling sampled whoosh that builds; shinespark adds a rising tone.
7. **Metroid (NES)** — run is silent; morph ball roll is a soft sq tick cycle.
8. **Zelda: A Link to the Past (SNES, 1991)** — Pegasus boots dash: a sampled whoosh with footstep rattle.
9. **Street Fighter II (Arcade)** — dash does not exist; the whoosh of a jump kick is the nearest: sampled air swish.
10. **Ninja Gaiden (NES)** — wall jump off and dash: short noise burst with a sq tick.
11. **Castlevania: Rondo of Blood (PC Engine, 1993)** — backflip: a light sampled air swish, ~0.2 s.
12. **Strider (Arcade, 1989)** — slide: a scraping noise burst, bright and gritty.
13. **Shinobi (Arcade, 1987)** — jump dash: short sq descending with noise.
14. **Gunstar Heroes (MD, 1993)** — slide: a noise whoosh with a low thump at the end.
15. **Kirby Super Star (SNES, 1996)** — dash: a soft puff repeating per step, noise-based.
16. **Super Mario Bros. 3 (NES)** — P-meter run: a repeating sq tick accelerating, then the flight chime.
17. **F-Zero (SNES, 1990)** — boost: a rising filtered noise sweep with a tonal shimmer, ~0.6 s.
18. **Wipeout (PS1, 1995)** — boost pad: a rising sampled sweep with a bright tonal swell.
19. **Rocket Knight Adventures (MD, 1993)** — rocket dash: FM rising burst plus noise jet, ~0.4 s.
20. **Mega Man Zero (GBA, 2002)** — dash: short sampled whoosh with a quick low thump.
21. **Hollow Knight (2017)** — dash: a sharp noise swish with a low body.

**Archetypes:** `dash_whoosh` (rising-then-falling filtered noise), `dash_zip` (tonal rising zip plus noise), `dash_rev` (repeated rising revs then release, spin dash), `dash_skid` (falling screech), `dash_boost` (long rising sweep with shimmer).

## Splash

1. **Super Mario Bros. (NES)** — entering water is silent; swimming stroke is the jump sweep, so Mario has no splash.
2. **Sonic the Hedgehog (MD)** — water splash: sampled splash with bubbles, ~0.5 s.
3. **Donkey Kong Country (SNES)** — water entry: sampled splash with a low "bloop".
4. **Zelda: Link's Awakening (GB)** — water splash: noise burst shaped with a quick low-pass fall, ~0.3 s.
5. **Zelda: A Link to the Past (SNES)** — water splash: sampled splash; swimming is a repeated small splash.
6. **Ecco the Dolphin (MD, 1992)** — jump out of water: FM swell plus sampled splash.
7. **Frogger (Arcade, 1981)** — drowning splash: descending sq warble with a noise burst.
8. **Pitfall! (Atari 2600)** — fall into water: a short noise burst and a low tone.
9. **Super Mario 64 (N64)** — water entry: sampled splash, bubbles, and a low thump for the dive.
10. **Banjo-Kazooie (N64, 1998)** — splash: sampled with a bright top and a bubbly tail.
11. **Earthworm Jim (MD)** — splat: a wet noise burst with a low sq "plop".
12. **Wario Land (GB, 1994)** — water: noise burst with a sq "glug" sinking.
13. **Kirby's Dream Land (GB, 1992)** — water splash: noise burst with a short low-pass sweep.
14. **Chrono Trigger (SNES, 1995)** — water drop / splash menu: a sampled "plip" with a rising bubble pitch.
15. **Secret of Mana (SNES, 1993)** — water spells: swirling filtered noise with bubbles.
16. **Super Mario World (SNES)** — splash: sampled, bright, with a "bloop" at the end.
17. **Metroid Prime (GC, 2002)** — water entry: deep sampled plunge with filtered rumble.
18. **Spelunky (2008)** — water splash: noise burst plus bubble tones.
19. **Oddworld (PS1)** — dive: deep sampled plunge, long bubbly tail.
20. **Mega Man 2 (NES)** — Bubble Man's stage: bubbles rising are sq rising blips; no real splash exists on the 2A03, which is interesting in itself.
21. **Duck Hunt (NES, 1984)** — the duck falling into the grass: a descending sq "plop" with noise.

**Archetypes:** `splash_burst` (noise burst with falling low-pass, the GB family), `splash_plop` (low tone "bloop" plus noise), `splash_bubble` (rising bubble pitch, Chrono Trigger plip), `splash_plunge` (deep plunge with a long bubbly tail), `splash_glug` (sinking descending warble, Frogger).

## Shoot

1. **Space Invaders (Arcade, 1978)** — player shot: a fast descending sq sweep, ~0.1 s, with the famous "pew".
2. **Asteroids (Arcade, 1979)** — fire: a short sq "pip" with a tiny falling tail.
3. **Galaga (Arcade, 1981)** — fire: a short rising-then-falling sq chirp, bright.
4. **Defender (Arcade, 1981)** — laser: a harsh sq descending sweep with noise, ~0.15 s.
5. **Mega Man (NES)** — buster: sq very short descending blip, ~0.08 s; charged shot (MM4) is a longer noisy sq blast.
6. **Contra (NES)** — rifle: a sq descending blip plus a noise click, ~0.1 s; spread gun is three overlapping.
7. **Gradius (NES/Arcade, 1985)** — shot: sq quick falling chirp; laser is a sustained high sq with vibrato.
8. **R-Type (Arcade, 1987)** — wave cannon charge: a rising FM swell; release is a sampled blast.
9. **Metroid (NES)** — beam: sq descending blip; ice beam adds a higher second voice; missile is a noise whoosh.
10. **Super Metroid (SNES)** — power beam: sampled "pyoo" with a quick fall; charge beam builds a rising hum.
11. **Doom (DOS)** — pistol: sampled sharp crack with a short low body; shotgun: bigger crack plus pump.
12. **Wolfenstein 3D (DOS, 1992)** — pistol: sampled "pkow" with a bright transient.
13. **Duke Nukem 3D (DOS, 1996)** — pistol: sampled snappy crack; shotgun deep boom.
14. **Zelda (NES)** — sword beam: a sq rising-falling "fweep", ~0.3 s.
15. **Star Fox (SNES, 1993)** — laser: sampled bright "pew" with a quick falling pitch.
16. **Gun.Smoke / Commando (Arcade)** — rifle: short noise crack with a sq tick.
17. **Xevious (Arcade, 1982)** — zapper: rapid sq "tik" blips; blaster bomb is a descending noise.
18. **Phantasy Star / Alien Syndrome (SMS)** — gun: sq falling blip with noise edge.
19. **Thunder Force III (MD, 1990)** — shot: FM short descending "pyu" with a bright click.
20. **Half-Life (PC)** — pistol: sampled crack with a ring; crossbow a thwip.
21. **GoldenEye 007 (N64, 1997)** — PP7 silenced: a soft sampled "pft" thud.
22. **Cave Story (2004)** — polar star: sq quick descending blip, dry.

**Archetypes:** `shoot_pew` (fast descending sq sweep), `shoot_pip` (tiny tick, Asteroids, Mega Man), `shoot_chirp` (rise then fall, Galaga, Zelda beam), `shoot_crack` (noise transient plus low body, Doom), `shoot_laser` (sustained high tone with vibrato, Gradius), `shoot_charge` (rising swell then blast, R-Type).

## Swing

1. **Castlevania (NES)** — whip: a sharp noise crack, ~0.1 s, with a tiny sq tick on the hit.
2. **Zelda (NES)** — sword: a sq short descending "shing" with a quick vibrato, ~0.15 s.
3. **Zelda: A Link to the Past (SNES)** — sword: sampled bright metallic swish with a ring; spin attack adds a sweep.
4. **Zelda: Ocarina of Time (N64)** — sword swing: sampled air swish, ~0.2 s, plus Link's voice.
5. **Ninja Gaiden (NES)** — sword: a very short sq "tsk" with noise, under 0.1 s.
6. **Golden Axe (Arcade)** — axe swing: sampled whoosh, mid-low, ~0.3 s.
7. **Street Fighter II (Arcade)** — normal attack whiff: sampled air swish, three sizes (light, medium, heavy).
8. **Final Fight (Arcade, 1989)** — punch whiff: sampled "whff", short.
9. **Prince of Persia (DOS)** — sword swing: sampled whoosh with a metallic ring on contact.
10. **Shovel Knight (2014)** — shovel swing: noise swish with a sq "ting".
11. **Secret of Mana (SNES)** — sword swing: sampled swish, charge levels add rising tone.
12. **Chrono Trigger (SNES)** — Crono's katana: sampled fast swish with a bright metallic edge.
13. **Mega Man X (SNES)** — Zero's saber (X3): sampled bright swish with an energy hum.
14. **Super Mario RPG (SNES, 1996)** — hammer swing: a sampled whoosh and bonk.
15. **Double Dragon (Arcade, 1987)** — punch whiff: a short noise burst.
16. **Rygar (Arcade/NES, 1986)** — diskarmor throw: sq rising-falling whir with noise.
17. **Kid Icarus (NES)** — arrow: sq short "pyew" (really a shoot).
18. **Castlevania: SotN (PS1)** — sword swing: sampled whoosh with a stereo flutter.
19. **Golden Sun (GBA, 2001)** — sword slash: sampled bright slash with a quick ring.
20. **Soul Blade (PS1, 1996)** — swing whiff: layered sampled whoosh, big and low.
21. **Bushido Blade (PS1, 1997)** — swing: a dry air swish, then a wet cut on contact.

**Archetypes:** `swing_whoosh` (filtered noise swish, three sizes), `swing_crack` (whip snap), `swing_shing` (short tone with vibrato and a metallic edge), `swing_whir` (rising-falling whir, thrown weapon), `swing_hum` (energy blade: whoosh plus a tonal hum).

## Hit

1. **Super Mario Bros. (NES)** — stomp: a sq "boink" rising then falling quickly, ~0.15 s.
2. **Super Mario Bros. (NES)** — block bump: a short sq descending thunk, ~0.1 s.
3. **Mega Man (NES)** — enemy hit: a noise "tsh" tick, ~0.05 s.
4. **Street Fighter II (Arcade)** — light hit: sampled sharp slap; heavy hit: a deep sampled thud with a crunch.
5. **Final Fight (Arcade)** — punch landing: sampled meaty thump.
6. **Punch-Out!! (NES, 1987)** — punch hit: a sampled-ish DPCM thud with a high tick.
7. **Zelda (NES)** — sword hits enemy: a sq short descending "tink"; hitting a wall is a higher "tink".
8. **Zelda: ALttP (SNES)** — sword hit: sampled metallic "ting" with a ring; hitting flesh is a dull thud.
9. **Contra (NES)** — bullet hit enemy: a short noise burst; boss hit is a sq "tung".
10. **Castlevania (NES)** — whip hit: sq descending "tunk" plus noise.
11. **Double Dragon (NES)** — punch hit: a low sq thud with a noise edge.
12. **Mortal Kombat (Arcade, 1992)** — hit: sampled wet thud with a bone crunch.
13. **Golden Axe (Arcade)** — hit: sampled metallic chop plus grunt.
14. **Sonic (MD)** — hitting a badnik: a sampled "pop" burst; monitor break is a glassy pop.
15. **Breakout / Arkanoid (Arcade)** — paddle hit: a sq "tick" at one pitch; brick hit a different pitch.
16. **Pong (Arcade, 1972)** — paddle: a short sq "pok" at one pitch; wall a lower pitch.
17. **Tetris (GB, 1989)** — piece lands: a short sq "tuk".
18. **Kirby's Adventure (NES)** — inhale hit / star hit: sq descending "bonk" with vibrato.
19. **Ghosts 'n Goblins (Arcade)** — lance hits: a bright sq "tink" with noise.
20. **Earthbound (SNES)** — bash hit: sampled "whack" with a little comic reverb.
21. **Bomberman (NES, 1985)** — bomb explodes (see Explode), but a wall hit is a short sq tick.
22. **Super Smash Bros. (N64, 1999)** — hit: sampled punch with a bright snap, heavier hits add a low boom.

**Archetypes:** `hit_boink` (up-then-down tone), `hit_thunk` (short falling tone plus noise), `hit_tick` (noise-only tick), `hit_ting` (metallic ring), `hit_thud` (deep body with a crunch), `hit_pok` (single-pitch pure tick, Pong, Breakout).

## Hurt

1. **Super Mario Bros. (NES)** — shrink/hurt: a sq descending warble with a pitch wobble, ~0.4 s.
2. **Sonic (MD)** — lose rings: a bright sampled ring scatter plus a FM "ouch" sweep.
3. **Mega Man (NES)** — hurt: a sq descending buzz with vibrato and a noise edge, ~0.3 s.
4. **Zelda (NES)** — Link hurt: a sq fast descending "wee-oo" with a second lower voice.
5. **Zelda: ALttP (SNES)** — Link hurt: a sampled grunt-like "uh" from the SPC, short.
6. **Zelda: OoT (N64)** — Link hurt: sampled voice "augh" plus a hit thud.
7. **Castlevania (NES)** — Simon hurt: a sq descending with a quick noise burst, ~0.3 s.
8. **Metroid (NES)** — Samus hurt: a sq rapidly repeating descending blip, buzzy.
9. **Super Metroid (SNES)** — Samus hurt: sampled electronic "dzzt" with a falling tone.
10. **Contra (NES)** — death: a sq descending sweep followed by a noise crash.
11. **Pac-Man (Arcade, 1980)** — death: a long descending wobbling sq sweep ending in two pops, ~1.5 s (also Lose).
12. **Street Fighter II (Arcade)** — hurt voice: sampled grunts in two sizes.
13. **Kirby's Adventure (NES)** — hurt: a sq descending "bwoo" with a noise burst.
14. **Pokémon Red (GB)** — low HP: repeating sq high beep (really Alert); hurt is the attack hit "thump".
15. **Final Fantasy (NES, 1987)** — damage: a sq "tch" tick plus a short descending tone.
16. **Final Fantasy VI (SNES, 1994)** — damage: sampled hit "tssh" with a pitched edge.
17. **Doom (DOS)** — player hurt: sampled grunt "ugh", two variants.
18. **Quake (PC, 1996)** — player hurt: sampled grunts with a low body.
19. **Mega Man X (SNES)** — X hurt: sampled electronic "zzt" plus a short voice.
20. **Duck Tales (NES)** — hurt: sq descending wobble, short.
21. **Prince of Persia (DOS)** — hurt: sampled grunt plus a sword "clang" when parried.
22. **Shovel Knight (2014)** — hurt: sq descending buzz with noise, NES-style.

**Archetypes:** `hurt_warble` (descending wobbling tone, Mario, Pac-Man), `hurt_buzz` (descending buzz with vibrato plus noise, Mega Man), `hurt_twovoice` (fast descent on two voices, Zelda), `hurt_stutter` (rapid repeated descending blips, Metroid), `hurt_grunt` (voice plus thud), `hurt_zzt` (electronic short crackle, X).

## Explode

1. **Space Invaders (Arcade)** — invader death: a noise burst with a quick fall, ~0.2 s.
2. **Asteroids (Arcade)** — asteroid breaks: a noise burst, three sizes, low-pass falling.
3. **Bomberman (NES)** — bomb: a noise burst with a low sq thump, ~0.4 s.
4. **Mega Man (NES)** — enemy death: a sq rapidly rising-falling warble "bweep-bweep" plus noise; boss death is a long repeated version.
5. **Contra (NES)** — explosion: noise burst with a falling low-pass and a low sq body, ~0.5 s.
6. **Gradius (NES)** — explosion: noise burst plus a short tri thump.
7. **Super Mario Bros. 3 (NES)** — Bob-omb: a noise "psh-oom" with a falling pitch.
8. **Metroid (NES)** — enemy death: noise burst plus a sq descending blip.
9. **Zelda (NES)** — bomb: a noise burst with a low tri thud, ~0.5 s.
10. **Sonic (MD)** — badnik explosion: a sampled "pop" with a noise tail; Eggman's machine a longer rumble.
11. **Doom (DOS)** — rocket explosion: sampled boom with a long low tail and debris.
12. **Quake (PC)** — grenade: sampled boom with a bright crack and a long rumble.
13. **Star Fox (SNES)** — explosion: sampled noise boom with a bit of digital grit.
14. **Defender (Arcade)** — explosion: a harsh falling noise sweep with a sq tone bending down.
15. **Missile Command (Arcade, 1980)** — explosion: a noise burst with slow decay; the end-of-game "THE END" rumble.
16. **R-Type (Arcade)** — explosion: sampled crunchy boom with a metallic clatter.
17. **Raiden (Arcade, 1990)** — explosions: layered sampled booms, dense and overlapping.
18. **Super Metroid (SNES)** — bomb: sampled "whump" with a bright flash tone; power bomb a long rising-then-falling roar.
19. **GoldenEye 007 (N64)** — grenade: sampled sharp crack and a long reverberant boom.
20. **Metal Slug (Arcade, 1996)** — explosion: sampled big boom with debris clatter and a high ring.
21. **Worms (Amiga/PC, 1995)** — explosion: a sampled soft "foomp" with a comic tail.
22. **Bomb Jack (Arcade, 1984)** — bomb: a sq descending tone with noise.

**Archetypes:** `explode_burst` (noise burst, falling low-pass, 0.2 to 0.5 s), `explode_thump` (noise plus low tri body), `explode_warble` (rising-falling tone warble plus noise, Mega Man death), `explode_boom` (long boom with rumble tail and debris), `explode_crack` (sharp crack then reverberant boom), `explode_foomp` (soft comic puff).

## Coin

1. **Super Mario Bros. (NES)** — coin: two sq notes, B5 then E6 (a fourth up), the second held, ~0.4 s.
2. **Sonic (MD)** — ring: a two-note FM bell, alternating left and right channel pitches each pickup, bright.
3. **Zelda (NES)** — rupee: a short sq two-note "pling", up a fifth.
4. **Zelda: ALttP (SNES)** — rupee: sampled bright chime, one note with a sparkle; 20-rupee adds a higher one.
5. **Donkey Kong Country (SNES)** — banana: a soft sampled "plip" one note with quick decay.
6. **Super Mario World (SNES)** — coin: sampled version of the two notes, rounder.
7. **Kirby's Dream Land (GB)** — point star: sq rising two-note.
8. **Pac-Man (Arcade)** — dot: the "waka" alternating two pitched sq blips, one per dot.
9. **Mega Man (NES)** — energy pellet: a sq short "pip-pip" rising; 1-up a longer arpeggio.
10. **Castlevania (NES)** — heart: a sq short bright "ting".
11. **Spyro the Dragon (PS1, 1998)** — gem: a sampled bright glass "ting" with pitch varying by gem colour.
12. **Crash Bandicoot (PS1, 1996)** — wumpa fruit: a sampled plucky "plonk" rising in pitch per consecutive pickup.
13. **Banjo-Kazooie (N64)** — musical note: a sampled note that rises per consecutive pickup.
14. **Metroid (NES)** — energy pickup: a sq rising "beep-beep" short.
15. **Tetris (NES)** — line clear: a sq "clunk"; four lines a short fanfare (Win).
16. **Bubble Bobble (Arcade)** — fruit: a sq short two-note rising, dry.
17. **Wonder Boy (SMS)** — fruit: a sq single "pip".
18. **Earthworm Jim (MD)** — atom: a sampled "bwip" with a bright edge.
19. **Rayman (PS1)** — ting: a sampled small bell with a sparkle.
20. **Super Mario 64 (N64)** — coin: sampled version with a brighter tail; red coin a longer rising chime.
21. **Commander Keen (DOS)** — points item: PC speaker rising arpeggio of three steps.
22. **Alex Kidd (SMS)** — money bag: a sq short descending two-note, oddly.

**Archetypes:** `coin_twonote` (two sq notes a fourth or fifth apart, second held), `coin_bell` (bright bell with sparkle), `coin_pip` (single tiny tick), `coin_rising` (pitch climbs per pickup; one preset gives different pitches), `coin_waka` (alternating two blips), `coin_arp` (three rising steps).

## Powerup

1. **Super Mario Bros. (NES)** — mushroom: a rising sq arpeggio of eight steps, ~0.6 s.
2. **Super Mario Bros. (NES)** — mushroom appears: a sq rising "bwoop" slide (also Unlock).
3. **Sonic (MD)** — speed shoes / shield: FM rising swell with a bright chime; invincibility starts a jingle.
4. **Mega Man (NES)** — weapon get: a rising sq fanfare (Win); energy refill a repeated rising "pip" ladder.
5. **Metroid (NES)** — item get: the famous rising sq fanfare with vibrato, ~2 s (also Unlock).
6. **Castlevania (NES)** — whip upgrade: a sq rising two-step with a bright end.
7. **Kirby's Adventure (NES)** — copy ability: a sq rising arpeggio with a noise sparkle.
8. **Zelda (NES)** — heart container / item: the rising "da-na-na-naa" sq fanfare (Unlock as well).
9. **Pac-Man (Arcade)** — power pellet: the siren drops and a pulsing sq "wawawa" begins; the pickup itself is a rising sq slide.
10. **Gradius (NES)** — power-up bar select: a sq short rising "pip"; speed up adds a little arpeggio.
11. **Contra (NES)** — weapon pickup: a sq rising three-note.
12. **Bubble Bobble (Arcade)** — candy: a sq rising arpeggio.
13. **Donkey Kong Country (SNES)** — barrel / Kong letter: a sampled rising shimmer.
14. **Mega Man X (SNES)** — upgrade capsule: sampled rising chord swell with a shimmer, ~1 s.
15. **Super Metroid (SNES)** — item: sampled rising fanfare with a long shimmer.
16. **Secret of Mana (SNES)** — level up: a sampled rising chord with bells (Win-ish).
17. **Earthbound (SNES)** — PSI learn: a sampled rising bell run.
18. **Doom (DOS)** — item pickup: a sampled bright "dink"; armor a thud; powerup a longer rising "wohh".
19. **Quake (PC)** — quad damage: a sampled deep rising "whoom" with a shimmer.
20. **Pokémon Red (GB)** — item get: a sq short rising fanfare; level up a longer one.
21. **Super Mario World (SNES)** — cape feather: sampled rising arpeggio, brighter.
22. **Duck Tales (NES)** — item: a sq rising two-note with a quick shimmer.

**Archetypes:** `powerup_ladder` (rising stepped arpeggio, eight steps), `powerup_slide` (continuous rising sweep), `powerup_swell` (rising chord with shimmer), `powerup_threenote` (short rising three-note), `powerup_whoom` (deep rising tone with a bright top).

## Unlock

1. **Zelda (NES)** — secret found: the eight-note sq "da-na-na-na-na-na-na-naaa", ~1.2 s.
2. **Zelda (NES)** — door unlock: a sq short "clunk" with a little rising pip.
3. **Zelda: ALttP (SNES)** — chest open: a sampled rising sparkle then the item fanfare.
4. **Super Mario Bros. (NES)** — item block / vine: a sq rising "bwoop".
5. **Metroid (NES)** — door open: a sq rising "shwip" with noise, short.
6. **Super Metroid (SNES)** — door: a sampled hiss and clank, then the shutter slide.
7. **Castlevania (NES)** — door: a sq descending "clank" then creak noise.
8. **Resident Evil (PS1)** — door opening: a long sampled creak with a latch and a step, ~3 s (also Door).
9. **Doom (DOS)** — switch: a sampled "chk" click; secret found: a short sampled "ding-ding".
10. **Final Fantasy (NES)** — treasure: a sq short rising two-note.
11. **Final Fantasy VI (SNES)** — chest: a sampled bright rising "dli-ding".
12. **Chrono Trigger (SNES)** — chest: a sampled rising shimmer with a pop.
13. **Pokémon Red (GB)** — item found: sq rising short fanfare; PC open a sq "boop".
14. **Earthbound (SNES)** — present open: a sampled "pop" then a chime.
15. **Metal Gear Solid (PS1)** — codec / item: a sampled electronic "beep-beep" rising, bright.
16. **Tomb Raider (PS1)** — secret: a sampled rising glissando chime.
17. **Banjo-Kazooie (N64)** — jiggy: a sampled rising fanfare with a bell.
18. **Mega Man (NES)** — boss door: a sq descending "chk-chk-chk" shutter pattern.
19. **Spelunky (2008)** — chest open: a sampled clunk then a sparkle.
20. **Castlevania: SotN (PS1)** — item: a sampled sparkle chord.
21. **Shovel Knight (2014)** — chest: sq rising arpeggio with a noise latch.
22. **Portal (2007)** — not retro, but its door "chk-whoosh" is the archetype of the sci-fi door unlock.

**Archetypes:** `unlock_secret` (eight-note rising phrase), `unlock_clunk` (latch click then a rising pip), `unlock_shimmer` (rising sparkle with a pop), `unlock_shutter` (repeated descending clicks), `unlock_beep` (two rising electronic beeps).

## Win

1. **Super Mario Bros. (NES)** — level clear: the sq fanfare with a triangle bass, ~3 s.
2. **Sonic (MD)** — act clear: the FM fanfare, ~2 s, bright and brassy.
3. **Zelda (NES)** — dungeon complete / triforce: a rising sq fanfare with a held chord.
4. **Mega Man 2 (NES)** — stage clear: a sq fanfare with a falling then rising ending.
5. **Final Fantasy (NES)** — victory: the rising sq four-note fanfare then the march.
6. **Final Fantasy VI (SNES)** — victory: sampled brass version of the same.
7. **Pokémon Red (GB)** — battle won: a sq rising fanfare with a bass line, ~2 s.
8. **Tetris (NES)** — level up / tetris: a sq short rising fanfare, ~1 s.
9. **Dr. Mario (NES, 1990)** — stage clear: a sq cheerful short fanfare.
10. **Street Fighter II (Arcade)** — round win: a sampled "you win" with a short brass sting.
11. **Castlevania (NES)** — stage clear: a sq rising fanfare with a tri bass.
12. **Donkey Kong Country (SNES)** — bonus win: a sampled jungle drum fanfare, short.
13. **Metroid (NES)** — item fanfare doubles as win.
14. **Super Mario World (SNES)** — course clear: sampled brass fanfare.
15. **Kirby's Adventure (NES)** — stage clear: sq dance jingle, longer.
16. **Earthbound (SNES)** — battle win: a sampled short brassy fanfare.
17. **Chrono Trigger (SNES)** — battle win: a sampled bright fanfare with strings.
18. **Bubble Bobble (Arcade)** — round clear: a sq short cheerful fanfare.
19. **Columns (MD, 1990)** — level up: an FM bell flourish.
20. **Puyo Puyo (Arcade/MD, 1992)** — win: a sampled voice plus FM fanfare.
21. **Secret of Mana (SNES)** — level up: a rising sampled chord (also Powerup).
22. **Advance Wars (GBA, 2001)** — victory: a sampled trumpet fanfare, short.

**Archetypes:** `win_fanfare` (rising phrase with a held final chord), `win_fourstep` (four rising notes then a march cadence), `win_sting` (one brass chord stab), `win_bell` (bell flourish), `win_short` (one-second cheerful jingle).

## Lose

1. **Super Mario Bros. (NES)** — death: a sq "bump" then a descending four-note phrase with a held low end, ~2.5 s.
2. **Pac-Man (Arcade)** — death: a long descending wobbling sq sweep ending in two pops.
3. **Sonic (MD)** — death: a FM short descending "duh-duh" sting then the drown/fall jingle.
4. **Mega Man (NES)** — death: a repeated rising-falling sq warble with noise (the "bweep" burst), ~1.5 s.
5. **Zelda (NES)** — death: a sq descending spiral with a low thud.
6. **Castlevania (NES)** — death: a sq descending phrase with a noise crash.
7. **Metroid (NES)** — death: a sq descending wobble, then the explosion sweep.
8. **Tetris (GB)** — game over: a sq short descending phrase, two bars.
9. **Dr. Mario (NES)** — game over: a sq comic descending phrase.
10. **Contra (NES)** — death: a sq falling sweep plus a noise crash.
11. **Donkey Kong (Arcade)** — death: a sq descending warble with a "splat".
12. **Frogger (Arcade)** — death: a sq descending warble and a noise splat.
13. **Donkey Kong Country (SNES)** — death: a sampled "bonk" plus a descending flute phrase.
14. **Pokémon Red (GB)** — whiteout: a sq slow descending phrase with a low bass.
15. **Final Fantasy (NES)** — party wipe: a sq slow minor phrase.
16. **Street Fighter II (Arcade)** — KO: a sampled gong plus the fall thud.
17. **Mortal Kombat (Arcade)** — "Finish Him" is a voice; the loss itself is a low sampled gong.
18. **Doom (DOS)** — player death: a sampled scream with a low thud.
19. **Kirby's Adventure (NES)** — death: a sq descending comic slide with a pop.
20. **Lemmings (Amiga, 1991)** — "Oh no" voice then a sampled pop.
21. **Bubble Bobble (Arcade)** — death: a sq descending wobble.
22. **Earthbound (SNES)** — death: a sampled descending phrase with a thud.

**Archetypes:** `lose_phrase` (bump then a descending minor phrase), `lose_spiral` (long descending wobble ending in pops), `lose_sting` (two-note falling sting), `lose_crash` (falling sweep plus noise crash), `lose_slide` (comic descending slide with a pop), `lose_gong` (low gong plus thud).

## Break

1. **Super Mario Bros. (NES)** — brick break: a noise burst with a sq "crunch" and four debris ticks, ~0.4 s.
2. **Zelda (NES)** — bombable wall: a noise crumble after the bomb, falling low-pass.
3. **Sonic (MD)** — monitor break: a sampled glassy "pop" with a bright shatter tail.
4. **Castlevania (NES)** — candle break: a short noise "tik" plus a sq pip; wall block a crumble.
5. **Mega Man (NES)** — block destroy: a noise burst with a quick low-pass fall.
6. **Breakout / Arkanoid (Arcade)** — brick: a sq tick; gold bricks a lower one.
7. **Donkey Kong Country (SNES)** — barrel break: a sampled wooden crack with splinters.
8. **Street Fighter II (Arcade)** — car bonus stage: sampled metal crunch and glass, ~0.5 s per hit; final collapse a long clatter.
9. **Final Fight (Arcade)** — barrel/drum break: a sampled wooden crunch; drum a metal clang.
10. **Golden Axe (Arcade)** — pot break: a sampled ceramic shatter, short.
11. **Zelda: ALttP (SNES)** — pot smash: a sampled ceramic crash with scattering pieces, ~0.4 s.
12. **Zelda: OoT (N64)** — pot: a sampled crash with a ringing shard tail; grass a swish.
13. **Diablo (PC, 1996)** — barrel: a sampled wood crack; urn a ceramic break.
14. **Doom (DOS)** — barrel explodes (Explode); glass is absent.
15. **Spelunky (2008)** — pot: a sampled ceramic crack; rock a dusty crumble.
16. **Super Metroid (SNES)** — bomb block: a sampled crumble with a low thud.
17. **Kirby's Adventure (NES)** — star block: a sq "pop" with a short noise.
18. **Wrecking Crew (NES, 1985)** — wall: a sq descending "clunk" with a noise crumble.
19. **Dig Dug (Arcade, 1982)** — rock falls: a sq descending wobble then a noise crash.
20. **Bust-a-Move (Arcade, 1994)** — bubble pop: a sampled bright pop; cluster a cascade of pops.
21. **Rampage (Arcade, 1986)** — building crumble: a long noise rumble with chunks.
22. **Prince of Persia (DOS)** — loose floor tile: a sampled crack then a crash on landing.

**Archetypes:** `break_crunch` (noise burst plus a few debris ticks), `break_shatter` (bright glassy pop with a tail), `break_ceramic` (crash with scattering pieces), `break_wood` (crack with splinters), `break_crumble` (long dusty rumble with chunks), `break_pop` (single bright pop).

## Door

1. **Metroid (NES)** — door: a sq rising "shwip" plus a noise hiss, ~0.3 s.
2. **Super Metroid (SNES)** — door: a sampled hiss, a clank and a sliding shutter, ~0.6 s.
3. **Zelda (NES)** — door open: a sq short "clunk"; shutter close a descending "clank".
4. **Zelda: ALttP (SNES)** — door: a sampled wooden creak then a thud.
5. **Zelda: OoT (N64)** — door: a sampled wooden creak with a latch, long.
6. **Resident Evil (PS1)** — door: the famous long creak and latch between rooms.
7. **Doom (DOS)** — door: a sampled motor hum rising, then a metal thud when stopping, ~1 s; blazing door a fast version.
8. **Wolfenstein 3D (DOS)** — door: a sampled sliding "shhk" with a thud.
9. **Duke Nukem 3D (DOS)** — door: a sampled hydraulic hiss and clunk.
10. **Half-Life (PC)** — door: sampled sliding metal with a servo whine and a thud.
11. **Castlevania (NES)** — door: a sq descending "clank" then a creak noise.
12. **Mega Man (NES)** — boss gate: a sq repeated descending "chk" ladder, ~0.8 s.
13. **Metal Gear (MSX2)** — elevator / door: a sq short "shwip".
14. **Metal Gear Solid (PS1)** — door: a sampled pneumatic hiss and slide.
15. **Final Fantasy VI (SNES)** — door: a sampled creak; dungeon gate a metal clang.
16. **Chrono Trigger (SNES)** — door: a sampled wooden creak with a pop.
17. **Pokémon Red (GB)** — door/enter: a sq short "doo-doot" descending.
18. **Super Mario Bros. (NES)** — pipe: a sq descending slide with vibrato, ~0.5 s.
19. **Super Mario 64 (N64)** — door: a sampled creak and slam; star door a bigger slam.
20. **Portal (2007)** — door: the "chk-whoosh" sliding hiss and clank.
21. **System Shock (PC, 1994)** — door: a sampled hydraulic slide with a bright tone.
22. **Prince of Persia (DOS)** — gate: a long ratcheting clank rising, then a slam dropping.

**Archetypes:** `door_shwip` (short rising tone plus hiss), `door_hiss_clank` (hiss, slide, clank), `door_creak` (wooden creak then thud), `door_motor` (hum rising then a metal thud), `door_shutter` (repeated descending clicks), `door_pipe` (descending slide with vibrato), `door_ratchet` (ratchet rising then a slam).

## Blip

1. **Super Mario Bros. (NES)** — menu cursor: a sq short "tik" one note, under 0.05 s.
2. **Zelda (NES)** — text: a sq high "tk" per letter, very short; cursor a lower one.
3. **Pokémon Red (GB)** — text: a sq "beep" per character; cursor move a short "pip".
4. **Final Fantasy (NES)** — cursor: a sq short "tick".
5. **Final Fantasy VI (SNES)** — cursor: a sampled bright "tik".
6. **Earthbound (SNES)** — text: a sampled "tk-tk" alternating per character.
7. **Chrono Trigger (SNES)** — cursor: a sampled bright "pip".
8. **Secret of Mana (SNES)** — ring menu move: a sampled soft "tok".
9. **Metal Gear Solid (PS1)** — codec text: a sampled quick "bip" per character.
10. **Phantasy Star (SMS)** — text: a sq high tick per letter.
11. **Dragon Quest (NES, 1986)** — text: a sq "pip" per character.
12. **Mega Man (NES)** — menu select: a sq "pip".
13. **Tetris (GB)** — rotate: a sq short "tik"; move a lower "tuk".
14. **Space Invaders (Arcade)** — invader march: four low sq notes stepping, the beat itself a kind of blip.
15. **Pong (Arcade)** — paddle hit (also Hit): a single-pitch pure "pok".
16. **Street Fighter II (Arcade)** — cursor: a sampled short "tick".
17. **Doom (DOS)** — menu: a sampled "dink"; invalid a low "blup".
18. **Civilization (DOS, 1991)** — click: PC speaker single tick.
19. **Windows 3.1 (1992)** — "ding" is a Confirm; the system beep is a single sq pip.
20. **Undertale (2015)** — text blips: sq very short bursts at character-specific pitches.
21. **Game Boy startup** — the boot "ding-ding" rising two-note, arguably Confirm.
22. **Shovel Knight (2014)** — text: a sq "tk" per character.

**Archetypes:** `blip_tick` (single-pitch tiny tick), `blip_pip` (short high square pip), `blip_text` (two alternating ticks), `blip_pok` (pure tone pok, Pong), `blip_dink` (short bright "dink").

## Confirm

1. **Super Mario Bros. (NES)** — start / 1-up: the sq rising "do-de-do" phrase is 1-up; start is a sq "pip-pip".
2. **Zelda: ALttP (SNES)** — menu select: a sampled bright "ding" with a tiny rise.
3. **Pokémon Red (GB)** — A press: a sq short "pip", slightly rising.
4. **Final Fantasy (NES)** — confirm: a sq two-note "pi-pip" rising.
5. **Final Fantasy VI (SNES)** — confirm: a sampled bright two-note.
6. **Chrono Trigger (SNES)** — confirm: a sampled rising "bli-ding".
7. **Earthbound (SNES)** — confirm: a sampled "pim" with a soft rise.
8. **Metal Gear Solid (PS1)** — codec open: a sampled "brrp" pair; confirm a bright "pip".
9. **Street Fighter II (Arcade)** — character select: a sampled rising "pwip".
10. **Tetris (NES)** — start: a sq short rising two-note.
11. **Secret of Mana (SNES)** — select: a sampled soft rising "tung".
12. **Mega Man X (SNES)** — select: a sampled rising "pip".
13. **Sonic (MD)** — menu accept: FM short rising "bling".
14. **Doom (DOS)** — menu accept: a sampled "pistol" sound, oddly.
15. **Windows 95 (1995)** — "ding": a bright bell, one note with a long decay.
16. **Mac startup chime (1984 onward)** — a chord swell; the Mac "quack" is a confirm-ish quack.
17. **Game Boy startup** — rising "ding-ding", two notes an octave apart.
18. **PlayStation startup (1994)** — the long chord swell, more Powerup than Confirm.
19. **Advance Wars (GBA)** — confirm: a sampled bright "pip-pip".
20. **Pokémon Gold (GBC, 1999)** — save: a sq rising arpeggio, short.
21. **Kirby Super Star (SNES)** — select: a sampled soft rising two-note.
22. **Metroid Prime (GC)** — menu: a sampled electronic rising "bweep" with a filter sweep.

**Archetypes:** `confirm_twonote` (two rising notes), `confirm_ding` (one bright bell note), `confirm_pwip` (quick rising sweep), `confirm_octave` (two notes an octave apart), `confirm_brrp` (short buzzy electronic pair).

## Alert

1. **Zelda (NES)** — low health: a repeating sq high "beep-beep" every half second.
2. **Pokémon Red (GB)** — low HP: a repeating sq high beep at a slower rate.
3. **Metroid (NES)** — low energy: a repeating sq high beep; escape countdown a faster one.
4. **Super Metroid (SNES)** — escape alarm: a sampled siren rising and falling, with a klaxon.
5. **Metal Gear (MSX2)** — "!" alert: a sq short rising stab, then the alert music.
6. **Metal Gear Solid (PS1)** — alert: the sampled "!" stab, a sharp rising two-note.
7. **Final Fantasy (NES)** — invalid: a sq low "buzz".
8. **Final Fantasy VI (SNES)** — invalid: a sampled low "bzzt".
9. **Pokémon Red (GB)** — invalid / wall bump: a sq low "thunk".
10. **Super Mario Bros. (NES)** — time running out warning: a short sq descending four-note.
11. **Sonic (MD)** — drowning countdown: an FM repeating low "bong" accelerating, then the drowning jingle.
12. **Doom (DOS)** — invalid menu: a low sampled "blup"; door locked: a sampled "oof".
13. **Mega Man (NES)** — energy low: no beep, but the boss intro siren is a sq rising wail.
14. **Space Invaders (Arcade)** — UFO: a repeating sq warble high; it is an alert of sorts.
15. **Galaga (Arcade)** — tractor beam: a sq rising-falling warble.
16. **Star Fox (SNES)** — incoming: a sampled rising "weeoo" alarm.
17. **Half-Life (PC)** — HEV warning: sampled klaxon and voice; low health a soft repeating beep.
18. **Street Fighter II (Arcade)** — round timer low: no sound, the music speeds up.
19. **Tetris (GB)** — stack high: music speeds up; the Game Over itself is Lose.
20. **Pac-Man (Arcade)** — the siren itself is an alert state; power pellet changes it to a pulsing "wawawa".
21. **Missile Command (Arcade)** — incoming: a repeating sq alarm chirp.
22. **Windows 95 (1995)** — error "chord": a dissonant two-note sting.

**Archetypes:** `alert_beep` (repeating high beep), `alert_siren` (rising-falling wail), `alert_stab` (sharp rising two-note), `alert_buzz` (low buzz, refused action), `alert_countdown` (accelerating low bong), `alert_chord` (dissonant two-note sting).

## Cast

1. **Final Fantasy (NES)** — spell: a sq rising arpeggio with vibrato; fire adds noise.
2. **Final Fantasy VI (SNES)** — Fire: a sampled whoosh with a crackle; Cure a rising bell shimmer; Thunder a crack.
3. **Zelda: ALttP (SNES)** — magic: a sampled shimmering swell with a bell; fire rod a whoosh.
4. **Secret of Mana (SNES)** — spells: sampled swirling noise sweeps with chimes, ~1.5 s.
5. **Chrono Trigger (SNES)** — Lightning: a sampled crack; Ice a crystalline shimmer; Fire a roar.
6. **Castlevania (NES)** — holy water: a sq short "shh" plus a crackle burst.
7. **Golden Axe (Arcade)** — magic: a sampled rising swell then a boom.
8. **Gauntlet (Arcade, 1985)** — magic potion: a sampled rising swirl then a "bwoosh".
9. **Zelda (NES)** — magic rod: a sq rising "shwee" with vibrato.
10. **Ghosts 'n Goblins (Arcade)** — fire: a sq short "fwoo" with noise.
11. **Dragon Quest (NES)** — spell: a sq rising arpeggio with a shimmer.
12. **Phantasy Star (SMS)** — technique: a sq rising warble.
13. **Shining Force (MD, 1992)** — spell: an FM rising swell with a chime cluster.
14. **Diablo (PC)** — firebolt: a sampled whoosh with a crackle; frost a crystalline hiss.
15. **Heretic (DOS, 1994)** — elven wand: a sampled bright "pyew" with a sparkle.
16. **Hexen (DOS, 1995)** — spells: sampled energy hums with crackle.
17. **Secret of Evermore (SNES, 1995)** — alchemy: sampled shimmer swells.
18. **Terranigma (SNES, 1995)** — magic: a sampled rising sparkle with a bell.
19. **Earthbound (SNES)** — PSI: a sampled rising electronic sweep with chorus, oddly digital.
20. **Pokémon Red (GB)** — psychic: a sq warbling sweep; thunder a noise crack; ember a noise puff.
21. **Kirby's Adventure (NES)** — spark: a sq buzzing crackle; fire a noise roar.
22. **Castlevania: SotN (PS1)** — spells: sampled swells with voice-like chords.

**Archetypes:** `cast_arp` (rising arpeggio with vibrato), `cast_shimmer` (rising bell shimmer, cure), `cast_whoosh` (whoosh plus crackle, fire), `cast_crack` (sharp electrical crack, thunder), `cast_crystal` (crystalline hiss and ringing, ice), `cast_swirl` (swirling filtered noise sweep).

## Warp

1. **Super Mario Bros. (NES)** — pipe: a sq descending slide with vibrato (also Door); warp zone is silent.
2. **Zelda (NES)** — whistle warp: a sq rising spiral; stairs a short descending.
3. **Zelda: ALttP (SNES)** — mirror warp: a sampled rising shimmer with a filter sweep, ~1.5 s.
4. **Metroid (NES)** — elevator: a sq long descending drone with vibrato.
5. **Super Metroid (SNES)** — save station / teleport: a sampled electronic swell with a rising tone.
6. **Final Fantasy (NES)** — teleport / exit: a sq rapid descending-rising warble.
7. **Final Fantasy VI (SNES)** — warp: a sampled whoosh with a pitch bend up and out.
8. **Chrono Trigger (SNES)** — time gate: a sampled rising swell with a long shimmer and a "whomp".
9. **Phantasy Star (SMS)** — teleport: a sq rising "bweee" with vibrato.
10. **Mega Man (NES)** — teleport in / out: a sq fast rising "bwip" (in) and falling (out), ~0.3 s.
11. **Mega Man X (SNES)** — teleport: a sampled rising zip with a filter sweep.
12. **Sonic (MD)** — special stage entry: FM swirling warble rising.
13. **Sonic CD (Sega CD, 1993)** — time warp: a sampled rising whoosh then a flash.
14. **Star Trek (Arcade, 1983)** — warp: a sq rising sweep with noise.
15. **Doom (DOS)** — teleport: a sampled deep "whoomp" with a reversed swell.
16. **Quake (PC)** — teleport: a sampled rush with a ringing tail.
17. **Half-Life (PC)** — teleport: a sampled electrical rising swirl.
18. **Portal (2007)** — portal enter: a sampled "fwoomp" with a filter rise.
19. **Earthbound (SNES)** — teleport: a sampled accelerating rush with a "whoosh".
20. **Secret of Mana (SNES)** — cannon travel: a sampled boom then a rising whistle.
21. **Pokémon Red (GB)** — teleport / fly: a sq rising sweep with vibrato.
22. **Diablo (PC)** — town portal: a sampled low swirl with a shimmer.

**Archetypes:** `warp_bwip` (fast rising or falling zip, Mega Man), `warp_spiral` (rising spiral with vibrato), `warp_shimmer` (rising swell with filter sweep), `warp_whoomp` (deep reversed swell then thump), `warp_drone` (long descending drone with vibrato), `warp_swirl` (swirling warble rising).

## Roar

1. **Zelda (NES)** — Aquamentus / dragon: a sq low descending growl with vibrato, ~0.6 s.
2. **Zelda: ALttP (SNES)** — boss roar: a sampled deep growl with a noise edge.
3. **Zelda: OoT (N64)** — King Dodongo / Volvagia: sampled roars with low rumble and a high screech layer.
4. **Super Mario World (SNES)** — Bowser: a sampled growl, low with a rasp.
5. **Super Mario 64 (N64)** — Bowser: a sampled roar, deep, with a long tail.
6. **Mega Man (NES)** — Yellow Devil: silent; the "roar" is the boss intro siren (Alert).
7. **Metroid (NES)** — Kraid / Ridley: sq low buzzing pulses, a "growl" by repetition.
8. **Super Metroid (SNES)** — Ridley: a sampled screech, high and rough; Kraid a deep roar.
9. **Castlevania (NES)** — Dracula's bat form: a sq descending shriek.
10. **Castlevania: SotN (PS1)** — bosses: sampled roars with voice samples.
11. **Rampage (Arcade)** — monster roar: a sampled low growl with grit.
12. **Altered Beast (Arcade, 1988)** — werewolf: a sampled "rise from your grave" voice; roar a sampled growl.
13. **Golden Axe (Arcade)** — dragon mount: a sampled roar with a fire tail.
14. **Doom (DOS)** — imp: a sampled screech; demon a growl; cyberdemon a deep roar with stomps.
15. **Quake (PC)** — shambler: a sampled roar with a high screech layer.
16. **Primal Rage (Arcade, 1994)** — dinosaur roars: sampled, long, with a growl start and screech end.
17. **Jurassic Park (SNES/MD, 1993)** — T. rex: a sampled roar with a deep rumble.
18. **Monster Hunter (PS2, 2004)** — monster roars: sampled layered growl and screech; not retro, but the modern archetype.
19. **Pokémon Red (GB)** — Pokémon cries: sq descending warbles with duty-cycle changes, each 0.3 to 0.8 s; the closest a Game Boy gets to a roar.
20. **Ecco the Dolphin (MD)** — whale call: FM low rising-falling moan.
21. **Kirby's Dream Land (GB)** — Whispy Woods: a sq low "huff" noise.
22. **Donkey Kong (Arcade)** — DK's "roar": a sq low descending burp-like tone.

**Archetypes:** `roar_growl` (low tone with vibrato and rasp), `roar_screech` (high rough rising-falling), `roar_pulses` (repeated low buzzing pulses), `roar_layered` (growl start into screech end), `roar_cry` (Pokémon-style descending warble with duty change), `roar_moan` (low rising-falling moan).

## Whirr

1. **Metroid (NES)** — morph ball roll: a soft repeating sq tick cycle.
2. **Mega Man 2 (NES)** — Metal Man blades / Air Man fan: a sq rapid buzzing cycle; the fan a noise whirr.
3. **Super Metroid (SNES)** — elevator: a sampled motor hum with a rising start.
4. **Sonic (MD)** — spin dash charge: FM repeated revs; Eggman's machines a steady FM motor hum.
5. **Sonic 2 (MD)** — Chemical Plant tubes: a sampled rushing whirr.
6. **Castlevania (NES)** — clockwork gears (Clock Tower): a sq ticking cycle.
7. **Doom (DOS)** — lift: a sampled motor hum with a thud at each end; chainsaw idle a sampled rough buzz.
8. **Wolfenstein 3D (DOS)** — door motor: a sampled short whirr.
9. **Half-Life (PC)** — ceiling turret: a sampled servo whine; elevator a hum.
10. **Metal Gear Solid (PS1)** — camera: a sampled servo pan whirr; elevator a hum.
11. **Final Fantasy VI (SNES)** — Magitek armor: a sampled stomping servo whirr.
12. **Chrono Trigger (SNES)** — machines in the factory: sampled motor hums and clanks.
13. **Mega Man X (SNES)** — ride armor: a sampled hydraulic whirr; charging a rising hum.
14. **F-Zero (SNES)** — engine: a sampled hum with pitch following speed.
15. **Pole Position (Arcade, 1982)** — engine: a sq buzz with pitch following speed.
16. **Out Run (Arcade, 1986)** — engine: FM buzz with a gear change drop.
17. **Pilotwings (SNES, 1990)** — propeller: a sampled buzzing drone.
18. **Choplifter (Apple II, 1982)** — helicopter: a sq rapid clicking cycle.
19. **Desert Strike (MD, 1992)** — rotor: a sampled chopping whirr.
20. **Star Fox (SNES)** — Arwing engine: a sampled hum with a bright edge.
21. **R.C. Pro-Am (NES, 1988)** — engine: a sq buzz with pitch following speed.
22. **Portal (2007)** — turret: a servo whine with clicks.

**Archetypes:** `whirr_motor` (steady hum with a start and stop), `whirr_servo` (whine seeking a position), `whirr_tick` (repeating tick cycle), `whirr_rev` (buzz with pitch following speed), `whirr_rotor` (chopping cycle), `whirr_gears` (clockwork ticking with rattle).

## Heal

1. **Zelda (NES)** — fairy / heart: a sq rising arpeggio, bright; the fairy fountain a long sparkle.
2. **Zelda: ALttP (SNES)** — heart refill: a sampled rising shimmer, repeated per heart.
3. **Zelda: OoT (N64)** — heal / fairy: a sampled bell shimmer with a rising glissando.
4. **Final Fantasy (NES)** — Cure: a sq rising arpeggio with a soft bell-like duty.
5. **Final Fantasy VI (SNES)** — Cure: a sampled rising harp glissando with a shimmer, ~1.2 s.
6. **Final Fantasy VII (PS1, 1997)** — Cure: a sampled chime swell with a bright sparkle.
7. **Chrono Trigger (SNES)** — Aura / tonic: a sampled rising bell shimmer.
8. **Secret of Mana (SNES)** — Cure Water: a sampled watery shimmer with chimes.
9. **Earthbound (SNES)** — Lifeup: a sampled rising electronic sweep with a sparkle.
10. **Pokémon Red (GB)** — Pokémon Center heal: the sq five-note jingle then a "ding".
11. **Pokémon Red (GB)** — potion: a sq rising short "bli-bli-bling".
12. **Dragon Quest (NES)** — Heal: a sq rising three-note sparkle.
13. **Phantasy Star (SMS)** — Res: a sq rising shimmer.
14. **Metroid (NES)** — energy refill: a sq repeated rising "pip" ladder.
15. **Super Metroid (SNES)** — energy tank / refill: a sampled rising bell run.
16. **Mega Man (NES)** — energy refill: a sq rapid rising "pip-pip-pip" ladder, one pip per unit.
17. **Secret of Evermore (SNES)** — heal: a sampled chime swell.
18. **Diablo (PC)** — potion: a sampled gulp and a soft rising "ahh".
19. **Doom (DOS)** — medkit: a sampled bright "dink" (really Coin); soul sphere a long rising "wohh".
20. **Breath of Fire (SNES, 1993)** — heal: a sampled rising bell.
21. **Golden Sun (GBA)** — Ply: a sampled rising shimmer with a chord.
22. **Shining Force (MD)** — Heal: an FM rising chime cluster.

**Archetypes:** `heal_arp` (rising bell-like arpeggio), `heal_shimmer` (rising glissando with sparkle), `heal_ladder` (repeated rising pips, one per unit), `heal_swell` (chime chord swell), `heal_jingle` (five-note jingle then a ding), `heal_watery` (watery shimmer with chimes).

---

## What was carried into the synths

- **Transfxr** gained one verb preset per verb (24 verbs; Step is better served by the physical engines). Each preset holds several archetypes from the lists above and picks one per press, with a small random pitch shift. Transfxr's pitch curves are the natural home for the sweep-based NES, SMS and arcade sounds.
- **Engine verb presets** gained variants where one archetype was not enough: Crittr Roar (growl, screech, pulses, layered, cry), Machinr Whirr (motor, servo, gears, toy, engine), Machinr and Clonkr Door (creak, latch, motor, shutter), Whooshr Door (hiss and slide), Birdr Jump (chirp), and more.
- **The Soundboard catalogue** now draws on retired engines as hidden ingredients where they fit the references: Pulser (android core, energy core) and Rollr (minecart, metal roller) for Whirr, Rumblr (boss approach, stone door) for Roar and Door, Notifr for Alert and Confirm, Tappr for Blip, Pewpr for Shoot.
