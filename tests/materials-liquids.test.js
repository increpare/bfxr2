const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, plain} = require('./helpers/synth-context');

function setup(name) {
    const api = createContext([name]);
    api.run(`var synth = new ${name}(); Math.random = SoundDSP.rng(0.314159);`);
    return api;
}
function digest(pcm) {
    return crypto.createHash('sha256').update(Buffer.from(pcm.buffer, pcm.byteOffset, pcm.byteLength)).digest('hex');
}
function features(pcm) {
    let energy = 0, weighted = 0, crossings = 0, peak = 0;
    for (let i = 0; i < pcm.length; i++) {
        energy += pcm[i] * pcm[i];
        weighted += pcm[i] * pcm[i] * i / pcm.length;
        peak = Math.max(peak, Math.abs(pcm[i]));
        if (i && pcm[i] * pcm[i - 1] < 0) crossings++;
    }
    return {rms: Math.sqrt(energy / pcm.length), peak, centroid: weighted / energy,
        crossings: crossings / (pcm.length / 44100), duration: pcm.length / 44100};
}
function safeAudio(pcm, label, audible = true) {
    assert.ok(pcm instanceof Float32Array, `${label}: PCM buffer`);
    assert.ok(pcm.length > 2000 && pcm.length <= 7 * 44100, `${label}: finite duration`);
    for (const sample of pcm) assert.ok(Number.isFinite(sample) && Math.abs(sample) < 1, `${label}: safe sample`);
    assert.ok(pcm[0] === 0, `${label}: starts at zero`);
    assert.ok(pcm[pcm.length - 1] === 0, `${label}: ends at zero`);
    if (audible) {
        const metrics = features(pcm);
        assert.ok(metrics.peak > 0.025 && metrics.rms > 0.0015, `${label}: audible, ${JSON.stringify(metrics)}`);
    }
}

for (const name of ['Clonkr', 'Squishr']) {
    test(`${name} saves repeatable, audible PCM and changes when variation changes`, () => {
        const {run} = setup(name);
        const first = run('synth.generate_sound(); synth.sound.getBuffer().slice()');
        const second = run('synth.generate_sound(); synth.sound.getBuffer().slice()');
        safeAudio(first, name);
        assert.deepEqual(first, second);
        assert.notEqual(digest(first), digest(run('synth.set_param("seed", 0.17); synth.generate_sound(); synth.sound.getBuffer()')));
        assert.ok(run('synth.generate_sound_uri().startsWith("data:audio/wav;base64,")'));
    });

    test(`${name} has named randomized categories with genuinely different sound families`, () => {
        const {run} = setup(name);
        const recipes = plain(run('synth.recipes'));
        assert.ok(recipes.length >= 8);
        const metrics = [], hashes = new Set();
        for (const recipe of recipes) {
            assert.ok(Object.values(recipe.values).filter(Array.isArray).length >= 3, `${recipe.name}: several varying controls`);
            const params = [];
            for (let i = 0; i < 3; i++) {
                const pcm = run(`synth.generate_${recipe.id}(); synth.generate_sound(); synth.sound.getBuffer().slice()`);
                safeAudio(pcm, `${name} ${recipe.name} ${i}`);
                params.push(plain(run('synth.params')));
                if (!i) { metrics.push(features(pcm)); hashes.add(digest(pcm)); }
            }
            assert.notDeepEqual(params[0], params[1]);
            const variedControls = Object.keys(params[0]).filter(key => key !== 'seed' && params[0][key] !== params[1][key]);
            assert.ok(variedControls.length >= 3, `${recipe.name}: each click changes controls as well as the seed`);
            assert.ok(run(`synth.templates.some(t => t[0] === ${JSON.stringify(recipe.name)} && t[2] === 'generate_${recipe.id}')`));
        }
        assert.equal(hashes.size, recipes.length);
        assert.ok(Math.max(...metrics.map(m => m.crossings)) / Math.min(...metrics.map(m => m.crossings)) > 2, `${name}: varied timbres`);
        assert.ok(Math.max(...metrics.map(m => m.duration)) / Math.min(...metrics.map(m => m.duration)) > 1.8, `${name}: varied lengths`);
    });

    test(`${name} category generation, randomize, and mutate honor every locked control`, () => {
        const {run} = setup(name);
        assert.equal(run(`
            synth.generate_recipe(synth.recipes[0].id);
            for (const key of Object.keys(synth.params)) synth.set_locked_param(key, true);
            var locked = JSON.stringify(synth.params);
            for (const recipe of synth.recipes) synth.generate_recipe(recipe.id);
            synth.randomize_params(); synth.mutate_params();
            locked === JSON.stringify(synth.params);
        `), true);
    });

    test(`${name} stays finite and audible at control extremes and after randomization`, () => {
        const {run} = setup(name);
        const cases = plain(run(`(() => {
            const cases = [], enums = synth.param_info.filter(p => p.type === 'BUTTONSELECT');
            for (const edge of [0, 1]) {
                for (let variant = 0; variant < 6; variant++) {
                    synth.reset_params();
                    for (const info of synth.param_info) {
                        const p = synth.get_param_normalized(info);
                        if (p.type === 'RANGE' && p.name !== 'masterVolume') synth.set_param(p.name, edge ? p.max_value : p.min_value);
                    }
                    for (const info of enums) synth.set_param(info.name, info.values[variant % info.values.length][2]);
                    synth.set_param('masterVolume', 1);
                    cases.push({...synth.params});
                }
            }
            for (let i = 0; i < 6; i++) { synth.randomize_params(); cases.push({...synth.params}); }
            return cases;
        })()`));
        for (let i = 0; i < cases.length; i++) {
            const pcm = run(`synth.apply_params(${JSON.stringify(cases[i])}); synth.generate_sound(); synth.sound.getBuffer()`);
            safeAudio(pcm, `${name} extreme ${i}`);
        }
        assert.equal(run(`synth.apply_params({duration:Infinity, seed:NaN, extra:9}); !('extra' in synth.params) && Number.isFinite(synth.params.duration) && Number.isFinite(synth.params.seed)`), true);
        assert.ok(run('synth.set_param("masterVolume", 0); synth.generate_sound(); synth.sound.getBuffer().every(v => v === 0)'));
    });
}

test('Clonkr size lowers the object pitch and damping shortens its resonance', () => {
    const {run} = setup('Clonkr');
    run('synth.apply_params({material:1, action:0, hardness:0.7, hollowness:0.3, damping:0.3, duration:1, size:0.1, seed:0.5})');
    const small = run('Clonkr_DSP.render(synth.params)');
    const large = run('synth.set_param("size", 0.9); Clonkr_DSP.render(synth.params)');
    assert.ok(features(small).crossings > features(large).crossings * 2, 'large objects resonate lower');
    run('synth.apply_params({size:0.5, damping:0})');
    const ringing = run('Clonkr_DSP.render(synth.params)');
    const damped = run('synth.set_param("damping", 1); Clonkr_DSP.render(synth.params)');
    const tailEnergy = pcm => pcm.slice(13230).reduce((sum, value) => sum + value * value, 0);
    assert.ok(tailEnergy(ringing) > tailEnergy(damped) * 4, 'damping suppresses the late ringing');
});

test('Squishr bubble size lowers the bubbles and each soft/liquid control changes the sound', () => {
    const {run} = setup('Squishr');
    run('synth.apply_params({texture:1, bubbleSize:0.1, wetness:1, viscosity:0.5, pressure:0.5, stretch:0.3, duration:1, seed:0.5})');
    const small = run('Squishr_DSP.render(synth.params)');
    const large = run('synth.set_param("bubbleSize", 0.9); Squishr_DSP.render(synth.params)');
    assert.ok(features(small).crossings > features(large).crossings * 1.5, 'large bubbles resonate lower');
    for (const key of ['viscosity', 'stretch', 'pressure', 'wetness', 'bubbleSize']) {
        run(`synth.reset_params(); synth.set_param('${key}', 0)`);
        const low = run('Squishr_DSP.render(synth.params)');
        const high = run(`synth.set_param('${key}', 1); Squishr_DSP.render(synth.params)`);
        assert.notEqual(digest(low), digest(high), `${key}: changes the rendered sound`);
    }
});
