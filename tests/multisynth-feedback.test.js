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
