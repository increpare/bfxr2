const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const path=require('node:path');
const {createCompositionContext}=require('../tools/render/composition_context');
const setup=()=>createCompositionContext();
const source=(synth,seed=.31)=>({synth,params:{duration:.12},renderSeed:seed});
const patch=(a,b,balance=.35)=>({sources:JSON.stringify([a,b]),balance,masterVolume:.5,seed:.5});

test('cached two-voice render equals actual Mixr.generate_sound and saved snapshot replay',()=>{
 const api=setup();const p=patch(source('Transfxr'),source('Rustlr'));
 const cached=api.render(p);const actual=api.render(cached.params,{uncached:true});
 assert.deepEqual(cached.pcm,actual.pcm);
 assert.deepEqual(api.render(JSON.parse(JSON.stringify(cached.params))).pcm,actual.pcm);
 assert.ok(actual.pcm.some(v=>Math.abs(v)>.0001));
 assert.ok(actual.pcm.every(Number.isFinite));
});

test('balance endpoints agree with the corresponding single-source control',()=>{
 const api=setup();const a=source('Clonkr'),b=source('Transfxr');
 const mixed=api.render(patch(a,b,0));const single=api.render(patch(a,null,0));
 // Different source lengths can change end taper; compare the shared interior.
 assert.deepEqual(mixed.pcm.slice(0,Math.min(mixed.pcm.length,single.pcm.length)-128),single.pcm.slice(0,-128));
 const swapped=api.render(patch(b,a,1));assert.deepEqual(mixed.pcm,swapped.pcm);
});

test('source stochastic seed is stable across intervening requests and changes the noisy source',()=>{
 const api=setup();const a=api.source(source('Bfxr',.23));
 api.source(source('Rustlr',.74));
 assert.deepEqual(api.source(source('Bfxr',.23)).pcm,a.pcm);
 const noise={synth:'Bfxr',params:{waveType:3},renderSeed:.23};
 const x=api.source(noise).pcm,y=api.source({...noise,renderSeed:.71}).pcm;
 assert.notDeepEqual(x,y);
});

test('invalid or nested sources and nonfinite mix controls are rejected',()=>{
 const api=setup();
 for(const name of ['Mixr','Stackr','Footsteppr','constructor','Missing'])
  assert.throws(()=>api.render(patch(source(name),null)),/source/i);
 assert.throws(()=>api.render({...patch(source('Clonkr'),null),balance:NaN}),/finite/i);
 assert.throws(()=>api.render({sources:'[]'}),/source/i);
 assert.throws(()=>api.render({sources:'not json'}));
 assert.throws(()=>api.render({sources:JSON.stringify([source('Clonkr'),null,null])}),/source/i);
});

test('composition hash includes the actual Mixr DSP, Stackr source semantics and bridge dependencies',()=>{
 const info=setup().inventory();
 for(const key of ['js/audio/Mixr_DSP.js','js/synths/Mixr.js','js/synths/Stackr.js','tests/helpers/synth-context.js','tools/render/composition_context.js']){
  const bytes=fs.readFileSync(path.resolve(__dirname,'..',key));
  assert.equal(info.dependencies[key],crypto.createHash('sha256').update(bytes).digest('hex'));
 }
 const hash=crypto.createHash('sha256').update(info.baseSourceHash);
 for(const [key,value] of Object.entries(info.dependencies).sort()) hash.update(key).update('\0').update(value).update('\0');
 assert.equal(info.sourceHash,hash.digest('hex'));
});
