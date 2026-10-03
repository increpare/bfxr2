const test=require('node:test'),assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const names=['Glitchr','Pulser','Rumblr'];
function rms(a){return Math.sqrt(a.reduce((s,v)=>s+v*v,0)/a.length);}
for(const name of names)test(name+' recipes are fresh, audible, repeatable and locked correctly',()=>{
 const {run}=createContext([name]);run(`var s=new ${name}();Math.random=SoundDSP.rng(0.326);`);
 const recipes=plain(run('s.recipes'));assert.equal(recipes.length,{Glitchr:13,Pulser:8,Rumblr:8}[name]);
 for(const recipe of recipes){
  const a=plain(run(`s.generate_recipe('${recipe.id}');s.params`)),b=plain(run(`s.generate_recipe('${recipe.id}');s.params`));
  assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3);
  const pcm=run(`s.generate_sound();s.sound.getBuffer().slice()`);
  assert.equal(pcm.length,Math.round(b.duration*44100));assert.ok(rms(pcm)>0.0015,recipe.id);
  assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1));assert.ok(pcm[0]===0&&pcm.at(-1)===0);
  assert.deepEqual(pcm,run('s.generate_sound();s.sound.getBuffer()'));
 }
 assert.ok(run(`s.set_param('masterVolume',0);${name}_DSP.render(s.params).every(v=>v===0)`));
 assert.ok(run(`Object.keys(s.params).forEach(k=>s.set_locked_param(k,true));var before=JSON.stringify(s.params);s.randomize_params();s.mutate_params();s.recipes.forEach(r=>s.generate_recipe(r.id));before===JSON.stringify(s.params)`));
});
test('double chamber rhythm adds energy between main beats',()=>{
 const {run}=createContext(['Pulser']);const [a,b]=run(`var s=new Pulser();s.apply_params({duration:2,beats:2,separation:0.5,secondary:0,murmur:0,size:0.2});var a=Pulser_DSP.render(s.params);s.set_param('secondary',1);[a,Pulser_DSP.render(s.params)]`);
 assert.ok(rms(b.slice(11025,19845))>rms(a.slice(11025,19845))*2);
});
test('large rumbling structures move the dominant motion lower',()=>{
 const {run}=createContext(['Rumblr']);const [a,b]=run(`var s=new Rumblr();s.apply_params({duration:2,size:0,roughness:0,dust:0,tremor:0,sweep:0});var a=Rumblr_DSP.render(s.params);s.set_param('size',1);[a,Rumblr_DSP.render(s.params)]`);
 function crossings(p){let n=0;for(let i=1;i<p.length;i++)if(p[i]*p[i-1]<0)n++;return n;}
 assert.ok(crossings(a)>crossings(b)*2);
});
test('digital packet losses reduce energy while crushing changes the texture',()=>{
 const {run}=createContext(['Glitchr']);const [a,b,c]=run(`var s=new Glitchr();s.apply_params({duration:2,dropout:0,fragment:0.2,crush:0,seed:0.4});var a=Glitchr_DSP.render(s.params);s.set_param('dropout',1);var b=Glitchr_DSP.render(s.params);s.apply_params({dropout:0,crush:1});[a,b,Glitchr_DSP.render(s.params)]`);
 assert.ok(rms(b)<rms(a)*0.8);assert.notDeepEqual(a,c);
});
test('short and maximum sounds remain finite under extreme controls',()=>{
 for(const name of names){const {run}=createContext([name]);assert.ok(run(`var s=new ${name}();['min_value','max_value'].every(limit=>{for(const raw of s.param_info){const info=s.get_param_normalized(raw);if(info.type==='RANGE')s.set_param(info.name,info[limit]);}s.set_param('masterVolume',1);const p=${name}_DSP.render(s.params);return p.length<=5*44100&&p.every(v=>Number.isFinite(v)&&Math.abs(v)<1)&&p[0]===0&&p[p.length-1]===0;});`));}
});
