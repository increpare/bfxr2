'use strict';
// Headless loader for the browser-side Bfxr synth. Runs the shipped scripts
// unmodified inside a node:vm context and exposes a deterministic render().
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

// Order matters: globals first (lerp/Math.clamp), Bfxr_DSP before Bfxr
// (class field initializer reads Bfxr_DSP.version), templates.js before
// SynthBase (post_initialize reads TEMPLATES_JSON).
const SOURCES = [
    'js/globals.js',
    'js/audio/AKWF.js',
    'js/audio/Bfxr_DSP.js',
    'js/synths/templates.js',
    'js/synths/SynthBase.js',
    'js/synths/Bfxr.js',
];

const BOOTSTRAP = `
// Deterministic mulberry32 PRNG replaces this realm's Math.random so noise
// waveforms render identically for identical seeds.
function __setSeed(seed) {
    let a = seed >>> 0;
    Math.random = function () {
        a |= 0;
        a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

var __synth = new Bfxr();
var __defaults = __synth.default_params();

function __render(params, seed) {
    __setSeed(seed);
    // Fresh merged copy every render: Bfxr_DSP.reset()/clampTotalLength()
    // mutate the params object they are given.
    var merged = Object.assign({}, __defaults, params);
    merged.masterVolume = 0.5;
    var dsp = new Bfxr_DSP(merged, __synth);
    dsp.generate_sound();
    // generate_sound() can return early without assigning the buffer.
    return (dsp.buffer instanceof Float32Array) ? dsp.buffer : null;
}

function __paramInfo() {
    var params = [];
    var waveTypes = null;
    for (var i = 0; i < __synth.param_info.length; i++) {
        var raw = __synth.param_info[i];
        var n = __synth.get_param_normalized(raw);
        if (n.type === 'BUTTONSELECT') {
            waveTypes = raw.values.map(function (v) {
                return { name: v[0], value: v[2] };
            });
            params.push({
                name: n.name,
                type: 'BUTTONSELECT',
                default: n.default_value,
                values: raw.values.map(function (v) { return v[2]; }),
            });
        } else {
            params.push({
                name: n.name,
                type: 'RANGE',
                default: n.default_value,
                min: n.min_value,
                max: n.max_value,
            });
        }
    }
    return {
        version: Bfxr_DSP.version,
        sampleRate: Bfxr_DSP.sampleRate,
        permalocked: __synth.permalocked,
        params: params,
        waveTypes: waveTypes,
    };
}

({ render: __render, paramInfo: __paramInfo });
`;

function createBfxrContext() {
    const ctx = vm.createContext({ console });
    for (const rel of SOURCES) {
        const code = fs.readFileSync(path.join(REPO_ROOT, rel), 'utf8');
        new vm.Script(code, { filename: rel }).runInContext(ctx);
    }
    const api = new vm.Script(BOOTSTRAP, { filename: 'bootstrap.js' }).runInContext(ctx);
    return {
        // -> Float32Array (vm realm, contents fine) or null on failed render
        render: (params, seed) => api.render(params, seed >>> 0),
        paramInfo: () => api.paramInfo(),
    };
}

module.exports = { createBfxrContext, REPO_ROOT };
