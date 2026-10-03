#!/usr/bin/env node
// How varied is each Soundboard verb? Press every verb many times and measure the spread of
// what comes out: distinct ingredients drawn, distinct archetypes, and the mean pairwise
// distance between takes in a small feature space (length, brightness, noisiness, envelope).
//   node tools/render/verb_variety.js [--presses 24] [--json out.json]
'use strict';
const fs=require('node:fs'),path=require('node:path');
const {createBoardContext,activeDuration,plain}=require('../../tests/helpers/board-context');
const args={presses:24};
for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const presses=parseInt(args.presses,10),rate=44100;
function features(pcm){
 const hop=256;const env=[];let peak=0;
 for(let i=0;i<pcm.length;i+=hop){let e=0;const end=Math.min(pcm.length,i+hop);for(let j=i;j<end;j++)e+=pcm[j]*pcm[j];const v=Math.sqrt(e/hop);env.push(v);if(v>peak)peak=v;}
 const thr=Math.max(peak*0.03,0.0005);const active=env.map((v,i)=>v>=thr?i:-1).filter(i=>i>=0);
 const first=active[0]||0,last=active[active.length-1]||0;const span=Math.max(1,last-first+1);
 let zc=0,n=0;for(let i=first*hop+1;i<Math.min(pcm.length,(last+1)*hop);i++){n++;if((pcm[i]>=0)!==(pcm[i-1]>=0))zc++;}
 const zcr=n?zc*rate/n:0;
 // Tonal proxy: strongest normalised autocorrelation between 60 Hz and 2 kHz near the peak.
 const centre=Math.min(pcm.length-2048,Math.max(0,env.indexOf(peak)*hop-512));let best=0;
 const seg=pcm.subarray(centre,centre+2048);let e0=0;for(const v of seg)e0+=v*v;
 if(e0>1e-9)for(let lag=22;lag<=735;lag+=3){let c=0;for(let i=0;i+lag<seg.length;i++)c+=seg[i]*seg[i+lag];best=Math.max(best,c/e0);}
 let w=0,wt=0;env.forEach((v,i)=>{w+=v*v;wt+=v*v*i;});const centroidTime=w?(wt/w-first)/span:0;
 const attack=(env.indexOf(peak)-first)/span;
 return {duration:Math.log2(Math.max(0.01,activeDuration(pcm))),brightness:Math.log2(Math.max(50,zcr)),tonal:best,centroidTime,attack};
}
const scale={duration:1.5,brightness:1.5,tonal:0.5,centroidTime:0.3,attack:0.3}; // rough spread of each feature over the whole board
function distance(a,b){let d=0;for(const k in scale){const x=(a[k]-b[k])/scale[k];d+=x*x;}return Math.sqrt(d/Object.keys(scale).length);}
const api=createBoardContext();
const verbs=plain(api.run('GAME_VERBS'));
const report={};
for(const verb of verbs){
 api.run(`Math.random=SoundDSP.rng(${0.5+verbs.indexOf(verb)*0.013});var board=new Soundboard();`);
 const takes=[];
 for(let i=0;i<presses;i++){
  api.run(`board.generate_recipe(${JSON.stringify(verb.id)});board.generate_sound();`);
  const pcm=api.run('board.sound.getBuffer()');
  const label=plain(api.run('board.get_sources().map(s=>s.synth+":"+(s.generator||"")).join("+")'));
  const archetype=plain(api.run('board.get_sources().map(s=>s.synth==="Transfxr"?(s.params&&JSON.stringify([s.params.waveType,Math.round(s.params.duration*10)])):"").join("|")'));
  takes.push({label,archetype,f:features(pcm)});
 }
 let sum=0,count=0;for(let i=0;i<takes.length;i++)for(let j=i+1;j<takes.length;j++){sum+=distance(takes[i].f,takes[j].f);count++;}
 const ingredients=new Set(takes.map(t=>t.label)).size,entries=plain(api.run(`Soundboard.entries(${JSON.stringify(verb.id)}).length`));
 const repeats=takes.filter((t,i)=>i&&t.label===takes[i-1].label).length;
 let minDistinct8=8;for(let i=0;i+8<=takes.length;i++)minDistinct8=Math.min(minDistinct8,new Set(takes.slice(i,i+8).map(t=>t.label)).size);
 const durations=takes.map(t=>2**t.f.duration);
 report[verb.id]={entries,ingredients,repeats,minDistinct8,spread:+(sum/count).toFixed(3),durationRange:[+Math.min(...durations).toFixed(2),+Math.max(...durations).toFixed(2)],
  tonalShare:+(takes.filter(t=>t.f.tonal>0.5).length/takes.length).toFixed(2),brightnessOctaves:+((Math.max(...takes.map(t=>t.f.brightness))-Math.min(...takes.map(t=>t.f.brightness)))).toFixed(2)};
}
console.log('verb      entries drawn  in8 spread  duration range   tonal  brightness span');
for(const [id,r] of Object.entries(report))console.log(`${id.padEnd(9)} ${String(r.entries).padStart(7)} ${String(r.ingredients).padStart(5)} ${String(r.minDistinct8).padStart(4)} ${r.spread.toFixed(3).padStart(7)}  ${(r.durationRange[0]+'–'+r.durationRange[1]+' s').padEnd(16)} ${r.tonalShare.toFixed(2).padStart(5)}  ${r.brightnessOctaves.toFixed(2).padStart(5)} oct`);
if(args.json)fs.writeFileSync(path.resolve(args.json),JSON.stringify(report,null,1));
