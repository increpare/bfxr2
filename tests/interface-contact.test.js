const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup() {
    let context;
    assert.doesNotThrow(() => { context = createContext([ 'Rustlr']); },
        'tactile and inventory sound engines must load');
    return context;
}
function rms(data) {
    let energy = 0;
    for (const sample of data) energy += sample * sample;
    return Math.sqrt(energy / data.length);
}
function energy(data, from, to) {
    let sum = 0;
    for (let i = Math.round(from * 44100); i < Math.min(data.length, Math.round(to * 44100)); i++) sum += data[i] ** 2;
    return sum;
}
function centroid(data) {
    let sum = 0, weighted = 0;
    for (let i = 0; i < data.length; i++) { const power = data[i] ** 2; sum += power; weighted += power * i; }
    return weighted / sum / data.length;
}
function brightness(data) {
    let sum = 0, difference = 0;
    for (let i = 1; i < data.length; i++) { sum += data[i] ** 2; difference += (data[i] - data[i - 1]) ** 2; }
    return difference / sum;
}
function bounded(data, frames) {
    assert.ok(data instanceof Float32Array);
    assert.equal(data.length, frames);
    assert.ok(data[0] === 0 && data.at(-1) === 0, 'edge fades reach zero');
    assert.ok(data.every(sample => Number.isFinite(sample) && Math.abs(sample) <= 0.951));
}

test('Rustlr travel moves friction energy and cloth filters bright foil microcontacts', () => {
    const {run} = setup();
    run('const rustle = new Rustlr(); rustle.apply_params({duration:1,material:0,gesture:2,grain:0.5,density:0.75,folds:4,pressure:0.6,motion:-1,seed:0.31})');
    const early = run('Rustlr_DSP.render(rustle.params)');
    const late = run('rustle.set_param("motion",1); Rustlr_DSP.render(rustle.params)');
    assert.ok(centroid(late) > centroid(early) + 0.15, 'travel biases the gesture toward its arrival or departure');
    const cloth = run('rustle.apply_params({motion:0,material:1}); Rustlr_DSP.render(rustle.params)');
    const foil = run('rustle.set_param("material",4); Rustlr_DSP.render(rustle.params)');
    assert.ok(brightness(foil) > brightness(cloth) * 2, 'cloth softens the friction and foil stays crisp');
    assert.ok(rms(cloth) > 0.002 && rms(foil) > 0.002);
});

test('all Rustlr contact families are fresh, audible, seeded and replay saved parameters exactly', () => {
    const {run} = setup();
    for (const name of [ 'Rustlr']) {
        const results = run(`(() => {
            const synth = new ${name}();
            const generateRandom = SoundDSP.rng(0.418);
            return synth.recipes.map(recipe => {
                Math.random = generateRandom;
                synth.generate_recipe(recipe.id);
                const firstParams = {...synth.params};
                synth.generate_recipe(recipe.id);
                const secondParams = {...synth.params};
                const restored = new ${name}();
                restored.apply_params(JSON.parse(JSON.stringify(firstParams)));
                Math.random = () => { throw new Error('render must use its saved seed'); };
                const first = ${name}_DSP.render(firstParams);
                const replay = ${name}_DSP.render(restored.params);
                restored.set_param('seed',0.947);
                return {id:recipe.id, firstParams, secondParams, first, replay,
                    reseeded:${name}_DSP.render(restored.params),
                    controls:Object.entries(recipe.values).filter(([key, value]) => key !== 'seed' && Array.isArray(value) && value[0] !== value[1]).length};
            });
        })()`);
        assert.equal(results.length, 8);
        assert.equal(new Set(results.map(result => result.id)).size, 8);
        for (const result of results) {
            assert.ok(result.controls >= 3, result.id + ' varies multiple controls');
            const a = plain(result.firstParams), b = plain(result.secondParams);
            assert.notEqual(a.seed, b.seed);
            delete a.seed; delete b.seed;
            assert.notDeepEqual(a, b, result.id + ' changes more than its seed');
            bounded(result.first, Math.round(result.firstParams.duration * 44100));
            assert.ok(rms(result.first) > 0.0015, result.id + ' is audible');
            assert.deepEqual(result.first, result.replay, result.id + ' replays exactly');
            assert.notDeepEqual(result.first, result.reseeded, result.id + ' has seeded detail');
        }
        assert.equal(new Set(results.map(result => Buffer.from(result.first.buffer).toString('base64'))).size, 8);
    }
});

test('quiet contact presets retain audible peaks across varied draws', () => {
    const {run} = setup();
    const levels = plain(run(`(() => {
        const result=[];
        for(const C of [Rustlr]) {
            const synth=new C(); Math.random=SoundDSP.rng(0.381);
            for(const recipe of synth.recipes) {
                for(let variation=0;variation<20;variation++) {
                    synth.generate_recipe(recipe.id);
                    const pcm=C.DSP.render(synth.params);
                    let energy=0,peak=0;
                    for(const sample of pcm) {energy+=sample*sample; peak=Math.max(peak,Math.abs(sample));}
                    result.push({name:synth.name,id:recipe.id,variation,peak,rms:Math.sqrt(energy/pcm.length)});
                }
            }
        }
        return result;
    })()`));
    for(const level of levels) {
        assert.ok(level.rms > 0.0015, `${level.name} ${level.id} ${level.variation}: audible energy`);
        assert.ok(level.peak > 0.025, `${level.name} ${level.id} ${level.variation}: audible peak ${level.peak}`);
    }
});

test('contact controls honor locks, and Rustlr folds stay integral across every parameter path', () => {
    const {run} = setup();
    for (const name of [ 'Rustlr']) {
        const result = plain(run(`(() => {
            Math.random = SoundDSP.rng(0.88);
            const synth = new ${name}();
            synth.set_param('duration',0.419);
            synth.set_param('seed',0.219);
            synth.set_param('masterVolume',0.38);
            synth.locked_params.duration = synth.locked_params.seed = true;
            for (const recipe of synth.recipes) synth.generate_recipe(recipe.id);
            synth.randomize_params(); synth.mutate_params();
            return {duration:synth.params.duration,seed:synth.params.seed,volume:synth.params.masterVolume,
                volumeLocked:synth.locked_params.masterVolume,templates:synth.templates.map(item => item[0])};
        })()`));
        assert.equal(result.duration, 0.419);
        assert.equal(result.seed, 0.219);
        assert.equal(result.volume, 0.38);
        assert.equal(result.volumeLocked, true);
        assert.ok(result.templates.includes('Randomize') && result.templates.includes('Mutate'));
    }
    const counts = plain(run(`(() => {
        const synth = new Rustlr();
        const generated = synth.recipes.map(recipe => {synth.generate_recipe(recipe.id); return synth.params.folds;});
        synth.randomize_params(); generated.push(synth.params.folds);
        synth.mutate_params(); generated.push(synth.params.folds);
        const imported = [3.6,3.4,-10,999,NaN].map(folds => {synth.apply_params({folds}); return synth.params.folds;});
        synth.set_param('folds',6); synth.locked_params.folds=true;
        synth.apply_params({folds:2.1},true); synth.generate_recipe('wrapper'); synth.mutate_params();
        return {generated,imported,locked:synth.params.folds,fallback:synth.default_params().folds};
    })()`));
    assert.ok(counts.generated.every(count => Number.isInteger(count) && count >= 1 && count <= 12));
    assert.deepEqual(counts.imported, [4,3,1,12,counts.fallback]);
    assert.equal(counts.locked, 6);
});

test('contact engines are bounded and muted for defaults, limits and malformed imports', () => {
    const {run} = setup();
    for (const [name,low,high] of [['Rustlr',0.08,3]]) {
        const variants = run(`(() => {
            const synth = new ${name}();
            const variants = [synth.params];
            for (const limit of ['min_value','max_value']) {
                const params={};
                for (const info of synth.param_info) {
                    const normalized=synth.get_param_normalized(info);
                    params[normalized.name]=normalized.type==='BUTTONSELECT' ? info.values[limit==='min_value'?0:info.values.length-1][2] : normalized[limit];
                }
                params.masterVolume=1;
                variants.push(params);
            }
            variants.push({...synth.params,duration:Infinity,hardness:NaN,pressure:NaN,seed:NaN});
            return variants.map(params => ({params,pcm:${name}_DSP.render(params),muted:${name}_DSP.render({...params,masterVolume:0})}));
        })()`);
        for (const variant of variants) {
            const expected = Number.isFinite(variant.params.duration) ? variant.params.duration : 0.65;
            bounded(variant.pcm, Math.round(expected * 44100));
            assert.ok(variant.pcm.length >= low * 44100 && variant.pcm.length <= high * 44100);
            assert.ok(variant.muted.every(sample => sample === 0), name + ' mutes exactly');
        }
    }
});
