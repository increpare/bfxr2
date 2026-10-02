const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const {rng}=require('../tools/preset_survey/render_corpus');
function load(){
 const math=Object.create(Math);math.random=rng(4002);
 const ctx=vm.createContext({console,Math:math});
 for(const file of ['js/globals.js','js/synths/templates.js','js/synths/SynthBase.js','js/audio/Transfxr_DSP.js',
  'js/synths/PresetFamily.js','js/synths/TransfxrPresets.js','js/synths/Transfxr.js']){
  if(fs.existsSync(path.join(root,file)))vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),ctx);
 }
 return code=>vm.runInContext(code,ctx);
}
test('family sampling varies multiple controls while retaining a complete joint exemplar',()=>{
 const run=load();
 const result=run(`var bank={exemplars:[{waveType:0,duration:0.2,pitch:{start:0.3,end:0.7,curve:'Ease Out'},
 tone:{start:0.8,end:0.4,curve:'Linear'}},{waveType:2,duration:0.7,pitch:{start:0.65,end:0.2,curve:'Linear'},
 tone:{start:0.9,end:0.5,curve:'Ease In'}}]};
 Array.from({length:40},()=>PresetFamily.sample(bank));`);
 assert.ok(new Set(result.map(p=>p.duration)).size>10);
 assert.ok(new Set(result.map(p=>p.waveType)).size>1);
 assert.ok(new Set(result.map(p=>p.tone.start)).size>10);
 assert.ok(result.every(p=>p.pitch.start>=0&&p.pitch.start<=1&&p.tone.end>=0&&p.tone.end<=1));
});
test('sampling never aliases or mutates the shipped bank',()=>{
 const run=load();
 assert.equal(run(`var bank={exemplars:[{duration:0.5,pitch:{start:0.2,end:0.8,curve:'Smooth'}}]};
 var before=JSON.stringify(bank); var value=PresetFamily.sample(bank); value.pitch.start=99;
 JSON.stringify(bank)===before;`),true);
});
test('new Transfxr families expose substantially more variation and preserve locks',()=>{
 const run=load();
 const result=run(`var s=new Transfxr();s.set_param('pitch',{start:0.2,end:0.9,curve:'Steps'});
 s.set_locked_param('pitch',true);const before=JSON.stringify(s.params.pitch);const volume=s.params.masterVolume;
 Transfxr.preset_families.map(f=>{
  const values=Array.from({length:32},()=>{s['generate_family_'+f.id]();return JSON.parse(JSON.stringify(s.params));});
  return {count:f.exemplars.length,durations:new Set(values.map(p=>p.duration)).size,
   filters:new Set(values.map(p=>JSON.stringify(p.tone))).size,
   locked:values.every(p=>JSON.stringify(p.pitch)===before&&p.masterVolume===volume)};
 });`);
 assert.equal(result.length,16);
 for(const family of result){assert.ok(family.count>=10);assert.ok(family.durations>16);assert.ok(family.filters>16);assert.ok(family.locked);}
 assert.equal(run(`s.templates.filter(t=>t[2].startsWith('generate_family_')).length`),16);
});
test('interpolation rejects differing trajectory shapes',()=>{
 const run=load();
 assert.equal(run(`PresetFamily.compatible({waveType:0,pitch:{curve:'Linear'},tone:{curve:'Pulse'}},
 {waveType:0,pitch:{curve:'Linear'},tone:{curve:'Ease In'}})`),false);
});
test('dry short exemplars remain dry during variation',()=>{
 const run=load();
 assert.equal(run(`var dry={exemplars:[{duration:0.1,echo:0}]};
 Array.from({length:40},()=>PresetFamily.sample(dry)).every(p=>p.echo===0);`),true);
 assert.equal(run(`PresetFamily.sample({exemplars:[{duration:0.1,echo:0},{duration:0.2,echo:0.5}]},()=>0.25).echo`),0);
});
