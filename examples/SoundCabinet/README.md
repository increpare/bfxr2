# Sound Cabinet examples

40 editable sounds, one from every category in Clonkr, Machinr, Jinglr, and Squishr. These are exact saved variants of the randomized category buttons; clicking a category in the app creates another sound in that family.

## Load and explore

Use **Open Data** in Bfxr and choose [SoundCabinet.bcol](SoundCabinet.bcol), or drag the collection onto the app. It opens Clonkr and fills the four Sound Cabinet tabs. Loading replaces the sound lists in those four tabs; use **Save .bcol** first if you want to keep an existing collection.

Select a sound in a tab to play or edit it. **Export WAV** saves that sound; **Export All** exports sounds from all tabs into one ZIP. A row lock protects its control during category generation, Randomize, and Mutate. The saved examples start with only Sound Volume locked, so the other controls are ready to explore.

## Rebuild the audio

From the repository root:

```sh
node tools/render/specialized_examples.js
```

An optional final argument chooses another output folder. The script uses stable per-category seeds, selects representative variants within the normal recipe ranges, and writes 40 individual 44.1 kHz mono PCM16 WAVs, the editable collection, this guide, the showcase, and [validation.json](validation.json). WAVs are generated locally and ignored by Git. Rebuilding overwrites generated files in the chosen folder.

Every example is checked for finite samples, peaks below full scale, audible RMS, and identical audio after loading its saved parameters. This render contains 40 sounds with RMS 0.0242–0.2071 and maximum peak 0.4750.

## Short showcase

[Play the 14.3-second showcase](sound_cabinet_showcase.wav). Each gesture and musical phrase plays completely, with 0.28-second gaps. The reel balances playback levels; individual WAVs retain exactly the levels stored in the collection.

| Start | End | Tab | Sound |
| --- | --- | --- | --- |
| 00:00.00 | 00:00.32 | Clonkr | Wood Knock |
| 00:00.60 | 00:03.70 | Clonkr | Glass Ping |
| 00:03.98 | 00:04.24 | Machinr | Camera Shutter |
| 00:04.52 | 00:06.72 | Machinr | Rusty Winch |
| 00:07.00 | 00:07.22 | Squishr | Water Drop |
| 00:07.50 | 00:08.28 | Squishr | Suction Cup |
| 00:08.56 | 00:09.17 | Squishr | Slime Step |
| 00:09.45 | 00:11.84 | Jinglr | Discovery |
| 00:12.12 | 00:14.25 | Jinglr | Checkpoint |

## Phrase editing

**Jinglr:** reseed melody and instrument independently. Edited phrases and their settings travel together in saved sounds and Mixr copies.

## Clonkr

Materials and contact: choose Wood, Glass, Metal, Ceramic, or Rubber, then Hit, Scrape, or Rattle. Size lowers the resonance as the object gets larger; Hollowness emphasizes its body. Strike Hardness changes the attack and upper modes, Damping shortens ringing, and Duration controls resonance and the length of continued contact.

| Category | Character | Length |
| --- | --- | --- |
| [Teacup](clonkr_teacup.wav) | Tap a small hollow china cup. | 1.03 s |
| [Glass Ping](clonkr_glass_ping.wav) | A bright, delicate piece of glass. | 3.10 s |
| [Wood Knock](clonkr_wood_knock.wav) | A dry knock on a wooden block or door. | 0.32 s |
| [Dungeon Gate](clonkr_dungeon_gate.wav) | Heavy iron scraping and ringing in a stone passage. | 4.96 s |
| [Metal Clang](clonkr_metal_clang.wav) | Strike a resonant metal plate. | 3.53 s |
| [Ceramic Crack](clonkr_ceramic_crack.wav) | Brittle pottery cracking into short rattling shards. | 0.37 s |
| [Rubber Thud](clonkr_rubber_thud.wav) | A heavy cushioned bounce. | 0.27 s |
| [Loose Bolts](clonkr_loose_bolts.wav) | A handful of small metal parts tumbling together. | 2.49 s |
| [Dragged Crate](clonkr_dragged_crate.wav) | Rough wood scraping along the floor. | 1.36 s |
| [Coin Drop](clonkr_coin_drop.wav) | A small coin bouncing and settling. | 1.76 s |

## Machinr

Mechanism chooses the moving parts. Speed and Load control their movement; Roughness and Gear Looseness add worn bearings, friction, and rattles. Size changes the register, while Duration, Start Time, and Stop Time shape the movement.

| Category | Character | Length |
| --- | --- | --- |
| [Tiny Motor](machinr_tiny_motor.wav) | A fresh little electric motor spinning up. | 1.05 s |
| [Rusty Winch](machinr_rusty_winch.wav) | Slow, strained gears with a different creak each time. | 2.20 s |
| [Camera Shutter](machinr_camera_shutter.wav) | A quick spring release, double click and winding tail. | 0.26 s |
| [Clockwork](machinr_clockwork.wav) | A new tiny escapement, ticking against its gears. | 1.75 s |
| [Engine Trouble](machinr_engine_trouble.wav) | An engine coughing under uneven load. | 2.28 s |
| [Servo](machinr_servo.wav) | A high motor whine seeking a new position. | 0.70 s |
| [Windup Toy](machinr_windup_toy.wav) | A loose little spring-powered mechanism winding down. | 2.00 s |
| [Heavy Door](machinr_heavy_door.wav) | A deep hinge creak with a weighty closing latch. | 2.00 s |

## Jinglr

Choose an Instrument, Key, Scale, and Octave, then shape the phrase with Tempo, Swing, Brightness, Decay, and Echo. Contour, Rhythm and Notes shape the tune. The ten-digit seed combines five melody digits with five instrument-character digits.

| Category | Character | Length |
| --- | --- | --- |
| [Confirm](jinglr_confirm.wav) | A quick, bright yes. | 0.47 s |
| [Message](jinglr_message.wav) | A small, soft arrival. | 0.67 s |
| [Dismiss](jinglr_dismiss.wav) | A short downward reply. | 0.48 s |
| [Denied](jinglr_denied.wav) | A compact, low refusal. | 0.55 s |
| [Discovery](jinglr_discovery.wav) | An inquisitive rising sparkle. | 2.39 s |
| [Victory](jinglr_victory.wav) | A brisk, bright upward fanfare. | 2.15 s |
| [Failure](jinglr_failure.wav) | A drooping little minor-key defeat. | 3.95 s |
| [Secret](jinglr_secret.wav) | An elusive chime from somewhere nearby. | 3.03 s |
| [Warning](jinglr_warning.wav) | An urgent repeated arcade call. | 1.68 s |
| [Checkpoint](jinglr_checkpoint.wav) | A small reassuring arrival. | 2.13 s |
| [Puzzle Solved](jinglr_puzzle_solved.wav) | A curious idea resolving into a bright finish. | 2.91 s |
| [Lullaby](jinglr_lullaby.wav) | A soft wandering tune with time to breathe. | 5.63 s |

## Squishr

Texture selects slime, bubbles, suction, splat, gulp, or spring. Viscosity thickens and muffles the material; Stretch lengthens its deformation; Pressure adds force and activity; Wetness brings bubbles forward; Bubble Size lowers their resonance as they grow. Duration sets the gesture length.

| Category | Character | Length |
| --- | --- | --- |
| [Slime Step](squishr_slime_step.wav) | A sticky footstep through a puddle of goo. | 0.61 s |
| [Bubble Pop](squishr_bubble_pop.wav) | A small rounded bubble bursting. | 0.26 s |
| [Suction Cup](squishr_suction_cup.wav) | Stretch the seal, then pop it free. | 0.78 s |
| [Wet Splat](squishr_wet_splat.wav) | A wet impact spraying small droplets. | 0.40 s |
| [Gulp](squishr_gulp.wav) | A low, hollow swallow of liquid. | 0.46 s |
| [Springy Goo](squishr_springy_goo.wav) | Elastic slime springing back into shape. | 0.92 s |
| [Bubbling Potion](squishr_bubbling_potion.wav) | An active cauldron of uneven rounded bubbles. | 2.19 s |
| [Mud Pull](squishr_mud_pull.wav) | Slowly pull something out of thick, sticky mud. | 1.59 s |
| [Water Drop](squishr_water_drop.wav) | A light high droplet falling into water. | 0.22 s |
| [Jelly Wobble](squishr_jelly_wobble.wav) | A large soft jelly shaking from side to side. | 1.45 s |
