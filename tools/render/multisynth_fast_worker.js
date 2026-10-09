#!/usr/bin/env node
'use strict';
// Same protocol and sources as multisynth_worker.js, but the synths run in the
// main realm rather than a vm context. A contextified global makes every
// top-level function/var lookup go through interceptors; rendering is ~5x
// slower there. Output is bit-identical (tests/test_sfxmatch_render.py).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const readline = require('node:readline');
const REPO_ROOT = path.resolve(__dirname, '../..');
const contextFile = path.join(__dirname, 'multisynth_context.js');
// The vm context stays the source of truth for inventory, sourceHash and the
// HOST/BRIDGE shims; reuse them verbatim instead of maintaining a second copy.
const inventory = require(contextFile).createMultisynthContext().inventory();
const contextSource = fs.readFileSync(contextFile, 'utf8');
const shim = name => {
    const match = contextSource.match(new RegExp('const ' + name + ' = `([\\s\\S]*?)`;'));
    if (!match) throw new Error('Cannot find ' + name + ' in multisynth_context.js');
    return match[1];
};
const names = inventory.synths.map(synth => synth.name);
const wanted = new Set(['js/globals.js', 'js/audio/AKWF.js', 'js/audio/BfxrWaveforms.js',
    'js/audio/riffwave.js', 'js/audio/RealizedSound.js', 'js/audio/SoundDSP.js',
    'js/audio/puredata.js', 'js/audio/puredata_modules.js', 'js/audio/puredata_parser.js',
    'js/synths/templates.js', 'js/synths/SynthBase.js', 'js/synths/PresetSynth.js',
    'js/synths/PresetFamily.js', 'js/synths/TransfxrPresets.js',
    ...names.map(name => 'js/synths/' + name + '.js'),
    ...names.filter(name => name !== 'Footsteppr').map(name => 'js/audio/' + name + '_DSP.js')]);
const index = fs.readFileSync(path.join(REPO_ROOT, 'index.html'), 'utf8');
const sources = [...index.matchAll(/<script\s+src="([^"?]+)(?:\?[^\"]*)?"/g)]
    .map(match => match[1]).filter(source => wanted.has(source));
if (sources.length !== wanted.size) throw new Error('Missing or duplicate synth scripts in index.html');

// Synths log to console; stdout carries the protocol, so silence them.
for (const level of ['log', 'info', 'warn', 'error', 'debug']) console[level] = () => {};
const storage = new Map();
globalThis.__names = names;
globalThis.localStorage = {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, String(value))};
vm.runInThisContext(shim('HOST'), {filename: 'multisynth-host.js'});
for (const source of sources)
    vm.runInThisContext(fs.readFileSync(path.join(REPO_ROOT, source), 'utf8'), {filename: source});
vm.runInThisContext(shim('BRIDGE'), {filename: 'multisynth-bridge.js'});
// canonical: the controls a render would use, without rendering (for native engines).
const bridge = vm.runInThisContext('({sample:__sample,render:__render,' +
    'canonical:request=>__canonical(__newSynth(request.synth),request.params)})');

function checkSeed(seed) {
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw new Error('Seed must be an unsigned 32-bit integer');
}

const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
lines.on('line', line => {
    if (!line.trim()) return;
    let response;
    try {
        const request = JSON.parse(line);
        switch (request.op) {
            case 'inventory': response = inventory; break;
            case 'sample':
                checkSeed(request.seed);
                response = {params: JSON.parse(JSON.stringify(bridge.sample(request)))};
                break;
            case 'canonical':
                response = {params: JSON.parse(JSON.stringify(bridge.canonical(request)))};
                break;
            case 'render': {
                checkSeed(request.seed);
                const {params, pcm} = bridge.render(request);
                const audio = Buffer.from(pcm.buffer, pcm.byteOffset, pcm.byteLength).toString('base64');
                response = {sampleRate: 44100, params: JSON.parse(JSON.stringify(params)), audio};
                break;
            }
            default: throw new Error('Unknown operation: ' + request.op);
        }
        response = {ok: true, ...response};
    } catch (error) { response = {ok: false, error: error.message}; }
    process.stdout.write(JSON.stringify(response) + '\n');
});
