#!/usr/bin/env node
// Rebuild the editable Sound Cabinet and its exact 44.1 kHz mono examples.
// Per-category seeds keep existing examples stable when another category is added.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, root, plain} = require('../../tests/helpers/synth-context');
const {encodeWav16} = require('./wav');

const rate = 44100;
const output = path.resolve(process.argv[2] || path.join(root, 'examples/SoundCabinet'));
const families = ['Clonkr', 'Machinr', 'Jinglr', 'Squishr'];
const api = createContext(['Transfxr', ...families]);
const counts = [10, 8, 12, 10];
const descriptions = {
    Clonkr: 'Materials and contact: choose Wood, Glass, Metal, Ceramic, or Rubber, then Hit, Scrape, or Rattle. Size lowers the resonance as the object gets larger; Hollowness emphasizes its body. Strike Hardness changes the attack and upper modes, Damping shortens ringing, and Duration controls resonance and the length of continued contact.',
    Machinr: 'Mechanism chooses the moving parts. Speed and Load control their movement; Roughness and Gear Looseness add worn bearings, friction, and rattles. Size changes the register, while Duration, Start Time, and Stop Time shape the movement.',

    Jinglr: 'Choose an Instrument, Key, Scale, and Octave, then shape the phrase with Tempo, Swing, Brightness, Decay, and Echo. Contour, Rhythm and Notes shape the tune. The ten-digit seed combines five melody digits with five instrument-character digits.',
    Squishr: 'Texture selects slime, bubbles, suction, splat, gulp, or spring. Viscosity thickens and muffles the material; Stretch lengthens its deformation; Pressure adds force and activity; Wetness brings bubbles forward; Bubble Size lowers their resonance as they grow. Duration sets the gesture length.'};

function seedFor(text) {
    let hash = 2166136261;
    for (const character of text) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
    return (hash >>> 0) / 4294967296;
}

function preferredScore(family, recipe, params) {
    let score = 0;
    // Favor a moderate gesture length while preserving the category's ranges.
    const duration = recipe.values.duration;
    if (Array.isArray(duration)) {
        const target = duration[0] + (duration[1] - duration[0]) * 0.4;
        score += Math.abs(params.duration - target) / Math.max(0.01, duration[1] - duration[0]);
    }
    if (family === 'Clonkr' && recipe.id === 'dungeon_gate' && params.action !== 1) score += 3;
    if (family === 'Jinglr') {
        const instruments = {discovery:1, victory:2, failure:0, secret:1, warning:2,
            checkpoint:3, puzzle_solved:0, lullaby:3};
        if (params.instrument !== instruments[recipe.id]) score += 3;
        // Short phrases keep the examples useful as game cues, while the lullaby breathes.
        const targetNotes = recipe.id === 'lullaby' ? 5 : recipe.id === 'puzzle_solved' ? 7 : 4;
        score += Math.abs(params.noteCount - targetNotes) * 0.1;
    }
    return score;
}

function measure(pcm, label) {
    let peak = 0, energy = 0, nonFinite = 0;
    for (const sample of pcm) {
        if (!Number.isFinite(sample)) { nonFinite++; continue; }
        peak = Math.max(peak, Math.abs(sample));
        energy += sample * sample;
    }
    const rms = Math.sqrt(energy / Math.max(1, pcm.length));
    assert.equal(nonFinite, 0, `${label}: all samples must be finite`);
    assert.ok(peak < 1, `${label}: peak ${peak} must remain below full scale`);
    assert.ok(peak > 0.025 && rms > 0.0015, `${label}: must be audible (peak ${peak}, RMS ${rms})`);
    return {frames:pcm.length, duration:pcm.length / rate, peak, rms, nonFinite,
        pcmSha256:crypto.createHash('sha256').update(Buffer.from(pcm.buffer, pcm.byteOffset, pcm.byteLength)).digest('hex')};
}

fs.mkdirSync(output, {recursive:true});
const collection = {}, sounds = [];
for (const [familyIndex, family] of families.entries()) {
    const recipes = plain(api.run(`var synth = new ${family}(); synth.recipes`));
    assert.equal(recipes.length, counts[familyIndex], `${family}: expected category count`);
    const files = [];
    for (const recipe of recipes) {
        let chosen;
        for (let candidate = 0; candidate < 12; candidate++) {
            const generationSeed = seedFor(`SoundCabinet/v1/${family}/${recipe.id}/${candidate}`);
            const params = plain(api.run(`Math.random = SoundDSP.rng(${generationSeed});
                synth.generate_recipe(${JSON.stringify(recipe.id)}); synth.params`));
            const score = preferredScore(family, recipe, params);
            if (!chosen || score < chosen.score) chosen = {params, score, generationSeed};
        }
        const paramsJSON = JSON.stringify(chosen.params);
        const pcm = api.run(`synth.apply_params(${paramsJSON}); synth.generate_sound(); synth.sound.getBuffer().slice()`);
        const metrics = measure(pcm, `${family} / ${recipe.name}`);
        // Saved phrases and nested layer snapshots must reproduce the same PCM.
        const restored = api.run(`var restored = new ${family}(); restored.apply_params(${paramsJSON});
            restored.generate_sound(); restored.sound.getBuffer()`);
        assert.equal(measure(restored, `${family} / ${recipe.name} reload`).pcmSha256, metrics.pcmSha256);
        const file = `${family.toLowerCase()}_${recipe.id}.wav`;
        fs.writeFileSync(path.join(output, file), encodeWav16(pcm, rate));
        files.push([recipe.name, paramsJSON, paramsJSON]);
        sounds.push({synth:family, id:recipe.id, name:recipe.name, tip:recipe.tip,
            file, generationSeed:chosen.generationSeed, ...metrics, pcm});
        console.log(`${family.padEnd(7)} ${recipe.name.padEnd(19)} ${metrics.duration.toFixed(2)} s  peak ${metrics.peak.toFixed(3)}  RMS ${metrics.rms.toFixed(3)}`);
    }
    collection[family] = {files, selected_file_index:0, create_new_sound:true, play_on_change:true,
        locked_params:plain(api.run('synth.locked_params'))};
}
collection.active_tab_name = 'Clonkr';
assert.equal(sounds.length, 40);
fs.writeFileSync(path.join(output, 'SoundCabinet.bcol'), JSON.stringify(collection, null, 2) + '\n');

// Solids → mechanisms → wet creatures → music.
// Gestures and musical phrases play to completion.
const showcasePlan = [
    ['Clonkr', 'wood_knock'], ['Clonkr', 'glass_ping'],
    ['Machinr', 'camera_shutter'], ['Machinr', 'rusty_winch'],

    ['Squishr', 'water_drop'], ['Squishr', 'suction_cup'], ['Squishr', 'slime_step'],
    ['Jinglr', 'discovery'], ['Jinglr', 'checkpoint']];
const clips = [];
const gap = Math.round(0.28 * rate);
let frame = 0;
for (const [family, id, excerptSeconds] of showcasePlan) {
    const sound = sounds.find(entry => entry.synth === family && entry.id === id);
    assert.ok(sound, `showcase source ${family}/${id}`);
    const clip = sound.pcm.slice(0, excerptSeconds ? Math.round(excerptSeconds * rate) : sound.pcm.length);
    const gain = Math.min(2.4, 0.095 / sound.rms, 0.72 / sound.peak);
    const fade = Math.round(0.12 * rate);
    for (let i = 0; i < clip.length; i++) {
        const envelope = excerptSeconds ? Math.min(1, i / fade, (clip.length - 1 - i) / fade) : 1;
        clip[i] *= gain * envelope;
    }
    clips.push({synth:family, name:sound.name, file:sound.file, start:frame / rate,
        end:(frame + clip.length) / rate, gain, excerpt:Boolean(excerptSeconds), pcm:clip});
    frame += clip.length + gap;
}
const reel = new Float32Array(frame - gap);
for (const clip of clips) reel.set(clip.pcm, Math.round(clip.start * rate));
const reelMetrics = measure(reel, 'Sound Cabinet showcase');
assert.ok(reelMetrics.duration >= 10 && reelMetrics.duration <= 40, 'showcase must last 10–40 seconds');
const showcaseFile = 'sound_cabinet_showcase.wav';
fs.writeFileSync(path.join(output, showcaseFile), encodeWav16(reel, rate));

const withoutPCM = ({pcm, ...entry}) => entry;
const report = {sampleRate:rate, format:'mono PCM16 WAV', sounds:sounds.map(withoutPCM),
    showcase:{file:showcaseFile, ...reelMetrics, gap:gap / rate, clips:clips.map(withoutPCM)}};
fs.writeFileSync(path.join(output, 'validation.json'), JSON.stringify(report, null, 2) + '\n');

function timestamp(seconds) {
    const minutes = Math.floor(seconds / 60);
    return `${String(minutes).padStart(2, '0')}:${(seconds - minutes * 60).toFixed(2).padStart(5, '0')}`;
}
const readme = [
    '# Sound Cabinet examples', '',
    '40 editable sounds, one from every category in Clonkr, Machinr, Jinglr, and Squishr. These are exact saved variants of the randomized category buttons; clicking a category in the app creates another sound in that family.', '',
    '## Load and explore', '',
    'Use **Open Data** in Bfxr and choose [SoundCabinet.bcol](SoundCabinet.bcol), or drag the collection onto the app. It opens Clonkr and fills the four Sound Cabinet tabs. Loading replaces the sound lists in those four tabs; use **Save .bcol** first if you want to keep an existing collection.', '',
    'Select a sound in a tab to play or edit it. **Export WAV** saves that sound; **Export All** exports sounds from all tabs into one ZIP. A row lock protects its control during category generation, Randomize, and Mutate. The saved examples start with only Sound Volume locked, so the other controls are ready to explore.', '',
    '## Rebuild the audio', '',
    'From the repository root:', '',
    '```sh', 'node tools/render/specialized_examples.js', '```', '',
    'An optional final argument chooses another output folder. The script uses stable per-category seeds, selects representative variants within the normal recipe ranges, and writes 40 individual 44.1 kHz mono PCM16 WAVs, the editable collection, this guide, the showcase, and [validation.json](validation.json). WAVs are generated locally and ignored by Git. Rebuilding overwrites generated files in the chosen folder.', '',
    `Every example is checked for finite samples, peaks below full scale, audible RMS, and identical audio after loading its saved parameters. This render contains ${sounds.length} sounds with RMS ${Math.min(...sounds.map(s => s.rms)).toFixed(4)}–${Math.max(...sounds.map(s => s.rms)).toFixed(4)} and maximum peak ${Math.max(...sounds.map(s => s.peak)).toFixed(4)}.`, '',
    '## Short showcase', '',
    `[Play the ${reelMetrics.duration.toFixed(1)}-second showcase](${showcaseFile}). Each gesture and musical phrase plays completely, with 0.28-second gaps. The reel balances playback levels; individual WAVs retain exactly the levels stored in the collection.`, '',
    '| Start | End | Tab | Sound |', '| --- | --- | --- | --- |',
    ...clips.map(clip => `| ${timestamp(clip.start)} | ${timestamp(clip.end)} | ${clip.synth} | ${clip.name}${clip.excerpt ? ' (excerpt)' : ''} |`), '',
    '## Phrase editing', '',
    '**Jinglr:** reseed melody and instrument independently. Edited phrases and their settings travel together in saved sounds and Mixr copies.', ''
];
for (const family of families) {
    readme.push(`## ${family}`, '', descriptions[family], '', '| Category | Character | Length |', '| --- | --- | --- |');
    for (const sound of sounds.filter(entry => entry.synth === family)) {
        readme.push(`| [${sound.name}](${sound.file}) | ${sound.tip} | ${sound.duration.toFixed(2)} s |`);
    }
    readme.push('');
}
fs.writeFileSync(path.join(output, 'README.md'), readme.join('\n'));
console.log(`Wrote ${sounds.length} exact examples and ${reelMetrics.duration.toFixed(2)} s showcase to ${output}`);
