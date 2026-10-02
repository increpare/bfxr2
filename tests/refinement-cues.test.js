const test=require('node:test');const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
test('Jinglr short cues keep seed reconstruction and reseed both melody and instrument',()=>{
 const {run}=createContext(['Jinglr']);
 for(const id of ['confirm','message','dismiss','denied'])assert.equal(run(`(()=>{const s=new Jinglr();s.generate_recipe('${id}');
 const first={...s.params};s.generate_recipe('${id}');const pcm=Jinglr_DSP.render(s.params);
 return s.melody_matches_seed()&&first.seed!==s.params.seed&&first.instrumentSeed!==s.params.instrumentSeed&&pcm.length<44100*.8&&pcm.some(v=>Math.abs(v)>.02);})()`),true,id);
});
test('Snore is a direct generator and Pluckr tremolo is independent of string material',()=>{
 const {run}=createContext(['Breathr','Pluckr']);
 assert.equal(run(`(()=>{const b=new Breathr();b.generate_snore();return b.params.source===2&&b.params.cycles===1;})()`),true);
 assert.equal(run(`new Pluckr().get_param_info('material').values.some(v=>v[0]==='Gravity')`),false);
 const [a,b]=run(`(()=>{const s=new Pluckr();s.apply_params({duration:1,strings:1,damping:0,tremolo:0});return [Pluckr_DSP.render(s.params),Pluckr_DSP.render({...s.params,tremolo:1,tremoloRate:5})];})()`);
 assert.notDeepEqual(a,b);assert.ok(b.every(Number.isFinite));
 assert.equal(run(`(()=>{const s=new Pluckr();const old={...s.params};delete old.tremolo;delete old.tremoloRate;s.set_param('tremolo',1);s.apply_params(old);return s.params.tremolo===0;})()`),true);
});
test('Signlr ping seeds change resonator character with clean deterministic output',()=>{
 const {run}=createContext(['Signlr']);
 const [a,b,replay]=run(`(()=>{const s=new Signlr();s.generate_recipe('radar_blip');s.set_param('seed',.24);const a=Signlr_DSP.render(s.params);
 return [a,Signlr_DSP.render({...s.params,seed:.79}),Signlr_DSP.render(s.params)];})()`);
 assert.deepEqual(a,replay);assert.notDeepEqual(a,b);assert.ok(a.every(v=>Number.isFinite(v)&&Math.abs(v)<1));
});
test('mode-specific controls are disabled when their mechanism does not use them',()=>{
 const {run}=createContext(['Signlr','Pewpr']);
 assert.equal(run(`(()=>{const signal=new Signlr();signal.set_param('encoding',4);if(!['symbols','corruption','interference'].every(k=>signal.param_is_disabled(k)))return false;
 signal.set_param('encoding',0);if(signal.param_is_disabled('symbols'))return false;
 const weapon=new Pewpr();weapon.set_param('kind',2);if(!weapon.param_is_disabled('sweep'))return false;weapon.set_param('kind',0);return !weapon.param_is_disabled('sweep');})()`),true);
});
test('retired Gravity share links keep their modulation when migrated to explicit tremolo',()=>{
 const {run,load}=createContext(['Pluckr']);load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const s=new Pluckr(),old={...s.params,material:5};delete old.tremolo;delete old.tremoloRate;tabs=[{synth:s}];
 const link='Pluckr~Gravity~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k])).join('~');s.apply_params(SaveLoad.shallow_dict_deserialize(link)[2]);
 return s.params.material===4&&s.params.tremolo===.35&&s.params.tremoloRate===1.7;})()`),true);
});
