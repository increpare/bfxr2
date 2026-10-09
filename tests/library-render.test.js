const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

function engines() {
    const context = vm.createContext({console: {log() {}, error: console.error}});
    vm.runInContext('const SAMPLE_RATE=44100, CONVERSION_FACTOR=2*Math.PI/SAMPLE_RATE;', context);
    const scripts = [...fs.readFileSync(path.join(root, 'index.html'), 'utf8')
        .matchAll(/<script src="([^"]+)"/g)].map(m => m[1].split('?')[0])
        .filter(p => p === 'js/globals.js' || p.startsWith('js/synths/') || p.startsWith('js/audio/'))
        .filter(p => !p.endsWith('audio_globals.js') && !p.endsWith('RealizedSound.js') && !p.endsWith('riffwave.js'));
    for (const file of scripts) vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), context, {filename: file});
    return code => vm.runInContext(code, context);
}

test('every engine renders PCM without Web Audio', () => {
    const run = engines();
    for (const name of ['Bfxr', 'Footsteppr', 'Transfxr', 'Mixr', 'Clonkr', 'Machinr', 'Jinglr',
        'Squishr', 'Crittr', 'Birdr', 'Signlr', 'Fractr', 'Riftr', 'Swarmr', 'Rustlr', 'Boomr',
        'Zappr', 'Whooshr', 'Bouncr', 'Breathr', 'Choirr', 'Pluckr', 'Glitchr']) {
        assert.equal(run(`(() => {
            const synth = new ${name}();
            if (synth.name === 'Mixr') synth.generate_recipe('cyber_bird');
            const before = JSON.stringify(synth.params), pcm = synth.render();
            return pcm instanceof Float32Array && pcm.length > 100 && pcm.every(Number.isFinite)
                && JSON.stringify(synth.params) === before;
        })()`), true, name);
    }
});

test('the editor wraps exactly the same PCM renderer for legacy and current engines', () => {
    const run = engines();
    run('class RealizedSound { static from_buffer(pcm) { return {getBuffer:()=>pcm,stop(){}}; } }');
    for (const name of ['Bfxr', 'Footsteppr', 'Transfxr', 'Clonkr', 'Mixr']) {
        assert.equal(run(`(() => {
            const synth = new ${name}(), before = JSON.stringify(synth.params), original = Math.random;
            try {
                Math.random = SoundDSP.rng(.3); const pcm = synth.render();
                Math.random = SoundDSP.rng(.3); synth.generate_sound();
                return pcm.length === synth.sound.getBuffer().length && pcm.every((v,i)=>v===synth.sound.getBuffer()[i])
                    && JSON.stringify(synth.params) === before;
            } finally { Math.random = original; }
        })()`), true, name);
    }
});

test('library mutations preserve discrete choices, scores, source assignments and bounds', () => {
    const run = engines();
    run('const BFXR_SYNTHS={Bfxr,Footsteppr,Transfxr,Mixr,Clonkr,Machinr,Jinglr,Squishr,Crittr,Birdr,Signlr,Fractr,Riftr,Swarmr,Rustlr,Boomr,Zappr,Whooshr,Bouncr,Breathr,Choirr,Pluckr,Glitchr};');
    run(fs.readFileSync(path.join(root, 'js/library/sounds.js'), 'utf8'));
    assert.equal(run(`(() => {
        const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
        const check = (before,after) => {
            const synth=LibrarySounds.engine(before.synth_type);
            for (const raw of synth.param_info) {
                const info=synth.get_param_normalized(raw), a=before.params[info.name], b=after.params[info.name];
                if (info.type==='BUTTONSELECT' || ['masterVolume','seed','instrumentSeed','phrase'].includes(info.name)) {
                    if (!same(a,b)) return false;
                } else if (info.type==='RANGE') {
                    if (!Number.isFinite(b) || b<info.min_value || b>info.max_value) return false;
                } else if (info.type==='KNOB_TRANSITION') {
                    if (a.curve!==b.curve || ['start','end'].some(key=>b[key]<info.min_value||b[key]>info.max_value)) return false;
                }
            }
            return true;
        };
        for (const name of Object.keys(BFXR_SYNTHS)) {
            const synth=LibrarySounds.engine(name);
            if (name==='Mixr') synth.generate_recipe('crystal_prize');
            if (name==='Jinglr') synth.set_param('phrase','[{"degree":0,"beats":2},{"degree":7,"beats":0.5}]');
            const sound={synth_type:name,params:JSON.parse(JSON.stringify(synth.params)),renderSeed:.3};
            const saved=JSON.stringify(sound);
            for (const amount of [.05,1]) {
                const mutated=LibrarySounds.mutate(sound,amount,.2);
                if (!check(sound,mutated) || JSON.stringify(sound)!==saved) return false;
                if (name==='Mixr') {
                    const a=JSON.parse(sound.params.sources),b=JSON.parse(mutated.params.sources);
                    if (a.length!==b.length || a.some((source,i)=>source.synth!==b[i].synth ||
                        source.generator!==b[i].generator || source.renderSeed!==b[i].renderSeed ||
                        !check({synth_type:source.synth,params:source.params},{params:b[i].params}))) return false;
                }
            }
        }
        return true;
    })()`), true);
});
