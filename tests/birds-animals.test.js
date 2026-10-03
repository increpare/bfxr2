const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, plain} = require('./helpers/synth-context');
const energy = pcm => pcm.reduce((sum, v) => sum + v*v, 0);
const rms = pcm => Math.sqrt(energy(pcm)/pcm.length);
function runs(pcm) {
    const levels = [];
    for (let i=0;i+220<pcm.length;i+=220) levels.push(rms(pcm.slice(i,i+220)));
    const threshold=Math.max(...levels)*0.18;
    return levels.filter((v,i)=>v>threshold&&(!i||levels[i-1]<=threshold)).length;
}

test('Crittr randomization favors short calls and preserves locked longer sounds', () => {
    const {run}=createContext(['Crittr']);
    const result=plain(run(`(() => {
        Math.random=SoundDSP.rng(0.381);const s=new Crittr(),durations=[],voices=[];
        for(let i=0;i<180;i++){s.randomize_params();durations.push(s.params.duration);voices.push(s.params.voice);}
        s.set_param('duration',4);s.set_param('calls',7);s.set_param('voice',7);
        s.set_locked_param('duration',true);s.set_locked_param('calls',true);s.set_locked_param('voice',true);
        s.randomize_params();return {durations,voices,locked:s.params};
    })()`));
    assert.ok(result.durations.every(v=>v>=0.15&&v<=1.5),'random calls fit within 1.5 seconds');
    assert.ok(result.voices.includes(6)&&result.voices.includes(7),'randomizer includes dogs and cats');
    assert.equal(result.locked.duration,4);assert.equal(result.locked.calls,7);assert.equal(result.locked.voice,7);
});

test('Crittr adds fresh woof and meow families while legacy voices keep exact PCM',()=>{
    const {run}=createContext(['Crittr']);
    const result=run(`(() => {const s=new Crittr();Math.random=SoundDSP.rng(0.341);
        return ['woof','meow'].map(id=>{const found=s.recipes.some(r=>r.id===id);s.generate_recipe(id);
            const first={...s.params},pcm=Crittr_DSP.render(first);s.generate_recipe(id);
            return {id,found,first,second:{...s.params},pcm,replay:Crittr_DSP.render(JSON.parse(JSON.stringify(first)))};});})()`);
    for(const r of result){assert.ok(r.found,r.id+' recipe exists');assert.equal(r.first.voice,r.id==='woof'?6:7);
        assert.ok(Object.keys(r.first).filter(k=>k!=='seed'&&r.first[k]!==r.second[k]).length>=3);
        assert.ok(rms(r.pcm)>0.004);assert.deepEqual(r.pcm,r.replay);}
    const hashes=['e1e438db86bd634572fcd3028b36f566a056652db8ee140f01bfd0d10569f138','9043f2ccfb410416db407a0280a74f3f3b6715ea268be18a69bb59822d687178','b31f91cf21cf9f84eb5f5ec0bb0a9604ff9459a55cffd4ad03adfd41eb19be4c','d4a6df23cc6fbf9a6d29ef6b3e595c192c4f429c3aed141017f0c5702dd0362a','0cda822bd2ef57de43eed0367f17785ecbad302a8bb9f9161b61685763e8e6f1','a7436b4f64df76bfc3970520e56e4c72b2f0bf9ba79ee9bcd89ae9c8adb18fcb'];
    for(let voice=0;voice<6;voice++){const pcm=run(`Crittr_DSP.render({...new Crittr().params,voice:${voice},seed:0.327,duration:0.3})`);
        assert.equal(crypto.createHash('sha256').update(Buffer.from(pcm.buffer)).digest('hex'),hashes[voice]);}
});

test('dog barks have explosive attacks and cat vowels evolve through a voiced call',()=>{
    const {run}=createContext(['Crittr']);
    const [dog,cat,still]=run(`[Crittr_DSP.render({voice:6,duration:0.65,calls:1,gap:0.1,pitch:0.3,breath:0.2,seed:0.41}),
        Crittr_DSP.render({voice:7,duration:0.65,calls:1,gap:0.1,pitch:0.55,morph:1,seed:0.41}),
        Crittr_DSP.render({voice:7,duration:0.65,calls:1,gap:0.1,pitch:0.55,morph:0,seed:0.41})]`);
    assert.ok(energy(dog.slice(300,5500))>energy(dog.slice(17000,22200))*3,'bark releases quickly');
    assert.notDeepEqual(cat,still,'mouth evolution changes the meow');
    assert.ok(rms(cat.slice(7000,15000))>0.01,'meow has sustained voicing');
});

test('Birdr recipes are short, varied, seeded and preserve every lock',()=>{
    const {run}=createContext(['Birdr']);
    const result=run(`(() => {const s=new Birdr();Math.random=SoundDSP.rng(0.381);
        const recipes=s.recipes.map(r=>{s.generate_recipe(r.id);const first={...s.params};s.generate_recipe(r.id);
            return {id:r.id,first,second:{...s.params},pcm:Birdr_DSP.render(first),replay:Birdr_DSP.render(JSON.parse(JSON.stringify(first)))};});
        Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));const before=JSON.stringify(s.params);
        s.recipes.forEach(r=>s.generate_recipe(r.id));s.randomize_params();s.mutate_params();
        return {recipes,locked:before===JSON.stringify(s.params)};})()`);
    assert.ok(result.recipes.length>=8);assert.ok(result.locked);
    for(const r of result.recipes){assert.ok(r.first.duration<=2,r.id);assert.ok(rms(r.pcm)>0.004,r.id);
        assert.ok(Object.keys(r.first).filter(k=>k!=='seed'&&r.first[k]!==r.second[k]).length>=3,r.id);
        assert.deepEqual(r.pcm,r.replay);}
});

test('bird syllables articulate separate calls and anatomy changes a fixed phrase',()=>{
    const {run}=createContext(['Birdr']);
    const data=run(`(() => {const p={...new Birdr().params,duration:1.2,gap:0.5,trill:0,breath:0,rasp:0,rhythm:0,seed:0.53};
        return {single:Birdr_DSP.render({...p,syllables:1}),many:Birdr_DSP.render({...p,syllables:4}),
            voices:[0,1,2,3,4].map(voice=>Birdr_DSP.render({...p,voice,syllables:2})),
            changed:['sweep','arch','trill','duet','rasp','breath','rhythm','variation'].map(k=>[Birdr_DSP.render({...p,[k]:0}),Birdr_DSP.render({...p,[k]:1})])};})()`);
    assert.equal(runs(data.single),1);assert.equal(runs(data.many),4);
    for(let a=0;a<data.voices.length;a++)for(let b=a+1;b<data.voices.length;b++)assert.notDeepEqual(data.voices[a],data.voices[b]);
    for(const [a,b] of data.changed)assert.notDeepEqual(a,b);
});

for(const name of ['Birdr','Crittr'])test(name+' raw synthesis remains stable for every anatomy and boundary',()=>{
    const {run}=createContext([name]);
    const data=run(`(() => {const s=new ${name}(),results=[],finish=SoundDSP.finish;
        SoundDSP.finish=(pcm,volume)=>{results.push({raw:pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<10)});return finish.call(SoundDSP,pcm,volume);};
        for(const option of s.param_info.find(p=>p.name==='voice').values)for(const edge of ['min_value','max_value']){
            s.param_info.forEach(info=>{const p=s.get_param_normalized(info);if(p.type==='RANGE')s.set_param(p.name,p[edge]);});
            s.set_param('voice',option[2]);s.set_param('masterVolume',1);s.set_param('duration',edge==='max_value'?5:0.3);
            const pcm=${name}_DSP.render(s.params);Object.assign(results.at(-1),{pcm});}
        const invalid=${name}_DSP.render({duration:NaN,seed:Infinity,voice:Infinity,pitch:NaN});Object.assign(results.at(-1),{pcm:invalid});
        SoundDSP.finish=finish;return {results,mute:${name}_DSP.render({masterVolume:0})};})()`);
    for(const r of data.results){assert.ok(r.raw);assert.ok(r.pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.equal(Math.abs(r.pcm[0]),0);assert.equal(Math.abs(r.pcm.at(-1)),0);}
    assert.ok(data.mute.every(v=>v===0));
});


test('Birdr integer edits, short randomization and saved seeds survive all generation paths',()=>{
    const {run}=createContext(['Birdr']);
    const result=plain(run(`(() => {
        const s=new Birdr();Math.random=SoundDSP.rng(0.418);
        const counts=[4.56,4.49,-10,999,NaN].map(value=>{s.apply_params({syllables:value});return s.params.syllables;});
        const generated=[];for(let i=0;i<60;i++){s.randomize_params();generated.push({...s.params});}
        s.set_param('syllables',7);s.set_locked_param('syllables',true);s.randomize_params();s.mutate_params();
        const locked=s.params.syllables;
        Math.random=()=>{throw new Error('audio must use only its saved seed');};
        const a=Birdr_DSP.render(s.params),b=Birdr_DSP.render({...s.params,seed:s.params.seed===0.123?0.456:0.123});
        return {counts,generated,locked,changed:a.some((v,i)=>v!==b[i])};
    })()`));
    assert.deepEqual(result.counts,[5,4,1,16,3]);assert.equal(result.locked,7);assert.ok(result.changed);
    for(const p of result.generated){assert.ok(p.duration<=2);assert.ok(Number.isInteger(p.syllables));}
});
