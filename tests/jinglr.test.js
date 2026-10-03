const test = require('node:test');
const assert = require('node:assert/strict');
const {createContext, plain} = require('./helpers/synth-context');

function setup() {
    const api = createContext(['Jinglr']);
    api.run('Math.random = SoundDSP.rng(0.314159); var s = new Jinglr();');
    return api;
}

test('saved phrases render deterministic, audible, finite PCM', () => {
    const {run} = setup();
    const [a,b] = run(`s.generate_discovery(); var a = Jinglr_DSP.render(s.params);
        [a,Jinglr_DSP.render(JSON.parse(JSON.stringify(s.params)))];`);
    assert.deepEqual(a,b);
    assert.ok(a.some(value => Math.abs(value) > 0.03));
    assert.ok(a.every(value => Number.isFinite(value) && Math.abs(value) < 1));
    assert.ok(a[0]===0);
    assert.ok(a.at(-1)===0);
});

test('scale degrees map to musical pitches and beat durations', () => {
    const {run} = setup();
    const score = plain(run(`s.apply_params({key:0,scale:0,octave:4,tempo:120,swing:0,
        phrase:JSON.stringify([{degree:0,beats:1},{degree:2,beats:0.5},{degree:4,beats:2},{degree:null,beats:1}])});
        Jinglr_DSP.schedule(s.params);`));
    assert.deepEqual(score.events.map(event => event.midi),[60,64,67,null]);
    assert.deepEqual(score.events.map(event => event.start),[0,0.5,0.75,1.75]);
    assert.deepEqual(score.events.map(event => event.duration),[0.5,0.25,1,0.5]);
    assert.equal(score.duration,2.25);
});

test('key, scale, tempo and each instrument change the realized phrase', () => {
    const {run} = setup();
    const result = run(`s.apply_params({phrase:JSON.stringify([{degree:2,beats:1},{degree:4,beats:1}]),scale:0,key:0});
        var base=Jinglr_DSP.render(s.params); var before=Jinglr_DSP.schedule(s.params);
        s.set_param('scale',1); var minor=Jinglr_DSP.schedule(s.params);
        s.set_param('key',5); var shifted=Jinglr_DSP.schedule(s.params);
        s.set_param('tempo',220); var fast=Jinglr_DSP.schedule(s.params);
        var voices=[0,1,2,3,4,5,6,7].map(instrument=>{s.set_param('instrument',instrument);return Jinglr_DSP.render(s.params);});
        [before,minor,shifted,fast,voices];`);
    assert.equal(result[0].events[0].midi-result[1].events[0].midi,1);
    assert.equal(result[2].events[0].midi-result[1].events[0].midi,5);
    assert.ok(result[3].duration<result[2].duration);
    for(let i=0;i<result[4].length;i++) for(let j=0;j<i;j++) assert.notDeepEqual(result[4][i],result[4][j]);
});

test('rendered note frequencies and onsets agree with the saved score', () => {
    const {run} = setup();
    const pcm = run(`s.apply_params({instrument:3,brightness:0,echo:0,tempo:120,octave:4,key:0,scale:0,
        phrase:'[{"degree":null,"beats":1},{"degree":0,"beats":1},{"degree":4,"beats":1}]'});
        Jinglr_DSP.render(s.params);`);
    const frequencyAt = seconds => {
        const crossings=[];
        for(let i=Math.floor(seconds*44100);i<(seconds+0.15)*44100;i++) {
            if(pcm[i-1]<=0 && pcm[i]>0) crossings.push(i);
        }
        return 44100*(crossings.length-1)/(crossings.at(-1)-crossings[0]);
    };
    assert.ok(pcm.slice(1000,20000).every(value=>Math.abs(value)<0.001));
    assert.ok(Math.abs(frequencyAt(0.55)-261.6256)<1);
    assert.ok(Math.abs(frequencyAt(1.05)-391.9954)<1);
});

test('swing, brightness, decay and echo each audibly alter the saved score', () => {
    const {run}=setup();
    const results=run(`['swing','brightness','decay','echo'].map(name=>{
        s.reset_params(); var base=Jinglr_DSP.render(s.params);
        s.set_param(name,name==='swing' ? 0.5 : 0.8);
        var changed=Jinglr_DSP.render(s.params);
        return [name,base.length!==changed.length || base.some((value,index)=>value!==changed[index])];
    });`);
    for(const [name,changed] of results) assert.ok(changed,name);
});

test('all category buttons produce fresh stored melodies and preserve locked controls', () => {
    const {run} = setup();
    const rows = run(`s.recipes.map(recipe=>{
        s.generate_recipe(recipe.id); var first=s.params.phrase; var seed=s.params.seed;
        s.generate_recipe(recipe.id); var second=s.params.phrase;
        s.set_locked_param('tempo',true); s.set_locked_param('scale',true); s.set_locked_param('phrase',true);
        var tempo=s.params.tempo, scale=s.params.scale; s.generate_recipe(recipe.id);
        var result=[recipe.name,first,second,seed!==s.params.seed,
            s.melody_matches_seed() && s.params.tempo===tempo && s.params.scale===scale,
            Jinglr_DSP.render(s.params).some(v=>Math.abs(v)>0.01)];
        s.set_locked_param('tempo',false); s.set_locked_param('scale',false); s.set_locked_param('phrase',false);
        return result;
    });`);
    assert.ok(rows.length>=8);
    for(const [name,first,second,fresh,locked,audible] of rows) {
        assert.notEqual(first,second,name); assert.ok(fresh,name); assert.ok(locked,name); assert.ok(audible,name);
    }
});

test('phrase edits change audio and pure rests stay silent', () => {
    const {run} = setup();
    const [a,b,silence] = run(`s.set_param('phrase','[{"degree":0,"beats":1}]');
        var a=Jinglr_DSP.render(s.params); s.set_param('phrase','[{"degree":7,"beats":1}]');
        var b=Jinglr_DSP.render(s.params); s.set_param('phrase','[{"degree":null,"beats":2}]');
        [a,b,Jinglr_DSP.render(s.params)];`);
    assert.notDeepEqual(a,b);
    assert.ok(silence.length>=44100/2);
    assert.ok(silence.every(value=>value===0));
});

test('note count, contour and rhythm controls rebuild persistent phrase data', () => {
    const {run} = setup();
    const result = plain(run(`s.set_param('noteCount',8); var eight=JSON.parse(s.params.phrase);
        s.set_param('contour',1); var down=JSON.parse(s.params.phrase);
        s.set_param('rhythm',1); var dotted=JSON.parse(s.params.phrase);
        [eight,down,dotted];`));
    assert.equal(result[0].length,8);
    assert.ok(result[1][0].degree>result[1].at(-1).degree);
    assert.notDeepEqual(result[1].map(n=>n.beats),result[2].map(n=>n.beats));
});

test('phrase JSON is validated and exact imported notes survive apply and share round trips', () => {
    const {run,load} = setup();
    load('js/Tab.js'); load('js/SaveLoad.js');
    const result = plain(run(`s.apply_params({noteCount:8,contour:1,rhythm:1,seed:0.7,
        phrase:'[{"degree":-2,"beats":0.75},{"degree":null,"beats":2}]'});
        var saved=JSON.parse(JSON.stringify(s.params)); var copy=new Jinglr(); copy.apply_params(saved);
        tabs=[{synth:s}]; var link=SaveLoad.shallow_dict_serialize('Jinglr','Own phrase',s.params);
        var restored=SaveLoad.shallow_dict_deserialize(link)[2];
        s.set_param('phrase','not json'); var fallback=JSON.parse(s.params.phrase);
        s.set_param('phrase',JSON.stringify(Array.from({length:30},()=>({degree:200,beats:-10}))));
        [saved,copy.params,restored,fallback,JSON.parse(s.params.phrase)];`));
    assert.deepEqual(result[0],result[1]); assert.deepEqual(result[0],result[2]);
    assert.ok(result[3].length>0 && result[3].length<=12);
    assert.equal(result[4].length,12);
    assert.ok(result[4].every(note=>note.degree===14 && note.beats===0.25));
});

test('mutate preserves locked phrase, timbre and volume', () => {
    const {run} = setup();
    assert.equal(run(`s.set_param('phrase','[{"degree":3,"beats":0.75},{"degree":null,"beats":1}]');
        s.set_locked_param('phrase',true); s.set_locked_param('instrument',true);
        var phrase=s.params.phrase, instrument=s.params.instrument;
        s.mutate_params();
        s.params.phrase===phrase && s.params.instrument===instrument && s.params.masterVolume===0.5;`),true);
});

test('maximum score and extreme settings remain bounded in length and amplitude', () => {
    const {run} = setup();
    const results = run(`[0,1,2,3,4,5,6,7].map(instrument=>{
        s.apply_params({phrase:JSON.stringify(Array.from({length:12},(_,i)=>({degree:i%2?-7:14,beats:2}))),
            instrument,key:11,octave:6,tempo:60,swing:0.6,brightness:1,decay:1,echo:0.8,masterVolume:1});
        var pcm=Jinglr_DSP.render(s.params);
        return [pcm.length,pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<1)];
    });`);
    for(const [length,bounded] of results) {assert.ok(length<44100*28);assert.ok(bounded);}
});

test('eight instrument buttons generate fresh voices without changing melody settings', () => {
    const {run}=setup();
    const results=run(`var original=JSON.stringify(Object.fromEntries(Object.entries(s.params)
        .filter(([key])=>!['instrument','instrumentSeed'].includes(key))));
        s.get_param_info('instrument').values.map(option=>{
            s.generate_instrument(option[2]); var first=s.params.instrumentSeed;
            s.generate_instrument(option[2]);
            return [option[0],s.params.instrument===option[2],first!==s.params.instrumentSeed,
                original===JSON.stringify(Object.fromEntries(Object.entries(s.params)
                    .filter(([key])=>!['instrument','instrumentSeed'].includes(key))))];
        });`);
    assert.equal(results.length,8);
    for(const [name,family,fresh,melody] of results) {assert.ok(family,name);assert.ok(fresh,name);assert.ok(melody,name);}
});

test('instrument category and instrument character locks operate independently', () => {
    const {run}=setup();
    const result=plain(run(`s.set_param('instrument',3); s.set_param('instrumentSeed',12345);
        s.set_locked_param('instrument',true); s.generate_instrument(7);
        var lockedFamily=[s.params.instrument,s.params.instrumentSeed!==12345];
        s.set_locked_param('instrument',false); s.set_locked_param('instrumentSeed',true);
        var seed=s.params.instrumentSeed; s.generate_instrument(6);
        [lockedFamily,s.params.instrument,s.params.instrumentSeed===seed];`));
    assert.deepEqual(result,[[3,true],6,true]);
});

test('instrument seeds reproduce independent voices for all families', () => {
    const {run}=setup();
    const result=run(`[0,1,2,3,4,5,6,7].map(instrument=>{
        s.apply_params({instrument,instrumentSeed:12537,phrase:'[{"degree":0,"beats":1}]',echo:0});
        var first=Jinglr_DSP.render(s.params);
        s.set_param('instrumentSeed',86302); var second=Jinglr_DSP.render(s.params);
        s.set_param('instrumentSeed',12537); var restored=Jinglr_DSP.render(s.params);
        var before=s.params.phrase; s.apply_params({seed:0.8324}); var sameNotes=Jinglr_DSP.render(s.params);
        return [instrument,first,second,restored,sameNotes,s.params.phrase===before];
    });`);
    for(const [instrument,first,second,restored,sameNotes,phrasePreserved] of result) {
        assert.notDeepEqual(first,second,'voice variation '+instrument);
        assert.deepEqual(first,restored,'voice reproducibility '+instrument);
        assert.deepEqual(first,sameNotes,'independent melody seed '+instrument);
        assert.ok(phrasePreserved);
    }
});

test('instrument variation changes spectral balance and envelope, not only phase', () => {
    const {run}=setup();
    const voices=run(`[0,1,2,3,4,5,6,7].map(instrument=>[12537,86302].map(instrumentSeed=>{
        s.apply_params({instrument,instrumentSeed,phrase:'[{"degree":0,"beats":2}]',echo:0,tempo:120});
        return Jinglr_DSP.render(s.params);
    }));`);
    const measures=pcm=>{
        let early=0,late=0,difference=0,total=0;
        for(let i=1;i<pcm.length;i++) {
            const energy=pcm[i]*pcm[i]; total+=energy;
            if(i<4410) early+=energy;
            if(i>=8820 && i<17640) late+=energy;
            difference+=(pcm[i]-pcm[i-1])**2;
        }
        return [late/Math.max(early,1e-12),difference/Math.max(total,1e-12)];
    };
    for(let instrument=0;instrument<voices.length;instrument++) {
        const a=measures(voices[instrument][0]),b=measures(voices[instrument][1]);
        assert.ok(Math.abs(a[0]-b[0])>0.005,'envelope '+instrument);
        assert.ok(Math.abs(a[1]-b[1])>0.00001,'spectrum '+instrument);
    }
});

test('presets and randomize refresh locked character while mutate retains it', () => {
    const {run}=setup();
    assert.equal(run(`s.recipes.every(recipe=>{
        s.generate_recipe(recipe.id); var previous=s.params.instrumentSeed;
        s.generate_recipe(recipe.id); var fresh=s.params.instrumentSeed!==previous;
        s.set_locked_param('instrumentSeed',true); var locked=s.params.instrumentSeed;
        s.generate_recipe(recipe.id);var presetFresh=s.params.instrumentSeed!==locked;
        locked=s.params.instrumentSeed;s.randomize_params();var randomFresh=s.params.instrumentSeed!==locked;
        locked=s.params.instrumentSeed;s.mutate_params();
        var retained=presetFresh && randomFresh && s.params.instrumentSeed===locked;
        s.set_locked_param('instrumentSeed',false);
        return fresh && retained;
    });`),true);
});

test('instrument seed imports, randomize and mutate retain bounded integers', () => {
    const {run}=setup();
    assert.deepEqual(plain(run(`[-20,12345.7,200000,NaN].map(instrumentSeed=>{
        s.set_param('instrumentSeed',instrumentSeed);return s.params.instrumentSeed;
    });`)),[0,12346,99999,42731]);
    assert.equal(run(`Array.from({length:50},()=>{
        s.randomize_params();s.mutate_params();return s.params.instrumentSeed;
    }).every(seed=>Number.isInteger(seed)&&seed>=0&&seed<=99999);`),true);
});

test('displayed five-digit melody seed reconstructs generated and mutated phrases', () => {
    const {run}=setup();
    assert.equal(run(`s.recipes.every(recipe=>{
        s.generate_recipe(recipe.id); s.generate_phrase(true); s.mutate_params();
        var code=Math.round(s.params.seed*99999), phrase=s.params.phrase;
        var valid=s.params.seed===code/99999 && s.melody_matches_seed();
        s.set_param('seed',code/99999);
        return valid && s.params.phrase===phrase;
    });`),true);
    assert.equal(run(`s.set_param('seed',0.123456789); s.params.seed===12346/99999 && s.melody_matches_seed();`),true);
});

test('legacy custom phrases retain notes and report when they differ from the seed', () => {
    const {run}=setup();
    const result=plain(run(`s.set_param('instrumentSeed',12345);
        s.apply_params({seed:0.123456789,instrument:3,phrase:'[{"degree":null,"beats":1}]'});
        var imported=[s.params.instrumentSeed,s.params.phrase,s.melody_matches_seed()];
        s.set_param('instrumentSeed',12345);s.apply_params({tempo:170});
        var preserved=s.params.instrumentSeed===12345;
        s.set_locked_param('phrase',true); var before=JSON.stringify(s.params);s.melody_matches_seed();
        [imported,preserved,before===JSON.stringify(s.params)];`));
    assert.deepEqual(result,[[42731,'[{"degree":null,"beats":1}]',false],true,true]);
});

test('preset buttons reseed both halves despite obsolete melody and instrument locks', () => {
    const {run}=setup();
    assert.equal(run(`s.set_param('tempo',137);s.set_locked_param('tempo',true);
        for(const name of ['phrase','seed','instrument','instrumentSeed'])s.set_locked_param(name,true);
        Math.random=()=>0.25;
        s.recipes.every(recipe=>[0,1,2].every(()=>{
            var melody=s.params.seed, voice=s.params.instrumentSeed;
            s['generate_'+recipe.id]();
            return s.params.seed!==melody && s.params.instrumentSeed!==voice &&
                s.melody_matches_seed() && s.params.tempo===137 && s.params.masterVolume===0.5;
        }));`),true);
});
