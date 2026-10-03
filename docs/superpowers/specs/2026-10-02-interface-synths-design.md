# Interface sound makers

Add five compact tabs for the feedback games use repeatedly. The user wants more synth types, especially interfaces, and has established that every tab needs randomized preset buttons and minimal explanatory UI.

## Sound models

- **Tappr:** tactile controls. Short spring/detent impulses with independent down/up contacts, body resonance and a tiny electronic layer. Focus, Select, Back, Toggle On, Toggle Off, Disabled, Panel Open and Panel Close.
- **Rustlr:** inventory handling. Seeded clusters of filtered micro-contacts, friction and creases for Paper, Cloth, Leather, Plastic, Foil and Zip. Card Flick, Page Turn, Bag Open, Equip Gear, Item Slide, Cloth Fold, Wrapper and Zip Pouch.
- **Notifr:** readable alerts. Compact overlapping tone groups with attack/spacing, interval tension and urgency. Message, Quest Update, Objective Done, Achievement, Low Health, Warning, Denied and Connected. This is an alert designer, with no score editor.
- **Tickr:** progress and counters. Distinct timed ticks move from an initial cadence toward a finishing cadence, with pitch accumulation, ratchet texture and a separate completion sound. Count Coins, Level Fill, Combo Build, Countdown, Research, Scan, Lockpick and Download.
- **Holor:** spectral interface gestures. Brief frequency-shifted/FM sidebands, swept resonant bands and moving comb coloration for Cursor Trail, Radial Menu, Map Ping, Target Lock, Drag Drop, Panel Swipe, Tooltip and Data Reveal.

Each engine gets eight range-based recipes plus Randomize and Mutate. Presets vary several controls and choose a fresh stored seed; lock behavior matches the established synths. Audio is mono 44.1 kHz, deterministic, finite, bounded, muted at zero volume, with smooth endpoints. Duration is explicit and bounded (maximum five seconds), including tails; discrete counters are integral. Frequent-use presets should be short and restrained.

## Integration

Use the existing SoundDSP/PresetSynth contracts. Append tabs after Swarmr to preserve saved active-tab indexes. Register scripts, add Stackr source constructors, and use standard 390-pixel parameter panels with no new prose blocks. The twenty tab names should remain navigable in the existing wrapping bar.

Generate forty editable examples and an approximately 15–30-second reel using normal recipe generation with stable seeds. Save one complete collection under examples/Interface. Verify saved files, share links, old collections, and copied Stackr layers. Browser testing should cover each tab and ordinary generation, plus reload and layout; avoid the file chooser because its existing browser backend has stalled for many minutes in prior turns.

## Scope decisions

Separate sound models give useful controls for each interaction. A single generic UI tab would bury the differences; collections assembled only from older generators would add categories without new synthesis. Keep the existing synthesis architecture and familiar Bfxr controls. No framework migration or menu redesign is needed.
