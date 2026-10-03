const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');
function setup(name) {
    const api = createContext([name]);
    api.run(`var synth = new ${name}(); Math.random = SoundDSP.rng(0.381);
        var finish = SoundDSP.finish; SoundDSP.finish = function(pcm, ...args) {
            if (!pcm.every(Number.isFinite)) throw Error('Nonfinite raw samples');
            return finish.call(this, pcm, ...args);
        };`);
    return api;
}
function energy(pcm, from=0, to=pcm.length / 44100) {
    let sum=0; for(let i=Math.round(from*44100);i<Math.min(pcm.length,Math.round(to*44100));i++)sum+=pcm[i]**2;
    return sum;
}
function brightness(pcm) {
    let difference=0; for(let i=1;i<pcm.length;i++)difference+=(pcm[i]-pcm[i-1])**2;
    return Math.sqrt(difference/energy(pcm));
}
test('Fractr offers physical short breaks and hides Pixel while loading its serialized material', () => {
    const {run}=setup('Fractr');
    const recipes=plain(run('synth.recipes'));
    assert.ok(!recipes.some(r=>/pixel/i.test(r.name)));
    assert.ok(run("!synth.get_param_info('material').values.some(v=>v[2]===4)"));
    assert.equal(run('synth.apply_params({material:4});synth.params.material'),4);
    assert.ok(run(`(()=>{for(let i=0;i<80;i++){synth.randomize_params();if(synth.params.material===4)return false;}return true;})()`));
    for(const id of ['bone_scatter','biscuit_crunch','glass_snap','ice_crack']) {
        const pcm=run(`synth.generate_recipe('${id}');Fractr_DSP.render(synth.params)`);
        assert.ok(run('synth.params.duration')<0.9,`${id} is a brief break`);
        assert.ok(energy(pcm)>0.25,`${id} has a substantial snap`);
        assert.ok(energy(pcm,0,0.16)/energy(pcm)>0.68,`${id} leads with a structural failure`);
    }
});
test('Fractr structural material bodies differ and loose shards are independently controllable', () => {
    const {run}=setup('Fractr');
    const sounds=run(`[0,1,6,7].map(material=>Fractr_DSP.render({...synth.params, material,
        duration:0.7,seed:0.38,stress:0.3,fracture:1,shards:0,fragmentSize:0.65,spread:0.5}))`);
    assert.ok(brightness(sounds[0])>brightness(sounds[2])*1.5,'glass has a sharper edge than bone');
    assert.ok(energy(sounds[3],0.06,0.12)>energy(sounds[2],0.06,0.12)*1.4,'biscuit sustains an irregular crunch beyond the bone snap');
    const [dry,scatter]=run(`[0,1].map(shards=>Fractr_DSP.render({...synth.params,material:0,duration:1,
        spread:1,seed:0.4,shards}))`);
    assert.ok(energy(scatter,0.2)>energy(dry,0.2)*10,'shards adds a distinct aftermath');
    assert.ok(run(`[0,1,2,3,4,5,6,7].every(material=>Fractr_DSP.render({...synth.params,material,
        fracture:0,stress:0,shards:0}).every(sample=>sample===0))`),'all material layers can be silenced independently');
});
test('Boomr has independently audible delayed gas and aftershock layers', () => {
    const {run}=setup('Boomr');
    const base=`{...synth.params,duration:2,size:0.8,pressure:0,blast:0,tail:0,debris:0,space:0,gas:0,aftershock:0,seed:0.53}`;
    const [silent,gas,shock]=run(`[{}, {gas:1}, {aftershock:1}].map(change=>Boomr_DSP.render({...${base},...change}))`);
    assert.equal(energy(silent),0);
    assert.ok(energy(gas,0.08,1)>5,'gas persists as audible escaping material');
    assert.ok(energy(shock,0.18,1)>2,'secondary ground fronts occur after the primary blast');
    assert.ok(brightness(gas)>brightness(shock)*1.7,'gas and aftershock occupy different spectral ranges');
});
test('Boomr rubble size moves contact spectrum while mechanisms shape different time envelopes', () => {
    const {run}=setup('Boomr');
    const [grit,rubble]=run(`[0,1].map(rubbleSize=>Boomr_DSP.render({...synth.params,duration:1.8,
        pressure:0,blast:0,tail:0,gas:0,aftershock:0,space:0,debris:1,rubbleSize,seed:0.29}))`);
    assert.ok(brightness(grit)>brightness(rubble)*2,'heavy rubble is much darker than shrapnel');
    const [pop,fuel,depth,collapse,vent]=run(`[5,1,2,4,6].map(mechanism=>Boomr_DSP.render({...synth.params,
        mechanism,duration:2,size:0.65,debris:0,gas:0,aftershock:0,space:0,seed:0.23}))`);
    const late=pcm=>energy(pcm,0.2)/energy(pcm);
    assert.ok(late(fuel)>late(pop)*3,'fuel sustains beyond the dry pop');
    assert.ok(late(collapse)>late(pop)*5,'structural collapse has successive delayed failures');
    assert.ok(brightness(vent)>brightness(depth)*2,'escaping gas differs from water pressure');
});
for(const name of ['Fractr','Boomr'])test(`${name} new controls stay finite, deterministic and locked`,()=>{
    const {run}=setup(name);
    const pcm=run(`synth.generate_recipe(synth.recipes[1].id);${name}_DSP.render(synth.params)`);
    assert.deepEqual(pcm,run(`${name}_DSP.render(synth.params)`));
    assert.ok(run(`(()=>{for(const key of Object.keys(synth.params))synth.set_locked_param(key,true);
        const before=JSON.stringify(synth.params);for(const r of synth.recipes)synth.generate_recipe(r.id);
        synth.randomize_params();synth.mutate_params();return before===JSON.stringify(synth.params)})()`));
    run(`for(const high of [false,true]){synth.reset_params();for(const raw of synth.param_info){const p=synth.get_param_normalized(raw);
        if(p.type==='RANGE')synth.set_param(p.name,high?p.max_value:p.min_value);}synth.set_param('masterVolume',1);
        for(let kind=0;kind<=7;kind++)${name}_DSP.render({...synth.params,${name==='Fractr'?'material':'mechanism'}:kind});}`);
});
