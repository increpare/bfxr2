const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function context() {
    let result;
    assert.doesNotThrow(() => { result = createContext(['Machinr', 'Weathr']); },
        'both specialized synths and their renderers must load');
    return result;
}
function rms(data) { return Math.sqrt(data.reduce((sum, x) => sum + x*x, 0) / data.length); }
function roughness(data) {
    let sum = 0;
    for (let i=1; i<data.length; i++) sum += (data[i]-data[i-1])**2;
    return Math.sqrt(sum/(data.length-1))/rms(data);
}
function bounded(data) {
    for (const value of data) assert.ok(Number.isFinite(value) && Math.abs(value) <= 0.951);
}
const categoryAudio = new Map();
function renderCategories(name) {
    if (categoryAudio.has(name)) return categoryAudio.get(name);
    const {run} = context();
    const result = run(`(() => {
        const synth = new ${name}();
        return synth.recipes.map((recipe,index) => {
            synth.generate_recipe(recipe.id);
            synth.set_param('seed', 0.4321);
            synth.set_param('duration', '${name}' === 'Weathr' ? 4 : 0.55);
            const first = ${name}_DSP.render(synth.params);
            return [first,index === 0 ? ${name}_DSP.render(synth.params) : null];
        });
    })()`);
    categoryAudio.set(name,result);
    return result;
}

test('machine and weather categories generate fresh controls and respect locked values', () => {
    const {run} = context();
    for (const name of ['Machinr', 'Weathr']) {
        const values = plain(run(`(() => {
            const synth = new ${name}();
            const results = synth.recipes.map(recipe => {
                synth.generate_recipe(recipe.id);
                const first = {...synth.params};
                synth.generate_recipe(recipe.id);
                return {first, second:{...synth.params}, name:recipe.name};
            });
            const key = '${name}' === 'Machinr' ? 'speed' : 'density';
            synth.set_param(key, 0.123);
            synth.locked_params[key] = true;
            synth.locked_params.seed = true;
            synth.set_param('seed', 0.321);
            synth.generate_recipe(synth.recipes[0].id);
            return {results, locked:synth.params[key], seed:synth.params.seed, volume:synth.params.masterVolume};
        })()`));
        assert.ok(values.results.length >= 8);
        for (const {first, second, name:category} of values.results) {
            assert.notEqual(first.seed, second.seed, category+' chooses fresh sound texture');
            delete first.seed; delete second.seed;
            assert.notDeepEqual(first, second, category+' varies its physical controls too');
        }
        assert.equal(values.locked, 0.123);
        assert.equal(values.seed, 0.321);
        assert.equal(values.volume, 0.5);
    }
});

test('all categories render audible, repeatable and differentiated sound', () => {
    for (const name of ['Machinr', 'Weathr']) {
        const buffers = renderCategories(name);
        const fingerprints = [];
        for (const [first,second] of buffers) {
            if (second) assert.deepEqual(first,second);
            assert.ok(rms(first) > 0.005, name+' category is audible');
            bounded(first);
            fingerprints.push(Array.from(first.slice(500,550)).join(','));
        }
        assert.equal(new Set(fingerprints).size, buffers.length);
    }
});

test('weather exports continuous four to ten second loops without silent edge padding', () => {
    const {run} = context();
    assert.equal(run('new Weathr().loop_preview'), true);
    const loops = renderCategories('Weathr').map(pair => pair[0]);
    for (const loop of loops) {
        assert.equal(loop.length, 4*44100);
        const edge = new Float32Array([...loop.slice(-512), ...loop.slice(0,512)]);
        assert.ok(rms(edge) > rms(loop)*0.12, 'loop join remains alive');
        let maxStep = 0;
        for (let i=1; i<loop.length; i++) maxStep = Math.max(maxStep,Math.abs(loop[i]-loop[i-1]));
        assert.ok(Math.abs(loop[0]-loop.at(-1)) <= maxStep, 'join is no sharper than the rendered texture');
        // Repeating the actual export must preserve the same boundary at every repetition.
        const repeated = new Float32Array(loop.length*3);
        repeated.set(loop); repeated.set(loop,loop.length); repeated.set(loop,loop.length*2);
        assert.equal(repeated[loop.length]-repeated[loop.length-1], repeated[2*loop.length]-repeated[2*loop.length-1]);
    }
});

test('weather colour filtering has the same steady state across a rotated loop', () => {
    const {run} = context();
    const [original,rotated] = run(`(() => {
        const input=Float32Array.from({length:400},(_,i) => i%13 === 0 ? 0.7 : -0.08);
        const shifted=Float32Array.from(input,(_,i) => input[(i+137)%input.length]);
        return [Weathr_DSP.circularLowpass(input,17), Weathr_DSP.circularLowpass(shifted,17)];
    })()`);
    for(let i=0;i<original.length;i++) {
        assert.ok(Math.abs(rotated[i]-original[(i+137)%original.length])<1e-7,
            'the filter has no special startup transient at the export boundary');
    }
});

test('density changes environmental activity and brightness opens its spectrum', () => {
    const {run} = context();
    const [sparse,dense,dark,bright] = run(`(() => {
        const synth = new Weathr();
        synth.generate_recipe('rain');
        Object.assign(synth.params,{duration:4, seed:0.256, turbulence:0.4, brightness:0.55});
        return [{density:0.05},{density:0.95},{density:0.6,brightness:0},{density:0.6,brightness:1}]
            .map(change => Weathr_DSP.render({...synth.params,...change}));
    })()`);
    assert.ok(rms(dense) > rms(sparse)*1.4, 'denser rain has stronger continuous activity');
    assert.ok(roughness(bright) > roughness(dark)*2, 'brightness raises high frequency energy');
});

test('machine speed, load, looseness and start/stop controls change the mechanism', () => {
    const {run} = context();
    const result = run(`(() => {
        const synth = new Machinr();
        synth.generate_recipe('tiny_motor');
        Object.assign(synth.params,{duration:1,seed:0.32,startTime:0.01,stopTime:0.02});
        return [{speed:0.15},{speed:0.85},{load:0.05},{load:0.9},{looseness:0},{looseness:1},
            {startTime:0.6},{stopTime:0.6}].map(change => Machinr_DSP.render({...synth.params,...change}));
    })()`);
    for (const pair of [[0,1],[2,3],[4,5]]) assert.notDeepEqual(result[pair[0]],result[pair[1]]);
    assert.ok(rms(result[6].slice(0,4410)) < rms(result[0].slice(0,4410))*.6);
    assert.ok(rms(result[7].slice(-4410)) < rms(result[0].slice(-4410))*.6);
});

test('extreme controls remain finite and bounded with exact requested durations', () => {
    const {run} = context();
    for (const name of ['Machinr','Weathr']) {
        const buffers = run(`(() => {
            const synth = new ${name}();
            return [0,1].map(high => {
                for (const raw of synth.param_info) {
                    const info=synth.get_param_normalized(raw);
                    if (info.type === 'RANGE') synth.set_param(info.name, high ? info.max_value : info.min_value);
                }
                synth.set_param('masterVolume', 1);
                synth.set_param('duration', '${name}' === 'Weathr' ? (high ? 10 : 4) : 0.2);
                return ${name}_DSP.render(synth.params);
            });
        })()`);
        for (const [i,buffer] of buffers.entries()) {
            bounded(buffer);
            assert.equal(buffer.length, (name==='Weathr'?(i ? 10 : 4):0.2)*44100);
        }
    }
});
