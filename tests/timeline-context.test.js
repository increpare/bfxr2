'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {createTimelineContext}=require('../tools/render/timeline_context');
const {createCompositionContext}=require('../tools/render/composition_context');

test('native Stackr preserves delays, canonical controls and uncached replay',()=>{
 const api=createTimelineContext();
 const source={synth:'Transfxr',params:{},start:.2,gain:.5,pitch:0};
 const input={layers:JSON.stringify([source]),seed:.5,masterVolume:.5,spacing:1};
 const a=api.render(input), b=api.render(a.params,{uncached:true});
 assert.deepEqual(a.pcm,b.pcm);
 assert.deepEqual(a.params,b.params);
 assert(a.pcm.slice(0,8820).every(x=>x===0));
 assert(a.pcm.slice(8820).some(x=>Math.abs(x)>1e-5));
 const one=api.source(source,.5), two=api.source(source,.5);
 assert.deepEqual(one.pcm,two.pcm);
 assert.deepEqual(one.source,two.source);
 assert.equal(api.inventory().baseSourceHash,createCompositionContext().inventory().baseSourceHash);
});

test('timeline rejects invalid requests and recovers',()=>{
 const api=createTimelineContext();
 assert.throws(()=>api.render({layers:'[]'}),/layers/i);
 assert.throws(()=>api.render({layers:JSON.stringify([{synth:'Footsteppr',params:{}}])}),/source/i);
 assert.throws(()=>api.render({layers:JSON.stringify([{synth:'Transfxr',params:{},start:NaN}])}),/start/i);
 assert(api.render({layers:JSON.stringify([{synth:'Transfxr',params:{},start:0,gain:.5,pitch:0}])}).pcm.length>0);
});
