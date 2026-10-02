const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function context() {
    const ctx = vm.createContext({console:{log(){},error:console.error}, Float32Array});
    vm.runInContext(`const SAMPLE_RATE=44100; const AUDIO_CONTEXT={
        createBuffer(channels,length) { const pcm=new Float32Array(length); return {
            getChannelData(){return pcm;}, copyToChannel(data){pcm.set(data);}
        }; }
    };`,ctx);
    for (const file of ['js/globals.js','js/audio/AKWF.js','js/audio/BfxrWaveforms.js','js/audio/riffwave.js','js/audio/RealizedSound.js',
        'js/synths/templates.js','js/synths/SynthBase.js',
        'js/audio/ChattrLexicon.js','js/audio/ChattrFormants.js','js/audio/Chattr_Pronunciation.js','js/audio/Chattr_DSP.js',
        'js/synths/Chattr.js','js/Tab.js','js/SaveLoad.js']) {
        const filename=path.join(__dirname,'..',file);
        if (fs.existsSync(filename)) vm.runInContext(fs.readFileSync(filename,'utf8'),ctx);
    }
    return code=>vm.runInContext(code,ctx);
}
const plain=value=>JSON.parse(JSON.stringify(value));

test('TEXT parameters preserve strings and bound imported text',()=>{
    const run=context();
    assert.equal(run(`var s=new SynthBase(); s.param_info=[{type:'TEXT',name:'text',default_value:'Hello!',max_length:160}];
        s.params=s.default_params(); s.set_param('text','a'.repeat(200)); s.params.text.length;`),160);
});

test('speech is deterministic, audible, finite, faded and bounded',()=>{
    const run=context();
    const [a,b]=run(`var s=new Chattr(); s.set_param('text','Hello, little world!');
        s.generate_sound(); var a=s.sound.getBuffer().slice(); s.generate_sound(); [a,s.sound.getBuffer()];`);
    assert.deepEqual(a,b);
    assert.ok(a.length>44100/2 && a.length<44100*10);
    assert.equal(a[0],0); assert.equal(a.at(-1),0);
    assert.ok(a.some(v=>Math.abs(v)>0.05));
    assert.ok(a.every(v=>Number.isFinite(v)&&Math.abs(v)<1));
});

test('pace and punctuation change timing, questions change delivery',()=>{
    const run=context();
    const result=run(`var s=new Chattr(); s.set_param('text','hello there');
        var normal=Chattr_DSP.schedule(s.params); s.set_param('speed',1);
        var fast=Chattr_DSP.schedule(s.params); s.set_param('speed',0.5); s.set_param('text','hello, there...');
        var paused=Chattr_DSP.schedule(s.params); s.set_param('text','hello?');
        var question=Chattr_DSP.render(s.params); s.set_param('text','hello.');
        [normal.duration,fast.duration,paused.duration,question,Chattr_DSP.render(s.params)];`);
    assert.ok(result[1]<result[0]); assert.ok(result[2]>result[0]);
    assert.notDeepEqual(result[3],result[4]);
});

test('empty input, punctuation and zero volume produce silence',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(); ['', '   ', '...!?'].every(text=>{
        s.set_param('text',text); return Chattr_DSP.render(s.params).every(v=>v===0);
    }) && (s.set_param('text','Hello!'),s.set_param('masterVolume',0),Chattr_DSP.render(s.params).every(v=>v===0));`),true);
});

test('character recipes are audible and different, preserving words and locks',()=>{
    const run=context();
    const voices=run(`var s=new Chattr(); s.set_param('text','Tea for two?'); s.set_locked_param('pitch',true);
        var pitch=s.params.pitch; Chattr.characters.map(c=>{s.generate_character(c.id,false);
            return [c.name,s.params.text,s.params.pitch===pitch,Chattr_DSP.render(s.params)];});`);
    assert.equal(voices.length,9);
    const signatures=new Set();
    for(const [name,text,locked,pcm] of voices){
        assert.equal(text,'Tea for two?'); assert.ok(locked,name);
        let energy=0;
        for(const v of pcm){assert.ok(Number.isFinite(v)&&Math.abs(v)<1,name);energy+=v*v;}
        assert.ok(Math.sqrt(energy/pcm.length)>0.008,name);
        signatures.add(pcm.length+':'+energy.toFixed(5));
    }
    assert.equal(signatures.size,9);
});

test('randomize and mutate retain words, volume and locked voice controls',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(); s.set_param('text','My own words ~ 🐸'); s.set_locked_param('mouth',true);
        var mouth=s.params.mouth; s.randomize_params(); s.mutate_params();
        s.params.text==='My own words ~ 🐸' && s.params.mouth===mouth && s.params.masterVolume===0.5;`),true);
});

test('voice imports are bounded and Unicode text renders safely',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(); s.apply_params({text:'Héllo 世界 🐸',pitch:99,speed:-2,
        mouth:NaN,texture:99,unexpected:123});
        s.params.pitch===1 && s.params.speed===0 && s.params.texture===0 && !('unexpected' in s.params) &&
        Chattr_DSP.render(s.params).every(v=>Number.isFinite(v)&&Math.abs(v)<1);`),true);
});

test('share links round trip punctuation, tilde, quotes, newlines and Unicode',()=>{
    const run=context();
    const result=run(`var s=new Chattr(); tabs=[{synth:s}]; s.set_param('text','Hello ~ "friend"!\\n🐸 50% \\u263a');
        var link=SaveLoad.shallow_dict_serialize('Chattr','Voice',s.params);
        [s.params,SaveLoad.shallow_dict_deserialize(link)[2]];`);
    assert.deepEqual(plain(result[0]),plain(result[1]));
});

test('saved speech files round trip text and voice settings',()=>{
    const run=context();
    const result=run(`var s=new Chattr(); s.set_param('text','Oh! A letter for me?'); s.set_param('mouth',0.81);
        var tab=Object.create(Tab.prototype); Object.assign(tab,{name:'Chattr',synth:s,selected_file_index:0,
            files:[['Letter',JSON.stringify(s.params),JSON.stringify(s.params)]]});
        var file=tab.serialize_params(); var restored;
        tabs=[{synth:s,set_active_tab(){},create_new_sound_from_params(name,params){restored=params;}}];
        SaveLoad.load_serialized_synth(file); [s.params,restored];`);
    assert.deepEqual(plain(result[0]),plain(result[1]));
});

test('WAV export uses current text even without replay',()=>{
    const run=context();
    const [short,long]=run(`var s=new Chattr(); s.set_param('text','hi'); var short=s.generate_sound_uri();
        s.set_param('text','Hello, tiny traveller!'); [short,s.generate_sound_uri()];`);
    const a=Buffer.from(short.split(',')[1],'base64'),b=Buffer.from(long.split(',')[1],'base64');
    assert.equal(b.toString('ascii',0,4),'RIFF');assert.equal(b.readUInt32LE(24),44100);
    assert.ok(b.length>a.length*2);
});

test('typing in a textarea never triggers global sound shortcuts',()=>{
    const run=context();
    assert.equal(run(`var intercepted=false; var document={activeElement:{tagName:'TEXTAREA',nodeName:'TEXTAREA',
        classList:{contains(){return false;}}}};
        var tab=Object.create(Tab.prototype); tab.active=true; tab.toggle_all_locks=()=>intercepted=true;
        tab.on_key_down({key:'l',preventDefault(){},stopPropagation(){}}); !intercepted;`),true);
});

test('each voice control changes the rendered delivery',()=>{
    const run=context();
    const result=run(`var s=new Chattr(); s.set_param('text','A frog? Hello!');
        var base=Chattr_DSP.render(s.params); s.param_info.filter(Array.isArray).map(info=>{
            var old=s.params[info[2]]; s.set_param(info[2],old>0.5?0.1:0.9);
            var changed=Chattr_DSP.render(s.params); s.set_param(info[2],old);
            return [info[2],base.length!==changed.length || base.some((v,i)=>v!==changed[i])];
        });`);
    for(const [name,changed] of result) assert.ok(changed,name);
});

test('extreme controls and maximum-length input stay finite and bounded',()=>{
    const run=context();
    const results=run(`var s=new Chattr(); [0,1,2].map(texture=>{
        s.apply_params({text:'a!? '.repeat(80),texture,pitch:1,mouth:0,speed:0,expression:1,
            inflection:1,wobble:1,breath:1,grit:1,spacing:1,masterVolume:1});
        var pcm=Chattr_DSP.render(s.params);
        return [s.params.text.length,pcm.length,pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1)];
    });`);
    for(const [length,samples,bounded] of results){
        assert.equal(length,160); assert.ok(samples<44100*65); assert.ok(bounded);
    }
});

test('old numeric share links still deserialize unchanged',()=>{
    const run=context();
    assert.deepEqual(plain(run(`tabs=[{synth:{name:'Legacy',default_params(){return {a:0,b:0};}}}];
        SaveLoad.shallow_dict_deserialize('Legacy~Saved~0.25~-0.5')[2];`)),{a:0.25,b:-0.5});
});

test('text limits never split an emoji into an invalid surrogate',()=>{
    const run=context();
    const value=run(`var s=new Chattr(); s.set_param('text','a'.repeat(159)+'🐸'); s.params.text;`);
    assert.equal(value,'a'.repeat(159));
    assert.equal(value.isWellFormed(),true);
});

test('repeated punctuation produces one bounded pause',()=>{
    const run=context();
    const duration=run(`var s=new Chattr(); s.set_param('text','Hi'+'!'.repeat(150)); Chattr_DSP.schedule(s.params).duration;`);
    assert.ok(duration<2,`Repeated punctuation added ${duration} seconds`);
});

test('voice edits refresh the portrait with autoplay off',()=>{
    const run=context();
    assert.equal(run(`var updatedPitch=null; var s=new Chattr();
        SaveLoad.save_all_collections=()=>{};
        var tab=Object.create(Tab.prototype); Object.assign(tab,{synth:s,selected_file_index:0,
            files:[['Voice','{}','{}']],play_on_change:false,update_ablements(){},redraw_waveform(){},
            text_controls:{text:{update(){updatedPitch=s.params.pitch;}}}});
        tab.slider_changed('pitch',0.87); updatedPitch;`),0.87);
});

test('speech uses English phonemes, silent letters, vowel distinctions and stress',()=>{
    const run=context();
    const phones=text=>plain(run(`var s=new Chattr(); s.set_param('text',${JSON.stringify(text)});
        Chattr_DSP.schedule(s.params).events.map(e=>e.phone+(e.stress===null?'':e.stress));`));
    assert.deepEqual(phones('phone'),['F','OW1','N']);
    assert.deepEqual(phones('ship'),['SH','IH1','P']);
    assert.deepEqual(phones('sheep'),['SH','IY1','P']);
    assert.deepEqual(phones('knight'),phones('night'));
    assert.deepEqual(phones('two'),phones('too'));
    assert.deepEqual(phones('hello'),['HH','AH0','L','OW1']);
});

test('articulation and personality keep the same pronunciation',()=>{
    const run=context();
    const [a,b]=run(`var s=new Chattr(); s.set_param('text','The sheep found a phone.');
        s.apply_params({articulation:0,seed:0}); var a=Chattr_DSP.schedule(s.params).events.map(e=>e.phone);
        s.apply_params({articulation:1,seed:1}); [a,Chattr_DSP.schedule(s.params).events.map(e=>e.phone)];`);
    assert.ok(a.every(Boolean)); assert.deepEqual(a,b);
});

test('numbers are spoken and unfamiliar words have deterministic phonemes',()=>{
    const run=context();
    const [number,words,unknown]=run(`var s=new Chattr();
        function phones(text){s.set_param('text',text);return Chattr_DSP.schedule(s.params).events.map(e=>e.phone);}
        [phones('12'),phones('twelve'),phones('flomble')];`);
    assert.deepEqual(number,words); assert.ok(unknown.length>=4 && unknown.every(Boolean));
});

test('legacy Chattr links acquire articulation without shifting existing fields',()=>{
    const run=context();
    const [old,loaded]=run(`var s=new Chattr(); tabs=[{synth:s}];
        var old={...s.params}; delete old.articulation; delete old.waveType; old.text='My old voice?'; old.pitch=0.81;
        var link=SaveLoad.shallow_dict_serialize('Chattr','Old',old);
        [old,SaveLoad.shallow_dict_deserialize(link)[2]];`);
    assert.equal(loaded.articulation,0.8);
    delete loaded.articulation;
    assert.equal(loaded.waveType,-1); delete loaded.waveType;
    assert.deepEqual(plain(old),plain(loaded));
});

test('full articulation gives consonants their own excitation and vowels their glides',()=>{
    const run=context();
    const value=run(`var s=new Chattr(); s.apply_params({text:'sea boy',articulation:1});
        var score=Chattr_DSP.schedule(s.params);
        var hiss=score.events.find(e=>e.phone==='S'), vowel=score.events.find(e=>e.phone==='IY'), diphthong=score.events.find(e=>e.phone==='OY');
        [Chattr_DSP.target(s.params,hiss).voicing,Chattr_DSP.target(s.params,vowel).voicing,
            Chattr_DSP.target(s.params,diphthong).F2,Chattr_DSP.target(s.params,diphthong,true).F2];`);
    assert.equal(value[0],0); assert.equal(value[1],1); assert.ok(value[3]>value[2]*1.5);
});

test('legacy saved voices restore the same articulation regardless of selected voice',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(); var old={...s.params}; delete old.articulation;
        s.set_param('articulation',0.1); s.apply_params(old); s.params.articulation;`),0.8);
});

test('new voice controls start unlocked when loading a pre-articulation lock map',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(); delete s.locked_params.articulation;
        s.set_locked_param('pitch',true); var tab=Object.create(Tab.prototype);
        Object.assign(tab,{synth:s,load_param(){},update_ui(){}}); tab.load_params(s);
        var pitch=s.params.pitch; s.generate_character('clear_speaker',false);
        s.params.articulation===1 && s.params.pitch===pitch && s.locked_params.text;`),true);
});

test('number expansion at the slowest speed has a duration budget and reports shortening',()=>{
    const run=context();
    const result=run(`var s=new Chattr();s.apply_params({text:'9'.repeat(160),speed:0,spacing:1});
        var score=Chattr_DSP.schedule(s.params);[score.duration,score.truncated];`);
    assert.ok(result[0]<=60,`Scheduled ${result[0]} seconds`); assert.equal(result[1],true);
});

test('importing a legacy collection keeps new controls in lock-all operations',()=>{
    const run=context();
    assert.equal(run(`var s=new Chattr(), oldLocks={...s.locked_params};delete oldLocks.articulation;
        var tab=Object.create(Tab.prototype);Object.assign(tab,{synth:s,files:[],lock_buttons:{texture:{}},
            update_ui(){},update_ablements(){},update_locks(){},set_active_tab(){}});
        SaveLoad.save_all_collections=()=>{};tabs=[tab];
        SaveLoad.load_serialized_collection(JSON.stringify({Chattr:{files:[],selected_file_index:-1,
            create_new_sound:true,play_on_change:false,locked_params:oldLocks},active_tab_index:0}));
        tab.toggle_all_locks();s.locked_params.articulation===true && s.locked_params.pitch===true;`),true);
});
