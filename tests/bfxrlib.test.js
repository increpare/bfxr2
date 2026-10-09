const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
let distribution;

function library(format = 'readable', extra = {}) {
    distribution ||= require('../tools/build-library').buildLibrary();
    const context = vm.createContext({console: {log() {}, error: console.error}, setTimeout, clearTimeout, ...extra});
    const random = vm.runInContext('Math.random', context);
    vm.runInContext(distribution[format], context);
    return {api: context.bfxr, context, random};
}
const plain = value => JSON.parse(JSON.stringify(value));

function fakeAudio() {
    const state = {contexts: [], sources: [], buffers: [], gains: [], resumes: 0};
    class AudioContext {
        constructor() { this.state = 'suspended'; this.currentTime = 0; this.destination = {}; state.contexts.push(this); }
        resume() { state.resumes++; this.state = 'running'; return Promise.resolve(); }
        createBuffer(channels, length, rate) {
            const pcm = new Float32Array(length);
            const buffer = {length, sampleRate: rate, copyToChannel(data) {pcm.set(data);}, getChannelData() {return pcm;}};
            state.buffers.push(buffer); return buffer;
        }
        createBufferSource() {
            const source = {playbackRate: {value: 1}, stops: 0, disconnected: false,
                connect() {}, disconnect() {this.disconnected = true;}, start() {this.started = true;},
                stop() {this.stops++; if (this.onended) this.onended();}};
            state.sources.push(source); return source;
        }
        createGain() {
            const gain = {gain: {value: 1}, connect() {}, disconnect() {this.disconnected = true;}};
            state.gains.push(gain); return gain;
        }
    }
    return {state, AudioContext};
}

for (const format of ['readable', 'minified']) {
    test(`${format}: one global, no setup, stable preset IDs and seeds`, () => {
        const {api, context, random} = library(format);
        assert.deepEqual(Object.keys(context).sort(), ['bfxr', 'clearTimeout', 'console', 'setTimeout']);
        assert.equal(vm.runInContext('Math.random', context), random);
        assert.equal(vm.runInContext('Math.clamp', context), undefined);
        assert.equal(api.synths().length, 23);
        assert.ok(api.presets('Bfxr').includes('jump'));
        assert.ok(api.presets('Transfxr').includes('bright_whistles'));
        assert.ok(api.presets('Jinglr').includes('confirm'));
        assert.deepEqual(plain(api.presets('Footsteppr')), ['snow', 'grass', 'dirt', 'gravel', 'wood']);
        for (const name of api.synths()) {
            const id = api.presets(name)[0];
            const first = api.preset(name, id, 12345), second = api.preset(name, id, 12345);
            assert.deepEqual(plain(first), plain(second), name);
            assert.equal(first.synth_type, name);
            assert.ok(first.params && first.version);
            const pcm = api.render(first);
            assert.ok(pcm.length > 100 && pcm.every(Number.isFinite), name);
            assert.deepEqual(Array.from(pcm), Array.from(api.render(second)), name);
        }
    });

    test(`${format}: exported objects/JSON render without changing input or cached PCM`, () => {
        const {api} = library(format);
        const sound = plain(api.preset('Bfxr', 'explosion', 'test-seed'));
        const saved = JSON.stringify(sound);
        const pcm = api.render(sound);
        assert.deepEqual(Array.from(pcm), Array.from(api.render(saved)));
        assert.equal(JSON.stringify(sound), saved);
        pcm.fill(9);
        assert.ok(api.render(sound).every(v => v !== 9));
        const exported = {...sound, file_name: 'my explosion'};
        delete exported.renderSeed;
        assert.ok(api.render(JSON.stringify(exported)).every(Number.isFinite));
        assert.deepEqual(plain(api.preset('Bfxr', 'jump', 0)), plain(api.preset('Bfxr', 'jump', 0)));
        assert.notDeepEqual(plain(api.preset('Bfxr', 'jump', 1)), plain(api.preset('Bfxr', 'jump', 2)));
    });

    test(`${format}: unknown synths and presets fail clearly`, () => {
        const {api} = library(format);
        assert.throws(() => api.preset('Chattr', 'hello'), /Unknown synth/);
        assert.throws(() => api.preset('Bfxr', 'typo'), /Unknown preset/);
        assert.throws(() => api.render('{'), /sound JSON/i);
        assert.throws(() => api.render({synth_type: 'Bfxr'}), /params/);
        assert.throws(() => api.preset('Bfxr', 'jump', NaN), /seed/i);
        assert.throws(() => api.render({synth_type: 'Bfxr', params: {}, renderSeed: Infinity}), /renderSeed/i);
    });

    test(`${format}: old Transfxr noise exports migrate before normalization`, () => {
        const {api} = library(format);
        const original = plain(api.preset('Transfxr', 'bright_whistles', 1));
        delete original.params.waveTo; delete original.params.morph;
        original.params.noise = {start: .2, end: .9, curve: 'Smooth'};
        const migrated = plain(original);
        migrated.params.waveTo = 7; migrated.params.morph = migrated.params.noise;
        delete migrated.params.noise;
        const identical = (a, b) => a.length === b.length && a.every((v,i) => v === b[i]);
        assert.ok(identical(api.render(original), api.render(migrated)), 'legacy noise migration');
        const sources = source => ({synth_type: 'Mixr', params: {sources: JSON.stringify([
            {synth: 'Transfxr', params: source.params, renderSeed: .3}
        ])}});
        assert.ok(identical(api.render(sources(original)), api.render(sources(migrated))), 'nested legacy noise migration');
    });

    test(`${format}: prewarming is asynchronous, needs no audio and playback reuses buffers`, async () => {
        const {state, AudioContext} = fakeAudio();
        const {api} = library(format, {AudioContext});
        const sound = plain(api.preset('Bfxr', 'jump', 1));
        const prewarm = api.cache(sound);
        assert.equal(typeof prewarm.then, 'function');
        await prewarm;
        await api.cacheMutations(sound, .05, 3);
        assert.equal(state.contexts.length, 0);
        const first = api.play(sound), second = api.play({...sound, file_name: 'different name'});
        assert.equal(state.contexts.length, 1);
        assert.equal(state.resumes, 1);
        assert.equal(state.sources[0].buffer, state.sources[1].buffer);
        assert.equal(state.sources[0].stops, 0);
        first.stop(); first.stop();
        assert.equal(state.sources[0].stops, 1);
        assert.equal(state.sources[0].disconnected, true);
        api.stopAll();
        assert.equal(state.sources[1].stops, 1);
        second.stop();
        const old = state.sources[1].buffer;
        api.clearCache();
        api.play(sound);
        assert.notEqual(state.sources.at(-1).buffer, old);
    });

    test(`${format}: cache uses normalized contents and includes render seeds`, () => {
        const {state, AudioContext} = fakeAudio();
        const {api} = library(format, {AudioContext});
        const sound = plain(api.preset('Bfxr', 'explosion', 1));
        sound.params.waveType = 3; // White noise uses the render seed; bitnoise has a fixed cycle.
        api.play(sound);
        const params = Object.fromEntries(Object.entries(sound.params).reverse());
        api.play(JSON.stringify({...sound, params}));
        assert.equal(state.buffers.length, 1);
        api.play({...sound, renderSeed: .123});
        assert.equal(state.buffers.length, 2);
        const first = state.buffers[0].getChannelData(0), second = state.buffers[1].getChannelData(0);
        assert.ok(first.some((v,i) => v !== second[i]));
    });

    test(`${format}: playback options and ended voices clean up independently`, () => {
        const {state, AudioContext} = fakeAudio();
        const {api} = library(format, {AudioContext});
        const sound = api.preset('Bfxr', 'jump', 1);
        const ended = api.play(sound, {volume: .3, pitch: 12, loop: true});
        assert.equal(state.sources[0].playbackRate.value, 2);
        assert.equal(state.sources[0].loop, true);
        assert.equal(state.gains[0].gain.value, .3);
        state.sources[0].onended();
        ended.stop(); api.stopAll();
        assert.equal(state.sources[0].stops, 0);
        assert.equal(state.sources[0].disconnected, true);
        assert.equal(state.gains[0].disconnected, true);
        for (const options of [{volume: -1}, {pitch: NaN}, {loop: 'yes'}]) {
            assert.throws(() => api.play(sound, options), /volume|pitch|loop/);
        }
        assert.equal(state.sources.length, 1);
    });

    test(`${format}: mutations fill a fixed pool and never drift or edit the original`, () => {
        const {state, AudioContext} = fakeAudio();
        const {api} = library(format, {AudioContext});
        const sound = plain(api.preset('Jinglr', 'confirm', 4)), before = JSON.stringify(sound);
        for (let i = 0; i < 3; i++) api.playMutated(sound, .05, 3);
        const buffers = new Set(state.sources.map(source => source.buffer));
        assert.equal(buffers.size, 3);
        for (let i = 0; i < 25; i++) api.playMutated(JSON.stringify(sound), .05, 3);
        assert.ok(state.sources.every(source => buffers.has(source.buffer)));
        assert.equal(state.buffers.length, 3);
        assert.equal(JSON.stringify(sound), before);
        api.playMutated(sound, .1, 3);
        assert.equal(state.buffers.length, 4);
        api.playMutated(sound, .05, 4);
        assert.equal(state.buffers.length, 5);
        api.play(sound); const original = state.sources.at(-1).buffer;
        api.playMutated(sound, 0, 3);
        assert.equal(state.sources.at(-1).buffer, original);
        for (const [amount, count] of [[-1,3], [NaN,3], [.05,0], [.05,1.5], [.05,257]]) {
            assert.throws(() => api.playMutated(sound, amount, count), /amount|count/);
        }
    });

    test(`${format}: autoplay rejection can recover on a gesture without unhandled rejection`, async () => {
        const {state, AudioContext} = fakeAudio();
        let attempts = 0;
        AudioContext.prototype.resume = function() {
            attempts++;
            if (attempts === 1) return Promise.reject(new Error('gesture required'));
            this.state = 'running'; return Promise.resolve();
        };
        const listeners = new Map();
        const {api} = library(format, {AudioContext,
            addEventListener(event, fn) {listeners.set(event, fn);},
            removeEventListener(event) {listeners.delete(event);}});
        api.play(api.preset('Bfxr', 'jump', 1));
        await new Promise(setImmediate);
        assert.equal(listeners.size, 3);
        listeners.get('pointerdown')();
        await new Promise(setImmediate);
        assert.equal(state.contexts[0].state, 'running');
        assert.equal(listeners.size, 0);
        assert.equal(attempts, 2);
    });

    test(`${format}: clearing cancels outstanding prewarm work`, async () => {
        const {state, AudioContext} = fakeAudio();
        const {api} = library(format, {AudioContext});
        const sound = api.preset('Bfxr', 'jump', 1);
        const pending = api.cacheMutations(sound, .05, 3);
        api.clearCache(); await pending;
        api.playMutated(sound, .05, 3);
        assert.equal(state.buffers.length, 1);
        assert.equal(state.contexts.length, 1);
        await assert.rejects(api.cacheMutations(sound, .05, 0), /count/);
    });
}

test('sample cache evicts by memory budget and least recent use', () => {
    const source = fs.readFileSync(path.join(root, 'js/library/cache.js'), 'utf8');
    const context = vm.createContext({});
    vm.runInContext(source, context);
    assert.equal(vm.runInContext(`(() => {
        const cache = new LibraryLRU(12);
        cache.set('a', 1, 4); cache.set('b', 2, 4); cache.set('c', 3, 4);
        cache.get('a'); cache.set('d', 4, 4);
        if (cache.get('b') !== undefined || cache.get('a') !== 1) return false;
        cache.set('a', 5, 8);
        if (cache.get('c') !== undefined || cache.get('d') !== 4 || cache.get('a') !== 5) return false;
        cache.set('huge', 6, 20);
        if (cache.get('huge') !== undefined || cache.get('a') !== 5) return false;
        cache.clear(); return cache.get('a') === undefined && cache.bytes === 0;
    })()`, context), true);
});
