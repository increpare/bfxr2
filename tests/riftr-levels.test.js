const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext}=require('./helpers/synth-context');
const peak=pcm=>pcm.reduce((p,v)=>Math.max(p,Math.abs(v)),0);
const rms=pcm=>Math.sqrt(pcm.reduce((p,v)=>p+v*v,0)/pcm.length);

test('Riftr quiet presets gain presence without changing their relative waveform or envelope',()=>{
    const {run}=createContext(['Riftr']);
    const cases=run(`(()=>{
        const synth=new Riftr(),finish=SoundDSP.finish,results=[];Math.random=SoundDSP.rng(.43);
        let reference;
        SoundDSP.finish=(raw,volume)=>{reference=finish.call(SoundDSP,raw.slice(),volume);return finish.call(SoundDSP,raw,volume);};
        for(const recipe of synth.recipes)for(let variant=0;variant<4;variant++){
            synth.generate_recipe(recipe.id);const pcm=Riftr_DSP.render(synth.params);
            results.push({id:recipe.id,pcm,reference});
        }
        SoundDSP.finish=finish;return results;
    })()`);
    for(const {id,pcm,reference} of cases){
        const gain=peak(pcm)/peak(reference);
        assert.ok(gain>=1-1e-6&&gain<=4.000001,id+' bounded gain');
        assert.ok(peak(pcm)>=0.39,id+' has an audible peak');
        assert.ok(peak(pcm)<0.476,id+' preserves headroom');
        assert.ok(Math.abs(rms(pcm)/rms(reference)-gain)<1e-6,id+' retains crest factor');
        for(let i=0;i<pcm.length;i++)assert.ok(Math.abs(pcm[i]-reference[i]*gain)<1e-7,id+' is one linear gain');
        if(['portal_tear','teleport_arrive','reality_glitch'].includes(id))assert.ok(gain>2,id+' is substantially louder');
    }
});

test('Riftr level adjustment keeps volume scaling, mute, tiny signals and silence safe',()=>{
    const {run}=createContext(['Riftr']);
    const results=run(`(()=>{
        const p={...new Riftr().params,duration:.3};
        const half=Riftr_DSP.render({...p,masterVolume:.5}),full=Riftr_DSP.render({...p,masterVolume:1}),mute=Riftr_DSP.render({...p,masterVolume:0});
        const finish=SoundDSP.finish;SoundDSP.finish=pcm=>new Float32Array(pcm.length);
        const silence=Riftr_DSP.render(p);
        SoundDSP.finish=pcm=>new Float32Array(pcm.length).fill(1e-12);const tiny=Riftr_DSP.render(p);
        SoundDSP.finish=finish;return {half,full,mute,silence,tiny};
    })()`);
    assert.ok(results.mute.every(v=>v===0));assert.ok(results.silence.every(v=>v===0));
    assert.ok(results.tiny.every(v=>v===Math.fround(1e-12)));
    assert.ok(results.full.every((v,i)=>Math.abs(v-results.half[i]*2)<1e-6));
});

test('Riftr extreme fields stay finite before conditioning and deterministic after gain',()=>{
    const {run}=createContext(['Riftr']);
    const checks=run(`(()=>{
        const s=new Riftr(),finish=SoundDSP.finish;let rawSafe=true;
        SoundDSP.finish=(pcm,volume)=>{rawSafe&&=pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<10);return finish.call(SoundDSP,pcm,volume);};
        const checks=[];
        for(const excitation of [0,1,2,3,4])for(const edge of [0,1]){
            const p={...s.params,excitation,duration:.3,feedback:edge,dispersion:edge,motion:edge,space:edge,field:edge,reverse:edge,pitch:edge,masterVolume:1};
            const a=Riftr_DSP.render(p),b=Riftr_DSP.render(p);
            checks.push(a.every((v,i)=>Number.isFinite(v)&&Math.abs(v)<1&&v===b[i])&&a[0]===0&&a.at(-1)===0);
        }
        SoundDSP.finish=finish;return {rawSafe,checks};
    })()`);
    assert.ok(checks.rawSafe);assert.ok(checks.checks.every(Boolean));
});

test('Mixr receives the same leveled Riftr audio as the standalone engine',()=>{
    const {run}=createContext(['Riftr','Mixr']);
    const result=run(`(()=>{
        const s=new Riftr();Math.random=SoundDSP.rng(.21);s.generate_recipe('portal_tear');
        const direct=Riftr_DSP.render(s.params),mix=new Mixr();mix.set_source(0,s);const pcm=Mixr_DSP.render(mix.params);
        return {direct,pcm};
    })()`);
    assert.ok(peak(result.pcm)>0.39);
    assert.ok(result.direct.slice(0,-128).every((v,i)=>v===result.pcm[i]));
});
