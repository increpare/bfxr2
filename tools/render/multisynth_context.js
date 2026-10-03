'use strict';
// Load the shipped browser synths unchanged, with only audio/storage host shims.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const REPO_ROOT = path.resolve(__dirname, '../..');
const EXCLUDED = [
    {name: 'Chattr', reason: 'Text and pronunciation controls require a separate search representation.'},
    {name: 'Mixr', reason: 'Composition depends on external source sounds.'},
    {name: 'Stackr', reason: 'Layer composition is outside the numeric single-synth search space.'},
];

const HOST = `
const SAMPLE_RATE = 44100;
// Match audio_globals.js: PureData filters convert Hz to radians per sample.
const CONVERSION_FACTOR = (2 * Math.PI) / SAMPLE_RATE;
function ULBS() {}
const AUDIO_CONTEXT = {currentTime:0, destination:{},
    createBuffer(channels,length,rate) {
        if (!Number.isFinite(length) || length < 1 || length > SAMPLE_RATE * 60)
            throw new Error('Invalid audio buffer length');
        const pcm = new Float32Array(length);
        return {getChannelData(){return pcm;}, copyToChannel(data){pcm.set(data);}};
    },
    createBufferSource(){return {connect(){},disconnect(){},start(){},stop(){}};}
};
function __setSeed(seed) {
    let a = seed >>> 0;
    Math.random = function() {
        a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}
`;

const BRIDGE = `
const __constructors = new Map(__names.map(name => [name, eval(name)]));
function __newSynth(name) {
    const Constructor = __constructors.get(name);
    if (!Constructor) throw new Error('Unknown or unsupported synth: ' + name);
    return new Constructor();
}
function __presets(synth) {
    return [...new Set([
        ...synth.templates.map(template => template[2]),
        ...Object.keys(synth).filter(key => key.startsWith('generate_') && typeof synth[key] === 'function')
    ])].filter(key => key !== 'mutate_params' && typeof synth[key] === 'function');
}
function __metadata(synth) {
    return synth.param_info.map(raw => {
        const info = synth.get_param_normalized(raw);
        const entry = {name:info.name, type:info.type, min:info.min_value,
            max:info.max_value, default:info.default_value};
        if (info.type === 'BUTTONSELECT') {
            entry.values = raw.values.map(value => value[2]);
            entry.min = Math.min(...entry.values);
            entry.max = Math.max(...entry.values);
        } else if (info.type === 'KNOB_TRANSITION') entry.values = raw.curves.slice();
        return entry;
    });
}
function __canonical(synth, values) {
    // Specialized apply_params methods batch dependent controls (Jinglr phrases).
    if (synth instanceof PresetSynth || synth instanceof Transfxr) synth.apply_params(values);
    else for (const info of __metadata(synth)) {
        if (Object.prototype.hasOwnProperty.call(values, info.name)) synth.set_param(info.name, values[info.name]);
    }
    synth.set_param('masterVolume', 0.5);
    return JSON.parse(JSON.stringify(synth.params));
}
function __inventory() {
    return __names.map(name => {
        const synth = __newSynth(name);
        return {name, params:__metadata(synth), presets:__presets(synth), defaults:synth.default_params()};
    });
}
function __sample(request) {
    __setSeed(request.seed);
    const synth = __newSynth(request.synth);
    if (!__presets(synth).includes(request.preset)) throw new Error('Unknown preset: ' + request.preset);
    synth[request.preset]();
    return __canonical(synth, synth.params);
}
function __render(request) {
    __setSeed(request.seed);
    const synth = __newSynth(request.synth);
    const params = __canonical(synth, request.params);
    // Bfxr mutates the parameter object during DSP reset; save controls first.
    synth.generate_sound();
    const pcm = synth.sound && synth.sound.getBuffer();
    if (!(pcm instanceof Float32Array) || !pcm.length) throw new Error('Synth returned no audio');
    for (let i = 0; i < pcm.length; i++)
        if (!Number.isFinite(pcm[i])) throw new Error('Synth returned nonfinite audio at sample ' + i);
    return {params, pcm};
}
`;

function createMultisynthContext({timeoutMs = 10000} = {}) {
    if (!Number.isInteger(timeoutMs) || timeoutMs < 1) throw new Error('timeoutMs must be a positive integer');
    const names = ['Bfxr', 'Footsteppr', 'Transfxr', ...fs.readdirSync(path.join(REPO_ROOT, 'js/synths'))
        .filter(file => file.endsWith('.js') && /^class \w+ extends PresetSynth\b/m.test(fs.readFileSync(path.join(REPO_ROOT, 'js/synths', file), 'utf8')))
        .map(file => path.basename(file, '.js')).filter(name => !EXCLUDED.some(entry => entry.name === name)).sort()];
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
    const storage = new Map();
    const ctx = vm.createContext({Float32Array, __names:names,
        console:{log(){},error(){},warn(){}},
        localStorage:{getItem:key => storage.get(key) ?? null,setItem:(key,value) => storage.set(key,String(value))}});
    const run = (code, filename) => new vm.Script(code, {filename}).runInContext(ctx, {timeout:timeoutMs});
    const hash = crypto.createHash('sha256').update(fs.readFileSync(__filename));
    // Its browser AudioContext setup is replaced by HOST, but its constants
    // remain rendering dependencies and must invalidate saved library hashes.
    const audioGlobals = 'js/audio/audio_globals.js';
    hash.update(audioGlobals).update('\0').update(fs.readFileSync(path.join(REPO_ROOT, audioGlobals))).update('\0');
    // Only registered tabs can reopen a saved collection in the current app.
    // Retired synths remain available here for explicit legacy searches.
    const appEntry = 'js/index.js';
    const appCode = fs.readFileSync(path.join(REPO_ROOT, appEntry), 'utf8');
    hash.update(appEntry).update('\0').update(appCode).update('\0');
    const activeSynths = new Set([...appCode.matchAll(/\badd_tab\s*\(\s*new\s+(\w+)\s*\(/g)].map(match => match[1]));
    run(HOST, 'multisynth-host.js');
    for (const source of sources) {
        const code = fs.readFileSync(path.join(REPO_ROOT, source), 'utf8');
        hash.update(source).update('\0').update(code).update('\0');
        run(code, source);
    }
    run(BRIDGE, 'multisynth-bridge.js');
    const sourceHash = hash.digest('hex');
    const plain = value => JSON.parse(JSON.stringify(value));
    const synths = plain(run('__inventory()', 'multisynth-inventory.js'));
    for (const synth of synths) synth.collectionCompatible = activeSynths.has(synth.name);
    const infoByName = new Map(synths.map(synth => [synth.name, synth]));
    function validate(synth, seed, params) {
        const info = infoByName.get(synth);
        if (!info) throw new Error('Unknown or unsupported synth: ' + synth);
        if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) throw new Error('Seed must be an unsigned 32-bit integer');
        if (params !== undefined) {
            if (!params || typeof params !== 'object' || Array.isArray(params)) throw new Error('Parameters must be an object');
            for (const [name, value] of Object.entries(params)) {
                const param = info.params.find(entry => entry.name === name);
                if (!param) throw new Error('Unknown parameter: ' + name);
                if (param.type === 'KNOB_TRANSITION') {
                    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Transition parameter must be an object: ' + name);
                    for (const key of Object.keys(value)) if (!['start','end','curve'].includes(key)) throw new Error('Unknown transition parameter: ' + key);
                    for (const key of ['start','end']) if (value[key] !== undefined && !Number.isFinite(value[key])) throw new Error('Parameter must be finite: ' + name + '.' + key);
                    if (value.curve !== undefined && typeof value.curve !== 'string') throw new Error('Transition curve must be a string');
                } else if (param.type === 'TEXT') {
                    if (typeof value !== 'string') throw new Error('Parameter must be a string: ' + name);
                } else if (!Number.isFinite(value)) throw new Error('Parameter must be finite: ' + name);
            }
        }
    }
    function invoke(op, request) {
        // JSON creates realm-native data and prevents caller objects being mutated.
        ctx.__requestJSON = JSON.stringify(request);
        try { return run('__' + op + '(JSON.parse(__requestJSON))', 'multisynth-' + op + '.js'); }
        finally { delete ctx.__requestJSON; }
    }
    return {
        inventory: () => plain({sampleRate:44100,sourceHash,synths,excluded:EXCLUDED}),
        sample(synth,preset,seed = 0) {
            validate(synth, seed);
            if (!infoByName.get(synth).presets.includes(preset)) throw new Error('Unknown preset: ' + preset);
            return plain(invoke('sample', {synth,preset,seed}));
        },
        render(synth,params = {},seed = 0) {
            validate(synth, seed, params);
            const result = invoke('render', {synth,params,seed});
            return {params:plain(result.params),pcm:new Float32Array(result.pcm)};
        }
    };
}

module.exports = {createMultisynthContext};
