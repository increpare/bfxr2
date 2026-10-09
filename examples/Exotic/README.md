# Exotic game sounds

40 editable sounds: eight randomized categories in each of five new tabs. Every preset click makes another variation.

Open **Exotic.bcol** with **Open Data**, or drag it onto Bfxr. This replaces the lists in these five tabs; save your collection first if needed. Select an example to hear and edit it. All five also work as copied sources in Mixr.

The [18.6-second reel](exotic_showcase.wav) plays ten complete sounds with 0.3-second gaps. Levels are balanced for the reel; individual WAVs match their saved settings exactly.

| Start | Tab | Sound |
| --- | --- | --- |
| 0.00 s | Crittr | Tiny Dragon |
| 1.22 s | Crittr | Ghost Whale |
| 4.35 s | Signlr | Alien Handshake |
| 6.25 s | Signlr | Broken Radio |
| 8.00 s | Fractr | Glass Cascade |
| 10.13 s | Fractr | Pixel Disintegrate |
| 11.49 s | Riftr | Phase Dash |
| 12.26 s | Riftr | Time Rewind |
| 13.82 s | Swarmr | Fireflies |
| 17.02 s | Swarmr | Seeking Missiles |

## Crittr

Nonverbal creature calls: moving throat resonances, calls and gaps, breath and subharmonic growls.

| Preset | Length |
| --- | --- |
| [Tiny Dragon](crittr_tiny_dragon.wav) | 0.92 s |
| [Cave Beast](crittr_cave_beast.wav) | 1.46 s |
| [Alien Purr](crittr_alien_purr.wav) | 2.31 s |
| [Insect Call](crittr_insect_call.wav) | 1.33 s |
| [Ghost Whale](crittr_ghost_whale.wav) | 2.83 s |
| [Clockwork Pet](crittr_clockwork_pet.wav) | 0.56 s |
| [Forest Spirit](crittr_forest_spirit.wav) | 1.21 s |
| [Angry Blob](crittr_angry_blob.wav) | 0.56 s |

## Signlr

Procedural transmissions: FSK, phase coding, chirps and radio packets, with interference and corruption.

| Preset | Length |
| --- | --- |
| [Derelict Beacon](signlr_derelict_beacon.wav) | 2.60 s |
| [Alien Handshake](signlr_alien_handshake.wav) | 1.60 s |
| [Distress Burst](signlr_distress_burst.wav) | 0.70 s |
| [Broken Radio](signlr_broken_radio.wav) | 1.45 s |
| [Sonar Map](signlr_sonar_map.wav) | 1.81 s |
| [Encrypted Packet](signlr_encrypted_packet.wav) | 0.67 s |
| [Lost Satellite](signlr_lost_satellite.wav) | 1.80 s |
| [Save Terminal](signlr_save_terminal.wav) | 0.81 s |

## Fractr

Separate falling fragments with material resonances, gravity, bounce and a controllable cascade.

| Preset | Length |
| --- | --- |
| [Glass Cascade](fractr_glass_cascade.wav) | 1.83 s |
| [Ice Wall](fractr_ice_wall.wav) | 1.84 s |
| [Crystal Break](fractr_crystal_break.wav) | 2.50 s |
| [Stone Collapse](fractr_stone_collapse.wav) | 4.54 s |
| [Pixel Disintegrate](fractr_pixel_disintegrate.wav) | 1.06 s |
| [Brittle Armor](fractr_brittle_armor.wav) | 1.02 s |
| [Bone Scatter](fractr_bone_scatter.wav) | 1.62 s |
| [Shatter Freeze](fractr_shatter_freeze.wav) | 4.07 s |

## Riftr

Moving feedback delays and dispersive fields, with time reversal, pitch travel and five excitations.

| Preset | Length |
| --- | --- |
| [Gravity Well](riftr_gravity_well.wav) | 1.87 s |
| [Time Rewind](riftr_time_rewind.wav) | 1.25 s |
| [Phase Dash](riftr_phase_dash.wav) | 0.48 s |
| [Force Field](riftr_force_field.wav) | 2.79 s |
| [Portal Tear](riftr_portal_tear.wav) | 2.69 s |
| [Teleport Arrive](riftr_teleport_arrive.wav) | 1.04 s |
| [Black Hole](riftr_black_hole.wav) | 4.81 s |
| [Reality Glitch](riftr_reality_glitch.wav) | 1.24 s |

## Swarmr

Independent emitters with collective pulses, scattered arrivals and approaching/receding pitch.

| Preset | Length |
| --- | --- |
| [Nanobots](swarmr_nanobots.wav) | 1.02 s |
| [Cave Bats](swarmr_cave_bats.wav) | 2.30 s |
| [Fireflies](swarmr_fireflies.wav) | 2.91 s |
| [Scarabs](swarmr_scarabs.wav) | 2.09 s |
| [Drone Patrol](swarmr_drone_patrol.wav) | 2.83 s |
| [Fairy Flock](swarmr_fairy_flock.wav) | 3.25 s |
| [Locusts](swarmr_locusts.wav) | 2.99 s |
| [Seeking Missiles](swarmr_seeking_missiles.wav) | 1.56 s |

## Rebuild

`node tools/render/exotic_examples.js` regenerates this collection, 40 WAVs, the reel and validation report. An optional argument chooses another output directory. WAVs are generated locally and ignored by Git.

Every example is checked for finite, bounded, audible audio, faded edges and bit-identical sound after reloading its saved parameters. See [validation.json](validation.json).
