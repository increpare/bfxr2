const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){
 const api=createContext(['Transfxr']);
 api.load('js/audio/ChattrLexicon.js');api.load('js/audio/ChattrFormants.js');
 api.load('js/audio/Chattr_Pronunciation.js');api.load('js/audio/Chattr_DSP.js');api.load('js/synths/Chattr.js');
 api.load('js/audio/Bfxr_DSP.js');api.load('js/synths/Bfxr.js');
 return api;
}
test('Transfxr and Chattr expose every Bfxr waveform without changing legacy choices',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{
 const base=new Bfxr().param_info.find(p=>p.name==='waveType').values.map(v=>v[0]);
 const trans=new Transfxr(),chat=new Chattr();
 return {base,trans:trans.param_info.find(p=>p.name==='waveType').values,
 chat:chat.param_info.find(p=>p.name==='waveType')?.values || [],voice:chat.params.waveType};})()`));
 for(const name of result.base){assert.ok(result.trans.some(v=>v[0]===name),`Transfxr ${name}`);assert.ok(result.chat.some(v=>v[0]===name),`Chattr ${name}`);}
 assert.deepEqual(result.trans.filter(v=>v[2]<4).map(v=>[v[0],v[2]]).sort(),[['Sin',0],['Triangle',1],['Saw',2],['Square',3]].sort());
 assert.equal(result.voice,-1);
});
test('all Transfxr waveforms render distinct repeatable bounded sounds',()=>{
 const {run}=setup();
 const sounds=run(`(()=>{const s=new Transfxr();s.apply_params({duration:0.12,echo:0,tone:{start:1,end:1,curve:'Linear'}});
 return s.param_info.find(p=>p.name==='waveType').values.map(v=>{s.set_param('waveType',v[2]);return [v[0],Transfxr_DSP.render(s.params),Transfxr_DSP.render(s.params)];});})()`);
 assert.equal(sounds.length,12);const signatures=new Set();
 for(const [name,a,b] of sounds){assert.deepEqual(a,b,name);assert.ok(a.every(v=>Number.isFinite(v)&&Math.abs(v)<1),name);assert.ok(a.some(v=>Math.abs(v)>.005),name);signatures.add(Buffer.from(a.buffer).toString('base64'));}
 assert.equal(signatures.size,12);
});
test('Chattr waveform changes timbre while retaining phonemes and old voice imports',()=>{
 const {run}=setup();
 const result=run(`(()=>{const s=new Chattr();s.set_param('text','Ah.');const old={...s.params};delete old.waveType;
 const sounds=s.param_info.find(p=>p.name==='waveType')?.values.map(v=>{s.set_param('waveType',v[2]);return [v[0],Chattr_DSP.schedule(s.params).events.map(e=>e.phone).join(' '),Chattr_DSP.render(s.params)];})||[];
 s.set_param('waveType',3);s.apply_params(old);return {sounds,restored:s.params.waveType};})()`);
 assert.equal(result.sounds.length,13);assert.equal(result.restored,-1);
 const signatures=new Set();
 for(const [name,phones,pcm] of result.sounds){assert.equal(phones,result.sounds[0][1]);assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1),name);assert.ok(pcm.some(v=>Math.abs(v)>.001),name);signatures.add(Buffer.from(pcm.buffer).toString('base64'));}
 assert.equal(signatures.size,13);
});
test('Chattr character buttons generate new voices beyond timing seeds and retain locks',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const s=new Chattr();Math.random=SoundDSP.rng(.382);s.set_param('text','Keep these words');s.set_locked_param('mouth',true);
 return Chattr.characters.map(c=>{s.generate_character(c.id);const a={...s.params};s.generate_character(c.id);return {a,b:{...s.params}};});})()`));
 for(const {a,b} of result){assert.equal(a.text,b.text);assert.equal(a.mouth,b.mouth);assert.ok(Object.keys(a).filter(k=>k!=='seed'&&a[k]!==b[k]).length>=3);}
});
test('Bitnoise starts with changing bits during short low-pitched effects',()=>{
 const {run}=setup();
 const samples=run(`(()=>{const osc=BfxrWaveforms.create(9,.5);return Array.from({length:800},(_,i)=>osc((i%100)/100,.01));})()`);
 assert.ok(Math.min(...samples)<0 && Math.max(...samples)>0,'initial register must not spend the whole short sound on a DC level');
});
