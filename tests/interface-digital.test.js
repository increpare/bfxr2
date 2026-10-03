const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function context() {
    let result;
    assert.doesNotThrow(() => { result = createContext(['Notifr','Holor']); },
        'notification and holographic gesture engines must load');
    return result;
}
function rms(data) {
    let sum=0;
    for (const value of data) sum+=value*value;
    return Math.sqrt(sum/data.length);
}
function toneEnergy(data, frequency) {
    let real=0,imaginary=0;
    for (let i=0;i<data.length;i++) {
        const weight=Math.sin(Math.PI*i/(data.length-1))**2;
        const phase=2*Math.PI*frequency*i/44100;
        real+=data[i]*weight*Math.cos(phase);
        imaginary+=data[i]*weight*Math.sin(phase);
    }
    return (real*real+imaginary*imaginary)/(data.length*data.length);
}
function activeRuns(data,thresholdFraction=0.13) {
    const levels=[];
    for(let i=0;i<data.length-220;i+=220) levels.push(rms(data.slice(i,i+220)));
    const threshold=Math.max(...levels)*thresholdFraction;
    return levels.reduce((count,level,i)=>count+(level>threshold&&(!i||levels[i-1]<=threshold)),0);
}
function bounded(data) {
    assert.ok(data instanceof Float32Array);
    assert.ok(data[0]===0 && data.at(-1)===0,'tapered edges');
    for(const value of data) assert.ok(Number.isFinite(value)&&Math.abs(value)<=0.951);
}

test('notification and hologram presets vary several controls while retaining locks',()=>{
    const {run}=context();
    const ids={Notifr:['message','quest_update','objective_done','achievement','low_health','warning','denied','connected'],
        Holor:['cursor_trail','radial_menu','map_ping','target_lock','drag_drop','panel_swipe','tooltip','data_reveal']};
    for(const name of Object.keys(ids)) {
        const result=plain(run(`(()=>{
            const synth=new ${name}(); Math.random=SoundDSP.rng(0.57);
            const families=synth.recipes.map(recipe=>{
                synth.generate_recipe(recipe.id); const first={...synth.params};
                synth.generate_recipe(recipe.id);
                return {id:recipe.id,first,second:{...synth.params},varying:Object.entries(recipe.values)
                    .filter(([key,value])=>key!=='seed'&&Array.isArray(value)&&value[0]!==value[1]).length};
            });
            synth.set_param('pitch',0.217); synth.set_param('seed',0.327); synth.set_param('masterVolume',0.43);
            synth.locked_params.pitch=synth.locked_params.seed=true;
            synth.generate_recipe(synth.recipes[0].id); synth.randomize_params(); synth.mutate_params();
            return {families,pitch:synth.params.pitch,seed:synth.params.seed,volume:synth.params.masterVolume,
                lockedVolume:synth.locked_params.masterVolume,templates:synth.templates.map(t=>t[0])};
        })()`));
        assert.deepEqual(result.families.map(f=>f.id),ids[name]);
        for(const family of result.families) {
            assert.ok(family.varying>=3,family.id+' changes at least three controls');
            assert.notEqual(family.first.seed,family.second.seed);
            delete family.first.seed; delete family.second.seed;
            assert.notDeepEqual(family.first,family.second);
        }
        assert.equal(result.pitch,0.217); assert.equal(result.seed,0.327); assert.equal(result.volume,0.43);
        assert.ok(result.lockedVolume);
        assert.ok(result.templates.includes('Randomize')&&result.templates.includes('Mutate'));
    }
});

test('notification pulse counts stay integral through editing, generation, import and locks',()=>{
    const {run}=context();
    const result=plain(run(`(()=>{
        const synth=new Notifr(); Math.random=SoundDSP.rng(0.12);
        const counts=synth.recipes.map(recipe=>{synth.generate_recipe(recipe.id);return synth.params.pulses;});
        synth.randomize_params(); counts.push(synth.params.pulses); synth.mutate_params(); counts.push(synth.params.pulses);
        const imported=[2.7,3.2,-5,100,NaN].map(pulses=>{synth.apply_params({pulses});return synth.params.pulses;});
        synth.set_param('pulses',5); synth.locked_params.pulses=true;
        synth.set_param('pulses',1.8,true); synth.generate_recipe('message'); synth.randomize_params(); synth.mutate_params();
        return {counts,imported,locked:synth.params.pulses,fallback:synth.default_params().pulses};
    })()`));
    assert.ok(result.counts.every(value=>Number.isInteger(value)&&value>=1&&value<=8));
    assert.deepEqual(result.imported,[3,3,1,8,result.fallback]);
    assert.equal(result.locked,5);
});

test('every interface family is audible, seeded, distinct and reproducible after saving',()=>{
    const {run}=context();
    for(const name of ['Notifr','Holor']) {
        const renders=run(`(()=>{
            const synth=new ${name}(); Math.random=SoundDSP.rng(0.761);
            return synth.recipes.map(recipe=>{
                synth.generate_recipe(recipe.id); synth.set_param('duration',0.4);
                const saved=JSON.stringify(synth.params),first=${name}_DSP.render(synth.params);
                const restored=new ${name}(); restored.apply_params(JSON.parse(saved));
                Math.random=()=>{throw Error('render must use saved seed');};
                const second=${name}_DSP.render(restored.params),changed=${name}_DSP.render({...restored.params,seed:0.321});
                Math.random=SoundDSP.rng(0.12+restored.params.seed*0.4);
                return {id:recipe.id,first,second,changed};
            });
        })()`);
        const fingerprints=new Set();
        for(const {id,first,second,changed} of renders) {
            assert.equal(first.length,17640); bounded(first);
            assert.ok(rms(first)>0.008,id+' is audible');
            assert.deepEqual(first,second,id+' restores exactly');
            assert.notDeepEqual(first,changed,id+' responds to seed');
            fingerprints.add(Array.from(first.slice(1200,1240)).join(','));
        }
        assert.equal(fingerprints.size,8);
    }
});

test('notification spacing separates the specified number of tone groups',()=>{
    const {run}=context();
    const [single,many]=run(`(()=>{
        const p={...new Notifr().params,duration:1.2,spacing:0.7,ring:0,echo:0,urgency:0,
            tone:0,interval:0,tension:0,softness:0.7};
        return [1,4].map(pulses=>Notifr_DSP.render({...p,pulses}));
    })()`);
    assert.equal(activeRuns(single),1); assert.equal(activeRuns(many),4);
});

test('notification intervals make overlapping pitched tones, and pitch transposes the root',()=>{
    const {run}=context();
    const [unison,chord,high]=run(`(()=>{
        const p={...new Notifr().params,duration:0.8,tone:0,pitch:0.4,pulses:1,spacing:0,
            urgency:0,softness:1,tension:0,ring:0.8,echo:0};
        return [{interval:0},{interval:7},{interval:0,pitch:0.7}].map(change=>Notifr_DSP.render({...p,...change}));
    })()`);
    const root=110*2**(0.4*4),fifth=root*2**(7/12),upper=110*2**(0.7*4);
    assert.ok(toneEnergy(chord,fifth)>toneEnergy(unison,fifth)*50+0.00002,'a real fifth joins the root');
    assert.ok(toneEnergy(unison,root)>toneEnergy(unison,upper)*100);
    assert.ok(toneEnergy(high,upper)>toneEnergy(high,root)*100);
});

test('notification echo rings after the last direct tone and urgency changes the rhythm',()=>{
    const {run}=context();
    const [dry,echo,calm,urgent]=run(`(()=>{
        const p={...new Notifr().params,duration:0.8,pulses:1,spacing:0.7,ring:0,echo:0,urgency:0};
        return [{},{echo:1},{pulses:5,spacing:0.55},{pulses:5,spacing:0.55,urgency:1}]
            .map(change=>Notifr_DSP.render({...p,...change}));
    })()`);
    assert.ok(rms(echo.slice(13230,17640))>rms(dry.slice(13230,17640))*3+0.001);
    assert.notDeepEqual(calm,urgent,'urgency changes pulse timing and tremolo');
});

test('notification tension adds a dissonant tone, softness removes harmonics, and ring extends decay',()=>{
    const {run}=context();
    const [calm,tense,bright,soft,short,long]=run(`(()=>{
        const p={...new Notifr().params,duration:0.8,pitch:0.4,pulses:1,interval:0,tension:0,
            spacing:0,urgency:0,softness:1,ring:0.7,echo:0,tone:0};
        return [{},{tension:1},{tone:3,softness:0},{tone:3,softness:1},
            {spacing:0.7,ring:0},{spacing:0.7,ring:1}].map(change=>Notifr_DSP.render({...p,...change}));
    })()`);
    const root=110*2**(0.4*4);
    assert.ok(toneEnergy(tense,root*2**0.5)>toneEnergy(calm,root*2**0.5)*20+0.00001);
    assert.ok(toneEnergy(bright,root*3)>toneEnergy(soft,root*3)*8,'softness rounds upper partials');
    assert.ok(rms(long.slice(17640,26460))>rms(short.slice(17640,26460))*20+0.01,'ring sustains the tail');
});

test('holographic sidebands add spectral components around a stable carrier',()=>{
    const {run}=context();
    const [clean,modulated]=run(`(()=>{
        const p={...new Holor().params,duration:0.8,gesture:0,pitch:0.4,sweep:0,scan:0,grain:0,comb:0,bandwidth:0.5};
        return [0,1].map(sidebands=>Holor_DSP.render({...p,sidebands}));
    })()`);
    const base=140*2**(0.4*4.6),offset=43+base*0.317;
    const sideEnergy=data=>toneEnergy(data,base+offset)+toneEnergy(data,Math.abs(base-offset));
    assert.ok(sideEnergy(modulated)>sideEnergy(clean)*30+0.00003,'FM creates measurable sidebands');
});

test('holographic sweep moves pitch while comb and scan independently color the gesture',()=>{
    const {run}=context();
    const [up,down,plain,comb,scan]=run(`(()=>{
        const p={...new Holor().params,duration:0.8,gesture:0,pitch:0.4,sweep:0,sidebands:0,
            grain:0,comb:0,scan:0};
        return [{sweep:0.8},{sweep:-0.8},{},{comb:1},{scan:1}]
            .map(change=>Holor_DSP.render({...p,...change}));
    })()`);
    const crossingRate=data=>{
        let changes=0; for(let i=1;i<data.length;i++) if(data[i]*data[i-1]<0) changes++;
        return changes/data.length;
    };
    const early=data=>crossingRate(data.slice(4410,8820)),late=data=>crossingRate(data.slice(26460,30870));
    assert.ok(late(up)>early(up)*1.5,'positive sweep climbs');
    assert.ok(early(down)>late(down)*1.5,'negative sweep falls');
    assert.notDeepEqual(plain,comb,'comb changes the waveform without a room reverb');
    assert.notDeepEqual(plain,scan,'scan moves the spectral bands');
});

test('holographic grain, bandwidth and gesture modes remain independent audible controls',()=>{
    const {run}=context();
    const renders=run(`(()=>{
        const p={...new Holor().params,duration:0.6,pitch:0.4,sweep:0,sidebands:0,
            grain:0,comb:0,scan:0,gesture:0};
        return [{},{grain:1,bandwidth:0},{grain:1,bandwidth:1},{gesture:1},{gesture:2},{gesture:3}]
            .map(change=>Holor_DSP.render({...p,...change}));
    })()`);
    const [clean,narrow,wide,ping,lock,reveal]=renders;
    assert.notDeepEqual(clean,narrow,'grain adds filtered digital texture');
    assert.notDeepEqual(narrow,wide,'bandwidth reshapes resonant noise');
    assert.ok(rms(ping.slice(17640,22050))<rms(clean.slice(17640,22050))*0.2,'ping decays rapidly');
    assert.ok(rms(reveal.slice(17640,22050))>rms(reveal.slice(2205,6615))*1.3,'reveal assembles toward its end');
    // Lock has a continuous quiet carrier under its eight stronger scanning pulses.
    assert.equal(activeRuns(lock,0.4),8,'lock adds focused scanning pulses');
    assert.equal(activeRuns(clean,0.4),1,'a plain sweep keeps a continuous envelope');
});

test('all interface modes stay safe at extremes, short durations, invalid input and mute',()=>{
    const {run}=context();
    for(const name of ['Notifr','Holor']) {
        const buffers=run(`(()=>{
            const synth=new ${name}(),buffers=[];
            const mode='${name}'==='Notifr'?'tone':'gesture';
            for(let high=0;high<2;high++) for(let kind=0;kind<4;kind++) {
                for(const raw of synth.param_info) {
                    const info=synth.get_param_normalized(raw);
                    if(info.type==='RANGE') synth.set_param(info.name,high?info.max_value:info.min_value);
                }
                synth.set_param(mode,kind); synth.set_param('masterVolume',1); synth.set_param('duration',0.08);
                buffers.push(${name}_DSP.render(synth.params));
            }
            return [...buffers,${name}_DSP.render({...synth.params,duration:-10}),
                ${name}_DSP.render({...synth.params,duration:999}),${name}_DSP.render({...synth.params,duration:NaN}),
                ${name}_DSP.render({...synth.params,masterVolume:0})];
        })()`);
        buffers.forEach(bounded);
        for(const data of buffers.slice(0,9)) assert.equal(data.length,3528);
        assert.equal(buffers[9].length,132300);
        assert.ok(buffers[10].length>=3528&&buffers[10].length<=132300);
        assert.ok(buffers[11].every(value=>value===0));
    }
});
