#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..');
function runtimeFingerprint(){
 return Object.fromEntries(require('./runtime_sources.json').map(file=>[file,
  crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')]));
}
function rng(seed){let a=seed>>>0;return()=>{a+=0x6D2B79F5;let t=Math.imul(a^(a>>>15),1|a);t^=t+Math.imul(t^(t>>>7),61|t);return((t^(t>>>14))>>>0)/4294967296;};}
function createContext(extra=[]){
 const ctx=vm.createContext({console});
 for(const file of ['js/globals.js','js/audio/AKWF.js','js/audio/BfxrWaveforms.js','js/synths/templates.js','js/synths/SynthBase.js','js/audio/Transfxr_DSP.js',
  ...extra,'js/synths/Transfxr.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),ctx,{filename:file});
 return ctx;
}
function wav(pcm){
 const bytes=Buffer.alloc(44+pcm.length*2);bytes.write('RIFF');bytes.writeUInt32LE(bytes.length-8,4);bytes.write('WAVEfmt ',8);
 bytes.writeUInt32LE(16,16);bytes.writeUInt16LE(1,20);bytes.writeUInt16LE(1,22);bytes.writeUInt32LE(44100,24);
 bytes.writeUInt32LE(88200,28);bytes.writeUInt16LE(2,32);bytes.writeUInt16LE(16,34);bytes.write('data',36);bytes.writeUInt32LE(pcm.length*2,40);
 for(let i=0;i<pcm.length;i++)bytes.writeInt16LE(Math.round(Math.max(-1,Math.min(1,pcm[i]))*32767),44+i*2);
 return bytes;
}
function candidate(index,random,defaults,examples){
 const pick=list=>list[Math.floor(random()*list.length)];
 const uniform=(lo,hi)=>lo+(hi-lo)*random();
 const log=(lo,hi)=>lo*Math.pow(hi/lo,random());
 const curves=['Linear','Ease In','Ease Out','Smooth','Triangle','Pulse','Bounce','Steps'];
 const p=JSON.parse(JSON.stringify(defaults));
 // One quarter of proposals explore familiar neighborhoods, with substantial
 // timbre, envelope and trajectory changes. Recipe labels never enter clustering.
 if(index%4===0){
  const example=examples[Math.floor(index/4)%examples.length];
  for(const [key,value]of Object.entries(example.params))p[key]=Array.isArray(value)?{start:value[0],end:value[1],curve:value[2]||'Linear'}:value;
  const shift=uniform(-0.18,0.18),factor=log(0.5,2);
  for(const name of ['pitch','tone','noise','vibrato','level']){
   p[name].start=Math.clamp(p[name].start+(name==='pitch'?shift:uniform(-0.25,0.25)),0,1);
   p[name].end=Math.clamp(p[name].end+(name==='pitch'?shift:uniform(-0.25,0.25)),0,1);
   if(random()<0.35)p[name].curve=pick(curves);
  }
  p.duration=Math.clamp(p.duration*factor,0.06,2.5);p.attack*=factor;p.release*=factor;
  p.resonance=uniform(0,0.85);p.echo=random()<0.4?0:uniform(0.08,0.65);
  if(random()<0.3)p.waveType=Math.floor(random()*4);
 }else{
  p.waveType=Math.floor(random()*4);
  p.duration=log(0.075,2.4);
  p.attack=random()<0.6?uniform(0,0.018):p.duration*uniform(0.08,0.48);
  p.release=p.duration*uniform(0.08,0.8);
  p.resonance=uniform(0,0.95);p.echo=random()<0.5?0:uniform(0.05,0.7);
  p.pitch={start:uniform(0.03,0.9),end:uniform(0.03,0.95),curve:curves[Math.floor(index/4)%curves.length]};
  p.tone={start:uniform(0.05,1),end:uniform(0.05,1),curve:pick(curves)};
  const regime=Math.floor(index/32)%4;
  p.noise={start:regime===0?0:uniform(regime===3?0.7:0,regime===1?0.22:1),
   end:regime===0?0:uniform(regime===3?0.7:0,regime===1?0.22:1),curve:pick(curves)};
  p.vibrato={start:random()<0.55?0:uniform(0,1),end:random()<0.55?0:uniform(0,1),curve:pick(curves)};
  p.level={start:uniform(0.35,1),end:uniform(0.08,1),curve:pick(curves)};
 }
 p.masterVolume=0.5;
 return p;
}
function renderSurvey(directory,count=512,seed=20261002){
 const output=path.resolve(directory),random=rng(seed),ctx=createContext();
 const defaults=JSON.parse(vm.runInContext('JSON.stringify(new Transfxr().default_params())',ctx));
 const examples=JSON.parse(vm.runInContext('JSON.stringify(Transfxr.examples)',ctx));
 const normalize=vm.runInContext('(p)=>{const s=new Transfxr();s.apply_params(p);return s.params;}',ctx);
 const render=vm.runInContext('(p)=>Transfxr_DSP.render(p)',ctx);
 fs.mkdirSync(path.join(output,'audio'),{recursive:true});
 const sounds=[],rejects={quiet:0,invalid:0};let proposal=0;
 while(sounds.length<count&&proposal<count*4){
  const params=normalize(candidate(proposal++,random,defaults,examples)),pcm=render(params);
  let sum=0,peak=0;for(const value of pcm){sum+=value*value;peak=Math.max(peak,Math.abs(value));}
  if(!Number.isFinite(sum)||peak>=1){rejects.invalid++;continue;}
  const rms=Math.sqrt(sum/pcm.length);if(rms<0.004){rejects.quiet++;continue;}
  const id='T'+String(sounds.length+1).padStart(3,'0');
  fs.writeFileSync(path.join(output,'audio',id+'.wav'),wav(pcm));
  sounds.push({id,proposal:proposal-1,params,duration:pcm.length/44100,rms,peak,audio:'audio/'+id+'.wav'});
  if(sounds.length%64===0)console.log('Rendered '+sounds.length+'/'+count+' sounds');
 }
 if(sounds.length<count)throw Error('Not enough audible proposals');
 const manifest={synth:'Transfxr',seed,count:sounds.length,proposals:proposal,rejected:rejects,sampleRate:44100,sounds};
 fs.writeFileSync(path.join(output,'corpus.json'),JSON.stringify(manifest,null,2)+'\n');
 console.log(JSON.stringify({accepted:sounds.length,proposals:proposal,rejected:rejects}));return manifest;
}
// Candidate generation uses the application's clamp helper but no other browser state.
Math.clamp=(v,lo,hi)=>Math.max(lo,Math.min(v,hi));
if(require.main===module)renderSurvey(process.argv[2]||path.join(root,'examples/Transfxr/survey'),+(process.argv[3]||512));
module.exports={rng,candidate,createContext,wav,renderSurvey,root,runtimeFingerprint};
