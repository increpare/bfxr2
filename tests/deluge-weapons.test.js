const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const names=['Boomr','Pewpr','Zappr'];
function setup(name){const api=createContext([name]);api.run(`var s=new ${name}();Math.random=SoundDSP.rng(0.31827);`);return api;}
function rms(pcm){return Math.sqrt(pcm.reduce((sum,v)=>sum+v*v,0)/pcm.length);}
function safe(pcm,duration,audible=true){assert.equal(pcm.length,Math.round(duration*44100));assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.equal(Math.abs(pcm[0]),0);assert.equal(Math.abs(pcm.at(-1)),0);if(audible)assert.ok(rms(pcm)>0.001);}
for(const name of names){
 test(`${name}: preset categories produce fresh multi-control variations and repeatable audio`,()=>{
  const {run}=setup(name),recipes=plain(run('s.recipes'));assert.equal(recipes.length,name==='Boomr'?11:8);const signatures=new Set();
  for(const recipe of recipes){
   const a=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
   const b=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
   assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3,recipe.name);assert.notEqual(a.seed,b.seed);
   const pcm=run('s.generate_sound();s.sound.getBuffer().slice()');safe(pcm,b.duration);
   assert.deepEqual(pcm,run('s.generate_sound();s.sound.getBuffer()'));
   signatures.add(pcm.length+':'+rms(pcm));assert.equal(b.masterVolume,0.5);
  }
  assert.equal(signatures.size,recipes.length);
 });
 test(`${name}: category generation, randomize and mutate preserve every lock`,()=>{
  const {run}=setup(name);assert.equal(run(`s.generate_recipe(s.recipes[0].id);Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));var before=JSON.stringify(s.params);s.recipes.forEach(r=>s.generate_recipe(r.id));s.randomize_params();s.mutate_params();before===JSON.stringify(s.params)`),true);
 });
 test(`${name}: minimum, maximum and invalid imported controls remain bounded and mute works`,()=>{
  const {run}=setup(name);
  for(const edge of ['min_value','max_value']){
   const [pcm,duration]=run(`s.reset_params();s.param_info.forEach(info=>{var p=s.get_param_normalized(info);if(p.type==='RANGE'&&p.name!=='masterVolume')s.set_param(p.name,p.${edge});});s.set_param('masterVolume',1);[${name}_DSP.render(s.params),s.params.duration]`);safe(pcm,duration,name!=='Boomr'||edge!=='min_value');
  }
  assert.equal(run(`s.param_info.forEach(info=>s.set_param(s.get_param_normalized(info).name,NaN));Object.values(s.params).every(Number.isFinite)`),true);
  assert.ok(run(`s.set_param('masterVolume',0);${name}_DSP.render(s.params).every(v=>v===0)`));
 });
}
test('integer weapon shots and electrical arcs normalize imports without changing locked values',()=>{
 for(const [name,control] of [['Pewpr','shots'],['Zappr','arcs']]){
  const {run}=setup(name);assert.equal(run(`s.set_param('${control}',3.6);s.params.${control}`),4);
  assert.equal(run(`s.set_locked_param('${control}',true);s.set_param('${control}',7.7,true);s.params.${control}`),4);
  assert.ok(run(`s.set_locked_param('${control}',false);s.set_param('${control}',NaN);Number.isInteger(s.params.${control})`));
 }
});
test('explosion muffling removes high-frequency blast energy',()=>{
 const {run}=setup('Boomr');const [a,b]=run(`s.apply_params({duration:1,pressure:0,debris:0,blast:1,tail:0.3,muffle:0});var a=Boomr_DSP.render(s.params);s.set_param('muffle',1);[a,Boomr_DSP.render(s.params)]`);
 function roughness(pcm){let energy=0,diff=0;for(let i=1;i<pcm.length;i++){energy+=pcm[i]*pcm[i];diff+=(pcm[i]-pcm[i-1])**2;}return diff/energy;}
 assert.ok(roughness(b)<roughness(a)*0.3);
});
test('weapon charging postpones the loud firing stage',()=>{
 const {run}=setup('Pewpr');const [a,b]=run(`s.apply_params({duration:1,shots:1,punch:1,body:0.75,grit:0,recoil:0,charge:0});var a=Pewpr_DSP.render(s.params);s.set_param('charge',0.9);[a,Pewpr_DSP.render(s.params)]`);
 function peakWindow(pcm){let peak=0,index=0;for(let i=0;i<pcm.length-441;i+=441){const energy=rms(pcm.slice(i,i+441));if(energy>peak){peak=energy;index=i;}}return index/44100;}
 assert.ok(peakWindow(b)>peakWindow(a)+0.25);
});
test('more electrical arcs fill more separate moments with sparks',()=>{
 const {run}=setup('Zappr');const [a,b]=run(`s.apply_params({duration:2,arcs:1,branching:0,crackle:0,hum:0,spark:1,spread:1,decay:0});var a=Zappr_DSP.render(s.params);s.set_param('arcs',20);[a,Zappr_DSP.render(s.params)]`);
 function active(pcm){let count=0;for(let i=0;i<pcm.length-441;i+=441)if(rms(pcm.slice(i,i+441))>0.008)count++;return count;}
 assert.ok(active(b)>active(a)*3);
});
