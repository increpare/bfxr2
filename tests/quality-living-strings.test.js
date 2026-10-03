const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');
const names = ['Breathr', 'Pulser', 'Pluckr'];
const categoryIds = {
    Breathr:['dash','hurt','lose','roar','inhale','exhale','sigh','snore','tired_runner','deep_breath','held_breath','gasp','sleeping_beast','diver','helmet','ghost_breath'],
    Pulser:['heartbeat','panic','giant_heart','android_core','poison','underwater','energy_core','last_life'],
    Pluckr:['coin','unlock','blip','confirm','heal','harp','kalimba','muted_guitar','metal_string','magic_harp','bass_pluck','broken_string','quest_pluck']
};
function setup() {
    const api = createContext(names);
    api.run('Math.random=SoundDSP.rng(0.319)');
    return api;
}
function energy(pcm, from = 0, to = pcm.length / 44100) {
    let sum = 0;
    for (let i = Math.round(from * 44100); i < Math.min(pcm.length, Math.round(to * 44100)); i++) sum += pcm[i] ** 2;
    return sum;
}
function brightness(pcm, from = 0, to = pcm.length / 44100) {
    let sum = 0, difference = 0;
    for (let i = Math.max(1, Math.round(from * 44100)); i < Math.min(pcm.length, Math.round(to * 44100)); i++) {
        sum += pcm[i] ** 2; difference += (pcm[i] - pcm[i - 1]) ** 2;
    }
    return difference / Math.max(1e-20, sum);
}
function normalizedCorrelation(pcm, lag, from, to) {
    let cross = 0, a = 0, b = 0;
    for (let i = Math.round(from * 44100); i < Math.round(to * 44100); i++) {
        cross += pcm[i] * pcm[i + lag]; a += pcm[i] ** 2; b += pcm[i + lag] ** 2;
    }
    return cross / Math.sqrt(a * b);
}

test('Breathr sources cover airflow, retro noise and snoring without replacing its categories', () => {
    const {run} = setup();
    const selector = plain(run("new Breathr().param_info.find(info=>info.name==='source') || null"));
    assert.ok(selector, 'a compact source selector is available');
    assert.equal(selector.type, 'BUTTONSELECT');
    assert.deepEqual(selector.values.map(value => value[0]), ['Airflow', 'Retro', 'Snore']);
    const sounds = run(`(() => {
        const p={duration:2.4,cycles:1,effort:0.55,inhale:0.45,hold:0.04,throat:0.6,rasp:0.5,flutter:0.35,space:0,seed:0.51};
        return [0,1,2].map(source=>Breathr_DSP.render({...p,source}));
    })()`);
    for (const pcm of sounds) assert.ok(energy(pcm) > 1, 'every source produces audible breathing');
    assert.notDeepEqual(sounds[0], sounds[1], 'retro uses a distinct excitation');
    assert.notDeepEqual(sounds[0], sounds[2], 'snoring changes airflow mechanics');
    assert.ok(brightness(sounds[0], 0.25, 0.8) > brightness(sounds[0], 1.25, 1.85) * 1.35,
        'drawn-in air is brighter than the softer outward flow');
    assert.ok(energy(sounds[0], 2.3, 2.4) < energy(sounds[0], 1.6, 1.7) * 0.04,
        'a breath rests before the next cycle');
});

test('Pulser heartbeat contains short pressure noise and independently controlled paired beats', () => {
    const {run} = setup();
    const [single, pair, late] = run(`(() => {
        const p={duration:1,beats:1,pitch:0.2,size:0.5,separation:0.4,secondary:0,murmur:0,tension:0.1,irregular:0,seed:0.51};
        return [Pulser_DSP.render(p),Pulser_DSP.render({...p,secondary:0.8}),Pulser_DSP.render({...p,secondary:0.8,separation:0.9})];
    })()`);
    assert.ok(energy(pair, 0.005, 0.12) > 1, 'first pressure transient is audible');
    assert.ok(energy(pair, 0.27, 0.39) > energy(single, 0.27, 0.39) * 8 + 0.1, 'second transient is audible');
    assert.ok(energy(late, 0.38, 0.52) > energy(pair, 0.38, 0.52) * 2, 'separation moves the second transient');
    assert.ok(brightness(single, 0.008, 0.08) > 0.001,
        'a heartbeat has a broad muffled contact transient, rather than only a ringing note');
});

test('Pluckr materials change loss, excitation and dispersion at identical tuning', () => {
    const {run} = setup();
    const selector = plain(run("new Pluckr().param_info.find(info=>info.name==='material') || null"));
    assert.ok(selector, 'string materials have a compact selector');
    assert.equal(selector.type, 'BUTTONSELECT');
    assert.deepEqual(selector.values.map(value => value[0]), ['Nylon', 'Steel', 'Gut', 'Rubber', 'Glass']);
    const sounds = run(`(() => {
        const p={duration:2,pitch:0.45,strings:1,damping:0.12,brightness:0.65,pluck:0.3,coupling:0,strum:0,inharmonic:0,seed:0.51};
        return [0,1,2,3,4].map(material=>Pluckr_DSP.render({...p,material}));
    })()`);
    const decay = pcm => energy(pcm, 0.5, 1.2) / energy(pcm, 0, 0.12);
    assert.ok(decay(sounds[3]) < decay(sounds[0]) * 0.25, 'rubber absorbs vibration faster than nylon');
    assert.ok(brightness(sounds[1], 0.03, 0.2) > brightness(sounds[0], 0.03, 0.2) * 1.4, 'steel retains brighter upper partials');
    const lag = Math.round(44100 / (55 * 2 ** (0.45 * 4)));
    assert.ok(normalizedCorrelation(sounds[0], lag, 0.12, 0.35) > 0.8, 'normal string keeps a pitched period');
    assert.ok(normalizedCorrelation(sounds[4], lag, 0.12, 0.35) < normalizedCorrelation(sounds[0], lag, 0.12, 0.35) - 0.08,
        'glass disperses partials, rather than just changing a pitch parameter');
    for (let a = 0; a < sounds.length; a++) {
        assert.ok(energy(sounds[a]) > 0.1, 'each material is audible');
        for (let b = a + 1; b < sounds.length; b++) assert.notDeepEqual(sounds[a], sounds[b]);
    }
});

for (const name of names) {
    test(name + ' preserves randomized category IDs, snapshots and every lock', () => {
        const {run} = setup();
        const result = run(`(() => {
            const synth=new ${name}();
            const entries=synth.recipes.map(recipe=>{
                synth.generate_recipe(recipe.id);const first={...synth.params};
                synth.generate_recipe(recipe.id);const second={...synth.params};
                const pcm=${name}_DSP.render(first), replay=${name}_DSP.render(JSON.parse(JSON.stringify(first)));
                return {id:recipe.id,first,second,pcm,replay};
            });
            Object.keys(synth.params).forEach(key=>synth.set_locked_param(key,true));
            const before=JSON.stringify(synth.params);
            synth.recipes.forEach(recipe=>synth.generate_recipe(recipe.id));synth.randomize_params();synth.mutate_params();
            return {entries,locked:before===JSON.stringify(synth.params)};
        })()`);
        assert.deepEqual(plain(result.entries.map(entry=>entry.id)), categoryIds[name]); assert.ok(result.locked);
        for (const entry of result.entries) {
            assert.ok(Object.keys(entry.first).filter(key=>key!=='seed'&&entry.first[key]!==entry.second[key]).length >= 3, entry.id);
            assert.deepEqual(entry.pcm, entry.replay);
            assert.ok(energy(entry.pcm) > 0.01, entry.id + ' is audible');
        }
    });
    test(name + ' raw PCM stays finite at every source and boundary before finish can hide errors', () => {
        const {run} = setup();
        const results = run(`(() => {
            const synth=new ${name}(),cases=[];
            const selector=synth.param_info.find(info=>info.type==='BUTTONSELECT');
            for(const choice of selector ? selector.values.map(value=>value[2]) : [0]) {
                for(const boundary of ['min_value','max_value']) {
                    synth.reset_params();
                    for(const info of synth.param_info) {const p=synth.get_param_normalized(info);if(p.type!=='BUTTONSELECT')synth.set_param(p.name,p[boundary]);}
                    if(selector)synth.set_param(selector.name,choice);
                    synth.set_param('duration',boundary==='max_value'?5:0.3);synth.set_param('masterVolume',1);cases.push({...synth.params});
                }
            }
            cases.push({...synth.default_params(),duration:NaN,seed:NaN});
            const finish=SoundDSP.finish,results=[];
            SoundDSP.finish=(pcm,volume)=>{results.push({rawFinite:pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<10)});return finish.call(SoundDSP,pcm,volume);};
            for(const p of cases){const pcm=${name}_DSP.render(p);Object.assign(results.at(-1),{pcm});}
            SoundDSP.finish=finish;
            return {results,mute:${name}_DSP.render({...synth.default_params(),masterVolume:0})};
        })()`);
        for (const {pcm, rawFinite} of results.results) {
            assert.ok(rawFinite, 'feedback and filters remain stable before conditioning');
            assert.ok(pcm.every(value=>Number.isFinite(value)&&Math.abs(value)<1));
            assert.equal(Math.abs(pcm[0]), 0); assert.equal(Math.abs(pcm.at(-1)), 0);
        }
        assert.ok(results.mute.every(value=>value===0));
    });
}

test('full legacy snapshots restore default sources while partial updates and locks retain choices', () => {
    const {run} = setup();
    for (const [name, key, selected] of [['Breathr','source',2],['Pluckr','material',4]]) {
        const result = plain(run(`(() => {
            const synth=new ${name}(),legacy={...synth.params};delete legacy.${key};
            synth.set_param('${key}',${selected});synth.apply_params({seed:0.71});const partial=synth.params.${key};
            synth.apply_params(legacy);const restored=synth.params.${key};
            const reference=${name}_DSP.render(legacy),pcm=${name}_DSP.render(synth.params);
            synth.set_param('${key}',${selected});synth.set_locked_param('${key}',true);synth.apply_params(legacy,true);
            return {partial,restored,locked:synth.params.${key},exact:reference.every((v,i)=>v===pcm[i])};
        })()`));
        assert.equal(result.partial, selected, 'partial changes preserve the selected source');
        assert.equal(result.restored, 0, 'full legacy saves restore the default source');
        assert.equal(result.locked, selected, 'locked imports preserve the selected source');
        assert.ok(result.exact, 'legacy import renders just like its missing-mode default');
    }
});
