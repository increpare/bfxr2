const test = require('node:test');
const assert = require('node:assert/strict');
const {feedbackPayload} = require('../tools/multisynth/feedback.js');
const model = {experimentId:'run', provenance:{sourceHash:'dsp'}, targets:[
 {id:'t1', name:'Click', sha256:'abc', folder:'001', selected:{id:'a',synth:'Clonkr',file:'1.wav'}, bfxr:{id:'b',synth:'Bfxr',file:'2.wav'}},
 {id:'t2', name:'Beep', sha256:'def', folder:'002', selected:{id:'c',synth:'Bfxr',file:'1.wav'}, bfxr:{id:'c',synth:'Bfxr',file:'1.wav'}}]};
test('feedback exports only touched targets and keeps independent candidate identities',()=>{
 const payload=feedbackPayload(model,{ratings:{a:2,b:5},notes:{t1:'Bfxr has the right attack'}});
 assert.equal(payload.targets.length,1);
 assert.equal(payload.targets[0].selected.rating,2);
 assert.equal(payload.targets[0].bfxr.rating,5);
 assert.equal(payload.targets[0].note,'Bfxr has the right attack');
 assert.equal(payload.provenance.sourceHash,'dsp');
});
test('identical Bfxr candidates share a rating; unrated and invalid scores stay null',()=>{
 const payload=feedbackPayload(model,{ratings:{a:0,b:6,c:4},notes:{t1:'Interesting but unlike reference'}});
 assert.equal(payload.targets[0].selected.rating,null);
 assert.equal(payload.targets[0].bfxr.rating,null);
 assert.equal(payload.targets[1].selected.rating,4);
 assert.equal(payload.targets[1].bfxr.rating,4);
 assert.deepEqual(feedbackPayload(model,{}).targets,[]);
});
test('previous-only feedback exports and previous ratings are independent',()=>{
 const comparison={...model,targets:[{...model.targets[0],previous:{id:'old',synth:'Pew',file:'previous.wav'}}]};
 const previousOnly=feedbackPayload(comparison,{ratings:{old:5}});
 assert.equal(previousOnly.targets.length,1);
 assert.equal(previousOnly.targets[0].previous.rating,5);
 assert.equal(previousOnly.targets[0].selected.rating,null);
 assert.equal(previousOnly.targets[0].bfxr.rating,null);
 const all=feedbackPayload(comparison,{ratings:{a:1,b:3,old:5}}).targets[0];
 assert.deepEqual([all.selected.rating,all.bfxr.rating,all.previous.rating],[1,3,5]);
});
test('previous and selected candidates share a rating only when their identities match',()=>{
 const comparison={...model,targets:[{...model.targets[0],previous:{...model.targets[0].selected,file:'previous.wav'}}]};
 const row=feedbackPayload(comparison,{ratings:{a:4}}).targets[0];
 assert.equal(row.selected.rating,4);
 assert.equal(row.previous.rating,4);
 assert.equal(row.bfxr.rating,null);
 assert.equal('previous' in feedbackPayload(model,{ratings:{a:4}}).targets[0],false);
});
