const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const schemas={Tappr:[['air','sweep']],Notifr:[['instrumentSeed']],Rollr:[['surface']],Breathr:[['mode','direction'],['mode','direction','source']],
 Pluckr:[['vibrato'],['vibrato','tremolo','tremoloRate'],['vibrato','material','tremolo','tremoloRate']],Fractr:[['shards'],['shards','stress','fracture']],Boomr:[['gas','aftershock','rubbleSize'],['gas','aftershock','rubbleSize','mechanism','space']],Pewpr:[['character','modulation']],
 Bouncr:[['surface','force','tail']],Glitchr:[['mode']],Rumblr:[['depth','harmonics']]};
for(const [name,versions] of Object.entries(schemas))for(const added of versions)test(name+' positional links missing '+added.join('/')+' preserve original fields',()=>{
 const {run,load}=createContext([name]);load('js/SaveLoad.js');
 const [expected,actual]=plain(run(`(()=>{const synth=new ${name}();tabs=[{synth}];synth.generate_recipe(synth.recipes[1].id);const old={...synth.params};
 for(const key of ${JSON.stringify(added)})delete old[key];
 const link='${name}~Legacy~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k]).replace(/~/g,'\\\\u007e')).join('~');
 return [{...synth.default_params(),...old,...('${name}'==='Breathr'?{mode:1}:{})},SaveLoad.shallow_dict_deserialize(link)[2]];})()`));
 assert.deepEqual(actual,expected);
});
for(const removed of [['voiceMode','character','voiceSeed'],['voiceMode','character','voiceSeed','waveType'],['voiceMode','character','voiceSeed','waveType','articulation']])test('Chattr positional link missing '+removed.join('/')+' preserves speech and words',()=>{
 const {run,load}=createContext();for(const name of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP'])load('js/audio/'+name+'.js');
 load('js/synths/Chattr.js');load('js/SaveLoad.js');
 const [expected,actual]=plain(run(`(()=>{const synth=new Chattr();synth.apply_params({text:'My old voice?',pitch:.81,articulation:.3,texture:2});tabs=[{synth}];
 const old={...synth.params};for(const key of ${JSON.stringify(removed)})delete old[key];
 const link='Chattr~Old~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k])).join('~');
 return [{...synth.default_params(),...old,voiceMode:0},SaveLoad.shallow_dict_deserialize(link)[2]];})()`));
 assert.deepEqual(actual,expected);
});
