const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup() {
    const api = createContext(['Rustlr', 'Rollr']);
    api.run(`var rustle = new Rustlr(), roll = new Rollr();
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

test('slow rolling maintains surface contact between broad wheel bumps', () => {
    const {run} = setup();
    const raw = run(`Rollr_DSP.render({...roll.params,duration:2,wheels:1,speed:0,
        roughness:0.15,slowing:0,size:0.6,material:0,seed:0.5}); rawContact`);
    const windows = [];
    for (let i = 4410; i < raw.length - 4410; i += 882) windows.push(rms(raw.slice(i, i + 882)));
    windows.sort((a, b) => a - b);
    assert.ok(windows[Math.floor(windows.length * 0.1)] > rms(raw) * 0.32,
        'the quietest moving sections retain rolling friction instead of isolated knocks');
});

test('rolling body sound is damped and broadband instead of an exposed periodic oscillator', () => {
    const {run} = setup();
    const pcm = run(`Rollr_DSP.render({...roll.params,duration:2,wheels:1,speed:0,
        roughness:0,slowing:0,size:0.6,material:0,seed:0.5})`);
    const correlations = [];
    for (let lag = 80; lag < 700; lag += 2) correlations.push(correlation(pcm, pcm, lag));
    let periodicity = 0;
    // A broad lowpass field is locally correlated, but does not repeat after a period.
    for (let i = 1; i < correlations.length - 1; i++) {
        if (correlations[i] > correlations[i - 1] && correlations[i] > correlations[i + 1]) {
            periodicity = Math.max(periodicity, correlations[i]);
        }
    }
    assert.ok(periodicity < 0.65, 'long-lived narrow body ringing must not dominate rolling: ' + periodicity);
});

test('full legacy Rollr saves reset surface while partial updates and locks retain it', () => {
    const {run} = setup();
    const result = plain(run(`(() => {
        const old = {...roll.params}; delete old.surface;
        roll.set_param('surface',1); roll.apply_params({speed:0.2});
        const partial = roll.params.surface;
        roll.apply_params(old); const legacy = roll.params.surface;
        roll.set_param('surface',3); roll.set_locked_param('surface',true);
        roll.apply_params(old,true);
        return {partial,legacy,locked:roll.params.surface,default:roll.default_params().surface};
    })()`));
    assert.equal(result.partial, 1);
    assert.equal(result.legacy, result.default);
    assert.equal(result.locked, 3);
});

test('rolling traverses different surfaces and faster travel raises texture frequency', () => {
    const {run} = setup();
    assert.ok(run('roll.param_info.some(info => info.name === "surface")'), 'surface has a compact selector');
    const buffers = run(`[0,1,2,3].map(surface => Rollr_DSP.render({...roll.params,
        duration:1,roughness:0.7,surface,seed:0.173,slowing:0}))`);
    assert.equal(new Set(buffers.map(pcm => Buffer.from(pcm.buffer).toString('base64'))).size, 4);
    const [slow, fast] = run(`[0.1,0.9].map(speed => Rollr_DSP.render({...roll.params,
        duration:2,wheels:1,surface:2,roughness:0.8,speed,slowing:0,seed:0.173}))`);
    assert.ok(brightness(fast) > brightness(slow) * 1.3, 'travel speed changes the rate of surface detail');
});

test('rolling slowdown loses kinetic energy and cloth remains softer than foil', () => {
    const {run} = setup();
    const roll = run(`Rollr_DSP.render({...roll.params,duration:3,speed:0.8,
        slowing:1,roughness:0.6,seed:0.413})`);
    assert.ok(rms(roll.slice(88200, 119070)) < rms(roll.slice(4410, 35280)) * 0.65);
    const [cloth, foil] = run(`[1,4].map(material => Rustlr_DSP.render({...rustle.params,
        duration:1,material,gesture:3,pressure:0.7,folds:7,seed:0.31}))`);
    assert.ok(brightness(foil) > brightness(cloth) * 3);
});

for (const name of ['Rustlr', 'Rollr']) {
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
