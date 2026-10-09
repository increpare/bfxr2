const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function rms(pcm) {
    let power = 0;
    for (const sample of pcm) power += sample * sample;
    return Math.sqrt(power / pcm.length);
}
function brightness(pcm) {
    let power = 0, difference = 0;
    for (let i = 1; i < pcm.length; i++) {
        power += pcm[i] ** 2;
        difference += (pcm[i] - pcm[i - 1]) ** 2;
    }
    return difference / power;
}
function correlation(a, b) {
    let ab = 0, aa = 0, bb = 0;
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
        ab += a[i] * b[i]; aa += a[i] ** 2; bb += b[i] ** 2;
    }
    return ab / Math.sqrt(aa * bb);
}
function spectralEnergy(pcm, low, high) {
    const length = 16384, start = 11025;
    let power = 0;
    for (let frequency = low; frequency <= high; frequency += 3) {
        let real = 0, imaginary = 0;
        for (let i = 0; i < length; i++) {
            const sample = pcm[start + i] * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (length - 1)));
            const phase = 2 * Math.PI * frequency * i / 44100;
            real += sample * Math.cos(phase); imaginary += sample * Math.sin(phase);
        }
        power += real * real + imaginary * imaginary;
    }
    return power;
}

test('impact objects and receiving surfaces independently change the collision', () => {
    const {run} = createContext(['Bouncr']);
    assert.equal(run('var s=new Bouncr();s.params.count'), 1, 'default is a single contact');
    assert.ok(run('s.param_info.some(info => info.name === "surface")'));
    const [concrete, metal, fabric, glass] = run(`[0,2,5,3].map(surface => Bouncr_DSP.render({
        ...s.params,duration:1.5,count:1,material:2,surface,size:0.45,hardness:0.8,seed:0.219}))`);
    assert.ok(correlation(concrete, metal) < 0.8, 'receiving material has its own resonances');
    assert.ok(brightness(concrete) > brightness(fabric) * 2, 'fabric absorbs the bright contact');
    assert.ok(correlation(glass, metal) < 0.8);
    const [rubber, wood] = run(`[0,1].map(material => Bouncr_DSP.render({
        ...s.params,duration:1.5,count:1,material,surface:2,seed:0.219}))`);
    assert.ok(correlation(rubber, wood) < 0.8, 'projectile identity survives a fixed target');
});

test('impact mass lowers the body, force changes contact and tail sets ringing length', () => {
    const {run} = createContext(['Bouncr']);
    run('var s=new Bouncr();s.apply_params({duration:2,count:1,material:2,surface:2,hardness:0.75,seed:0.219})');
    const [small, large, gentle, forceful, damped, ringing] = run(`[
        {size:0},{size:1},{force:0.1},{force:1},{tail:0},{tail:1}
    ].map(change => Bouncr_DSP.render({...s.params,...change}))`);
    assert.ok(brightness(small) > brightness(large) * 1.5);
    assert.ok(rms(forceful) > rms(gentle) * 1.3);
    assert.ok(correlation(gentle, forceful) < 0.98, 'force must affect contact shape as well as gain');
    assert.ok(rms(ringing.slice(11025,44100)) > rms(damped.slice(11025,44100)) * 3);
});

test('glitch families select distinct buffer, codec, scrub, crush, data and grain mechanisms', () => {
    const {run} = createContext(['Glitchr']);
    assert.equal(run('var s=new Glitchr();s.param_info.find(info=>info.name==="mode")?.values.length'), 8);
    const buffers = run(`Array.from({length:8},(_,mode)=>Glitchr_DSP.render({...s.params,
        mode,duration:1.4,dropout:0,seed:0.217}))`);
    for (let a = 0; a < buffers.length; a++) {
        assert.ok(rms(buffers[a]) > 0.01, 'mode ' + a + ' is audible');
        for (let b = a + 1; b < buffers.length; b++) {
            assert.ok(Math.abs(correlation(buffers[a],buffers[b])) < 0.85, a + ' differs from ' + b);
        }
    }
    assert.ok(Math.max(...buffers.map(brightness)) > Math.min(...buffers.map(brightness)) * 4,
        'different mechanisms have different spectral textures');
});

for (const name of ['Bouncr','Glitchr']) {
    test(name + ' preserves saved seeds, varies recipes and resets added controls on full legacy imports', () => {
        const {run} = createContext([name]);
        run(`var s=new ${name}();Math.random=SoundDSP.rng(0.718)`);
        const extras = {Bouncr:['surface','force','tail'],Glitchr:['mode']}[name];
        const legacy = plain(run(`(() => {
            const old={...s.params}; for(const key of ${JSON.stringify(extras)})delete old[key];
            for(const key of ${JSON.stringify(extras)})s.set_param(key,s.param_max(key));
            s.apply_params(old);return {current:s.params,defaults:s.default_params()};
        })()`));
        for (const key of extras) assert.equal(legacy.current[key],legacy.defaults[key], key);
        for (const recipe of plain(run('s.recipes'))) {
            const [first, second, pcm, replay] = run(`(() => {
                s.generate_recipe('${recipe.id}');const first={...s.params};
                s.generate_recipe('${recipe.id}');const second={...s.params};
                const savedRandom=Math.random;Math.random=()=>{throw new Error('unseeded DSP');};
                try {return [first,second,${name}_DSP.render(first),${name}_DSP.render(JSON.parse(JSON.stringify(first)))];}
                finally {Math.random=savedRandom;}
            })()`);
            assert.ok(Object.keys(first).filter(key=>key!=='seed'&&first[key]!==second[key]).length >= 3);
            assert.deepEqual(pcm,replay,recipe.id);
            assert.ok(rms(pcm) > 0.0015,recipe.id);
        }
    });

    test(name + ' raw and finished PCM stay finite through selector combinations and limits', () => {
        const {run} = createContext([name]);
        run(`var s=new ${name}(),finish=SoundDSP.finish;
            SoundDSP.finish=(pcm,volume)=>{if(!pcm.every(Number.isFinite))throw new Error('nonfinite raw PCM');
                return finish.call(SoundDSP,pcm,volume);}`);
        const variants = run(`(() => {
            const variants=[],selectors=s.param_info.filter(info=>info.type==='BUTTONSELECT');
            for(const high of [false,true]) {
                s.reset_params();
                for(const raw of s.param_info) {const info=s.get_param_normalized(raw);
                    if(info.type==='RANGE')s.set_param(info.name,high?info.max_value:info.min_value);}
                s.set_param('masterVolume',1);s.set_param('duration',0.35);
                const add=(index,params)=>{if(index===selectors.length){variants.push(params);return;}
                    for(const value of selectors[index].values)add(index+1,{...params,[selectors[index].name]:value[2]});};
                add(0,{...s.params});
            }
            variants.push({duration:Infinity,material:NaN,surface:Infinity,mode:NaN,depth:NaN,seed:NaN});
            return variants.map(params=>({pcm:${name}_DSP.render(params),mute:${name}_DSP.render({...params,masterVolume:0})}));
        })()`);
        for (const {pcm,mute} of variants) {
            assert.ok(pcm.every(sample=>Number.isFinite(sample)&&Math.abs(sample)<=0.951));
            assert.ok(pcm[0]===0&&pcm.at(-1)===0);
            assert.ok(mute.every(sample=>sample===0));
        }
    });
}
