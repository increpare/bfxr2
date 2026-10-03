# Sound Board: a game-verb front end for the Bfxr suite

**Goal:** Make the first thing a game developer sees a board of plain game verbs (Jump, Coin, Hurt…). Each button gives a fresh, varied interpretation of that verb drawn from the whole suite: classic Bfxr prefabs, the physical and exotic engines, Jinglr cues, and curated Mixfxr pairs. Everything stays editable in the engine that made it.

**Architecture:** The board is data, not a new synthesizer. A category is a weighted portfolio of *sources*; a source is one generator (`Synth:generate_x`) or a Mixfxr pair with balance and alignment. Board sounds are stored as Mixr records (a Mixr with one source renders that source alone), so save, load, share links, WAV export and "Layer in Stackr" already work. The one engine change is Mixfxr time alignment (start / peak / tail), which is what makes slow-developing sounds such as Sonar usable as mix partners.

**Tech stack:** Existing browser JavaScript and PresetSynth, Node test runner, headless rendering through `tests/helpers/synth-context.js`, feature measurement adapted from `tools/preset_survey/analyze.py`.

---

## 1. Why a board, and how many buttons

Bfxr's seven prefabs work because they are verbs a developer is already thinking in. The suite now has 23 tabs and roughly 230 named recipes, and the names are engine-centric ("Codec Warble", "Derelict Beacon"). A board inverts that: the verb is the button, the engines are hidden ingredients.

**Recommendation: 20 buttons, 4 columns × 5 rows, plus one optional row.** A board is only better than tabs if it is scannable in one glance and every label is a verb a developer recognises without reading a tooltip. What should scale is the *variety inside* each button, not the button count. The schema makes adding a row trivial, so start with 20 and add the fantasy row if the first 20 feel cramped.

Each row is a theme. Columns are not meaningful, rows are.

| Row | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| **Move** | Jump | Land | Step | Dash | Splash |
| **Fight** | Shoot | Swing | Hit | Hurt | Explode |
| **Reward** | Coin | Powerup | Unlock | Win | Lose |
| **World & UI** | Break | Door | Blip | Confirm | Alert |
| *Optional 5th row* | *Cast* | *Warp* | *Roar* | *Whirr* | *Heal* |

Candidates that fought for a slot and where they went: Heal (variety inside Powerup), Death (Lose and Hurt), Switch/Toggle (Door and Blip), Back/Denied (Alert, which means "attention or no"), Game Over (Lose), Enemy death (Hit plus Explode).

## 2. What each button draws from

Each category has a duration class so its interpretations feel interchangeable in a game, and a portfolio of sources. Weights are a first guess for the curation loop. `A × B` is a Mixfxr pair; alignment is noted where it matters. Engines in *italics* are retired from navigation but still render, so they can serve as hidden ingredients.

**Jump** · 0.1–0.4 s. Bfxr Jump (×4). Whooshr Dodge, Air Dash (soft jumps). Squishr (boingy). Bouncr Rubber on Wood (cartoon). Pluckr Bass Pluck shortened. Bfxr Jump × Whooshr Dodge, peak-aligned.

**Land** · 0.1–0.5 s. Footsteppr. Bouncr Heavy Soft Landing, Wood on Concrete, Stone into Earth. Clonkr. Boomr Tiny Pop. Bouncr × Rustlr Cloth Fold (thud with clothing).

**Step** · 0.1–0.3 s. Footsteppr across terrains (×4). Footsteppr × Rustlr (armour, cloth). Clonkr small tangs (metal floors).

**Dash** · 0.2–0.6 s. Whooshr Dodge, Air Dash, Cloth Swipe. Riftr Phase Dash. Breathr Exhale. Whooshr × Zappr Static Spark (electric dash), start-aligned.

**Splash** · 0.2–0.8 s. Squishr families. Bouncr × Squishr (existing Goo Collision). Bfxr Hit with pink noise. *Weathr* Bubbling Stream trimmed.

**Shoot** · 0.1–0.5 s. Bfxr Laser/Shoot (×4). *Pewpr* Laser Pistol, Coil Driver, Ion Beam. Zappr Static Spark. Whooshr Fast Projectile, Arrow Pass. Bfxr Shoot × Zappr, start-aligned.

**Swing** · 0.2–0.6 s. Whooshr Sword Swing, Heavy Swing, Wingbeat. Whooshr × Clonkr with the tang tail-aligned (swing that connects). Breathr Gasp × Whooshr (effortful swing).

**Hit** · 0.05–0.4 s. Bfxr Hit/Hurt (×3). Clonkr. Bouncr Steel on Concrete. Fractr Bone Snap, Glass Snap. Clonkr × Zappr (existing Live Wire). Boomr Tiny Pop.

**Hurt** · 0.1–0.5 s. Bfxr Hit/Hurt, lower and longer. Breathr Gasp. Crittr short calls. Squishr (wet hits). Bfxr Hurt × Breathr Gasp, start-aligned (the gasp sells the "player" part).

**Explode** · 0.5–3 s. Bfxr Explosion (×3). Boomr Grenade, Barrel, Fireball, Depth Charge, Distant Charge. Boomr × Breathr (existing Shockwaves). Fractr × Boomr re-tried peak-aligned (currently graded BAD when both start at 0).

**Coin** · 0.1–0.4 s. Bfxr Pickup/Coin (×4). Jinglr Confirm, Message (two notes). Pluckr Quest Pluck. Bouncr Coin on Glass. Bfxr Coin × Bouncr Coin on Glass. *Tickr* Count Coins for multi-coin bursts.

**Powerup** · 0.4–1.5 s. Bfxr Powerup (×3). Jinglr Discovery. Choirr Victory Chord shortened. Riftr Teleport Arrive. Zappr Magic Spark. Bfxr Powerup × Choirr, with Choirr tuned to the Bfxr start pitch (see §4).

**Unlock** · 0.5–2 s. Jinglr Secret, Discovery, Puzzle Solved. Jinglr × Clonkr (existing Treasure Box). Machinr Clockwork × Jinglr, jingle tail-aligned to the mechanism. Pluckr Magic Harp. Signlr Save Terminal.

**Win** · 1–3 s. Jinglr Victory, Checkpoint, Puzzle Solved (×4). Choirr Victory Chord. Jinglr × Choirr re-tried with key matching (currently BAD unmatched).

**Lose** · 0.8–2.5 s. Jinglr Failure, Denied. Choirr Ominous. Riftr Time Rewind. Glitchr Tape Scrub. Jinglr Failure × Breathr Sigh, tail-aligned.

**Break** · 0.2–1.5 s. Fractr Glass Cascade, Crystal Break, Stone Collapse, Brittle Armor, Biscuit Crunch (×4). Clonkr. Rustlr Wrapper (paper and cardboard). Fractr × Boomr Tiny Pop, start-aligned.

**Door** · 0.3–1.5 s. Machinr Heavy Door, Rusty Winch, Servo. Clonkr (latches). Fractr Stone Collapse (stone doors). Machinr × Clonkr, tang tail-aligned (door that latches). Riftr Portal Tear for sci-fi doors.

**Blip** · 0.03–0.15 s. Bfxr Blip/Select (×4). *Tappr* Focus, Select, Toggle On/Off. Signlr Radar Blip. Glitchr Phrase Stutter, one grain.

**Confirm** · 0.1–0.6 s. Jinglr Confirm, Message, Checkpoint. Bfxr Blip as a two-note rise. *Tappr* Panel Open. Pluckr single pluck. *Notifr* success patterns.

**Alert** · 0.2–1.2 s. Jinglr Warning, Denied, Dismiss. Signlr Distress Burst, Target Lock. Zappr Fuse Blow. *Notifr* warnings. Bfxr Blip repeated (via Jinglr Warning contour).

Optional row: **Cast** (Zappr Magic Spark, Choirr Fairy Choir, Riftr, Swarmr Fireflies, Zappr × Choirr tuned), **Warp** (Riftr Teleport Arrive, Portal Tear, Phase Dash; Riftr × Glitchr existing Reality Error), **Roar** (Crittr Cave Beast, Tiny Dragon, Angry Blob; Breathr Sleeping Beast; Crittr × Boomr Distant Charge), **Whirr** (Machinr Tiny Motor, Servo, Windup Toy; Swarmr Nanobots), **Heal** (Jinglr Message, Choirr Angelic shortened, Pluckr Harp, Bfxr Powerup slow).

## 3. How good my sound perception is, honestly

I cannot listen. I can render every sound headlessly and measure it, then reason about the numbers. The suite already has the measurement vocabulary in `tools/preset_survey/analyze.py`: duration, attack, time to peak, late energy, spectral centroid, flatness, band energies, flux, pitch and pitch slope. Previous plans in this folder end with "listening remains the aesthetic test", and that stays true.

**Reliable from measurement:** duration and duration class; onset speed and whether a sound is slow-developing; where the energy sits in time; loudness balance between two sources; tonal versus noisy; brightness; pitch direction; whether two sounds occupy the same bands at the same time, which predicts masking; structural failures such as "B has not reached half its peak before A has finished".

**Unreliable from measurement:** whether a sound *reads* as a jump; whether a jingle feels triumphant or cheesy; wooden versus plastic; whether a mix fuses into one object or stays two sounds; what is simply pleasant. Those are yours.

**Evidence from a probe run today.** I rendered the 20 Mixfxr recipes already graded GOOD/OK/BAD in `js/synths/Mixr.js`, three instances each, and measured each source. Two structural patterns separate cleanly; the rest do not.

| Pattern in the pair | Graded | Examples |
| --- | --- | --- |
| Two sustained tonal sources, pitch unmatched | both BAD | Choirr × Riftr, Jinglr × Choirr |
| Short noisy transient against a longer noisy body, both starting at 0 | three of three BAD | Whooshr × Fractr, Rustlr × Clonkr, Fractr × Boomr |
| One tonal plus one noisy, or very different registers | mostly OK/GOOD | Machinr × Birdr, Pluckr × Crittr, Clonkr × Zappr |
| Duration ratio over 3 | 4 BAD, 1 OK | mixed signal; Birdr × Bfxr is fine at 9:1 |

So the measurements catch the mechanical failures (clashing tonality, a transient buried in another transient, slow onsets) but cannot rank the survivors. That shapes the division of labour below: I filter and propose, you judge.

## 4. The Mixfxr complement problem

Your Sonar example is measurable: Riftr sources in the probe take 0.4 s to reach half peak, while a Whooshr swipe is finished at 0.15 s. Mixfxr currently sums both from sample zero, so the short sound is gone before the slow one arrives. Three changes make far more pairs work.

1. **Alignment mode on Mixr** (`align`: Start / Peak / Tail). Peak aligns the two loudness peaks; Tail starts B where A's energy has decayed to a threshold. Both are computed from the rendered PCM, so no per-recipe hand tuning and saved files stay deterministic. An explicit `offset` in seconds covers the rest.
2. **Role grammar.** Classify every generator automatically as transient, body or tail from its features (short with a sharp attack; medium; long with late energy). Propose pairs across roles, never transient × transient or body × body of the same noisiness. This is ordinary sound-design layering made mechanical.
3. **Key matching for tonal pairs.** Jinglr has a key; Choirr, Pluckr and Bfxr tonal presets have a root or start frequency. A `tune` option sets B's root to A's detected fundamental or a fifth above. The two tonal × tonal BAD recipes are the test cases.

Compatibility scoring, computed offline for all generator pairs (about 230² / 2, cheap at 3 renders each): duration ratio, onset gap, band-overlap in the shared time window, tonal/noisy mix, loudness ratio after balance. The score prunes candidates; it does not pick winners.

## 5. What you contribute

- **The verb list.** Confirm or edit the 20 and their duration classes. Names matter more than anything I write here.
- **Listening verdicts, in rounds.** Each round I render a candidate pack (about 8 interpretations per category, 160 clips) into a listening sheet like `examples/Cabinet/index.html`, with keyboard grading (G / O / B, same scale you already used in Mixr.js) and a JSON export. Ten to fifteen minutes per round; I expect two or three rounds. I turn verdicts into weight changes, pruned sources and new candidates.
- **Reference sounds.** A handful of WAVs per category from games whose sounds you like. I measure them to set each category's duration, brightness and tonality targets, and the existing matcher can place a Bfxr approximation. This is the most direct way to move your taste into numbers.
- **Aesthetic stance.** Is the board retro-first with foley as an alternate, or equal? This decides default weights and whether a Style toggle (Retro / Foley / Any) is on the board.

## 6. UI sketch

The board is the first tab. Twenty large buttons; click plays a fresh interpretation. Below the grid, a recipe card for the last sound: ingredient names ("Bfxr Jump × Whooshr Dodge, peak-aligned"), **Again** (new interpretation, never repeating the previous source), **Variation** (keep the ingredients, mutate), **Pin** (lock to this ingredient set so Again stays inside it), **Open in Mixfxr** or **Open in <engine>** (hands the parameters to that tab, as "Layer in Stackr" does now). Number keys 1–0 and QWERTY trigger buttons for a true sound-board feel. Optional Style toggle at the top.

## 7. Phases

- [ ] **Measurement harness.** Node script renders every generator N times, writes `generator_profiles.json` (duration class, onset, role, brightness, tonality) and the pairwise compatibility table. Port the needed features from `analyze.py` to JavaScript so tests can use them. Reproduce the probe table above as a test fixture.
- [ ] **Mixr alignment and tuning.** Add `align` and `offset`, then `tune`. Tests for determinism, legacy records (default Start keeps old files identical) and the four BAD recipes that alignment or tuning should rescue. Re-grade those by listening.
- [ ] **Board data and engine.** `js/synths/Board.js` (a Mixr subclass or thin wrapper) with the category schema: id, name, duration range, weighted sources, each a generator or a pair with balance and align. Tests: every source resolves, every category renders audible within its duration class, replay is deterministic, anti-repeat works, retired engines load lazily as before.
- [ ] **Board tab.** Grid, recipe card, Again / Variation / Pin / Open in, keyboard, Style toggle. First tab in `register_tabs`.
- [ ] **Curation round 1.** Candidate pack and listening sheet; apply verdicts.
- [ ] **Curation rounds 2–3.** Re-render, re-grade, prune and reweight until each category has at least five sources you graded GOOD or OK.
- [ ] **Examples and docs.** `examples/Board/` with a reel and editable links, README section, rebuild script in `tools/render/`.

Dependencies: the harness first, because alignment, role grammar and candidate packs all read its output. Board data and the Board tab can proceed in parallel with alignment, using Start alignment until the new modes land.

## 8. Risks

- **Interpretation drift.** A category whose interpretations differ too much stops being one button. The duration class and the curation rounds are the guard.
- **Retired engines.** Tappr, Notifr, Tickr and Pewpr are good ingredients but are excluded from the Mixr catalog by `Mixr.retired`. The board needs its own allowlist and must not re-expose them in Mixfxr's dropdowns.
- **Load time.** 20 categories × many sources means more engines loaded at startup. Lazy loading per the existing startup tests should hold; measure it.
- **Over-trusting the score.** Compatibility scores prune; a high score is not a good sound. Nothing ships without a listening verdict.
