'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const adapterPath = path.resolve(__dirname, '../tools/render/multisynth_context.js');

test('headless inventory describes numeric synths and transition endpoints', () => {
    assert.ok(fs.existsSync(adapterPath), 'production adapter exists');
    const api = require(adapterPath).createMultisynthContext();
    const inventory = api.inventory();
    assert.equal(inventory.sampleRate, 44100);
    assert.match(inventory.sourceHash, /^[a-f0-9]{64}$/);
    assert.equal(inventory.synths.find(synth => synth.name === 'Bfxr').collectionCompatible, true);
    assert.equal(inventory.synths.find(synth => synth.name === 'Rumblr').collectionCompatible, false);
    assert.ok(inventory.synths.length >= 30);
    for (const name of ['Bfxr', 'Transfxr', 'Footsteppr', 'Clonkr', 'Rumblr']) {
        const synth = inventory.synths.find(s => s.name === name);
        assert.ok(synth, name);
        assert.ok(synth.presets.length > 0);
        assert.ok(!synth.presets.includes('mutate_params'));
        assert.equal(synth.defaults.masterVolume, 0.5);
    }
    const pitch = inventory.synths.find(s => s.name === 'Transfxr').params.find(p => p.name === 'pitch');
    assert.equal(pitch.type, 'KNOB_TRANSITION');
    assert.equal(pitch.min, 0);
    assert.equal(pitch.max, 1);
    assert.deepEqual(pitch.default, {start: 0.48, end: 0.25, curve: 'Ease Out'});
    assert.deepEqual(inventory.excluded.map(s => s.name).sort(), ['Chattr', 'Mixr', 'Stackr']);
});

test('every advertised preset samples deterministically and each synth replays finite audio', () => {
    const api = require(adapterPath).createMultisynthContext();
    for (const synth of api.inventory().synths) {
        for (const preset of synth.presets) {
            const params = api.sample(synth.name, preset, 173);
            assert.deepEqual(params, api.sample(synth.name, preset, 173), `${synth.name}/${preset}`);
            assert.equal(params.masterVolume, 0.5);
        }
        for (const seed of [0, 1, 173]) {
            const params = api.sample(synth.name, synth.presets[0], seed);
            const first = api.render(synth.name, params, seed);
            assert.ok(first.pcm instanceof Float32Array, synth.name);
            assert.ok(first.pcm.length > 0, synth.name);
            assert.ok(first.pcm.every(Number.isFinite), synth.name);
            assert.deepEqual(first.params, params, synth.name);
            const replay = api.render(synth.name, first.params, seed);
            assert.deepEqual(first.pcm, replay.pcm, synth.name);
        }
    }
});

test('every Footsteppr terrain renders finite deterministic audio', () => {
    const api = require(adapterPath).createMultisynthContext();
    const info = api.inventory().synths.find(synth => synth.name === 'Footsteppr');
    for (const terrain of info.params.find(param => param.name === 'terrain').values) {
        for (const seed of [0, 1, 173]) {
            const params = {...api.sample('Footsteppr', 'randomize_params', seed), terrain};
            const {pcm} = api.render('Footsteppr', params, seed);
            assert.ok(pcm.length > 0 && pcm.every(Number.isFinite), `terrain ${terrain}, seed ${seed}`);
            assert.ok(pcm.some(value => value !== 0), `terrain ${terrain}, seed ${seed} is audible`);
            assert.deepEqual(pcm, api.render('Footsteppr', params, seed).pcm);
        }
    }
});

test('setters clamp controls, preserve pre-DSP params, and reject invalid input', () => {
    const api = require(adapterPath).createMultisynthContext();
    const input = {pitch: {start: -4, end: 3, curve: 'bad'}, duration: -1, masterVolume: 0.1};
    const result = api.render('Transfxr', input, 1);
    assert.equal(result.params.duration, 0.05);
    assert.deepEqual(result.params.pitch, {start: 0, end: 1, curve: 'Ease Out'});
    assert.equal(result.params.masterVolume, 0.5);
    assert.equal(input.pitch.start, -4);
    const bfxr = api.render('Bfxr', {attackTime: 0, sustainTime: 0, decayTime: 0}, 1);
    assert.equal(bfxr.params.sustainTime, 0);
    assert.throws(() => api.render('Chattr', {}, 0), /unsupported|unknown/i);
    assert.throws(() => api.sample('Bfxr', 'constructor', 0), /preset/i);
    assert.throws(() => api.render('Bfxr', {bogus: 1}, 0), /parameter/i);
    assert.throws(() => api.render('Bfxr', {attackTime: NaN}, 0), /finite/i);
    assert.throws(() => api.render('Transfxr', {pitch: {start: Infinity}}, 0), /finite/i);
    assert.throws(() => api.render('Bfxr', [], 0), /parameter/i);
    const jinglr = api.sample('Jinglr', 'generate_confirm', 7);
    assert.equal(api.render('Jinglr', jinglr, 1).params.phrase, jinglr.phrase);
    assert.throws(() => api.render('Jinglr', {phrase: 3}), /string/i);
    const noise = {waveType: 3, sustainTime: 0.2, decayTime: 0.2};
    assert.notDeepEqual(api.render('Bfxr', noise, 1).pcm, api.render('Bfxr', noise, 2).pcm);
    assert.notDeepEqual(api.sample('Clonkr', 'generate_teacup', 1), api.sample('Clonkr', 'generate_teacup', 2));
});

test('NDJSON worker keeps stdout clean and recovers after malformed requests', () => {
    const commands = [JSON.stringify({op: 'inventory'}), '{bad',
        JSON.stringify({op: 'sample', synth: 'Clonkr', preset: 'generate_teacup', seed: 1}),
        JSON.stringify({op: 'render', synth: 'Transfxr', params: {duration: 0.1}, seed: 1})];
    const child = spawnSync(process.execPath, [path.resolve(__dirname, '../tools/render/multisynth_worker.js')],
        {input: commands.join('\n') + '\n', encoding: 'utf8', maxBuffer: 4 * 1024 * 1024});
    assert.equal(child.status, 0, child.stderr);
    const rows = child.stdout.trim().split('\n').map(line => JSON.parse(line));
    assert.equal(rows.length, 4);
    assert.equal(rows[0].ok, true);
    assert.ok(rows[0].synths.length > 0);
    assert.equal(rows[1].ok, false);
    assert.equal(rows[2].params.masterVolume, 0.5);
    const pcm = require(adapterPath).createMultisynthContext().render('Transfxr', {duration: 0.1}, 1).pcm;
    const bytes = Buffer.from(rows[3].audio, 'base64');
    assert.equal(bytes.length, pcm.length * 4);
    for (let i = 0; i < pcm.length; i++) assert.equal(bytes.readFloatLE(i * 4), pcm[i]);
});
