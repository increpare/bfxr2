# Sound Board: a game-verb front end for the Bfxr suite

**Goal:** Make the first thing a game developer sees a board of plain game verbs (Jump, Coin, Hurt…). Each button gives a fresh, varied interpretation of that verb drawn from the whole suite: classic Bfxr prefabs, the physical and exotic engines, Jinglr cues, and curated Mixfxr pairs. Everything stays editable in the engine that made it.

**Architecture:** Three layers sharing one vocabulary of game verbs.

1. **Verb prefabs per synth.** Each engine gets game-verb preset buttons drawn from the standard vocabulary (Whooshr: Jump, Dash, Swing; Clonkr: Hit, Land, Door…). A synth only gets a verb it can carry as a clear base on its own. They are ordinary preset buttons in the engine's tab, listed first because this is a game sound tool, with the engine's character presets after them and Randomize / Mutate last. They are developed, locked, mutated and listened to with the tooling that already exists.
2. **Mixfxr verb recipes.** A mix is no longer "synth × synth, any generator". It names two verb prefabs, generated separately: `Whooshr:swing` as the base plus `Clonkr:hit` as the sweetener, with balance biased to the base and an alignment mode. The engine already addresses a specific generator (`Mixr.generated_source(synth, generator)`); only the recipe schema and the `*` wildcard change.
3. **The board.** One button per verb, selecting from a weighted catalogue of layer 1 and layer 2 entries for that verb. Board sounds are stored as Mixr records (a Mixr with one source renders that source alone), so save, load, share links, WAV export and Stackr layering already work.

The one engine change is Mixfxr time alignment (start / peak / tail), which makes slow-developing sounds such as Sonar usable as sweeteners.

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

## 2. The vocabulary as a shared constant

The 20 verbs (plus the optional row) become a single table, `GAME_VERBS` in `js/globals.js`: id, label, duration class, and a one-line meaning so every engine's prefab is aiming at the same target. Tests enforce the contract: a verb prefab's id must be in the vocabulary, its rendered duration must fall in the verb's class, and every verb must have at least three bases across the suite.

**Base and sweetener.** A verb prefab is always a base: it must read as its verb alone. The same prefab can serve as a sweetener in a mix for a *different* verb (Clonkr:hit sweetens Whooshr:swing). So the mix catalogue is written entirely in the vocabulary, and sweeteners need no second kind of prefab, only a role tag derived from measurement (transient, body, tail).

**Reuse, do not duplicate.** Bfxr's seven prefabs and several Jinglr cues are already verbs (Victory → Win, Confirm → Confirm, Failure → Lose). Those become aliases into the vocabulary rather than new recipes. Bfxr keeps its `.bcol` example-driven templates; PresetSynth engines use range recipes. Both produce a `generate_<verb>` method, which is all the layers above need.

**Rough size.** Each engine realistically carries three to six verbs, so about 100 verb prefabs across 24 engines, plus a few dozen mix recipes. The inventory in §8 decides which.

## 3. What each verb draws from

Each verb has a duration class so its interpretations feel interchangeable in a game. Below, each entry is a candidate verb prefab for that engine (to be built and listened to in its own tab) or a Mixfxr verb recipe written as `Base:verb × Sweetener:verb`. Weights are a first guess for the curation loop. Engines in *italics* are retired from navigation but still render, so they can serve as hidden ingredients.

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

## 4. How good my sound perception is, honestly

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

So the measurements catch the mechanical failures (clashing tonality, a transient buried in another transient, slow onsets) but cannot rank the survivors. That shapes the division of labour in §6: I filter and propose, you judge.

## 5. The Mixfxr complement problem

Your Sonar example is measurable: Riftr sources in the probe take 0.4 s to reach half peak, while a Whooshr swipe is finished at 0.15 s. Mixfxr currently sums both from sample zero, so the short sound is gone before the slow one arrives. Three changes make far more pairs work.

1. **Alignment mode on Mixr** (`align`: Start / Peak / Tail). Peak aligns the two loudness peaks; Tail starts B where A's energy has decayed to a threshold. Both are computed from the rendered PCM, so no per-recipe hand tuning and saved files stay deterministic. An explicit `offset` in seconds covers the rest.
2. **Role grammar.** Classify every generator automatically as transient, body or tail from its features (short with a sharp attack; medium; long with late energy). Propose pairs across roles, never transient × transient or body × body of the same noisiness. This is ordinary sound-design layering made mechanical.
3. **Key matching for tonal pairs.** Jinglr has a key; Choirr, Pluckr and Bfxr tonal presets have a root or start frequency. A `tune` option sets B's root to A's detected fundamental or a fifth above. The two tonal × tonal BAD recipes are the test cases.

Compatibility scoring is computed offline, but only over verb prefabs: each base against every prefab tagged with a complementary role. That is a few thousand pairs rather than all 230² / 2 generator pairs. Features: duration ratio, onset gap, band overlap in the shared time window, tonal/noisy mix, loudness ratio after balance. The score prunes candidates; it does not pick winners.

## 6. What you contribute

- **The verb list.** Confirm or edit the 20 and their duration classes. Names matter more than anything I write here.
- **Listening verdicts, in rounds.** Each round I render a candidate pack (about 8 interpretations per category, 160 clips) into a listening sheet like `examples/Cabinet/index.html`, with keyboard grading (G / O / B, same scale you already used in Mixr.js) and a JSON export. Ten to fifteen minutes per round; I expect two or three rounds. I turn verdicts into weight changes, pruned sources and new candidates.
- **Reference sounds.** A handful of WAVs per category from games whose sounds you like. I measure them to set each category's duration, brightness and tonality targets, and the existing matcher can place a Bfxr approximation. This is the most direct way to move your taste into numbers.
- **Aesthetic stance.** Is the board retro-first with foley as an alternate, or equal? This decides default weights and whether a Style toggle (Retro / Foley / Any) is on the board.

## 7. UI sketch

The board is the first tab. Twenty large buttons; click plays a fresh interpretation. Below the grid, a recipe card for the last sound: ingredient names ("Bfxr Jump × Whooshr Dodge, peak-aligned"), **Again** (new interpretation, never repeating the previous source), **Variation** (keep the ingredients, mutate), **Pin** (lock to this ingredient set so Again stays inside it), **Open in Mixfxr** or **Open in <engine>** (hands the parameters to that tab, as "Layer in Stackr" does now). Number keys 1–0 and QWERTY trigger buttons for a true sound-board feel. Optional Style toggle at the top.

## 8. Phases

- [x] **Vocabulary and measurement harness.** `GAME_VERBS` table. Node script renders every existing recipe N times and writes `generator_profiles.json` (duration class, onset, role, brightness, tonality). Port the needed features from `analyze.py` to JavaScript so tests can use them. Reproduce the probe table above as a test fixture.
- [x] **Base inventory.** (as `tools/render/verb_inventory.js`, measured rather than hand-ticked for the first pass) A synth × verb matrix: for each existing recipe, which verbs its measurements fit as a base and which role it could play as a sweetener. Marks thin verbs (Step, Splash, Shoot) where a new in-engine prefab is needed. This is the sheet you tick by ear.
- [x] **Verb prefabs, engine by engine.** Add `generate_<verb>` recipes (or rename existing ones that already are the verb) per the ticked inventory. A recipe gains an optional `verb` field; `initialize_presets` orders verb recipes first. The button reads as the verb ("Jump"), the tooltip carries the engine's flavour ("A soft air jump."). Tests: verb in vocabulary, duration in class, audible, deterministic replay.
- [ ] **Listening round 1, bases only.** Pack of every verb prefab, graded "reads as its verb" G/O/B. No mixes yet, so the question stays clean. Apply verdicts.
- [x] **Mixr alignment and tuning.** (align and offset shipped; `tune` for tonal pairs still open) Add `align` and `offset`, then `tune`. Recipe schema accepts `Synth:verb` entries and a base/sweetener distinction. Tests for determinism and legacy records (default Start keeps old files identical). Re-try the four BAD recipes that alignment or tuning should rescue.
- [x] **Mixfxr verb recipes.** (hand-picked base × sweetener pairs in the board catalogue; the offline compatibility score is still open) Compatibility scoring over bases × role-tagged sweeteners; propose recipes per verb; render and grade in listening round 2.
- [x] **Board data and tab.** `js/synths/Board.js` (a Mixr subclass or thin wrapper) reading the weighted catalogue of layer 1 and layer 2 entries per verb. Grid, recipe card, Again / Variation / Pin / Open in, keyboard, Style toggle. First tab in `register_tabs`. Tests: every entry resolves, anti-repeat works, retired engines load lazily as before.
- [ ] **Listening round 3 and reweighting.** Full board pack; prune and reweight until each verb has at least five entries graded GOOD or OK.
- [x] **Examples and docs.** `examples/Board/` with a reel and editable links, README section, rebuild script in `tools/render/`.

Dependencies: the vocabulary and harness first, since the inventory, prefab tests and compatibility scoring all read from them. Verb prefabs come before any mix work, because mixes are written in terms of them. The board tab can be built against layer 1 alone and gain layer 2 entries when they land.

## 9. Risks

- **Interpretation drift.** A verb whose prefabs differ too much across engines stops being one button. The shared vocabulary table, the duration class and the bases-only listening round are the guard.
- **Character presets with no verb.** Once verb prefabs lead each tab, some engine-flavoured presets ("Codec Warble", "Derelict Beacon") will have no board role. Whether they stay as colour, get renamed to a verb, or go is a per-engine call made during the inventory, not up front.
- **Retired engines.** Tappr, Notifr, Tickr and Pewpr are good ingredients but are excluded from the Mixr catalog by `Mixr.retired`. The board needs its own allowlist and must not re-expose them in Mixfxr's dropdowns.
- **Load time.** 20 categories × many sources means more engines loaded at startup. Lazy loading per the existing startup tests should hold; measure it.
- **Over-trusting the score.** Compatibility scores prune; a high score is not a good sound. Nothing ships without a listening verdict.

## 10. First build (overnight, 2026-10-03)

Shipped on this branch: the 25-verb vocabulary (`GAME_VERBS`), verb presets leading 19 engines (95 verb recipes: 86 new plus 9 tagged existing ones, beside Bfxr's eight and Footsteppr), Mixfxr Align/Offset, the Soundboard tab with its catalogue of 168 ingredients (123 solo, 45 base × sweetener mixes) and editor, a headless inventory harness, tests, and a 100-take gallery.

Measured: every ingredient renders finite, audible audio inside its verb's duration class across seeded takes. Not measured: whether it sounds good. The three listening rounds in §8 are still yours; the gallery at `examples/Soundboard/index.html` is round one's pack, bases and mixes together because the board is already live. Grade by ingredient name and I will reweight the catalogue.

Known gaps: no `tune` for tonal pairs yet, so Win and Heal avoid jingle × choir mixes; retired engines (Tappr, Pewpr) appear only as hidden ingredients and open in a legacy tab; the Style toggle (Retro / Foley / Any) is not built.
