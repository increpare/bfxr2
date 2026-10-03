const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function context() {
    const storage = new Map();
    const ctx = vm.createContext({console: {log() {}, error: console.error}, Float32Array,
        localStorage: {setItem(key,value){storage.set(key,value);},getItem(key){return storage.get(key);}}});
    // Only the browser's audio-device boundary is substituted; DSP and WAV encoding are real.
    vm.runInContext(`const SAMPLE_RATE = 44100; const AUDIO_CONTEXT = {
        createBuffer(channels, length, rate) { const pcm = new Float32Array(length); return {
            getChannelData() { return pcm; }, copyToChannel(data) { pcm.set(data); }
        }; }
    };`, ctx);
    for (const source of ['js/globals.js','js/audio/AKWF.js','js/audio/BfxrWaveforms.js', 'js/audio/riffwave.js', 'js/audio/RealizedSound.js',
        'js/synths/templates.js', 'js/synths/SynthBase.js', 'js/audio/Transfxr_DSP.js',
        'js/synths/PresetFamily.js', 'js/synths/TransfxrPresets.js',
        'js/synths/Transfxr.js', 'js/Tab.js', 'js/SaveLoad.js']) {
        if (fs.existsSync(path.join(root, source))) vm.runInContext(fs.readFileSync(path.join(root, source), 'utf8'), ctx);
    }
    return code => vm.runInContext(code, ctx);
}
const plain = v => JSON.parse(JSON.stringify(v));

test('transition defaults contain independent start, end and curve values', () => {
    const run = context();
    const result = run(`var s = new SynthBase(); s.param_info = [{type:'KNOB_TRANSITION', name:'pitch',
        default_value_l:0.2, default_value_r:0.8, default_tween:'Linear', min:0, max:1}];
        s.default_params();`);
    assert.deepEqual(plain(result.pitch), {start:0.2, end:0.8, curve:'Linear'});
});

test('Transfxr exposes no noise control and migrates old noise curves to White morphing', () => {
    const run=context();
    const result=run(`var s=new Transfxr();var names=s.param_info.map(info=>s.get_param_normalized(info).name);
        s.apply_params({noise:{start:0.25,end:0.8,curve:'Ease In'},waveTo:-1});
        [names.includes('noise'), 'noise' in s.params,s.params.waveTo,s.params.morph];`);
    assert.deepEqual(plain(result),[false,false,7,{start:0.25,end:0.8,curve:'Ease In'}]);
});

test('old positional Transfxr links migrate their noise texture', () => {
    const run=context();
    const result=run(`var s=new Transfxr();tabs=[{synth:s}];
        var old={...s.params,noise:{start:0.2,end:0.6,curve:'Linear'}};
        var link='Transfxr~Old~'+Object.keys(old).sort().map(k=>JSON.stringify(old[k])).join('~');
        var restored=SaveLoad.shallow_dict_deserialize(link)[2];
        [restored.waveTo,restored.morph,'noise' in restored];`);
    assert.deepEqual(plain(result),[7,{start:0.2,end:0.6,curve:'Linear'},false]);
});

test('transition edits clamp endpoints, copy input and respect locks', () => {
    const run = context();
    const result = run(`var s = new Transfxr(); var p = {start:-1, end:2, curve:'Linear'};
        s.set_param('pitch', p); p.start = 0.7;
        var before = JSON.stringify(s.params.pitch); s.set_locked_param('pitch', true);
        s.randomize_params(); s.mutate_params();
        [before, JSON.stringify(s.params.pitch), s.params.masterVolume];`);
    assert.deepEqual(JSON.parse(result[0]), {start:0, end:1, curve:'Linear'});
    assert.equal(result[0], result[1]);
    assert.equal(result[2], 0.5);
});

test('all curves stay bounded, with documented endpoints', () => {
    const run = context();
    assert.equal(run(`Transfxr_DSP.curves.every(([name, curve]) => {
        for (let i=0; i<=1000; i++) { let v=curve(i/1000); if (!Number.isFinite(v)||v<0||v>1) return false; }
        return Math.abs(curve(0)) < 1e-9 && Math.abs(curve(1) - (name==='Triangle'||name==='Pulse' ? 0:1)) < 1e-9;
    })`), true);
});

test('audio is deterministic, finite, bounded, faded at both ends and correctly sized', () => {
    const run = context();
    const [a,b] = run(`var s = new Transfxr(); s.set_param('duration', 0.5); s.set_param('echo',0);
        s.generate_sound(); var a = s.sound.getBuffer().slice(); s.generate_sound(); [a,s.sound.getBuffer()];`);
    assert.equal(a.length, 22050);
    assert.deepEqual(a,b);
    assert.equal(a[0],0);
    assert.ok(Math.abs(a.at(-1)) < 0.0001);
    assert.ok(a.some(v => Math.abs(v)>0.05));
    assert.ok(a.every(v => Number.isFinite(v)&&Math.abs(v)<1));
});

test('pitch transition raises measured oscillator frequency', () => {
    const run = context();
    const pcm = run(`var s = new Transfxr(); s.apply_params({duration:1,attack:0,release:0,echo:0,waveType:0,
        pitch:{start:0.3,end:0.7,curve:'Linear'}, tone:{start:1,end:1,curve:'Linear'},
        vibrato:{start:0,end:0,curve:'Linear'},
        level:{start:0.8,end:0.8,curve:'Linear'}}); s.generate_sound(); s.sound.getBuffer();`);
    function crossings(from,to) {
        let count=0; for(let i=Math.floor(from*44100); i<to*44100; i++) if(pcm[i]<=0&&pcm[i+1]>0) count++;
        return count/(to-from);
    }
    assert.ok(crossings(0.7,0.8) > crossings(0.2,0.3)*2);
});

test('master volume zero produces silence, and exports a 44.1 kHz WAV', () => {
    const run = context();
    const uri = run(`var s=new Transfxr(); s.set_param('masterVolume',0); s.generate_sound(); s.generate_sound_uri();`);
    const wav=Buffer.from(uri.split(',')[1], 'base64');
    assert.equal(wav.toString('ascii',0,4),'RIFF');
    assert.equal(wav.readUInt32LE(24),44100);
    assert.ok(wav.subarray(44).every(v=>v===0));
});

test('all example recipes render audible and distinct sounds', () => {
    const run = context();
    const examples=run(`var s=new Transfxr(); s.templates.filter(t=>t[2].startsWith('generate_')).map(t=>{
        s[t[2]](); s.generate_sound(); return [t[0],s.sound.getBuffer().slice()];
    });`);
    assert.ok(examples.length>=8);
    const signatures=new Set();
    for(const [name,pcm] of examples) {
        let energy=0, peak=0;
        for(const v of pcm) { assert.ok(Number.isFinite(v),name); energy+=v*v; peak=Math.max(peak,Math.abs(v)); }
        assert.ok(Math.sqrt(energy/pcm.length)>0.005,name+' is too quiet');
        assert.ok(peak<1,name+' clips');
        signatures.add(pcm.length+':'+energy.toFixed(3));
    }
    assert.equal(signatures.size,examples.length);
});

test('share links round trip transitions without breaking numeric links', () => {
    const run=context();
    const result=run(`var s=new Transfxr(); tabs=[{synth:s}];
        var link=SaveLoad.shallow_dict_serialize('Transfxr','Portal',s.params);
        [s.params,SaveLoad.shallow_dict_deserialize(link)[2]];`);
    assert.deepEqual(plain(result[0]),plain(result[1]));
});

test('old collections may omit the newly registered Transfxr tab', () => {
    const run=context();
    assert.equal(run(`var selected=false; var untouched={files:[['Keep me']],synth:{name:'Transfxr'}};
        tabs=[{synth:{name:'Bfxr'},update_ui(){},set_active_tab(){selected=true}},untouched];
        SaveLoad.load_serialized_collection(JSON.stringify({Bfxr:{files:[],selected_file_index:-1,
            create_new_sound:true,play_on_change:false,locked_params:{}},active_tab_index:0}));
        selected && untouched.files[0][0]==='Keep me';`),true);
});

test('export reflects edits even when the user has not pressed play again', () => {
    const run=context();
    const [before, after]=run(`var s=new Transfxr(); s.set_param('echo',0); s.set_param('duration',0.1);
        var first=s.generate_sound_uri(); s.set_param('duration',0.2); [first,s.generate_sound_uri()];`);
    assert.equal(Buffer.from(before.split(',')[1],'base64').length,44+4410*2);
    assert.equal(Buffer.from(after.split(',')[1],'base64').length,44+8820*2);
});

test('imports clamp and recover invalid parameters without retaining arbitrary fields', () => {
    const run=context();
    assert.equal(run(`var s=new Transfxr(); s.apply_params({duration:-2,waveType:99,echo:Infinity,
        pitch:{start:NaN,end:4,curve:'No such curve'},obsolete:123});
        s.params.duration===0.05 && s.params.waveType===0 && s.params.echo===0.15 &&
        s.params.pitch.start===0.48 && s.params.pitch.end===1 && !('obsolete' in s.params);`),true);
});

test('sound files round trip a complete transition through SaveLoad', () => {
    const run=context();
    const result=run(`var s=new Transfxr(); s.generate_example('portal_bloom',false);
        var tab=Object.create(Tab.prototype); tab.name='Transfxr'; tab.synth=s; tab.selected_file_index=0;
        tab.files=[['PortalBloom',JSON.stringify(s.params),JSON.stringify(s.params)]];
        var serialized=tab.serialize_params(); var restored;
        tabs=[{synth:s,set_active_tab(){},create_new_sound_from_params(name,params){restored={name,params};}}];
        SaveLoad.load_serialized_synth(serialized); [s.params,restored];`);
    assert.equal(result[1].name,'PortalBloom');
    assert.deepEqual(plain(result[0]),plain(result[1].params));
});

test('preset generation and mutation preserve a locked transition as a unit', () => {
    const run=context();
    assert.equal(run(`var s=new Transfxr(); s.set_param('pitch',{start:0.2,end:0.9,curve:'Steps'});
        s.set_locked_param('pitch',true); var before=JSON.stringify(s.params.pitch);
        Transfxr.examples.every(ex=>{s.generate_example(ex.id);s.mutate_params();return JSON.stringify(s.params.pitch)===before;});`),true);
});

test('extreme valid controls and random sounds remain finite within the output range', () => {
    const run=context();
    assert.equal(run(`var s=new Transfxr(); var valid=true;
        for(let i=0;i<16;i++) {
            s.randomize_params(); s.set_param('duration',i===0?4:0.06);
            if(i<8) s.apply_params({resonance:1,echo:0.8,masterVolume:1,waveType:i%4,
                tone:{start:i%2,end:1-i%2,curve:'Steps'}});
            s.generate_sound(); if(!s.sound.getBuffer().every(v=>Number.isFinite(v)&&Math.abs(v)<1)) valid=false;
        } valid;`),true);
});

test('legacy Bfxr and Footsteppr numeric links keep their exact wire format', () => {
    const run=context();
    assert.deepEqual(plain(run(`tabs=[{synth:{name:'Bfxr',default_params(){return {waveType:2,masterVolume:0.5};}}}];
        var link=SaveLoad.shallow_dict_serialize('Bfxr','Coin',{waveType:2,masterVolume:0.5});
        [link,SaveLoad.shallow_dict_deserialize(link)];`)),['Bfxr~Coin~0.5~2',['Bfxr','Coin',{masterVolume:0.5,waveType:2}]]);
});

test('export preserves an already-rendered Bfxr noise preview', () => {
    const run=context();
    for(const file of ['js/audio/Bfxr_DSP.js','js/synths/Bfxr.js']) run(fs.readFileSync(path.join(root,file),'utf8'));
    assert.equal(run(`var s=new Bfxr(); s.set_param('waveType',3); s.generate_sound();
        var original=s.sound; s.generate_sound_uri(); s.sound===original;`),true);
});

test('silent regeneration stops the previous playing source', () => {
    const run=context();
    assert.equal(run(`var s=new Transfxr(); var stopped=false; s.sound={stop(){stopped=true;}};
        s.generate_sound(); stopped;`),true);
});

test('replacing the current example with autoplay off persists and redraws it', () => {
    const run=context();
    const result=run(`var s=new Transfxr(); var saved=0,drawn=0;
        SaveLoad.save_all_collections=()=>saved++;
        var tab=Object.create(Tab.prototype); Object.assign(tab,{synth:s,create_new_sound:false,
            play_on_change:false,files:[['Original','{}','{}']],selected_file_index:0,
            update_ui(){},redraw_waveform(){drawn++;}});
        s.generate_example('laser_zip',false); tab.create_new_sound_from_params('Laser',s.params);
        [saved,drawn,tab.files.length,JSON.parse(tab.files[0][1]).pitch.curve];`);
    assert.deepEqual(plain(result),[1,1,1,'Ease Out']);
});

test('opening a collection persists it for the next reload', () => {
    const run=context();
    assert.equal(run(`var saved=0; SaveLoad.save_all_collections=()=>saved++;
        tabs=[{synth:{name:'Transfxr'},update_ui(){},set_active_tab(){}}];
        SaveLoad.load_serialized_collection(JSON.stringify({Transfxr:{files:[],selected_file_index:-1,
            create_new_sound:true,play_on_change:false,locked_params:{}},active_tab_index:0})); saved;`),1);
});

test('the WAV export button downloads the current rendered PCM', () => {
    const run=context();
    const result=run(`var download;
        var document={createElement(){return {click(){download={href:this.href,name:this.download};},remove(){}};}};
        var s=new Transfxr(); s.generate_example('laser_zip',false); s.set_param('echo',0);
        var tab=Object.create(Tab.prototype); tab.synth=s; tab.files=[['LaserZip']];tab.selected_file_index=0;
        tab.export_wav_button_clicked(); download;`);
    assert.equal(result.name,'LaserZip.wav');
    const wav=Buffer.from(result.href.split(',')[1],'base64');
    assert.equal(wav.length,44+Math.round(0.22*44100)*2);
    assert.equal(wav.readUInt32LE(24),44100);
});

test('collection import synchronizes visible generation and playback checkboxes', () => {
    const run=context();
    assert.equal(run(`var nodes={Transfxr_checkbox_create_new_sound:{checked:false},Transfxr_checkbox_loop:{checked:false}};
        var document={getElementById(id){return nodes[id];}};
        var tab=Object.create(Tab.prototype); Object.assign(tab,{name:'Transfxr',synth:{name:'Transfxr'},
            update_ui_file_list(){},update_ui_params(){},update_ablements(){},update_locks(){},set_active_tab(){}});
        tabs=[tab]; SaveLoad.load_serialized_collection(JSON.stringify({Transfxr:{files:[],selected_file_index:-1,
            create_new_sound:true,play_on_change:true,locked_params:{}},active_tab_index:0}));
        nodes.Transfxr_checkbox_create_new_sound.checked && nodes.Transfxr_checkbox_loop.checked;`),true);
});
