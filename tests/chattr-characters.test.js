const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createContext, plain} = require('./helpers/synth-context');

function setup() {
    const api = createContext([]);
    for (const name of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP']) api.load(`js/audio/${name}.js`);
    api.load('js/synths/Chattr.js');
    return api;
}
const digest = pcm => crypto.createHash('sha256').update(Buffer.from(pcm.buffer)).digest('hex');
const rms = pcm => Math.sqrt(pcm.reduce((sum, value) => sum + value * value, 0) / pcm.length);

test('new Chattr voices use character grains and Clear Speaker selects legacy speech', () => {
    const {run} = setup();
    assert.deepEqual(plain(run(`(()=>{const s=new Chattr(); const mode=s.params.voiceMode;
        s.generate_character('clear_speaker',false);return [mode,s.params.voiceMode];})()`)), [1,0]);
});

test('letter grains and character identity repeat independently of text position', () => {
    const {run} = setup();
    const result = plain(run(`(()=>{const s=new Chattr();s.apply_params({voiceMode:1,text:'mama mama',expression:0});
        const a=Chattr_DSP.schedule(s.params);s.set_param('text','mama');const b=Chattr_DSP.schedule(s.params);
        return {a:a.events,b:b.events,identity:Chattr_DSP.characterVoice(s.params)};})()`));
    assert.equal(result.a.length,8);
    assert.equal(result.b.length,4);
    assert.deepEqual(result.a.slice(0,4).map(e=>[e.grain,e.pitch]),result.a.slice(4).map(e=>[e.grain,e.pitch]));
    assert.deepEqual(result.a.slice(0,4).map(e=>e.grain),result.b.map(e=>e.grain));
    assert.ok(result.identity.formant > 0);
});

test('all character textures have finite audible raw samples before output limiting', () => {
    const {run} = setup();
    const voices = run(`(()=>{const s=new Chattr();s.apply_params({voiceMode:1,text:'Hello there!',waveType:-1});
        return s.get_param_info('character').values.map(v=>{s.set_param('character',v[2]);
            return [v[0],Chattr_DSP.renderChatterRaw(s.params,Chattr_DSP.schedule(s.params)),Chattr_DSP.render(s.params)];});})()`);
    const signatures = new Set(), brightness = [];
    assert.equal(voices.length,8);
    for (const [name,raw,pcm] of voices) {
        assert.ok(raw.every(Number.isFinite),name);
        assert.ok(rms(raw) > 0.035 && rms(raw) < 0.9,`${name}: raw RMS ${rms(raw)}`);
        assert.ok(pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1),name);
        let difference=0;
        for(let i=1;i<raw.length;i++) difference+=(raw[i]-raw[i-1])**2;
        brightness.push(Math.sqrt(difference/raw.length)/rms(raw));
        signatures.add(digest(pcm));
    }
    assert.equal(signatures.size,8);
    assert.ok(Math.max(...brightness)>Math.min(...brightness)*1.7,'textures must change spectrum substantially');
});

test('timbre seed changes sound without moving any syllables', () => {
    const {run} = setup();
    const [a,b,c,timingA,timingB] = run(`(()=>{const s=new Chattr();s.apply_params({voiceMode:1,text:'mama',expression:0,wobble:0,voiceSeed:.12});
        const a=Chattr_DSP.render(s.params), b=Chattr_DSP.render(s.params), timing=Chattr_DSP.schedule(s.params).events.map(e=>[e.start,e.duration]);s.set_param('voiceSeed',.81);
        return [a,b,Chattr_DSP.render(s.params),timing,Chattr_DSP.schedule(s.params).events.map(e=>[e.start,e.duration])];})()`);
    assert.deepEqual(a,b);assert.notEqual(digest(a),digest(c));
    assert.deepEqual(timingA,timingB);
});

test('repeated character buttons change the instrument while preserving delivery and locks', () => {
    const {run} = setup();
    const result=plain(run(`(()=>{const s=new Chattr();Math.random=SoundDSP.rng(.762);s.apply_params({text:'Tea with me?',speed:.72,spacing:.66,seed:.21});
        s.set_locked_param('mouth',true);const before=Chattr_DSP.schedule(s.params).events.map(e=>[e.start,e.duration]);
        s.generate_character('tiny_alien');const a={...s.params};s.generate_character('tiny_alien');
        return {a,b:{...s.params},before,after:Chattr_DSP.schedule(s.params).events.map(e=>[e.start,e.duration])};})()`));
    assert.deepEqual(result.before,result.after);
    for(const key of ['text','speed','spacing','seed','articulation','expression','wobble','inflection','mouth']) assert.equal(result.a[key],result.b[key],key);
    assert.notEqual(result.a.voiceSeed,result.b.voiceSeed);
    assert.notEqual(result.a.pitch,result.b.pitch);
});

test('new friends stay in character mode, vary timbre, and preserve words and locks', () => {
    const {run} = setup();
    const result = plain(run(`(()=>{const s=new Chattr();Math.random=SoundDSP.rng(.471);s.set_param('text','My letter to you.');
        s.set_param('pitch',.23);s.set_locked_param('pitch',true);
        return Array.from({length:24},()=>{s.randomize_params();return {...s.params};});})()`));
    assert.ok(new Set(result.map(p=>p.character)).size>=5);
    for(const p of result){assert.equal(p.voiceMode,1);assert.equal(p.text,'My letter to you.');assert.equal(p.pitch,.23);}
});

test('old complete voices select speech regardless of the current character', () => {
    const {run} = setup();
    assert.deepEqual(plain(run(`(()=>{const s=new Chattr();const old={...s.params};delete old.voiceMode;delete old.character;
        s.set_param('character',7);s.apply_params(old);return [s.params.voiceMode,s.params.character];})()`)),[0,0]);
});

test('speech mode retains existing raw-buffer snapshots for vocal and palette sources', () => {
    const {run} = setup();
    for(const [waveType,hash] of [[-1,'c37b94b4311ca84983aa13befc7fae15e02418b7ca3ab3bb6f32579c3c92275c'],
        [0,'45340c085d1e93edb554bbb02ca0e845d555263b808bdd6619955c0ab6d381ac'],
        [11,'04f052b6c603582c07f3ac34b91b0fcd7ced6925728384a4b8b27cdd2395729a']]) {
        const pcm=run(`(()=>{const s=new Chattr();s.apply_params({voiceMode:0,text:'Hello, little world?',seed:.37,waveType:${waveType}});
            return Chattr_DSP.render(s.params);})()`);
        assert.equal(pcm.length,77841);assert.equal(digest(pcm),hash);
    }
});

test('every waveform keeps character grain timing and renders finite raw extremes', () => {
    const {run} = setup();
    const results=run(`(()=>{const s=new Chattr();s.apply_params({voiceMode:1,text:'Hello!',pitch:1,mouth:0,articulation:1,
        expression:1,wobble:1,grit:1,breath:1,inflection:1,speed:1,masterVolume:1});
        return s.get_param_info('waveType').values.map((v,i)=>{s.set_param('waveType',v[2]);s.set_param('character',i%8);
            const score=Chattr_DSP.schedule(s.params);return [v[0],score.events.map(e=>e.start),Chattr_DSP.renderChatterRaw(s.params,score)];});})()`);
    for(const [name,starts,raw] of results){assert.deepEqual(starts,results[0][1]);assert.ok(raw.every(Number.isFinite),name);assert.ok(rms(raw)>.008,name);}
});
