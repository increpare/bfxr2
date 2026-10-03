const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {createContext,rng,candidate,root}=require('../tools/preset_survey/render_corpus');
test('survey parameters survive importing into the editor unchanged',()=>{
 const corpus=JSON.parse(fs.readFileSync(path.join(root,'examples/Transfxr/survey/corpus.json'),'utf8'));
 const context=createContext(),apply=vm.runInContext('(p)=>{const s=new Transfxr();s.apply_params(p);return s.params;}',context);
 assert.equal(corpus.sounds.length,512);
 for(const sound of corpus.sounds){
  const {noise,...old}=sound.params;
  const noisy=noise.start>0||noise.end>0;
  assert.deepEqual(JSON.parse(JSON.stringify(apply(sound.params))),{...old,waveTo:noisy?7:-1,
   morph:noisy?noise:{start:0,end:1,curve:'Smooth'}},sound.id);
 }
});
test('seeded exploration repeats its sequence and covers voices and textures',()=>{
 const context=createContext();
 const defaults=JSON.parse(vm.runInContext('JSON.stringify(new Transfxr().default_params())',context));
 const examples=JSON.parse(vm.runInContext('JSON.stringify(Transfxr.examples)',context));
 const sample=seed=>{const random=rng(seed);return Array.from({length:256},(_,i)=>candidate(i,random,defaults,examples));};
 const a=sample(20261002);assert.deepEqual(a,sample(20261002));assert.notDeepEqual(a,sample(3));
 assert.equal(new Set(a.map(p=>p.waveType)).size,4);
 assert.ok(a.some(p=>p.waveTo===-1));assert.ok(a.some(p=>p.waveTo===7&&p.morph.start>.9));
 assert.ok(Math.max(...a.map(p=>p.duration))>Math.min(...a.map(p=>p.duration))*20);
});
