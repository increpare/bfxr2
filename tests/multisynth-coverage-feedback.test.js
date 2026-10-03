const test = require('node:test');
const assert = require('node:assert/strict');
const {feedbackPayload} = require('../tools/multisynth/coverage_feedback.js');
const model = {experimentId:'run',provenance:{sourceHash:'dsp'},targets:[
 {id:'t',name:'coin',candidates:[{id:'a',role:'automatic',file:'a.wav'},
 {id:'b',role:'guided',file:'b.wav'},{id:'a',role:'previous',file:'previous.wav'}]}]};
test('starts empty and exports likeness and usefulness independently',()=>{
 assert.deepEqual(feedbackPayload(model,{}).targets,[]);
 const target=feedbackPayload(model,{ratings:{a:{likeness:2},b:{usefulness:5}}}).targets[0];
 assert.equal(target.candidates[0].likeness,2);
 assert.equal(target.candidates[0].usefulness,null);
 assert.equal(target.candidates[1].likeness,null);
 assert.equal(target.candidates[1].usefulness,5);
 assert.equal(target.candidates[2].likeness,2);
 assert.equal(target.candidates[2].file,'previous.wav');
});
test('notes retain nulls; invalid values never become labels',()=>{
 const payload=feedbackPayload(model,{ratings:{a:{likeness:true,usefulness:6},b:{likeness:0}},notes:{t:'Very fun'}});
 assert.equal(payload.schemaVersion,2);
 assert.equal(payload.targets[0].note,'Very fun');
 for(const c of payload.targets[0].candidates) assert.deepEqual([c.likeness,c.usefulness],[null,null]);
 assert.deepEqual(feedbackPayload(model,{ratings:{a:{likeness:NaN}}}).targets,[]);
});

test('gallery saves, reloads and clears each dimension while synchronizing exact aliases',async()=>{
 const fs=require('node:fs'),vm=require('node:vm');
 const script=fs.readFileSync(require.resolve('../tools/multisynth/coverage_feedback.js'),'utf8');
 const storage=new Map();
 let copied;
 function element(dataset={},value='') {return {dataset,value,events:{},addEventListener(k,f){this.events[k]=f;},focus(){},select(){}};}
 function browser(){
  const inputs=[element({candidate:'a',dimension:'likeness'},'2'),element({candidate:'a',dimension:'usefulness'},'4'),
   element({candidate:'a',dimension:'likeness'},'2'),element({candidate:'a',dimension:'usefulness'},'4')];
  const clear=[element({clear:'a',dimension:'likeness'})];
  const note=element({note:'t'});
  const ids={'feedback-data':{textContent:JSON.stringify(model)},'feedback-json':element(),
   'feedback-status':element(),'copy-feedback':element(),'select-feedback':element()};
  const players=[{paused:false,pause(){this.paused=true;}},{paused:false,pause(){this.paused=true;}}];
  const events={};
  const document={addEventListener:(name,handler)=>{events[name]=handler;},getElementById:id=>ids[id],querySelectorAll:selector=>({
   'audio':players,'input[data-candidate]':inputs,'button[data-clear]':clear,'textarea[data-note]':[note]})[selector]};
  vm.runInNewContext(script,{document,localStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
   navigator:{clipboard:{writeText:async value=>{copied=value;}}}});
  return {inputs,clear,note,ids,players,events,payload:()=>JSON.parse(ids['feedback-json'].value)};
 }
 const first=browser();
 first.events.play({target:first.players[1]});
 assert.equal(first.players[0].paused,true);
 assert.equal(first.players[1].paused,false);
 assert.deepEqual(first.payload().targets,[]);
 first.inputs[0].events.change();
 first.inputs[1].events.change();
 assert.ok(first.inputs.every(i=>i.checked));
 const reloaded=browser();
 assert.ok(reloaded.inputs.every(i=>i.checked));
 reloaded.clear[0].events.click();
 assert.equal(reloaded.inputs[0].checked,false);
 assert.equal(reloaded.inputs[2].checked,false);
 assert.equal(reloaded.inputs[1].checked,true);
 assert.equal(reloaded.payload().targets[0].candidates[0].usefulness,4);
 assert.equal(reloaded.payload().targets[0].candidates[0].likeness,null);
 reloaded.note.value='Useful despite poor likeness';
 reloaded.note.events.input();
 await reloaded.ids['copy-feedback'].events.click();
 assert.equal(JSON.parse(copied).targets[0].note,'Useful despite poor likeness');
 assert.equal(browser().note.value,'Useful despite poor likeness');
});
