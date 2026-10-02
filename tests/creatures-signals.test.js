const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function context() {
    let result;
    assert.doesNotThrow(() => { result = createContext(['Crittr', 'Signlr']); },
        'creature and transmission definitions and engines must load');
    return result;
}
function rms(data) {
    let energy = 0;
    for (const value of data) energy += value * value;
    return Math.sqrt(energy / data.length);
}
function toneEnergy(data, frequency) {
    let real = 0, imaginary = 0;
    for (let i = 0; i < data.length; i++) {
        const window = Math.sin(Math.PI * i / (data.length - 1)) ** 2;
        const phase = 2 * Math.PI * frequency * i / 44100;
        real += data[i] * window * Math.cos(phase);
        imaginary += data[i] * window * Math.sin(phase);
    }
    return (real * real + imaginary * imaginary) / (data.length * data.length);
}
function activeRuns(data) {
    const levels = [];
    for (let i = 0; i < data.length - 220; i += 220) levels.push(rms(data.slice(i, i + 220)));
    const threshold = Math.max(...levels) * 0.16;
    return levels.reduce((sum, value, index) => sum + (value > threshold && (!index || levels[index - 1] <= threshold)), 0);
}
function bounded(data) {
    assert.ok(data instanceof Float32Array);
    assert.ok(data[0] === 0);
    assert.ok(data.at(-1) === 0);
    for (const value of data) assert.ok(Number.isFinite(value) && Math.abs(value) <= 0.951);
}

test('all creature and transmission families vary multiple controls and preserve locks', () => {
    const {run} = context();
    for (const name of ['Crittr', 'Signlr']) {
        const result = plain(run(`(() => {
            const synth = new ${name}();
            Math.random = SoundDSP.rng(0.419);
            const families = synth.recipes.map(recipe => {
                synth.generate_recipe(recipe.id);
                const first = {...synth.params};
                synth.generate_recipe(recipe.id);
                return {id:recipe.id, first, second:{...synth.params},
                    variableControls:Object.entries(recipe.values).filter(([key,value]) =>
                        key !== 'seed' && Array.isArray(value) && value[0] !== value[1]).length};
            });
            const key = '${name}' === 'Crittr' ? 'pitch' : 'carrier';
            synth.set_param(key, 0.123);
            synth.set_param('seed', 0.321);
            synth.set_param('masterVolume', 0.41);
            synth.locked_params[key] = synth.locked_params.seed = true;
            synth.generate_recipe(synth.recipes[0].id);
            synth.randomize_params();
            synth.mutate_params();
            return {families, locked:synth.params[key], seed:synth.params.seed, volume:synth.params.masterVolume,
                templates:synth.templates.map(item => item[0])};
        })()`));
        assert.ok(result.families.length >= 8);
        assert.equal(new Set(result.families.map(family => family.id)).size, result.families.length);
        for (const family of result.families) {
            assert.ok(family.variableControls >= 3, family.id + ' varies at least three controls');
            assert.notEqual(family.first.seed, family.second.seed);
            delete family.first.seed;
            delete family.second.seed;
            assert.notDeepEqual(family.first, family.second);
        }
        assert.equal(result.locked, 0.123);
        assert.equal(result.seed, 0.321);
        assert.equal(result.volume, 0.41);
        assert.ok(result.templates.includes('Randomize') && result.templates.includes('Mutate'));
    }
});

test('call and packet counters stay integral through presets, edits, imports and locks', () => {
    const {run} = context();
    for (const [name,key] of [['Crittr','calls'],['Signlr','packets']]) {
        const result = plain(run(`(() => {
            const synth = new ${name}();
            Math.random = SoundDSP.rng(0.419);
            const generated = synth.recipes.map(recipe => {
                synth.generate_recipe(recipe.id);
                return synth.params.${key};
            });
            synth.randomize_params();
            generated.push(synth.params.${key});
            synth.mutate_params();
            generated.push(synth.params.${key});
            const imported = [4.56,4.49,-10,999,NaN].map(value => {
                synth.apply_params({${key}:value});
                return synth.params.${key};
            });
            synth.set_param('${key}',6);
            synth.locked_params.${key} = true;
            synth.apply_params({${key}:9.4},true);
            synth.set_param('${key}',2.7,true);
            synth.generate_recipe(synth.recipes[0].id);
            synth.randomize_params();
            synth.mutate_params();
            const locked = synth.params.${key};
            synth.set_param('${key}',4.56);
            synth.set_param('${name}' === 'Signlr' ? 'symbols' : 'pitch',0.419);
            return {generated,imported,locked,edited:synth.params.${key},
                continuous:synth.params['${name}' === 'Signlr' ? 'symbols' : 'pitch'],
                fallback:synth.default_params().${key}};
        })()`));
        assert.ok(result.generated.every(value => Number.isInteger(value) && value >= 1 && value <= 12));
        assert.deepEqual(result.imported,[5,4,1,12,result.fallback]);
        assert.equal(result.locked,6);
        assert.equal(result.edited,5);
        assert.equal(result.continuous,0.419);
    }
});

test('every new family is audible, distinct, seeded and exactly reproducible from saved parameters', () => {
    const {run} = context();
    for (const name of ['Crittr', 'Signlr']) {
        const results = run(`(() => {
            const synth = new ${name}();
            Math.random = SoundDSP.rng(0.632);
            return synth.recipes.map(recipe => {
                synth.generate_recipe(recipe.id);
                synth.set_param('duration', 0.7);
                const saved = JSON.stringify(synth.params);
                const first = ${name}_DSP.render(synth.params);
                const restored = new ${name}();
                restored.apply_params(JSON.parse(saved));
                Math.random = () => { throw new Error('render must use its saved seed'); };
                const second = ${name}_DSP.render(restored.params);
                const changed = ${name}_DSP.render({...restored.params,seed:0.127});
                Math.random = SoundDSP.rng(synth.params.seed);
                return {id:recipe.id,first,second,changed};
            });
        })()`);
        const fingerprints = new Set();
        for (const {id,first,second,changed} of results) {
            assert.equal(first.length, 30870);
            bounded(first);
            assert.ok(rms(first) > 0.004, id + ' is audible');
            assert.deepEqual(first, second, id + ' reloads exact PCM');
            assert.notDeepEqual(first, changed, id + ' responds to variation');
            fingerprints.add(Array.from(first.slice(1800,1830)).join(','));
        }
        assert.equal(fingerprints.size, results.length);
    }
});

test('creature call count schedules separate vocal gestures', () => {
    const {run} = context();
    const [single,many] = run(`(() => {
        const params = {...new Crittr().params, duration:1.2, seed:0.3, gap:0.5, breath:0,
            flutter:0, contour:0, morph:0, growl:0};
        return [1,4].map(calls => Crittr_DSP.render({...params,calls}));
    })()`);
    assert.equal(activeRuns(single), 1);
    assert.equal(activeRuns(many), 4);
});

test('creature growl adds a genuine half-frequency throat component', () => {
    const {run} = context();
    const [clean,growling] = run(`(() => {
        const params = {...new Crittr().params,duration:0.8,pitch:0.4,seed:0.2,calls:1,gap:0,
            contour:0,flutter:0,morph:0,breath:0};
        return [0,1].map(growl => Crittr_DSP.render({...params,growl}));
    })()`);
    const subharmonic = 45 * 2 ** (0.4 * 5) / 2;
    assert.ok(toneEnergy(growling,subharmonic) > toneEnergy(clean,subharmonic)*20 + 0.00001,
        'growl creates subharmonics below the original call pitch');
});

test('creature throat size and evolution reshape the resonant call', () => {
    const {run} = context();
    const [small,large,still,moving] = run(`(() => {
        const params = {...new Crittr().params,duration:0.7,calls:1,gap:0,seed:0.342,breath:0.75,
            flutter:0,contour:0,growl:0,morph:0};
        return [{size:0},{size:1},{size:0.4,morph:0},{size:0.4,morph:1}]
            .map(change => Crittr_DSP.render({...params,...change}));
    })()`);
    const brightness = data => {
        let energy=0, differences=0;
        for(let i=1;i<data.length;i++) {
            energy += data[i]*data[i];
            differences += (data[i]-data[i-1])**2;
        }
        return Math.sqrt(differences/energy);
    };
    assert.ok(brightness(small) > brightness(large)*2,
        'a small throat shifts resonances upward');
    assert.notDeepEqual(still,moving,'evolution animates the throat independently of pitch');
});

test('transmission packet count and gap create the requested bursts', () => {
    const {run} = context();
    const [single,many] = run(`(() => {
        const params = {...new Signlr().params,duration:1.2,seed:0.5,gap:0.5,interference:0,
            corruption:0,echo:0,encoding:0,deviation:0};
        return [1,4].map(packets => Signlr_DSP.render({...params,packets}));
    })()`);
    assert.equal(activeRuns(single), 1);
    assert.equal(activeRuns(many), 4);
});

test('transmission carrier moves its tone and corruption loses symbols', () => {
    const {run} = context();
    const [low,high,clear,broken] = run(`(() => {
        const params = {...new Signlr().params,duration:0.8,seed:0.61,packets:1,gap:0,encoding:0,
            drift:0,interference:0,corruption:0,echo:0,deviation:0,symbols:1};
        return [{carrier:0.25},{carrier:0.7},{carrier:0.4},{carrier:0.4,corruption:1}]
            .map(change => Signlr_DSP.render({...params,...change}));
    })()`);
    const lowFrequency = 90 * 2 ** (0.25 * 5.7);
    const highFrequency = 90 * 2 ** (0.7 * 5.7);
    assert.ok(toneEnergy(low,lowFrequency) > toneEnergy(low,highFrequency)*100);
    assert.ok(toneEnergy(high,highFrequency) > toneEnergy(high,lowFrequency)*100);
    assert.ok(rms(broken) < rms(clear)*0.7, 'corruption drops audible symbols');
});

test('transmission echo leaves delayed energy after a packet closes', () => {
    const {run} = context();
    const [dry,echo] = run(`(() => {
        const params = {...new Signlr().params,duration:0.9,seed:0.13,packets:1,gap:0.6,
            corruption:0,interference:0};
        return [0,1].map(echo => Signlr_DSP.render({...params,echo}));
    })()`);
    const start = Math.round(0.39*44100), end = Math.round(0.47*44100);
    assert.ok(rms(echo.slice(start,end)) > rms(dry.slice(start,end))*5 + 0.005);
});

test('extremes, hostile durations and mute remain bounded with faded edges', () => {
    const {run} = context();
    for (const name of ['Crittr','Signlr']) {
        const buffers = run(`(() => {
            const synth = new ${name}();
            const extremes = [0,1].map(high => {
                for (const raw of synth.param_info) {
                    const info = synth.get_param_normalized(raw);
                    if (info.type === 'RANGE') synth.set_param(info.name, high ? info.max_value : info.min_value);
                }
                synth.set_param('duration',0.2);
                synth.set_param('masterVolume',1);
                return ${name}_DSP.render(synth.params);
            });
            return [...extremes,${name}_DSP.render({...synth.params,duration:-9}),
                ${name}_DSP.render({...synth.params,duration:999}),
                ${name}_DSP.render({...synth.params,duration:NaN}),
                ${name}_DSP.render({...synth.params,masterVolume:0})];
        })()`);
        buffers.forEach(bounded);
        assert.equal(buffers[0].length,8820);
        assert.equal(buffers[1].length,8820);
        assert.equal(buffers[2].length,6615);
        assert.equal(buffers[3].length,220500);
        assert.ok(buffers[4].length >= 6615 && buffers[4].length <= 220500);
        assert.ok(buffers[5].every(value => value === 0));
    }
});
