const test=require('node:test'),assert=require('node:assert/strict');
const {CachedAudioPlayer,auditionThreshold}=require('../tools/multisynth/quick_audio_support.js');
function buffer(start,end,duration=10){
 const a=new Float32Array(duration*1000);a.fill(.5,start*1000,end*1000);
 return {duration,sampleRate:1000,numberOfChannels:1,getChannelData:()=>a};
}
test('short sound with a long quiet buffer is logged after half its signal support',()=>{
 assert.equal(auditionThreshold(buffer(0,.4)),.2);
});
test('leading silence and late audible events remain part of the threshold',()=>{
 assert.equal(auditionThreshold(buffer(2,2.4)),2.2);
 const b=buffer(0,.4);b.getChannelData(0).fill(.5,8000,8400);
 assert.equal(auditionThreshold(b),4.2);
});
test('an early stop before the signal is not evidence; meaningful exposure is',async()=>{
 const b=buffer(2,2.4),seen=[],sources=[];
 const context={currentTime:0,state:'running',resume:async()=>{},destination:{},
 createGain:()=>({gain:{value:1},connect(){}}),decodeAudioData:async()=>b,
 createBufferSource(){const s={connect(){},start(){},stop(){}};sources.push(s);return s;}};
 const p=new CachedAudioPlayer({context,fetch:async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(1)}),onAudition:x=>seen.push(x)});
 await p.play('a');context.currentTime=1;p.stop();assert.deepEqual(seen,[]);
 await p.play('b');context.currentTime+=2.21;p.stop();assert.deepEqual(seen,['b']);
 sources[0].onended();assert.deepEqual(seen,['b']);
});
