const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){const api=createContext(['Swarmr']);api.run('var s=new Swarmr();Math.random=SoundDSP.rng(0.314159);');return api;}
function rms(pcm){return Math.sqrt(pcm.reduce((sum,v)=>sum+v*v,0)/pcm.length);}
function safe(pcm){assert.ok(pcm.length>=0.25*44100&&pcm.length<=5*44100);assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.ok(pcm[0]===0);assert.ok(pcm.at(-1)===0);assert.ok(rms(pcm)>0.002);}
test('swarm snapshots render identical finite audio and retain their stored variation',()=>{
 const {run}=setup();const a=run('s.generate_nanobots();s.generate_sound();s.sound.getBuffer().slice()');
 safe(a);assert.deepEqual(a,run('s.generate_sound();s.sound.getBuffer()'));
 assert.notDeepEqual(a,run('s.set_param("seed",0.17);s.generate_sound();s.sound.getBuffer()'));
});
test('eight swarm categories vary multiple controls and render distinct audible events',()=>{
 const {run}=setup();const recipes=plain(run('s.recipes'));assert.equal(recipes.length,8);
 const signatures=new Set();
 for(const recipe of recipes){
  const a=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
  const b=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
  assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3,recipe.name);
  const pcm=run('s.generate_sound();s.sound.getBuffer()');safe(pcm);
  signatures.add(pcm.length+':'+rms(pcm));
 }
 assert.equal(signatures.size,8);
});
test('cohesion aligns otherwise scattered chirps into collective pulses',()=>{
 const {run}=setup();const buffers=run(`s.apply_params({kind:1,count:32,duration:3,speed:0.5,agitation:0,movement:0,scatter:0,cohesion:0});
 var a=Swarmr_DSP.render(s.params);s.set_param('cohesion',1);[a,Swarmr_DSP.render(s.params)];`);
 function contrast(pcm){let bins=[];for(let i=22050;i<pcm.length-22050;i+=1102)bins.push(rms(pcm.slice(i,i+1102)));const mean=bins.reduce((a,b)=>a+b)/bins.length;return Math.sqrt(bins.reduce((a,b)=>a+(b-mean)**2,0)/bins.length)/mean;}
 assert.ok(contrast(buffers[1])>contrast(buffers[0])*1.5);
});
test('passing motion lowers the pitch as the swarm recedes',()=>{
 const {run}=setup();const pcm=run(`s.apply_params({kind:4,count:3,duration:3,agitation:0,movement:1,scatter:0,cohesion:1,size:0.4});Swarmr_DSP.render(s.params);`);
 function crossings(start,end){let count=0;for(let i=Math.floor(start*pcm.length)+1;i<end*pcm.length;i++)if(pcm[i]*pcm[i-1]<0)count++;return count;}
 assert.ok(crossings(0.15,0.4)>crossings(0.6,0.85)*1.3);
});
test('population, activity, size and scatter change the realized swarm',()=>{
 const {run}=setup();for(const [key,low,high] of [['count',3,32],['speed',0,1],['agitation',0,1],['size',0,1],['scatter',0,1]]){
  const [a,b]=run(`s.reset_params();s.set_param('duration',0.5);s.set_param('${key}',${low});var a=Swarmr_DSP.render(s.params);s.set_param('${key}',${high});[a,Swarmr_DSP.render(s.params)];`);
  assert.notDeepEqual(a,b,key);
 }
});
test('swarm locks, mute and extreme populations behave correctly',()=>{
 const {run}=setup();assert.equal(run(`s.generate_nanobots();Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));var before=JSON.stringify(s.params);
 s.recipes.forEach(r=>s.generate_recipe(r.id));s.randomize_params();s.mutate_params();before===JSON.stringify(s.params);`),true);
 const buffers=run(`s=new Swarmr();[0,1,2,3,4,5].map(kind=>{s.apply_params({kind,count:32,duration:0.3,speed:1,cohesion:1,agitation:1,size:0,movement:1,scatter:1,masterVolume:1});return Swarmr_DSP.render(s.params);});`);
 buffers.forEach(safe);
 safe(run(`s.set_param('duration',5);Swarmr_DSP.render(s.params);`));
 assert.ok(run(`s.set_param('masterVolume',0);Swarmr_DSP.render(s.params).every(v=>v===0);`));
});
test('activity speed affects every agent type',()=>{
 const {run}=setup();for(let kind=0;kind<6;kind++){
  const [a,b]=run(`s.reset_params();s.apply_params({kind:${kind},duration:0.3,count:3,speed:0.1});var a=Swarmr_DSP.render(s.params);s.set_param('speed',0.9);[a,Swarmr_DSP.render(s.params)];`);
  assert.notDeepEqual(a,b,'agent type '+kind);
 }
});
test('short scattered tick swarms still contain audible arrivals at slow speeds',()=>{
 const {run}=setup();
 for(const seed of [0.15,0.5,1]){
  const pcm=run(`s.apply_params({kind:3,duration:0.25,count:3,speed:0,cohesion:1,scatter:1,seed:${seed}});Swarmr_DSP.render(s.params);`);
  safe(pcm);
 }
});
