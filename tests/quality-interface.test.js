const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
test('Tappr action generators make single gestures instead of repeated notification taps',()=>{
 const {run}=createContext(['Tappr']);
 const draws=plain(run(`(()=>{Math.random=SoundDSP.rng(.312);const s=new Tappr();return s.recipes.flatMap(r=>Array.from({length:8},()=>{s.generate_recipe(r.id);return {id:r.id,...s.params};}));})()`));
 assert.ok(draws.every(p=>p.release===0),'second contact is opt-in across the interface kit');
 assert.ok(new Set(draws.map(p=>p.electronic.toFixed(2))).size>10);
});
test('Notifr instrument generators keep the alert pattern but reseed bell construction',()=>{
 const {run}=createContext(['Notifr']);
 assert.equal(run('typeof new Notifr().reseed_instrument'),'function');
 const data=run(`(()=>{const s=new Notifr();s.generate_recipe('achievement');const initial={...s.params};
 s.reseed_instrument(1);const a={...s.params},first=Notifr_DSP.render(a);s.reseed_instrument(1);const b={...s.params};
 return {initial,a,b,first,second:Notifr_DSP.render(b),replay:Notifr_DSP.render(a)};})()`);
 for(const key of ['duration','pitch','interval','pulses','spacing','urgency']){assert.equal(data.initial[key],data.a[key]);assert.equal(data.a[key],data.b[key]);}
 assert.notEqual(data.a.instrumentSeed,data.b.instrumentSeed);
 assert.notDeepEqual(data.first,data.second);assert.deepEqual(data.first,data.replay);
});
test('Notifr instrument seed changes spectral shape rather than only phase',()=>{
 const {run}=createContext(['Notifr']);
 const sounds=run(`(()=>{const s=new Notifr();s.apply_params({tone:1,pulses:1,duration:.4,softness:.1,ring:.8,echo:0});
 return [.1,.9].map(instrumentSeed=>Notifr_DSP.render({...s.params,instrumentSeed}));})()`);
 function roughness(a){let d=0,e=0;for(let i=1;i<a.length;i++){d+=(a[i]-a[i-1])**2;e+=a[i]**2;}return d/e;}
 assert.ok(Math.abs(roughness(sounds[0])-roughness(sounds[1]))>.003);
});
test('Notifr instruments respect locks and recipes reseed both pattern and instrument',()=>{
 const {run}=createContext(['Notifr']);
 assert.equal(run('typeof new Notifr().reseed_instrument'),'function');
 assert.equal(run(`(()=>{const s=new Notifr();s.generate_recipe('message');const before={...s.params};
 s.generate_recipe('message');if(before.seed===s.params.seed||before.instrumentSeed===s.params.instrumentSeed)return false;
 s.set_param('tone',2);s.set_param('instrumentSeed',.123);s.set_locked_param('tone',true);s.set_locked_param('instrumentSeed',true);
 s.reseed_instrument(1);s.generate_recipe('warning');return s.params.tone===2&&s.params.instrumentSeed===.123;})()`),true);
});
test('Stackr starts empty and copies sources as simultaneous layers',()=>{
 const {run}=createContext(['Transfxr','Stackr']);
 const data=plain(run(`(()=>{const s=new Stackr();s.create_random_template();const initial=s.get_layers();const source=new Transfxr();s.add_source(source,'Air');s.add_source(source,'Impact');return {initial,layers:s.get_layers()};})()`));
 assert.equal(data.initial.length,0);assert.deepEqual(data.layers.map(l=>l.start),[0,0]);
});
test('Layer in Stackr copies the selected sound, updates and opens the stack',()=>{
 const {run,load}=createContext(['Transfxr','Stackr']);load('js/Tab.js');
 assert.equal(run('typeof Tab.prototype.layer_in_stackr'),'function');
 assert.equal(run(`(()=>{const source=Object.create(Tab.prototype);source.synth=new Transfxr();source.name='Transfxr';source.get_current_file_name=()=> 'Whoosh';
 const destination={name:'Stackr',synth:new Stackr(),parameter_changed(){this.changed=true;this.savedActive=this.opened===true;},set_active_tab(){this.opened=true;}};
 tabs=[source,destination];source.layer_in_stackr();return destination.changed&&destination.opened&&destination.savedActive&&destination.synth.get_layers()[0].name==='Whoosh';})()`),true);
});
test('returning to a source refreshes Layer in Stackr after freeing a full stack',()=>{
 const {run,load}=createContext(['Transfxr','Stackr']);load('js/Tab.js');
 assert.equal(run(`(()=>{const source=Object.create(Tab.prototype);source.synth=new Transfxr();source.name='Transfxr';source.selected_file_index=-1;source.stack_button={};
 const stack={name:'Stackr',synth:new Stackr()};tabs=[source,stack];for(let i=0;i<6;i++)stack.synth.add_source(source.synth,'Layer');
 source.update_ablements();if(!source.stack_button.disabled)return false;
 stack.synth.set_param('layers',[]);globalThis.document={getElementById(){return {classList:{add(){}}};},getElementsByClassName(){return [];}};
 source.set_active_tab();return source.stack_button.disabled===false;})()`),true);
});
test('legacy Tappr files reset new gesture controls without changing partial edits',()=>{
 const {run}=createContext(['Tappr']);
 assert.equal(run(`(()=>{const s=new Tappr();const old={...s.params};delete old.sweep;delete old.air;
 s.apply_params({sweep:.9,air:.8});s.apply_params(old);
 if(s.params.sweep!==0||s.params.air!==0)return false;
 s.apply_params({sweep:.5,air:.4});s.apply_params({duration:.2});return s.params.sweep===.5&&s.params.air===.4;})()`),true);
});
test('soft bell instruments retain distinct partials at the softest setting',()=>{
 const {run}=createContext(['Notifr']);
 const [a,b]=run(`(()=>{const s=new Notifr();s.apply_params({tone:1,pulses:1,duration:.4,softness:1,ring:.8,echo:0,seed:.312});return [.1,.9].map(instrumentSeed=>Notifr_DSP.render({...s.params,instrumentSeed}));})()`);
 let cross=0,aa=0,bb=0;for(let i=0;i<a.length;i++){cross+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i];}
 assert.ok(cross/Math.sqrt(aa*bb)<.99,'softness must not collapse every bell into the same sine');
});
test('unlocking a parameter refreshes instrument generator availability immediately',()=>{
 const {run,load}=createContext(['Notifr']);load('js/Tab.js');load('js/SaveLoad.js');
 assert.equal(run(`(()=>{const tab=Object.create(Tab.prototype);tab.synth=new Notifr();tab.synth.set_locked_param('instrumentSeed',true);
 let refreshed=false;tab.custom_editor={update(){refreshed=!tab.synth.locked_param('instrumentSeed');}};SaveLoad.save_all_collections=()=>{};
 tab.lock_param_clicked({classList:{add(){},remove(){}}},'instrumentSeed',false);return refreshed;})()`),true);
});
