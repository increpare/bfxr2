const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){
 const api=createContext(['Transfxr']);
 api.load('js/audio/Bfxr_DSP.js');api.load('js/synths/Bfxr.js');
 return api;
}
test('Transfxr exposes every Bfxr waveform without changing legacy choices',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{
 const base=new Bfxr().param_info.find(p=>p.name==='waveType').values.map(v=>v[0]);
 const trans=new Transfxr();
 return {base,trans:trans.param_info.find(p=>p.name==='waveType').values};})()`));
 for(const name of result.base){assert.ok(result.trans.some(v=>v[0]===name),`Transfxr ${name}`);}
 assert.deepEqual(result.trans.filter(v=>v[2]<4).map(v=>[v[0],v[2]]).sort(),[['Sin',0],['Triangle',1],['Saw',2],['Square',3]].sort());
});
test('all Transfxr waveforms render distinct repeatable bounded sounds',()=>{
 const {run}=setup();
 const sounds=run(`(()=>{const s=new Transfxr();s.apply_params({duration:0.12,echo:0,tone:{start:1,end:1,curve:'Linear'}});
 return s.param_info.find(p=>p.name==='waveType').values.map(v=>{s.set_param('waveType',v[2]);return [v[0],Transfxr_DSP.render(s.params),Transfxr_DSP.render(s.params)];});})()`);
 assert.equal(sounds.length,12);const signatures=new Set();
 for(const [name,a,b] of sounds){assert.deepEqual(a,b,name);assert.ok(a.every(v=>Number.isFinite(v)&&Math.abs(v)<1),name);assert.ok(a.some(v=>Math.abs(v)>.005),name);signatures.add(Buffer.from(a.buffer).toString('base64'));}
 assert.equal(signatures.size,12);
});

test('Bitnoise starts with changing bits during short low-pitched effects',()=>{
 const {run}=setup();
 const samples=run(`(()=>{const osc=BfxrWaveforms.create(9,.5);return Array.from({length:800},(_,i)=>osc((i%100)/100,.01));})()`);
 assert.ok(Math.min(...samples)<0 && Math.max(...samples)>0,'initial register must not spend the whole short sound on a DC level');
});
