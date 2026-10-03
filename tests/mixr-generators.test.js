const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const setup=()=>createContext(['Clonkr','Jinglr','Transfxr','Stackr','Mixr']);
test('Mixr catalog exposes preset generators without generated files or retired engines',()=>{
 const {run}=setup();
 const list=plain(run('Mixr.generators()'));
 assert.ok(list.some(g=>g.synth==='Clonkr'&&g.generator==='generate_glass_ping'));
 assert.ok(list.some(g=>g.synth==='Transfxr'&&g.generator==='generate_morph'));
 assert.ok(list.every(g=>!['Stackr','Mixr','Chattr','Pewpr','Rumblr'].includes(g.synth)));
});
test('Regen keeps the chosen family and the other source unchanged',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const s=new Mixr();s.set_generator(0,'Clonkr','generate_glass_ping');s.set_generator(1,'Jinglr','generate_discovery');
 const a=s.get_sources(),balance=s.params.balance;s.regenerate_source(0);const b=s.get_sources();
 return a[0].generator===b[0].generator&&a[0].params.material===b[0].params.material&&JSON.stringify(a[0].params)!==JSON.stringify(b[0].params)
 &&JSON.stringify(a[1])===JSON.stringify(b[1])&&s.params.balance===balance;})()`),true);
});
test('Regen Both changes both snapshots without changing choices or balance',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const s=new Mixr();s.set_generator(0,'Clonkr','generate_wood_knock');s.set_generator(1,'Clonkr','generate_glass_ping');s.set_param('balance',.7);
 const a=s.get_sources();s.regenerate_both();const b=s.get_sources();return b.every((source,i)=>source.generator===a[i].generator&&source.params.seed!==a[i].params.seed)&&s.params.balance===.7;})()`),true);
});
test('Mixr generator snapshots survive named links and replay without regenerating',()=>{
 const {run,load}=setup();load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const s=new Mixr();s.set_generator(0,'Clonkr','generate_glass_ping');s.set_generator(1,'Jinglr','generate_discovery');
 tabs=[{synth:s}];const before=JSON.stringify(s.params),saved=SaveLoad.shallow_dict_deserialize(SaveLoad.shallow_dict_serialize('Mixr','Mix',s.params));
 const copy=new Mixr();copy.apply_params(saved[2]);s.generate_sound();copy.generate_sound();
 return JSON.stringify(s.params)===before&&copy.get_sources()[0].generator==='generate_glass_ping'&&s.sound.getBuffer().every((v,i)=>v===copy.sound.getBuffer()[i]);})()`),true);
});
test('Invalid generators cannot execute arbitrary methods or replace a slot',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const s=new Mixr();s.set_generator(0,'Clonkr','generate_glass_ping');const before=s.params.sources;
 for(const method of ['constructor','set_param','generate_sound','mutate_params','generate_missing'])if(s.set_generator(0,'Clonkr',method)!==false)return false;
 return s.params.sources===before&&s.set_generator(2,'Clonkr','generate_glass_ping')===false;})()`),true);
});
test('Legacy snapshots remain playable and are not silently regenerated as another preset',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const s=new Mixr(),a=new Clonkr();a.generate_glass_ping();s.set_source(0,a,'My edited glass');const before=s.params.sources;
 s.regenerate_source(0);return s.params.sources===before;})()`),true);
});
test('curated Mixr pairs invoke only listed generators and create fresh playable snapshots',()=>{
 const names=['Clonkr','Machinr','Jinglr','Squishr','Crittr','Birdr','Signlr','Fractr','Riftr','Swarmr','Boomr','Zappr','Whooshr','Breathr','Choirr','Pluckr','Stackr','Mixr'];
 const {run}=createContext(names);
 const result=plain(run(`(()=>{Math.random=SoundDSP.rng(.613);const mix=new Mixr();return mix.recipes.map(recipe=>{
 mix.generate_recipe(recipe.id);const first=mix.params.sources;mix.generate_recipe(recipe.id);const sources=mix.get_sources();mix.generate_sound();const pcm=mix.sound.getBuffer();
 return {id:recipe.id,fresh:first!==mix.params.sources,valid:sources.every((s,i)=>s.synth===recipe.pair[i][0]&&s.generator==='generate_'+recipe.pair[i][1]),
 audible:pcm.some(v=>Math.abs(v)>.025),finite:pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<=1)};});})()`));
 for(const entry of result)assert.deepEqual({...entry,id:undefined},{id:undefined,fresh:true,valid:true,audible:true,finite:true});
});
test('old named Breathr links run cycle migration before merging defaults',()=>{
 const {run,load}=createContext(['Breathr','Stackr']);load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const s=new Breathr(),old={...s.params,duration:2.7};delete old.mode;delete old.direction;tabs=[{synth:s}];
 const decoded=SaveLoad.shallow_dict_deserialize('Breathr~@2~'+JSON.stringify({filename:'Old breath',params:old}));
 return decoded[2].mode===1&&decoded[2].duration===2.7&&s.params.mode===0;})()`),true);
});
test('classic coin and explosion generators set valid pitch jump timing',()=>{
 const {run}=createContext(['Bfxr','Stackr','Mixr']);
 const result=plain(run(`(()=>{const errors=[];console.error=(...args)=>errors.push(args.join(' '));Math.random=()=>.1;
 const coin=Mixr.generated_source('Bfxr','generate_pickup_coin'),boom=Mixr.generated_source('Bfxr','generate_explosion');
 return {errors,onsets:[coin.params.pitch_jump_onset_percent,boom.params.pitch_jump_onset_percent]};})()`));
 assert.deepEqual(result.errors,[]);assert.ok(result.onsets.every(x=>x>=0&&x<1));assert.ok(result.onsets[1]>0);
});
