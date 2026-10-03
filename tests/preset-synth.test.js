const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function example(){const api=createContext();api.run(`class TestSynth extends PresetSynth {
    name='Test'; param_info=[...PresetSynth.common_params,['Pitch','','pitch',0.5,0,1],
        {type:'BUTTONSELECT',name:'kind',default_value:0,values:[['A','',0],['B','',1]]}];
    recipes=[{name:'Test sound',id:'test',tip:'A test',values:{pitch:[0.2,0.8],kind:[0,1]}}];
    static DSP={render(p){return SoundDSP.finish(new Float32Array([0,0.3,-0.3,0]),p.masterVolume);}};
    constructor(){super();this.initialize_presets();}
} var s=new TestSynth();`);return api;}
test('category buttons produce fresh stored parameters and respect locks',()=>{
 const {run}=example();const result=run(`s.generate_test();var first=s.params.pitch;s.generate_test();var second=s.params.pitch;
 s.set_locked_param('pitch',true);s.generate_test();[first,second,s.params.pitch,s.params.masterVolume];`);
 assert.notEqual(result[0],result[1]);assert.equal(result[1],result[2]);assert.equal(result[3],0.5);
});
test('preset synth imports validate known fields and produce reproducible audio',()=>{
 const {run}=example();assert.equal(run(`s.apply_params({pitch:8,kind:99,masterVolume:NaN,extra:2});
 s.generate_sound();var a=s.sound.getBuffer().slice();s.generate_sound();
 s.params.pitch===1 && s.params.kind===0 && s.params.masterVolume===0.5 && !('extra' in s.params) && a.every((v,i)=>v===s.sound.getBuffer()[i]);`),true);
});
test('seeded randomness and finishing are finite, bounded and deterministic',()=>{
 const {run}=example();assert.equal(run(`var a=SoundDSP.rng(0.2),b=SoundDSP.rng(0.2);var equal=true;
 for(let i=0;i<100;i++) if(a()!==b())equal=false;
 var pcm=SoundDSP.finish(Float32Array.from({length:1000},(_,i)=>Math.sin(i)*10),1);
 equal && pcm[0]===0 && pcm[999]===0 && pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1);`),true);
});

test('loop previews loop their audio source and can be stopped',()=>{
 const {run}=example();assert.equal(run(`s.loop_preview=true;s.play();var loop=s.sound.source.loop;s.sound.stop();loop===true&&s.sound.source===null;`),true);
});
test('global locks refresh the state of specialized editors',()=>{
 const api=example();api.load('js/Tab.js');api.run('var SaveLoad={save_all_collections(){}};');
 assert.equal(api.run(`var refreshed=0;var tab=Object.create(Tab.prototype);
 Object.assign(tab,{synth:s,lock_buttons:{pitch:{}},update_locks(){},custom_editor:{update(){refreshed++;}}});
 tab.toggle_all_locks();s.locked_param('pitch') && refreshed===1;`),true);
});
test('new controls in older saved tabs start unlocked unless permanently locked',()=>{
 const api=example();api.load('js/Tab.js');assert.equal(api.run(`delete s.locked_params.pitch;
 var tab=Object.create(Tab.prototype);Object.assign(tab,{synth:s,load_param(){},update_ui(){}});
 tab.load_params(s);s.locked_param('pitch')===false && s.locked_param('masterVolume')===true;`),true);
});
