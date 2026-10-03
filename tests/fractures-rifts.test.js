const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, plain} = require('./helpers/synth-context');

function setup(name) {
    let api;
    assert.doesNotThrow(() => { api = createContext(['Fractr', 'Riftr']); }, 'both exotic engines load');
    api.run(`var synth = new ${name}(); Math.random = SoundDSP.rng(0.3159);`);
    return api;
}
function hash(pcm) {
    return crypto.createHash('sha256').update(Buffer.from(pcm.buffer, pcm.byteOffset, pcm.byteLength)).digest('hex');
}
function energy(pcm, start = 0, end = pcm.length) {
    let sum = 0;
    for (let i = start; i < end; i++) sum += pcm[i] * pcm[i];
    return sum;
}
function metrics(pcm) {
    let sum = 0, weighted = 0, difference = 0, peak = 0;
    for (let i = 0; i < pcm.length; i++) {
        const square = pcm[i] * pcm[i];
        sum += square;
        weighted += square * i / pcm.length;
        if (i) difference += (pcm[i] - pcm[i - 1]) ** 2;
        peak = Math.max(peak, Math.abs(pcm[i]));
    }
    return {rms:Math.sqrt(sum / pcm.length), centroid:weighted / sum, brightness:Math.sqrt(difference / sum), peak};
}
function safe(pcm, label, audible = true) {
    assert.ok(pcm instanceof Float32Array, label + ' supplies float PCM');
    assert.ok(pcm.length >= 0.15 * 44100 && pcm.length <= 6 * 44100, label + ' bounded length');
    assert.ok(pcm.every(sample => Number.isFinite(sample) && Math.abs(sample) <= 0.951), label + ' bounded finite samples');
    assert.equal(Math.abs(pcm[0]), 0, label + ' begins at zero');
    assert.equal(Math.abs(pcm.at(-1)), 0, label + ' ends at zero');
    if (audible) {
        const m = metrics(pcm);
        assert.ok(m.rms > 0.0015 && m.peak > 0.025, label + ' audible ' + JSON.stringify(m));
    }
}

for (const name of ['Fractr', 'Riftr']) {
    test(name + ' recipes vary physical controls, remain audible and reproduce exact saved PCM', () => {
        const {run} = setup(name);
        const recipes = plain(run('synth.recipes'));
        assert.ok(recipes.length >= 8);
        const hashes = new Set();
        for (const recipe of recipes) {
            assert.ok(Object.values(recipe.values).filter(Array.isArray).length >= 3, recipe.id + ' varies several controls');
            const first = plain(run(`synth.generate_${recipe.id}(); synth.params`));
            const pcm = run(`${name}_DSP.render(synth.params)`);
            safe(pcm, name + ' ' + recipe.id);
            assert.deepEqual(pcm, run(`${name}_DSP.render(synth.params)`), 'same stored variant is repeatable');
            hashes.add(hash(pcm));
            const second = plain(run(`synth.generate_${recipe.id}(); synth.params`));
            assert.ok(Object.keys(first).filter(key => key !== 'seed' && first[key] !== second[key]).length >= 3,
                recipe.id + ' changes physical controls as well as its seed');
            assert.ok(run(`synth.templates.some(t => t[2] === 'generate_${recipe.id}')`));
        }
        assert.equal(hashes.size, recipes.length, 'all categories have distinct waveforms');
        assert.ok(run('synth.generate_sound(); synth.generate_sound_uri().startsWith("data:audio/wav;base64,")'));
    });

    test(name + ' recipes, randomize and mutate preserve every locked parameter', () => {
        const {run} = setup(name);
        assert.equal(run(`(() => {
            synth.generate_recipe(synth.recipes[0].id);
            for (const key of Object.keys(synth.params)) synth.set_locked_param(key, true);
            const before = JSON.stringify(synth.params);
            for (const recipe of synth.recipes) synth.generate_recipe(recipe.id);
            synth.randomize_params(); synth.mutate_params();
            return before === JSON.stringify(synth.params);
        })()`), true);
    });

    test(name + ' control extremes remain finite, mute works and render uses no global random source', () => {
        const {run} = setup(name);
        const buffers = run(`(() => {
            const cases = [];
            for (const high of [false, true]) {
                synth.reset_params();
                for (const raw of synth.param_info) {
                    const info = synth.get_param_normalized(raw);
                    if (info.type === 'RANGE') synth.set_param(info.name, high ? info.max_value : info.min_value);
                    if (info.type === 'BUTTONSELECT') synth.set_param(info.name, raw.values[high ? raw.values.length - 1 : 0][2]);
                }
                synth.set_param('masterVolume', 1);
                cases.push(${name}_DSP.render(synth.params));
            }
            synth.reset_params();
            Math.random = () => { throw new Error('global randomness in renderer'); };
            cases.push(${name}_DSP.render({...synth.params, seed:0.1}));
            cases.push(${name}_DSP.render({...synth.params, seed:0.9}));
            cases.push(${name}_DSP.render({...synth.params, masterVolume:0}));
            return cases;
        })()`);
        buffers.forEach((pcm, i) => safe(pcm, name + ' extreme ' + i, i !== 4 && !(name==='Fractr' && i===0)));
        if(name==='Fractr')assert.ok(buffers[0].every(v=>v===0),'all source amounts at zero is silent');
        assert.equal(buffers[0].length, Math.round(0.15 * 44100));
        assert.equal(buffers[1].length, 6 * 44100);
        assert.notEqual(hash(buffers[2]), hash(buffers[3]), 'variation changes sound');
        assert.ok(buffers[4].every(value => value === 0), 'mute is exact');
    });
}

test('Fractr stores whole fragment counts for imports, recipes, randomization and mutation without bypassing locks', () => {
    const {run} = setup('Fractr');
    assert.equal(run('synth.apply_params({fragments:20.7}); synth.params.fragments'), 21, 'imports round fragment counts');
    assert.equal(run('synth.apply_params({fragments:200.2}); synth.params.fragments'), 96, 'imports retain bounds');
    assert.equal(run('synth.set_param("fragments", 18); synth.set_locked_param("fragments", true); synth.apply_params({fragments:29.8}, true); synth.params.fragments'), 18, 'locked imports remain unchanged');
    const counts = plain(run(`(() => {
        synth.set_locked_param('fragments', false);
        const counts = [];
        for (const recipe of synth.recipes) {
            synth.generate_recipe(recipe.id); counts.push(synth.params.fragments);
            synth.mutate_params(); counts.push(synth.params.fragments);
        }
        synth.randomize_params(); counts.push(synth.params.fragments);
        return counts;
    })()`));
    assert.ok(counts.every(value => Number.isInteger(value) && value >= 3 && value <= 96));
});

test('Fractr spreads independent fractures over time and fragment count fills the cascade', () => {
    const {run} = setup('Fractr');
    const [burst, cascade, sparse, dense] = run(`(() => {
        const p = {...synth.params, duration:2, seed:0.32, material:0, fracture:0, stress:0, shards:1, fragments:24, decay:0, bounce:0, gravity:0.4};
        return [{spread:0}, {spread:1}, {spread:1,fragments:3}, {spread:1,fragments:60}]
            .map(change => Fractr_DSP.render({...p,...change}));
    })()`);
    assert.ok(metrics(cascade).centroid > metrics(burst).centroid + 0.14, 'spread moves fracture energy later');
    const activeWindows = pcm => {
        let count = 0;
        for (let i = 0; i + 441 < pcm.length; i += 441) if (energy(pcm, i, i + 441) > 0.0005) count++;
        return count;
    };
    assert.ok(activeWindows(dense) > activeWindows(sparse) * 1.7, 'more fragments fill more distinct time windows');
});

test('Fractr fragment size and material alter the spectrum while decay and bounce prolong debris', () => {
    const {run} = setup('Fractr');
    const result = run(`(() => {
        const p = {...synth.params, duration:2, seed:0.72, material:2, fragments:5, spread:0, decay:0.2, bounce:0, gravity:0.2};
        return [{fragmentSize:0}, {fragmentSize:1}, {material:0}, {material:3}, {decay:0}, {decay:1}, {bounce:1}]
            .map(change => Fractr_DSP.render({...p,...change}));
    })()`);
    assert.ok(metrics(result[0]).brightness > metrics(result[1]).brightness * 1.7, 'large fragments have lower resonances');
    assert.ok(metrics(result[2]).brightness > metrics(result[3]).brightness * 1.5, 'glass is brighter than stone');
    assert.ok(energy(result[5], 13230) > energy(result[4], 13230) * 5, 'decay sustains late resonance');
    assert.ok(energy(result[6], 13230) > energy(result[4], 13230) * 4, 'bounces add later contacts');
    const [slow, fast] = run(`[{gravity:0},{gravity:1}].map(change => Fractr_DSP.render({...synth.params,duration:2,spread:1,bounce:1,seed:0.33,...change}))`);
    assert.ok(metrics(slow).centroid > metrics(fast).centroid * 1.12, 'strong gravity shortens flight time');
});

test('Riftr reverses the rendered field and feedback sustains actual delayed energy', () => {
    const {run} = setup('Riftr');
    const [forward, backward, dry, echo, resonant] = run(`(() => {
        const p = {...synth.params, duration:2, excitation:0, seed:0.81, reverse:0, pitch:0.5, space:0.5, motion:0, dispersion:0, feedback:0};
        return [{}, {reverse:1}, {field:0}, {field:1}, {field:1,feedback:0.98}]
            .map(change => Riftr_DSP.render({...p,...change}));
    })()`);
    for (let i = 0; i < forward.length; i += 31) assert.ok(Math.abs(forward[i] - backward[backward.length - 1 - i]) < 1e-6);
    assert.ok(metrics(backward).centroid > metrics(forward).centroid + 0.4, 'reverse turns a strike into an arrival');
    assert.ok(metrics(echo).centroid > metrics(dry).centroid + 0.005, 'the field delays the energy');
    assert.ok(energy(resonant, 17640) > energy(echo, 17640) * 10, 'feedback recirculates energy beyond the input');
});

test('Riftr space, dispersion and motion reshape the delayed field, and pitch tunes it', () => {
    const {run} = setup('Riftr');
    const result = run(`(() => {
        const p = {...synth.params, duration:1.5, excitation:0, seed:0.2, reverse:0, field:1, feedback:0.6, dispersion:0, motion:0};
        return [{space:0.1}, {space:0.95}, {dispersion:1}, {motion:1}, {field:0,pitch:0}, {field:0,pitch:1}]
            .map(change => Riftr_DSP.render({...p,...change}));
    })()`);
    assert.ok(metrics(result[1]).centroid > metrics(result[0]).centroid * 1.4, 'larger space extends propagation and echoes');
    assert.notEqual(hash(result[2]), hash(result[0]), 'dispersion changes the field');
    const [plainField, dispersed, moving] = run(`[{dispersion:0,motion:0},{dispersion:1,motion:0},{dispersion:0,motion:1}]
        .map(change => Riftr_DSP.render({...synth.params,duration:1.5,excitation:0,field:1,feedback:0.6,seed:0.2,...change}))`);
    assert.ok(metrics(dispersed).centroid > metrics(plainField).centroid + 0.002, 'allpass diffusion spreads the impulse in time');
    assert.notEqual(hash(moving), hash(plainField), 'moving read heads change the phase field');
    assert.ok(metrics(result[5]).brightness > metrics(result[4]).brightness * 1.6, 'pitch raises the excitation spectrum');
});
