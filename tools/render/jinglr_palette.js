#!/usr/bin/env node
// Compare independent instrument seeds while holding the whole melody constant.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, root, plain} = require('../../tests/helpers/synth-context');
const {encodeWav16} = require('./wav');

const rate = 44100;
const output = path.resolve(process.argv[2] || path.join(root, 'examples/Jinglr'));
const api = createContext(['Jinglr']);
const names = ['Pluck', 'Bell', 'Chip', 'Flute', 'Keys', 'Reed', 'FM', 'Strings'];
// Chosen from twelve candidates per family for different spectral balances AND
// attack/decay envelopes. A has the lower measured high-frequency energy ratio.
const voiceSeeds = [[57721,61803], [61803,99991], [57721,99991], [10001,22361],
    [31415,12537], [27182,31415], [99991,10001], [27182,12537]];
const melodyCode = 10153;
const controls = {masterVolume:0.5, seed:melodyCode / 99999, noteCount:4,
    key:0, scale:0, octave:4, contour:0, rhythm:0, tempo:126, swing:0,
    brightness:0.65, decay:0.45, echo:0};

function measure(pcm, label) {
    let peak = 0, energy = 0, difference = 0, early = 0, late = 0, nonFinite = 0;
    for (let i = 0; i < pcm.length; i++) {
        const sample = pcm[i];
        if (!Number.isFinite(sample)) { nonFinite++; continue; }
        const power = sample * sample;
        peak = Math.max(peak, Math.abs(sample));
        energy += power;
        if (i) difference += (sample - pcm[i - 1]) ** 2;
        if (i < 1500) early += power;
        if (i > 5000 && i < 8000) late += power;
    }
    const rms = Math.sqrt(energy / Math.max(1, pcm.length));
    assert.equal(nonFinite, 0, `${label}: finite audio`);
    assert.ok(peak > 0.025 && peak < 1 && rms > 0.005, `${label}: audible, bounded audio`);
    assert.ok(pcm[0] === 0 && pcm.at(-1) === 0, `${label}: silent endpoints`);
    return {frames:pcm.length, duration:pcm.length / rate, peak, rms, nonFinite,
        spectralBalance:difference / energy, firstNoteEnvelope:late / early,
        pcmSha256:crypto.createHash('sha256').update(Buffer.from(pcm.buffer, pcm.byteOffset, pcm.byteLength)).digest('hex')};
}

fs.mkdirSync(output, {recursive:true});
api.run(`var synth = new Jinglr(); synth.apply_params(${JSON.stringify(controls)}); synth.generate_phrase();`);
const phrase = api.run('synth.params.phrase');
const schedule = plain(api.run('Jinglr_DSP.schedule(synth.params)'));
assert.equal(api.run('synth.melody_matches_seed()'), true, 'displayed melody seed reconstructs the tune');
assert.deepEqual(schedule.events.map(note => note.midi), [60,64,67,72], 'C4–E4–G4–C5');
assert.ok(schedule.duration >= 1 && schedule.duration <= 1.5, 'short comparison tune');

const voices = [], files = [];
for (const [instrument, family] of names.entries()) {
    for (const [variation, instrumentSeed] of voiceSeeds[instrument].entries()) {
        const code = String(melodyCode).padStart(5, '0') + String(instrumentSeed).padStart(5, '0');
        const label = `${family} ${variation ? 'B' : 'A'} · ${code}`;
        const params = plain(api.run(`synth.set_param('instrument', ${instrument});
            synth.set_param('instrumentSeed', ${instrumentSeed}); synth.params`));
        assert.equal(params.phrase, phrase, `${label}: changing voice preserves the tune`);
        for (const [key, value] of Object.entries(controls)) assert.equal(params[key], value, `${label}: fixed ${key}`);
        const pcm = api.run('synth.generate_sound(); synth.sound.getBuffer().slice()');
        const metrics = measure(pcm, label);
        const paramsJSON = JSON.stringify(params);
        const restored = api.run(`var copy = new Jinglr(); copy.apply_params(${paramsJSON});
            copy.generate_sound(); copy.sound.getBuffer()`);
        assert.equal(measure(restored, `${label} restored`).pcmSha256, metrics.pcmSha256, 'saved PCM reproducibility');
        // The combined seed plus the same family and musical knobs reconstructs the same
        // notes and voice without importing hidden phrase data.
        const fromSeeds = api.run(`copy.reset_params(); copy.apply_params(${JSON.stringify(controls)});
            copy.set_param('seed', ${melodyCode} / 99999); copy.set_param('instrument', ${instrument});
            copy.set_param('instrumentSeed', ${instrumentSeed}); copy.generate_sound(); copy.sound.getBuffer()`);
        assert.equal(measure(fromSeeds, `${label} seeds`).pcmSha256, metrics.pcmSha256, 'two-seed PCM reproducibility');
        const file = `${String(instrument)}_${family.toLowerCase()}_${instrumentSeed}.wav`;
        fs.writeFileSync(path.join(output, file), encodeWav16(pcm, rate));
        files.push([label, paramsJSON, paramsJSON]);
        voices.push({instrument, family, variation:variation ? 'B' : 'A', instrumentSeed, code, file, ...metrics, pcm});
        console.log(`${code} ${family.padEnd(7)} ${variation ? 'B' : 'A'}  ${metrics.duration.toFixed(3)} s  peak ${metrics.peak.toFixed(3)}  RMS ${metrics.rms.toFixed(3)}`);
    }
    const [a,b] = voices.slice(-2);
    assert.notEqual(a.pcmSha256, b.pcmSha256, `${family}: different characters`);
    assert.ok(Math.abs(Math.log(a.spectralBalance / b.spectralBalance)) > 0.15, `${family}: spectral contrast`);
    assert.ok(Math.abs(Math.log(a.firstNoteEnvelope / b.firstNoteEnvelope)) > 0.15, `${family}: envelope contrast`);
}

const collection = {Jinglr:{files, selected_file_index:0, create_new_sound:true, play_on_change:true,
    locked_params:plain(api.run('synth.locked_params'))}, active_tab_index:7};
fs.writeFileSync(path.join(output, 'JinglrPalette.bcol'), JSON.stringify(collection, null, 2) + '\n');

const gap = Math.round(rate * 0.2);
const reel = new Float32Array(voices.reduce((total, voice) => total + voice.frames, 0) + gap * (voices.length - 1));
let offset = 0;
const clips = [];
for (const voice of voices) {
    // Mild level matching keeps the comparison comfortable. Full individual
    // renders remain at their stored masterVolume of 0.5.
    const gain = Math.min(1.35, Math.max(0.75, 0.105 / voice.rms), 0.7 / voice.peak);
    for (let i = 0; i < voice.frames; i++) reel[offset + i] = voice.pcm[i] * gain;
    clips.push({family:voice.family, variation:voice.variation, code:voice.code, file:voice.file,
        start:offset / rate, end:(offset + voice.frames) / rate, gain});
    offset += voice.frames + gap;
}
const reelMetrics = measure(reel, 'Instrument palette reel');
assert.ok(reelMetrics.duration >= 20 && reelMetrics.duration <= 40, '20–40 second audition');
const reelFile = 'jinglr_instrument_palette.wav';
fs.writeFileSync(path.join(output, reelFile), encodeWav16(reel, rate));
const report = {sampleRate:rate, format:'mono PCM16 WAV', melodyCode, controls, phrase:JSON.parse(phrase),
    melodyDuration:schedule.duration, voices:voices.map(({pcm, ...voice}) => voice),
    showcase:{file:reelFile, ...reelMetrics, gap:0.2, clips}};
fs.writeFileSync(path.join(output, 'validation.json'), JSON.stringify(report, null, 2) + '\n');

const timestamp = seconds => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${(seconds % 60).toFixed(2).padStart(5, '0')}`;
const readme = [
    '# Jinglr instrument palette', '',
    `Sixteen exact voices: two characters from each of Jinglr's eight instrument families. Every voice plays the same ${schedule.duration.toFixed(2)}-second C4–E4–G4–C5 tune. The different attack, tone, and decay come from the instrument seed; the notes and musical knobs stay fixed.`, '',
    `Listen to the [${reelMetrics.duration.toFixed(1)}-second audition reel](${reelFile}). Families play in order, with voice A followed by voice B and a 0.2-second gap between examples. Each phrase and its tail plays completely. The reel applies mild level matching (0.75–1.35×); individual WAVs keep Sound Volume at 0.5.`, '',
    '## Try the instruments', '',
    'Use **Open Data** to load [JinglrPalette.bcol](JinglrPalette.bcol). It opens Jinglr and replaces only that tab’s sound list. Save your current collection first if you want to keep those sounds.', '',
    'The ten-digit **Seed** contains five melody digits followed by five instrument-character digits. Choose the instrument family, then enter a listed seed to restore an example. The instrument buttons reseed only its character; **Reseed melody** changes only the tune.', '',
    '## Fixed musical settings', '',
    `Melody seed **${melodyCode}**; C major; octave 4; Rise contour; Even rhythm; 4 notes; tempo 126 BPM; swing 0; brightness 0.65; decay 0.45; echo 0; Sound Volume 0.5. These controls and that melody seed reconstruct the same tune without importing the collection.`, '',
    'Both examples in each family were selected from a small seed search for different spectral balances and envelopes. A has the lower measured high-frequency energy ratio of the pair. These are comparison points, not limits on the family’s range.', '',
    '## Voice codes and reel timestamps', '',
    '| Start | End | Family | Voice | Seed |', '| --- | --- | --- | --- | --- |',
    ...clips.map(clip => `| ${timestamp(clip.start)} | ${timestamp(clip.end)} | ${clip.family} | [${clip.variation}](${clip.file}) | ${clip.code} |`), '',
    '## Rebuild', '',
    'From the repository root:', '', '```sh', 'node tools/render/jinglr_palette.js', '```', '',
    'An optional output-folder argument writes the palette elsewhere. The script writes sixteen 44.1 kHz mono PCM16 WAVs, the reel, the editable collection, this guide, and [validation.json](validation.json). Generated WAVs are ignored by Git.', '',
    `The renderer verifies finite, audible, bounded audio; exact saved-parameter and two-seed PCM reproducibility; unchanged musical controls; and spectral/envelope differences within each pair. Individual RMS is ${Math.min(...voices.map(voice => voice.rms)).toFixed(4)}–${Math.max(...voices.map(voice => voice.rms)).toFixed(4)}, with maximum peak ${Math.max(...voices.map(voice => voice.peak)).toFixed(4)}.`, ''
];
fs.writeFileSync(path.join(output, 'README.md'), readme.join('\n'));
console.log(`Wrote 16 seeded voices and a ${reelMetrics.duration.toFixed(2)} s reel to ${output}`);
