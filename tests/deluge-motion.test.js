const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const names=['Whooshr','Bouncr','Rollr'];
function setup(name){const api=createContext([name]);api.run(`var s=new ${name}();Math.random=SoundDSP.rng(0.319);`);return api;}
function rms(pcm){return Math.sqrt(pcm.reduce((n,v)=>n+v*v,0)/pcm.length);}
function safe(pcm,duration){assert.equal(pcm.length,Math.round(duration*44100));assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.ok(pcm[0]===0&&pcm.at(-1)===0);assert.ok(rms(pcm)>0.0005);}
for(const name of names){
 test(name+' has eight fresh, audible, repeatable preset categories',()=>{
  const {run}=setup(name), recipes=plain(run('s.recipes'));assert.equal(recipes.length,{Whooshr:12,Bouncr:12,Rollr:8}[name]);
  for(const recipe of recipes){
   const a=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
   const b=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
   assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3,recipe.id);assert.notEqual(a.seed,b.seed);
   const pcm=run('s.generate_sound();s.sound.getBuffer().slice()');safe(pcm,b.duration);
   assert.deepEqual(pcm,run('s.generate_sound();s.sound.getBuffer()'));
   assert.notDeepEqual(pcm,run('s.set_param("seed",0.71);s.generate_sound();s.sound.getBuffer()'));
  }
 });
 test(name+' preserves locks and volume and safely renders limits',()=>{
  const {run}=setup(name);
  assert.equal(run(`s.set_param('masterVolume',0.23);s.recipes.forEach(r=>s.generate_recipe(r.id));s.params.masterVolume`),0.23);
  assert.equal(run(`Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));var before=JSON.stringify(s.params);s.recipes.forEach(r=>s.generate_recipe(r.id));s.randomize_params();s.mutate_params();before===JSON.stringify(s.params)`),true);
  for(const edge of [0,1]){
   const p=plain(run(`s=new ${name}();s.param_info.forEach(info=>{const n=s.get_param_normalized(info);s.set_param(n.name,${edge}?n.max_value:n.min_value)});s.set_param('masterVolume',1);if(s.name==='Whooshr')s.set_param('air',1);s.params`));
   safe(run(`${name}_DSP.render(s.params)`),p.duration);
  }
  assert.ok(run(`s.set_param('masterVolume',0);${name}_DSP.render(s.params).every(v=>v===0)`));
  const pcm=run(`${name}_DSP.render({duration:Infinity,seed:NaN,masterVolume:1})`);assert.ok(pcm.length<=5*44100&&pcm.every(Number.isFinite));
 });
}
test('whoosh flyby falls in pitch after passing the listener',()=>{
 const {run}=setup('Whooshr');const pcm=run(`s.apply_params({duration:2,air:0,whistle:1,movement:1,flutter:0,focus:0.25,size:0.5});Whooshr_DSP.render(s.params)`);
 function crossings(start,end){let n=0;for(let i=Math.round(start*44100)+1;i<end*44100;i++)if(pcm[i-1]*pcm[i]<0)n++;return n;}
 assert.ok(crossings(0.3,0.7)>crossings(1.3,1.7)*1.4);
});
test('bounce flight times shrink and increased gravity shortens the bounce sequence',()=>{
 const {run}=setup('Bouncr');
 function hits(pcm){const bins=[];for(let i=0;i<pcm.length;i+=220)bins.push(rms(pcm.slice(i,i+220)));const peaks=[];for(let i=1;i<bins.length-1;i++)if(bins[i]>0.035&&bins[i]>bins[i-1]&&bins[i]>=bins[i+1]&&(!peaks.length||i-peaks.at(-1)>7))peaks.push(i);return peaks;}
 const [a,b]=run(`s.apply_params({duration:3,count:5,bounce:0.8,material:1,hardness:1,spin:0,gravity:0,masterVolume:1});var a=Bouncr_DSP.render(s.params);s.set_param('gravity',1);[a,Bouncr_DSP.render(s.params)]`);
 const slow=hits(a),fast=hits(b);assert.ok(slow.length>=4,slow);assert.ok(fast.length>=4,fast);assert.ok(slow[2]-slow[1]<slow[1]-slow[0]);assert.ok(fast.at(-1)<slow.at(-1)*0.75);
});
test('rolling speed raises contact repetition and wheel counts normalize without breaking locks',()=>{
 const {run}=setup('Rollr');
 function peaks(pcm){let count=0,last=-10;const bins=[];for(let i=0;i<pcm.length;i+=220)bins.push(rms(pcm.slice(i,i+220)));for(let i=1;i<bins.length-1;i++)if(bins[i]>0.012&&bins[i]>bins[i-1]&&bins[i]>bins[i+1]&&i-last>3){count++;last=i;}return count;}
 const [a,b]=run(`s.apply_params({duration:2,wheels:1,roughness:0,hardness:1,speed:0,slowing:0,material:0,masterVolume:1});var a=Rollr_DSP.render(s.params);s.set_param('speed',1);[a,Rollr_DSP.render(s.params)]`);
 assert.ok(peaks(b)>peaks(a)*1.5,[peaks(a),peaks(b)]);
 assert.equal(run(`s.set_param('wheels',3.7);s.params.wheels`),4);
 assert.equal(run(`s.set_locked_param('wheels',true);s.set_param('wheels',1.2,true);s.params.wheels`),4);
 const bounce=setup('Bouncr');assert.equal(bounce.run(`s.set_param('count',4.8);s.params.count`),5);
});

test('whoosh source levels can be independently silenced',()=>{
 const {run}=setup('Whooshr');assert.ok(run(`s.apply_params({air:0,whistle:0});Whooshr_DSP.render(s.params).every(v=>v===0)`));
});
test('all motion controls alter the rendered sound at a fixed seed',()=>{
 const controls={Whooshr:['size','air','whistle','focus','flutter'],Bouncr:['count','bounce','size','hardness','spin'],Rollr:['wheels','roughness','size','hardness','slowing']};
 for(const [name,keys] of Object.entries(controls)){
  const {run}=setup(name);
  for(const key of keys){
   const [a,b]=run(`s.reset_params();s.set_param('duration',1);s.set_param('${key}',s.param_min('${key}'));var a=${name}_DSP.render(s.params);s.set_param('${key}',s.param_max('${key}'));[a,${name}_DSP.render(s.params)]`);
   assert.notDeepEqual(a,b,name+' '+key);
  }
 }
});
