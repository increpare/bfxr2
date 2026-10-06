const test=require('node:test'),assert=require('node:assert/strict');
const {CachedAudioPlayer}=require('../tools/multisynth/quick_audio_release.js');
function setup(){
 const sources=[],gains=[],heard=[],ended=[];
 const samples=new Float32Array(1000).fill(.5);
 const buffer={duration:1,sampleRate:1000,numberOfChannels:1,getChannelData:()=>samples};
 const context={currentTime:0,state:'running',destination:{},resume:async()=>{},decodeAudioData:async()=>buffer,
  createGain(){const calls=[];const g={calls,gain:{value:1,cancelScheduledValues:t=>calls.push(['cancel',t]),setValueAtTime:(v,t)=>calls.push(['set',v,t]),linearRampToValueAtTime:(v,t)=>calls.push(['ramp',v,t])},connect(){},disconnect(){g.disconnected=true;}};gains.push(g);return g;},
  createBufferSource(){const s={connect(g){s.gain=g;},start:(...a)=>s.started=a,stop:(...a)=>s.stopped=a,disconnect(){s.disconnected=true;}};sources.push(s);return s;}};
 const p=new CachedAudioPlayer({context,fetch:async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(1)}),onAudition:u=>heard.push(u),onEnded:u=>ended.push(u)});
 return {p,context,sources,gains,heard,ended,buffer};
}
test('manual interruption ramps to zero before stopping; replacement starts after release',async()=>{
 const {p,context,sources}=setup();await p.play('a');context.currentTime=.6;await p.play('b');
 assert.deepEqual(sources[0].gain.calls.slice(-2),[['set',1,.6],['ramp',0,.605]]);
 assert.deepEqual(sources[0].stopped,[.605]);assert.deepEqual(sources[1].started,[.605,0]);
});
test('natural playback keeps all samples and completion; cancelled callback cannot finish replacement',async()=>{
 const {p,context,sources,heard,ended,buffer}=setup();await p.play('a');context.currentTime=.6;await p.play('b');
 sources[0].onended();assert.deepEqual(heard,['a']);assert.deepEqual(ended,[]);
 assert.equal(sources[1].buffer,buffer);assert.equal(sources[1].stopped,undefined);
 assert.equal(sources[1].gain.calls.some(c=>c[0]==='ramp'),false);
 sources[1].onended();assert.deepEqual(ended,['b']);assert.deepEqual(heard,['a','b']);assert.ok(sources[1].disconnected);
});
test('stop before scheduled replacement starts creates no audition and does not reopen its gain',async()=>{
 const {p,context,sources,heard}=setup();await p.play('a');context.currentTime=.1;await p.play('b');p.stop();
 assert.deepEqual(sources[1].stopped,[.1]);assert.deepEqual(heard,[]);
 assert.equal(sources[1].gain.calls.some(c=>c[0]==='set'&&c[1]===1&&c[2]===.1),false);
});
test('zero release reproduces old abrupt stop for diagnostic comparison',async()=>{
 const {p,context,sources}=setup();p.stopFadeSeconds=0;await p.play('a');context.currentTime=.2;p.stop();
 assert.deepEqual(sources[0].stopped,[.2]);assert.equal(sources[0].gain.calls.some(c=>c[0]==='ramp'),false);
});
test('stop during decoding cancels pending playback without allocating a source',async()=>{
 const {p,context,sources}=setup();let finish;
 context.decodeAudioData=()=>new Promise(r=>{finish=r;});const pending=p.play('late');
 await new Promise(r=>setImmediate(r));p.stop();finish({duration:1});
 assert.equal(await pending,false);assert.equal(sources.length,0);
});
