const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){const api=createContext(['Tickr']);api.run('var s=new Tickr(); Math.random=SoundDSP.rng(0.284);');return api;}
function rms(pcm){return Math.sqrt(pcm.reduce((sum,v)=>sum+v*v,0)/pcm.length);}
function check(pcm){assert.ok(pcm.length>=Math.round(0.15*44100)&&pcm.length<=5*44100);assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.ok(pcm[0]===0&&pcm.at(-1)===0);assert.ok(rms(pcm)>0.0015);}
function onsets(pcm){const values=[];let quiet=true;for(let i=0;i<pcm.length;i+=220){const level=rms(pcm.slice(i,i+220));if(level>0.015&&quiet){values.push(i/44100);quiet=false;}if(level<0.002)quiet=true;}return values;}
test('progress renders repeat exactly and counters retain whole values',()=>{
 const {run}=setup();const a=run('s.generate_count_coins();s.generate_sound();s.sound.getBuffer().slice()');check(a);
 assert.deepEqual(a,run('s.generate_sound();s.sound.getBuffer()'));
 assert.notDeepEqual(a,run('s.set_param("seed",0.84);s.generate_sound();s.sound.getBuffer()'));
 assert.equal(run('s.set_param("count",7.8);s.params.count'),8);
 assert.equal(run('s.set_param("count",999);s.params.count'),48);
});
test('eight progress categories have fresh audible multi-control variations',()=>{
 const {run}=setup();const recipes=plain(run('s.recipes'));assert.equal(recipes.length,8);
 const signatures=new Set();
 for(const recipe of recipes){
  const a=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
  const b=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
  assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3,recipe.id);
  const pcm=run('s.generate_sound();s.sound.getBuffer()');check(pcm);signatures.add(pcm.length+':'+rms(pcm));
 }
 assert.equal(signatures.size,8);
});
test('acceleration moves audible tick intervals from slow to fast and back',()=>{
 const {run}=setup();
 for(const direction of [-1,0,1]){
  const pcm=run(`s.apply_params({kind:2,count:6,duration:3,decay:0,brightness:0.5,jitter:0,finish:0,acceleration:${direction}});Tickr_DSP.render(s.params)`);
  const times=onsets(pcm);assert.equal(times.length,6,JSON.stringify(times));
  const first=times[1]-times[0],last=times.at(-1)-times.at(-2);
  if(direction>0)assert.ok(first>last*2,JSON.stringify(times));
  else if(direction<0)assert.ok(last>first*2,JSON.stringify(times));
  else assert.ok(Math.abs(first-last)<0.015,JSON.stringify(times));
 }
});
test('completion is a separate audible endpoint after the counter',()=>{
 const {run}=setup();const [a,b]=run(`s.apply_params({duration:1,count:8,kind:2,decay:0.1,finish:0,jitter:0});var a=Tickr_DSP.render(s.params);s.set_param('finish',1);[a,Tickr_DSP.render(s.params)];`);
 // Whole-buffer DC removal can shift earlier samples by a tiny constant.
 assert.ok(a.slice(500,30000).every((v,i)=>Math.abs(v-b[i+500])<0.00001));
 assert.ok(rms(b.slice(37000))>rms(a.slice(37000))*4);
});
test('pitch rise changes the pitch of the last tick without changing tick timing',()=>{
 const {run}=setup();const pcm=run(`s.apply_params({kind:2,count:5,duration:2,decay:0.1,jitter:0,finish:0,rise:1,acceleration:0,brightness:0});Tickr_DSP.render(s.params);`);
 const times=onsets(pcm);assert.equal(times.length,5);
 function crossings(time){const begin=Math.round((time+0.01)*44100),end=begin+441;let count=0;for(let i=begin+1;i<end;i++)if(pcm[i]*pcm[i-1]<0)count++;return count;}
 assert.ok(crossings(times.at(-1))>crossings(times[0])*2);
});
test('short and long counters, timbres and silence remain safe and locks persist',()=>{
 const {run}=setup();
 for(let kind=0;kind<5;kind++)for(const count of [1,48])check(run(`s.apply_params({kind:${kind},count:${count},duration:0.15,finish:1,decay:1,pitch:1,rise:1,acceleration:1,jitter:1,brightness:1});Tickr_DSP.render(s.params)`));
 check(run('s.set_param("duration",5);Tickr_DSP.render(s.params)'));
 assert.ok(run('s.set_param("masterVolume",0);Tickr_DSP.render(s.params).every(v=>v===0)'));
 assert.equal(run(`Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));var before=JSON.stringify(s.params);s.recipes.forEach(r=>s.generate_recipe(r.id));s.randomize_params();s.mutate_params();before===JSON.stringify(s.params)`),true);
});
