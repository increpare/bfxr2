const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const schemas={Tappr:['air','sweep'],Notifr:['instrumentSeed'],Rollr:['surface'],Breathr:['source'],Pluckr:['material']};
for(const [name,added] of Object.entries(schemas))test(name+' legacy share links keep their original field positions',()=>{
 const {run,load}=createContext([name]);load('js/SaveLoad.js');
 const [expected,actual]=plain(run(`(()=>{const synth=new ${name}();tabs=[{synth}];synth.generate_recipe(synth.recipes[1].id);const old={...synth.params};
 const added=${JSON.stringify(added)};for(const key of added)delete old[key];
 const link=SaveLoad.shallow_dict_serialize('${name}','Legacy',old),parsed=SaveLoad.shallow_dict_deserialize(link)[2];
 return [{...synth.default_params(),...old},parsed];})()`));
 assert.deepEqual(actual,expected);
});
for(const removed of [['waveType'],['waveType','articulation']])test('Chattr legacy link missing '+removed.join('/')+' preserves words and source',()=>{
 const {run,load}=createContext();for(const name of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP'])load('js/audio/'+name+'.js');
 load('js/synths/Chattr.js');load('js/SaveLoad.js');
 const [expected,actual]=plain(run(`(()=>{const synth=new Chattr();synth.apply_params({text:'My old voice?',pitch:.81,articulation:.3,texture:2});tabs=[{synth}];
 const old={...synth.params};for(const key of ${JSON.stringify(removed)})delete old[key];
 const link=SaveLoad.shallow_dict_serialize('Chattr','Old',old);return [{...synth.default_params(),...old},SaveLoad.shallow_dict_deserialize(link)[2]];})()`));
 assert.deepEqual(actual,expected);
});
