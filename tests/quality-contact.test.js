const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup() {
    const api = createContext(['Rustlr']);
    api.run(`var rustle = new Rustlr();
        var finish = SoundDSP.finish;
        SoundDSP.finish = function(buffer, volume, options) {
            if (!buffer.every(Number.isFinite)) throw new Error('non-finite raw contact PCM');
            globalThis.rawContact = buffer.slice();
            return finish.call(this, buffer, volume, options);
};`);
    return api;
}
function rms(pcm) {
    let power = 0;
    for (const sample of pcm) power += sample * sample;
    return Math.sqrt(power / pcm.length);
}
function correlation(a, b, lag = 0) {
    let ab = 0, aa = 0, bb = 0;
    for (let i = 4410; i < a.length - 4410 - lag; i += 3) {
        ab += a[i] * b[i + lag]; aa += a[i] ** 2; bb += b[i + lag] ** 2;
    }
    return ab / Math.sqrt(aa * bb);
}
function brightness(pcm) {
    let power = 0, difference = 0;
    for (let i = 1; i < pcm.length; i++) {
        power += pcm[i] ** 2; difference += (pcm[i] - pcm[i - 1]) ** 2;
    }
    return difference / power;
}

test('Rustlr pressure changes stick-slip and crease behaviour, beyond a gain adjustment', () => {
    const {run} = setup();
    const [light, firm] = run(`[{pressure:0.15},{pressure:0.9}].map(change => {
        Rustlr_DSP.render({...rustle.params,duration:1,gesture:2,material:2,seed:0.312,...change});
        return rawContact;
    })`);
    assert.ok(correlation(light, firm) < 0.96, 'pressure must change contact timing or spectrum');
    assert.ok(rms(firm) > rms(light) * 1.3, 'firm contact still transfers more energy');
});

for (const name of ['Rustlr']) {
    test(name + ' recipes preserve locks, vary physical controls and replay saved PCM', () => {
        const {run} = setup();
        run(`var synth = new ${name}(); Math.random = SoundDSP.rng(0.316);`);
        for (const recipe of plain(run('synth.recipes'))) {
            const first = plain(run(`synth.generate_recipe('${recipe.id}'); synth.params`));
            const second = plain(run(`synth.generate_recipe('${recipe.id}'); synth.params`));
            assert.ok(Object.keys(first).filter(key => key !== 'seed' && first[key] !== second[key]).length >= 3);
            const [pcm, replay] = run(`(() => {
                const params = JSON.parse(JSON.stringify(synth.params));
                const random = Math.random;
                Math.random = () => { throw new Error('unseeded render'); };
                try { return [${name}_DSP.render(params), ${name}_DSP.render(params)]; }
                finally { Math.random = random; }
            })()`);
            assert.deepEqual(pcm, replay, recipe.id);
            assert.ok(rms(pcm) > 0.0015, recipe.id + ' has audible contact energy');
        }
        assert.ok(run(`Object.keys(synth.params).forEach(key => synth.set_locked_param(key,true));
            var saved=JSON.stringify(synth.params);
            synth.recipes.forEach(recipe=>synth.generate_recipe(recipe.id));
            synth.randomize_params(); synth.mutate_params(); JSON.stringify(synth.params)===saved`));
    });

    test(name + ' raw PCM stays finite for all materials and limits before output finishing', () => {
        const {run} = setup();
        const cases = run(`(() => {
            const synth = new ${name}(), cases = [];
            const materials = synth.param_info.find(info => info.name === 'material').values;
            for (const high of [false,true]) for (const material of materials) {
                synth.reset_params();
                for (const raw of synth.param_info) {
                    const info = synth.get_param_normalized(raw);
                    if (info.type === 'RANGE') synth.set_param(info.name, high ? info.max_value : info.min_value);
                }
                synth.set_param('material', material[2]); synth.set_param('masterVolume',1);
                cases.push({...synth.params});
            }
            cases.push({duration:Infinity,material:NaN,surface:Infinity,pressure:NaN,seed:NaN});
            return cases.map(params => ({pcm:${name}_DSP.render(params), raw:rawContact,
                mute:${name}_DSP.render({...params,masterVolume:0})}));
        })()`);
        for (const {pcm, raw, mute} of cases) {
            assert.ok(raw.every(Number.isFinite));
            assert.ok(pcm.every(sample => Number.isFinite(sample) && Math.abs(sample) <= 0.951));
            assert.ok(pcm[0] === 0 && pcm.at(-1) === 0);
            assert.ok(mute.every(sample => sample === 0));
        }
    });
}
