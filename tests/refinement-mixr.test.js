const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
const setup=()=>createContext(['Clonkr','Jinglr','Stackr','Mixr']);
test('Mixr holds two independent snapshots and rejects recursive mixes',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const mix=new Mixr(),source=new Clonkr();source.generate_recipe('glass_ping');
 mix.set_source(0,source,'Glass');const saved=mix.params.sources;source.set_param('seed',.81);
 if(mix.params.sources!==saved)return false;mix.set_source(1,mix,'Recursive');
 if(mix.get_sources()[1])return false;mix.set_source(1,source,'Changed glass');
 mix.set_param('sources',[...mix.get_sources(),mix.get_sources()[0]]);return mix.get_sources().length===2;})()`),true);
});
test('Mixr balance endpoints isolate sources and one occupied slot stays audible',()=>{
 const {run}=setup();
 const data=run(`(()=>{const p={sources:'[{"synth":"A"},{"synth":"B"}]',masterVolume:.5};
 const render=s=>new Float32Array(9000).fill(s.synth==='A'?.2:-.4);
 return [Mixr_DSP.render({...p,balance:0},render),Mixr_DSP.render({...p,balance:1},render),
 Mixr_DSP.render({...p,balance:.5},render),Mixr_DSP.render({...p,sources:'[null,{"synth":"B"}]',balance:0},render)];})()`);
 assert.equal(data[0][1000],Math.fround(.2));assert.equal(data[1][1000],Math.fround(-.4));
 assert.equal(data[2][1000],Math.fround(-.1));assert.equal(data[3][1000],data[1][1000]);
 assert.ok(data.every(a=>a.every(Number.isFinite)&&a.at(-1)===0));
});
test('Mixr sound files and share links carry both source snapshots',()=>{
 const {run,load}=setup();load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const s=new Mixr(),source=new Clonkr();source.generate_recipe('wood_knock');s.set_source(0,source,'Wood');
 source.generate_recipe('glass_ping');s.set_source(1,source,'Glass');s.set_param('balance',.71);s.generate_sound();const original=s.sound.getBuffer();
 tabs=[{synth:s}];const link=SaveLoad.shallow_dict_serialize('Mixr','Wood ~ glass',s.params);
 const decoded=SaveLoad.shallow_dict_deserialize(link),copy=new Mixr();copy.apply_params(decoded[2]);copy.generate_sound();
 return decoded[1]==='Wood ~ glass'&&copy.sound.getBuffer().every((v,i)=>v===original[i]);})()`),true);
});
test('Mix this sound opens Mixr before saving, fills both slots, then starts a fresh file',()=>{
 const {run,load}=setup();load('js/Tab.js');
 assert.equal(run(`(()=>{const source=Object.create(Tab.prototype);source.synth=new Clonkr();source.get_current_file_name=()=> 'Knock';
 const destination={name:'Mixr',synth:new Mixr(),set_active_tab(){this.open=true;},parameter_changed(){if(!this.open)throw Error('inactive');},
 create_new_sound_from_params(name,params,force){this.forced=force;this.synth.apply_params(params);}};
 tabs=[source,destination];source.mix_sound();source.mix_sound();if(destination.synth.get_sources().filter(Boolean).length!==2)return false;
 source.mix_sound();return destination.forced&&destination.synth.get_sources().filter(Boolean).length===1;})()`),true);
});
test('retired collections survive serialization and active tab names survive navigation pruning',()=>{
 const {run,load}=setup();load('js/SaveLoad.js');
 const result=plain(run(`(()=>{const archive={files:[['Old weather','{}','{}']],selected_file_index:0};SaveLoad.loaded_data={Weathr:archive};
 let opened;tabs=['Bfxr','Jinglr','Mixr','Pluckr'].map(name=>({synth:{name},files:[],set_active_tab(){opened=name;}}));
 SaveLoad.restore_active_tab({active_tab_index:28});const legacy=opened;SaveLoad.restore_active_tab({active_tab_index:9});
 const mix=opened;SaveLoad.restore_active_tab({active_tab_name:'Jinglr',active_tab_index:28});
 return [legacy,mix,opened,JSON.parse(SaveLoad.serialize_collection()).Weathr];})()`));
 assert.deepEqual(result.slice(0,3),['Pluckr','Mixr','Jinglr']);assert.equal(result[3].files[0][0],'Old weather');
});
test('explicit legacy sound imports open an archived engine on demand',()=>{
 const {run,load}=createContext(['Weathr','Stackr','Mixr']);load('js/SaveLoad.js');
 assert.equal(run(`(()=>{tabs=[];let loaded=false;class Tab{constructor(synth){this.synth=synth;tabs.push(this);}set_active_tab(){this.active=true;}create_new_sound_from_params(name,params){loaded=params.duration===.4;}}
 globalThis.Tab=Tab;SaveLoad.load_serialized_synth(JSON.stringify({synth_type:'Weathr',file_name:'Old wind',params:{duration:.4}}));
 return loaded&&tabs.length===1&&tabs[0].active&&tabs[0].synth.display_name==='Weathr (legacy)';})()`),true);
});
function characterSetup(){const api=createContext(['Pluckr','Stackr','Mixr']);for(const name of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP'])api.load('js/audio/'+name+'.js');api.load('js/synths/Chattr.js');return api;}
test('Mixr character reseeding retains words and rhythm while changing the voice',()=>{
 const {run}=characterSetup();
 assert.equal(run(`(()=>{const s=new Chattr();s.apply_params({text:'Keep my words!',speed:.8,seed:.123,character:3});const mix=new Mixr();mix.set_source(0,s,'Friend');
 mix.reseed_source(0);const a=mix.get_sources()[0].params;mix.reseed_source(0);const b=mix.get_sources()[0].params;
 return a.text==='Keep my words!'&&b.text===a.text&&a.speed===.8&&a.seed===.123&&a.character===3&&a.voiceSeed!==b.voiceSeed;})()`),true);
});
test('nested legacy sources run the same migrations as directly loaded sounds',()=>{
 const {run}=characterSetup();
 assert.equal(run(`(()=>{const voice=new Chattr(),oldVoice={...voice.params};for(const key of ['voiceMode','character','voiceSeed'])delete oldVoice[key];
 const strings=new Pluckr(),oldStrings={...strings.params,material:5};delete oldStrings.tremolo;delete oldStrings.tremoloRate;
 const a=Stackr.sanitize_source(new Chattr(),oldVoice),b=Stackr.sanitize_source(new Pluckr(),oldStrings);
 return a.voiceMode===0&&a.voiceSeed===.37&&b.material===4&&b.tremolo===.35&&b.tremoloRate===1.7;})()`),true);
});
