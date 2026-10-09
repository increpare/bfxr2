const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const schemas={Breathr:[['mode','direction'],['mode','direction','source']],
 Pluckr:[['vibrato'],['vibrato','tremolo','tremoloRate'],['vibrato','material','tremolo','tremoloRate']],Fractr:[['shards'],['shards','stress','fracture']],Boomr:[['gas','aftershock','rubbleSize'],['gas','aftershock','rubbleSize','mechanism','space']],
 Bouncr:[['surface','force','tail']],Glitchr:[['mode']]};
for(const [name,versions] of Object.entries(schemas))for(const added of versions)test(name+' positional links missing '+added.join('/')+' preserve original fields',()=>{
 const {run,load}=createContext([name]);load('js/SaveLoad.js');
 const [expected,actual]=plain(run(`(()=>{const synth=new ${name}();tabs=[{synth}];synth.generate_recipe(synth.recipes[1].id);const old={...synth.params};
 for(const key of ${JSON.stringify(added)})delete old[key];
 const link='${name}~Legacy~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k]).replace(/~/g,'\\\\u007e')).join('~');
 return [{...synth.default_params(),...old,...('${name}'==='Breathr'?{mode:1}:{})},SaveLoad.shallow_dict_deserialize(link)[2]];})()`));
 assert.deepEqual(actual,expected);
});
