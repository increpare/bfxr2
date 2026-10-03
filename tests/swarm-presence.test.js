const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext}=require('./helpers/synth-context');
const energy=pcm=>pcm.reduce((sum,v)=>sum+v*v,0);
function brightness(pcm){let e=0,d=0;for(let i=1;i<pcm.length;i++){e+=pcm[i]**2;d+=(pcm[i]-pcm[i-1])**2;}return d/e;}

test('wings carry broadband flutter and rotors carry rough blade noise at low tuning',()=>{
    const {run}=createContext(['Swarmr']);
    const [wings,rotors,wisps]=run(`[0,2,4].map(kind=>Swarmr_DSP.render({kind,duration:1,count:3,cohesion:1,agitation:0,size:0.75,movement:0,scatter:0,seed:0.31}))`);
    assert.ok(brightness(wings)>0.015,'wings have air and membrane texture beyond their fundamental');
    assert.ok(brightness(rotors)>0.012,'rotors have rough blade-passing turbulence');
    assert.ok(brightness(wings)>brightness(wisps)*12,'wings and wisps occupy distinct textures');
});

test('skittering agents make paired contacts within each step',()=>{
    const {run}=createContext(['Swarmr']);
    const pcm=run(`Swarmr_DSP.render({kind:3,duration:1,count:3,cohesion:1,agitation:0,speed:0.5,size:0.7,movement:0,scatter:0,seed:0.31})`);
    const secondary=pcm.slice(Math.round(0.023*44100),Math.round(0.04*44100));
    assert.ok(energy(secondary)>0.005,'a second footfall follows the first instead of isolated clock ticks');
});

test('swarm physical textures remain seeded and finite before output conditioning',()=>{
    const {run}=createContext(['Swarmr']);
    const result=run(`(() => {
        const p={duration:0.4,count:32,cohesion:1,agitation:1,speed:1,size:0,movement:1,scatter:1,seed:0.71,masterVolume:1};
        const finish=SoundDSP.finish;let valid=true;
        SoundDSP.finish=(pcm,volume)=>{valid=valid&&pcm.every(v=>Number.isFinite(v)&&Math.abs(v)<10);return finish.call(SoundDSP,pcm,volume);};
        Math.random=()=>{throw new Error('unseeded render');};
        const entries=[0,1,2,3,4,5].map(kind=>({pcm:Swarmr_DSP.render({...p,kind}),replay:Swarmr_DSP.render({...p,kind})}));
        SoundDSP.finish=finish;return {valid,entries};})()`);
    assert.ok(result.valid);
    for(const {pcm,replay} of result.entries){assert.deepEqual(pcm,replay);assert.ok(energy(pcm)>0.01);assert.equal(Math.abs(pcm[0]),0);assert.equal(Math.abs(pcm.at(-1)),0);}
});
