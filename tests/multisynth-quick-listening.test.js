const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {feedbackPayload} = require('../tools/multisynth/coverage_feedback.js');
function optional(name) {
 const file=path.join(__dirname,'../tools/multisynth',name+'.js');
 return fs.existsSync(file)?require(file):{};
}
const choice=optional('quick_choice'), audio=optional('quick_audio');
const target={id:'t',folder:'001',candidates:[
 {id:'raw',role:'raw',audioSha256:'raw',file:'raw.wav'},
 {id:'new',role:'selected',audioSha256:'new',file:'selected.wav'},
 {id:'old',role:'original',audioSha256:'old',file:'original.wav'},
 {id:'alias',role:'previous',audioSha256:'old',file:'previous.wav'}]};
const model={experimentId:'experiment',provenance:{sourceHash:'dsp'},targets:[target]};
const judgment={protocol:'feel-choice-v1',kind:'best',presentedCandidateIds:['new','old'],
 auditionedCandidateIds:['new','old'],preferredCandidateIds:['new']};

test('one-click choice exports ordinal feedback with null scalar ratings',()=>{
 const result=feedbackPayload(model,{choices:{t:judgment}});
 assert.equal(result.schemaVersion,3);
 assert.equal(result.targets.length,1);
 assert.deepEqual(result.targets[0].choice,judgment);
 for(const c of result.targets[0].candidates)assert.deepEqual([c.likeness,c.usefulness],[null,null]);
});
test('choices preserve existing ratings and ratings-only schema2',()=>{
 const state={choices:{t:judgment},ratings:{old:{likeness:4,usefulness:5}},notes:{t:'still useful'}};
 const result=feedbackPayload(model,state);
 assert.equal(result.targets[0].candidates[2].likeness,4);
 assert.equal(result.targets[0].note,'still useful');
 assert.equal(feedbackPayload(model,{ratings:state.ratings}).schemaVersion,2);
});
test('primary set hides raw predictions, deduplicates audible aliases and stays ordered on reload',()=>{
 assert.equal(typeof choice.primaryCandidates,'function');
 const first=choice.primaryCandidates(target,'experiment');
 assert.deepEqual(new Set(first.map(c=>c.id)),new Set(['new','old']));
 assert.deepEqual(first,choice.primaryCandidates(target,'experiment'));
 assert.equal(choice.primaryCandidates({...target,candidates:target.candidates.slice(0,3)},'experiment').length,2);
});
test('resume skips quick decisions and fully rated primary sets without inventing new choices',()=>{
 assert.equal(typeof choice.firstPendingIndex,'function');
 const second={...target,id:'t2'};
 assert.equal(choice.firstPendingIndex([target,second],{choices:{t:judgment}},'experiment'),1);
 assert.equal(choice.firstPendingIndex([target],{ratings:{new:{likeness:2},old:{likeness:3}}},'experiment'),1);
 assert.equal(choice.firstPendingIndex([target],{ratings:{new:{usefulness:5}}},'experiment'),0);
});
test('malformed stored choices never become feedback',()=>{
 assert.equal(typeof choice.validatedChoice,'function');
 assert.equal(choice.validatedChoice(target,{...judgment,preferredCandidateIds:['foreign']}),null);
 assert.equal(choice.validatedChoice(target,{...judgment,auditionedCandidateIds:['raw']}),null);
 assert.equal(choice.validatedChoice(target,{...judgment,kind:'none',preferredCandidateIds:['new']}),null);
 assert.deepEqual(feedbackPayload(model,{choices:{t:{...judgment,kind:'broken'}}}).targets,[]);
});

function platform() {
 const sources=[];
 const context={currentTime:0,state:'suspended',resume:async()=>{context.state='running';},
  createGain:()=>({gain:{value:1},connect(){}}),destination:{},decodeAudioData:async bytes=>({duration:bytes.duration||2}),
  createBufferSource(){const source={connect(){},start(...args){this.started=args;},stop(){this.stopped=true;},onended:null};sources.push(source);return source;}};
 const fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(4)});
 return {context,sources,fetch};
}
test('every replay starts at zero and stops the old source using cached audio',async()=>{
 assert.equal(typeof audio.CachedAudioPlayer,'function');
 const p=platform();let calls=0;
 const player=new audio.CachedAudioPlayer({...p,fetch:async(...a)=>{calls++;return p.fetch(...a);}});
 await player.play('a.wav');p.context.currentTime=1.7;
 await player.play('a.wav');
 assert.equal(calls,1);
 assert.equal(p.sources[0].stopped,true);
 assert.deepEqual(p.sources[1].started,[0,0]);
});
test('a late decode cannot start a stale clip or overlap a newer replay',async()=>{
 assert.equal(typeof audio.CachedAudioPlayer,'function');
 const p=platform();let resolve;
 const wait=new Promise(r=>{resolve=r;});
 const player=new audio.CachedAudioPlayer({...p,fetch:async url=>{
  if(url==='slow.wav')await wait;
  return p.fetch(url);
 }});
 const slow=player.play('slow.wav');await player.play('fast.wav');resolve();
 assert.equal(await slow,false);
 assert.equal(p.sources.length,1);
 player.stop();assert.equal(p.sources[0].stopped,true);
});
test('only meaningful listening creates audition evidence and stop cancels ended callbacks',async()=>{
 assert.equal(typeof audio.CachedAudioPlayer,'function');
 const p=platform(),heard=[],ended=[];
 const player=new audio.CachedAudioPlayer({...p,onAudition:url=>heard.push(url),onEnded:url=>ended.push(url)});
 await player.play('a');p.context.currentTime=.1;player.stop();
 assert.deepEqual(heard,[]);
 p.sources[0].onended();assert.deepEqual(ended,[]);
 await player.play('b');p.context.currentTime+=1.2;player.stop();
 assert.deepEqual(heard,['b']);
 await player.play('c');p.sources[2].onended();
 assert.deepEqual(heard,['b','c']);assert.deepEqual(ended,['c']);
});
test('a failed decode does not poison the cache or pretend playback started',async()=>{
 assert.equal(typeof audio.CachedAudioPlayer,'function');
 const p=platform();let count=0;
 p.context.decodeAudioData=async()=>{if(++count===1)throw Error('bad clip');return {duration:2};};
 const player=new audio.CachedAudioPlayer(p);
 await assert.rejects(player.play('bad'),/bad clip/);
 assert.equal(p.sources.length,0);
 await player.play('bad');assert.equal(p.sources.length,1);
});
