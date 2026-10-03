const test=require('node:test');
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const {createContext,plain}=require('./helpers/synth-context');
const digest=pcm=>crypto.createHash('sha256').update(Buffer.from(pcm.buffer)).digest('hex');
function brightness(pcm) {
    let energy=0,difference=0;
    for(let i=1;i<pcm.length;i++){energy+=pcm[i]**2;difference+=(pcm[i]-pcm[i-1])**2;}
    return difference/energy;
}

test('Breathr defaults to a short single breath and direction continuously changes its air',()=>{
    const {run}=createContext(['Breathr']);
    const defaults=plain(run('new Breathr().params'));
    assert.equal(defaults.mode,0);assert.ok(defaults.duration<1);
    const sounds=run(`[-1,-0.001,0,0.001,1].map(direction=>Breathr_DSP.render({...new Breathr().params,duration:0.65,space:0,direction}))`);
    assert.ok(brightness(sounds[0])>brightness(sounds[4])*1.3,'inhale has brighter turbulent air than exhale');
    const difference=(a,b)=>a.reduce((sum,v,i)=>sum+(v-b[i])**2,0);
    assert.ok(difference(sounds[1],sounds[3])<difference(sounds[0],sounds[4])*0.001,'middle direction has no inhale/exhale switch');
    for(const pcm of sounds)assert.ok(pcm.slice(11000,17000).some(v=>Math.abs(v)>0.02),'single breath has no intervening hold');
});

test('Breathr old snapshots restore the exact cycle and partial edits preserve mode',()=>{
    const {run}=createContext(['Breathr']);
    const result=run(`(()=>{
        const synth=new Breathr(),legacy={...synth.params,duration:2.7};delete legacy.mode;delete legacy.direction;
        synth.apply_params(legacy);const migrated={...synth.params},pcm=Breathr_DSP.render(migrated);
        synth.set_param('mode',0);synth.apply_params({seed:0.8});const partial=synth.params.mode;
        synth.set_locked_param('mode',true);synth.apply_params(legacy,true);
        return {migrated,pcm,partial,locked:synth.params.mode};
    })()`);
    assert.equal(result.migrated.mode,1);assert.equal(result.partial,0);assert.equal(result.locked,0);
    assert.equal(digest(result.pcm),'903995e028e66b22e4dc62f4014f310659cf6f5ec72bc2c97495900e1b29e8c7');
});

test('Breathr short inhale, exhale, gasp, sigh and snore recipes choose one breath',()=>{
    const {run}=createContext(['Breathr']);
    for(const id of ['inhale','exhale','gasp','sigh','snore']){
        const result=plain(run(`(()=>{const s=new Breathr();Math.random=SoundDSP.rng(0.31);s.generate_recipe('${id}');return {exists:s.recipes.some(r=>r.id==='${id}'),p:s.params};})()`));
        assert.ok(result.exists,id);assert.equal(result.p.mode,0,id);assert.ok(result.p.duration<1.8,id);
        if(['inhale','gasp','snore'].includes(id))assert.ok(result.p.direction<0,id);
        else assert.ok(result.p.direction>0,id);
    }
});

test('Breathr new random sounds favor short single breaths',()=>{
    const {run}=createContext(['Breathr']);
    const cases=plain(run(`(()=>{const s=new Breathr();Math.random=SoundDSP.rng(0.43);return Array.from({length:12},()=>{s.create_random_template();return {...s.params};});})()`));
    for(const p of cases){assert.equal(p.mode,0);assert.ok(p.duration<1.8);}
});

test('Pluckr tremolo affects volume only while vibrato moves the string pitch',()=>{
    const {run}=createContext(['Pluckr']);
    const result=run(`(()=>{
        const finish=SoundDSP.finish;SoundDSP.finish=pcm=>pcm;
        const p={...new Pluckr().params,duration:1,strings:1,coupling:0,damping:0,brightness:0.2,tremoloRate:4};
        const dry=Pluckr_DSP.render(p),tremolo=Pluckr_DSP.render({...p,tremolo:0.7}),vibrato=Pluckr_DSP.render({...p,vibrato:1});
        SoundDSP.finish=finish;return {dry,tremolo,vibrato};
    })()`);
    let movedCrossings=0;
    for(let i=0;i<result.dry.length;i++){
        const expected=result.dry[i]*(1-0.7*(0.5-0.5*Math.cos(2*Math.PI*4*i/44100)));
        assert.ok(Math.abs(result.tremolo[i]-expected)<1e-7,'tremolo is a volume multiplier');
        if(result.dry[i]*result.vibrato[i]<0)movedCrossings++;
    }
    assert.ok(movedCrossings>result.dry.length*0.1,'vibrato changes phase, not just loudness');
    const pitched=run(`Pluckr_DSP.render({...new Pluckr().params,duration:1,strings:1,coupling:0,damping:0,brightness:0.2,tremoloRate:2,vibrato:1})`);
    function period(from){
        let best=-1,period=0;
        for(let lag=180;lag<225;lag++){
            let cross=0,a=0,b=0;
            for(let i=Math.round(from*44100);i<Math.round((from+0.03)*44100);i++){
                cross+=pitched[i]*pitched[i+lag];a+=pitched[i]**2;b+=pitched[i+lag]**2;
            }
            const score=cross/Math.sqrt(a*b);if(score>best){best=score;period=lag;}
        }
        return period;
    }
    assert.ok(period(0.11)>period(0.36)*1.05,'vibrato audibly alternates between lower and higher tuning');
});

test('Pluckr snapshots without vibrato retain their sound and Gravity migration',()=>{
    const {run}=createContext(['Pluckr']);
    const result=run(`(()=>{
        const s=new Pluckr(),legacy={...s.params};delete legacy.vibrato;
        s.set_param('vibrato',1);s.apply_params(legacy);const pcm=Pluckr_DSP.render(s.params),restored=s.params.vibrato;
        s.apply_params({...legacy,material:5});return {pcm,restored,gravity:s.params};
    })()`);
    assert.equal(result.restored,0);
    assert.equal(digest(result.pcm),'6f1d78ea46d6ac6dd9fb9f09438aae2d4329bddff744df9d0a694f8315f26a1f');
    assert.equal(result.gravity.material,4);assert.equal(result.gravity.vibrato,0);
});

test('Breathr and Pluckr motion remain deterministic and finite before output conditioning',()=>{
    const {run}=createContext(['Breathr','Pluckr']);
    const checks=run(`(()=>{
        const finish=SoundDSP.finish;SoundDSP.finish=pcm=>pcm;const checks=[];
        for(const source of [0,1,2])for(const mode of [0,1])for(const edge of [0,1]){
            const p={...new Breathr().params,source,mode,direction:edge*2-1,duration:0.3,throat:edge,rasp:edge,flutter:edge,space:edge};
            const a=Breathr_DSP.render(p),b=Breathr_DSP.render(p);checks.push(a.every((v,i)=>Number.isFinite(v)&&Math.abs(v)<10&&v===b[i]));
        }
        for(const material of [0,1,2,3,4])for(const tremoloRate of [0.2,12]){
            const p={...new Pluckr().params,material,duration:0.3,vibrato:1,tremolo:1,tremoloRate};
            const a=Pluckr_DSP.render(p),b=Pluckr_DSP.render(p);checks.push(a.every((v,i)=>Number.isFinite(v)&&Math.abs(v)<10&&v===b[i]));
        }
        SoundDSP.finish=finish;return checks;
    })()`);
    assert.ok(checks.every(Boolean));
});

test('Breathr mode button immediately swaps single and cycle controls',()=>{
    const {run,load}=createContext(['Breathr']);load('js/Tab.js');
    assert.equal(run(`(()=>{const tab=Object.create(Tab.prototype);tab.synth=new Breathr();tab.synth.generate_sound=()=>{};
        const rows={cycles:{},inhale:{},hold:{},direction:{}};
        tab.sliders=Object.fromEntries(Object.keys(rows).map(key=>[key,{sliderElem:{closest(){return rows[key];}}}]));
        tab.files=[['Breath','{}','{}']];tab.selected_file_index=0;tab.text_controls={};tab.play_on_change=false;
        tab.update_ablements=()=>{};tab.redraw_waveform=()=>{};globalThis.SaveLoad={save_all_collections(){}};
        const children=[0,1].map(()=>({classList:{add(){},remove(){}}})),node={parentElement:{children}};
        tab.button_grid_button_clicked(node,'mode',0,0);const single=rows.cycles.hidden&&!rows.direction.hidden;
        tab.button_grid_button_clicked(node,'mode',1,1);return single&&!rows.cycles.hidden&&rows.direction.hidden;})()`),true);
});
