const test=require('node:test');const assert=require('node:assert/strict');const {createContext,plain}=require('./helpers/synth-context');
test('Transfxr waveform morph preserves old sound and matches either constant endpoint',()=>{
 const {run}=createContext(['Transfxr']);
 const result=run(`(()=>{const s=new Transfxr();s.generate_example('laser_zip',false);s.set_param('echo',0);const p={...s.params};
 const old={...p};delete old.waveTo;delete old.morph;
 const a=Transfxr_DSP.render(p),legacy=Transfxr_DSP.render(old),b=Transfxr_DSP.render({...p,waveType:6});
 const start=Transfxr_DSP.render({...p,waveTo:6,morph:{start:0,end:0,curve:'Linear'}}),end=Transfxr_DSP.render({...p,waveTo:6,morph:{start:1,end:1,curve:'Linear'}});
 return [a,legacy,start,b,end,Transfxr_DSP.render({...p,waveTo:6})];})()`);
 assert.deepEqual(result[0],result[1]);assert.deepEqual(result[0],result[2]);assert.deepEqual(result[3],result[4]);
 assert.notDeepEqual(result[5],result[0]);assert.notDeepEqual(result[5],result[3]);assert.ok(result[5].every(v=>Number.isFinite(v)&&Math.abs(v)<1));
});
test('Transfxr old positional links and snapshots reset morph controls',()=>{
 const {run,load}=createContext(['Transfxr']);load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const s=new Transfxr(),old={...s.params};delete old.morph;delete old.waveTo;tabs=[{synth:s}];
 const link='Transfxr~Old~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k])).join('~');
 const params=SaveLoad.shallow_dict_deserialize(link)[2];s.generate_morph();s.apply_params(old);
 return s.params.waveTo===-1 && params.waveTo===-1 && params.morph.curve==='Smooth';})()`),true);
});
