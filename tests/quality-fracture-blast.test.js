const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup(name) {
    const api = createContext([name]);
    api.run(`var synth = new ${name}(); Math.random = SoundDSP.rng(0.431);
        var finish = SoundDSP.finish;
        SoundDSP.finish = function(pcm, ...args) {
            if (!pcm.every(Number.isFinite)) throw new Error('Invalid PCM before finish');
            return finish.call(this, pcm, ...args);
        };`);
    return api;
}

// A sustained mode repeats over whole periods even when its amplitude decays.
// Search several possible periods, excluding adjacent samples of filtered noise.
function periodicity(pcm, start, end, minLag, maxLag) {
    let energy = 0;
    for (let i = start; i < end; i++) energy += pcm[i] * pcm[i];
    assert.ok(energy / (end - start) > 1e-6, 'the measured contact or pressure body must be audible');
    let strongest = 0;
    for (let lag = minLag; lag <= maxLag; lag += 3) {
        let product = 0, first = 0, second = 0;
        for (let i = start; i < end - lag; i += 2) {
            const a = pcm[i], b = pcm[i + lag];
            product += a * b; first += a * a; second += b * b;
        }
        if (first * second > 1e-16) strongest = Math.max(strongest, product / Math.sqrt(first * second));
    }
    return strongest;
}

test('ordinary Fractr materials crack without sustaining repeating pitched shard notes', () => {
    const {run} = setup('Fractr');
    for (const material of [0, 1, 3, 5, 6]) {
        const pcm = run(`Fractr_DSP.render({...synth.params, material:${material}, duration:1,
            fragments:3, spread:1, decay:0.7, bounce:0, fragmentSize:0.4, seed:0.5})`);
        const repeat = periodicity(pcm, 1500, 3700, 44, 660);
        assert.ok(repeat < 0.65, `material ${material} has repeating note correlation ${repeat}`);
    }
});

test('Fractr Crystal and Pixel retain their intentionally tuned character', () => {
    const {run} = setup('Fractr');
    for (const material of [2, 4]) {
        const pcm = run(`Fractr_DSP.render({...synth.params, material:${material}, duration:1,
            fragments:3, spread:1, decay:0.7, bounce:0, fragmentSize:0.4, seed:0.5})`);
        assert.ok(periodicity(pcm, 1500, 3700, 44, 660) > 0.8);
    }
});

test('Boomr pressure is an irregular shock and rumble instead of a pitched sweep', () => {
    const {run} = setup('Boomr');
    const pcm = run(`Boomr_DSP.render({...synth.params, duration:1, pressure:1,
        blast:0, tail:0, debris:0, muffle:0, seed:0.5})`);
    const repeat = periodicity(pcm, 2205, 8820, 147, 1500);
    assert.ok(repeat < 0.6, `pressure repeats like an oscillator: ${repeat}`);
});

test('Boomr debris produces rough short contacts rather than a shower of ringing notes', () => {
    const {run} = setup('Boomr');
    const pcm = run(`Boomr_DSP.render({...synth.params, duration:1, pressure:0,
        blast:0, tail:0, debris:1, muffle:0, spread:0, seed:0.5})`);
    const repeat = periodicity(pcm, 2205, 8820, 147, 1500);
    assert.ok(repeat < 0.6, `debris repeats like a ringing instrument: ${repeat}`);
});

for (const name of ['Fractr', 'Boomr']) {
    test(`${name} raw output is finite across materials, recipes and individual control boundaries`, () => {
        const {run} = setup(name);
        const recipes = plain(run('synth.recipes'));
        for (const recipe of recipes) {
            const result = run(`synth.generate_recipe('${recipe.id}'); ${name}_DSP.render(synth.params)`);
            assert.ok(result.some(value => Math.abs(value) > 0.001), recipe.id + ' is audible');
            assert.deepEqual(result, run(`${name}_DSP.render(synth.params)`), recipe.id + ' is deterministic');
        }
        const controls = plain(run(`synth.param_info.map(raw => synth.get_param_normalized(raw))`));
        for (const control of controls.filter(info => info.type === 'RANGE')) {
            for (const value of [control.min_value, control.max_value, NaN, Infinity]) {
                const literal = String(value);
                const pcm = run(`synth.reset_params(); ${name}_DSP.render({...synth.params, ${control.name}:${literal}})`);
                assert.ok(pcm.every(value => Number.isFinite(value) && Math.abs(value) <= 0.951));
            }
        }
        run(`for (const high of [false, true]) {
            synth.reset_params();
            for (const raw of synth.param_info) {
                const control = synth.get_param_normalized(raw);
                if (control.type === 'RANGE') synth.set_param(control.name, high ? control.max_value : control.min_value);
            }
            synth.set_param('masterVolume', 1);
            ${name === 'Fractr' ? 'for (let material = 0; material <= 6; material++) Fractr_DSP.render({...synth.params, material});' : 'Boomr_DSP.render(synth.params);'}
        }`);
        run(`Math.random = () => { throw new Error('Unseeded render randomness'); }; ${name}_DSP.render(synth.params)`);
        assert.ok(run(`${name}_DSP.render({...synth.params, masterVolume:0}).every(value => value === 0)`));
    });
}
