const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup(name) {
    const api = createContext([name]);
    api.run(`var s=new ${name}(); Math.random=SoundDSP.rng(0.284);
        var finish=SoundDSP.finish;
        SoundDSP.finish=function(pcm,...args){
            if(!pcm.every(Number.isFinite)) throw new Error('nonfinite raw PCM');
            return finish.call(this,pcm,...args);
};`);
    return api;
}
function energy(pcm, from=0, to=pcm.length) {
    let sum=0; for(let i=from;i<to;i++) sum+=pcm[i]*pcm[i]; return sum;
}
function distance(a,b) {
    let aa=0,bb=0,ab=0;
    for(let i=0;i<a.length;i++){aa+=a[i]*a[i];bb+=b[i]*b[i];ab+=a[i]*b[i];}
    return 1-Math.abs(ab/Math.sqrt(aa*bb));
}
function centroid(a) {
    let sum=0,weighted=0;
    for(let i=0;i<a.length;i++){sum+=a[i]*a[i];weighted+=a[i]*a[i]*i/a.length;}
    return weighted/sum;
}

test('Fractr fracture control adds a concentrated structural break before scattered pieces',()=>{
    const {run}=setup('Fractr');
    for(const material of [0,1,3,5,6]){
        const [soft,hard]=run(`[0,1].map(fracture=>Fractr_DSP.render({...s.params,
            material:${material},duration:1.5,fragments:3,spread:1,bounce:0,stress:0,fracture,seed:0.18}))`);
        assert.ok(energy(hard,300,1800)>energy(soft,300,1800)*2,`material ${material} has a structural crack`);
    }
});

test('Boomr explosion mechanisms change the event itself at otherwise identical settings',()=>{
    const {run}=setup('Boomr');
    const sounds=run(`Array.from({length:6},(_,mechanism)=>Boomr_DSP.render({...s.params,
        mechanism,duration:2,debris:0,space:0,seed:0.19}))`);
    for(let i=0;i<sounds.length;i++) for(let j=0;j<i;j++)
        assert.ok(distance(sounds[i],sounds[j])>0.15,`mechanisms ${i}/${j} are distinct`);
    assert.ok(centroid(sounds[4])>centroid(sounds[0])*1.8,'collapse has successive structural failures');
    assert.ok(centroid(sounds[1])>centroid(sounds[5])*1.8,'fuel bloom persists beyond a tiny pop');
});

test('Boomr space produces an actual later pressure field',()=>{
    const {run}=setup('Boomr');
    const [dry,space]=run(`[0,1].map(space=>Boomr_DSP.render({...s.params,
        duration:2,pressure:1,blast:0,debris:0,gas:0,aftershock:0,tail:0,space,seed:0.3}))`);
    assert.ok(energy(space,18000)>energy(dry,18000)*3,'reflections extend pressure into the tail');
});

test('new engines sanitize raw imports, reproduce every recipe and retain finite output at extremes',()=>{
    for(const name of ['Fractr','Boomr']){
        const {run}=setup(name);
        for(const recipe of plain(run('s.recipes'))){
            const a=run(`s.generate_recipe('${recipe.id}');${name}_DSP.render(s.params)`);
            assert.deepEqual(a,run(`${name}_DSP.render(s.params)`));
            assert.ok(energy(a)>0.01,recipe.id);
        }
        const controls=plain(run('s.param_info.map(raw=>s.get_param_normalized(raw))'));
        for(const control of controls) for(const invalid of ['NaN','Infinity','-Infinity']){
            assert.ok(run(`${name}_DSP.render({...s.params,${control.name}:${invalid}}).every(Number.isFinite)`));
        }
        run(`s.reset_params();Math.random=()=>{throw new Error('unseeded DSP');};`);
        const kinds=name==='Boomr'?6:7;
        for(let kind=0;kind<kinds;kind++) for(const edge of ['min_value','max_value']){
            const pcm=run(`s.reset_params();s.param_info.forEach(raw=>{const p=s.get_param_normalized(raw);
                if(p.type==='RANGE')s.set_param(p.name,p.${edge});});
                s.set_param('masterVolume',1);${name}_DSP.render({...s.params,
                    ${name==='Boomr'?'mechanism':'material'}:${kind}})`);
            assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<=0.951));
            assert.equal(Math.abs(pcm[0]),0);assert.equal(Math.abs(pcm.at(-1)),0);
        }
    }
});

for(const [name,added] of Object.entries({Fractr:['stress','fracture'],Boomr:['mechanism','space']})) {
    test(name+' complete legacy presets restore missing defaults regardless of the selected sound',()=>{
        const {run}=setup(name);
        const [expected,loaded]=plain(run(`(()=>{
            s.generate_recipe(s.recipes[1].id);
            const old={...s.params},added=${JSON.stringify(added)};
            for(const key of added)delete old[key];
            const expected={...s.default_params(),...old};
            for(const key of added)s.set_param(key,1);
            s.apply_params(old);
            return [expected,s.params];
        })()`));
        assert.deepEqual(loaded,expected);
        const [before,afterPartial,afterLocked,afterNew]=plain(run(`(()=>{
            const added=${JSON.stringify(added)};
            for(const key of added)s.set_param(key,1);
            const before={...s.params};s.apply_params({duration:0.6});
            const afterPartial={...s.params},old={...s.params};
            for(const key of added){delete old[key];s.set_locked_param(key,true);}
            s.apply_params(old,true);const afterLocked={...s.params};
            for(const key of added)s.set_locked_param(key,false);
            const modern={...old,[added[0]]:${name==='Boomr'?4:0.8}};s.apply_params(modern);
            return [before,afterPartial,afterLocked,s.params];
        })()`));
        for(const key of added){
            assert.equal(afterPartial[key],before[key],'partial edits preserve '+key);
            assert.equal(afterLocked[key],before[key],'locked legacy imports preserve '+key);
        }
        assert.equal(afterNew[added[0]],name==='Boomr'?4:0.8,'present new field survives migration');
        assert.equal(afterNew[added[1]],plain(run('s.default_params()'))[added[1]],'other missing new field resets');
    });
}
