# Five exotic game sound makers

The user requested five more experimental synth tabs for games and authorized broad creative choices. Retain Bfxr's randomized category buttons and compact controls; no introductory UI paragraphs. Preserve all existing tabs and concurrent work.

- **Crittr:** nonverbal creatures, using excitation through changing formants, subharmonics and segmented calls. Tiny dragons, cave beasts, alien purrs, insects, ghost whales, clockwork pets, forest spirits and angry blobs.
- **Signlr:** coded transmissions, using packet/bit scheduling, frequency/phase modulation and radio interference. Distress beacons, alien handshakes, sonar, broken radio, encrypted packets and terminals.
- **Fractr:** cascades of breakage, using timed shard particles and material resonators. Glass, ice, crystal, stone, armor and digital disintegration.
- **Riftr:** impossible spatial effects, using dispersive delays, resonant fields, reversals and phase motion. Teleports, gravity wells, force fields, rewind and reality tears.
- **Swarmr:** many small moving sources, with correlated and independent trajectories, collective pulses and Doppler-like pitch motion. Nanobots, bats, fireflies, scarabs, drones, fairies, locusts and seeking missiles.

Each engine must be substantively distinct. Use the existing SoundDSP/PresetSynth interface: pure render(params) -> 44.1 kHz mono Float32Array; stored parameters reproduce exact PCM. Each tab has at least eight named randomized recipes (vary several controls, not just the seed), Randomize, Mutate, existing parameter locks and standard save/link/WAV exports. Bound durations and output, fade short-event edges, ensure mute works. Keep source selection in Stackr working for all five.

Append tabs after Stackr, retaining previous saved active-tab indexes. Use compact wrapping tab bar and existing waveform label treatment. Provide an editable collection containing one exact variant of every new category, individual local WAVs and a short curated reel. Tests cover acoustically meaningful control effects, determinism, bounds, variations/locks and persistence. Inspect the actual UI, run complete tests and minification, and review before completion.
