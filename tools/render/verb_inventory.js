#!/usr/bin/env node
// Measure every Soundboard ingredient and engine verb preset headlessly.
//   node tools/render/verb_inventory.js [--takes 4] [--json out.json]
// Prints each verb's entries with measured active duration against the vocabulary's class.
'use strict';
const path=require('node:path');
const fs=require('node:fs');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
const args={takes:4};
for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
const takes=parseInt(args.takes,10);
const ENGINES=['Bfxr','Transfxr','Clonkr','Machinr','Jinglr','Squishr','Crittr','Birdr','Signlr','Fractr','Riftr','Swarmr','Rustlr','Boomr','Zappr','Whooshr','Bouncr','Breathr','Choirr','Pluckr','Glitchr','Tappr','Pewpr','Tickr','Stackr','Mixr'];
function boardContext(){
 const api=createContext(ENGINES);
 api.run('var CONVERSION_FACTOR=(2*Math.PI)/44100;');
 for(const file of ['js/audio/puredata.js','js/audio/puredata_modules.js','js/audio/puredata_parser.js','js/synths/Footsteppr.js','js/synths/Soundboard.js'])api.load(file);
 return api;
}
const rate=44100;
function measure(pcm){
 const hop=256;let peak=0;const env=[];
 for(let i=0;i<pcm.length;i+=hop){let e=0;const end=Math.min(pcm.length,i+hop);for(let j=i;j<end;j++)e+=pcm[j]*pcm[j];const v=Math.sqrt(e/hop);env.push(v);if(v>peak)peak=v;}
 const threshold=Math.max(peak*0.03,0.0005);let first=-1,last=-1;
 env.forEach((v,i)=>{if(v>=threshold){if(first<0)first=i;last=i;}});
 const duration=first<0?0:(last-first+1)*hop/rate;
 let abs=0;for(const v of pcm){if(!Number.isFinite(v))return {duration:0,peak:NaN,finite:false};abs=Math.max(abs,Math.abs(v));}
 return {duration:+duration.toFixed(3),peak:+abs.toFixed(3),onset:first<0?0:+(first*hop/rate).toFixed(3),finite:true};
}
function run(){
 const api=boardContext();
 const verbs=plain(api.run('GAME_VERBS'));
 const refs=plain(api.run('Soundboard.references()'));
 const unresolved=refs.filter(ref=>!api.run(`Mixr.resolve_reference(${JSON.stringify(ref)})`));
 const report={unresolved,verbs:{}};
 for(const verb of verbs){
  const entries=plain(api.run(`Soundboard.entries(${JSON.stringify(verb.id)})`));
  report.verbs[verb.id]=entries.map((entry,index)=>{
   const takesOut=[];
   for(let k=0;k<takes;k++){
    api.run(`Math.random=SoundDSP.rng(${(k+1)*0.137+index*0.011});var s=new Soundboard();s.apply_entry(Soundboard.entries(${JSON.stringify(verb.id)})[${index}]);s.generate_sound();`);
    const pcm=api.run('s.sound.getBuffer()');
    takesOut.push(measure(pcm));
   }
   const durations=takesOut.map(t=>t.duration);
   const low=Math.min(...durations),high=Math.max(...durations);
   const ok=takesOut.every(t=>t.finite&&t.peak>0.02)&&low>=verb.duration[0]*0.8&&high<=verb.duration[1]*1.25;
   return {label:entry.mix?entry.mix.join(' × '):entry.src,w:entry.w,range:[low,high],peak:Math.min(...takesOut.map(t=>t.peak)),ok};
  });
 }
 return {verbs,report};
}
const {verbs,report}=run();
if(report.unresolved.length)console.log('UNRESOLVED:',report.unresolved.join(', '));
let bad=0;
for(const verb of verbs){
 console.log(`\n${verb.name} [${verb.duration.join('–')} s]`);
 for(const e of report.verbs[verb.id]){
  if(!e.ok)bad++;
  console.log(`  ${e.ok?'ok ':'!! '} ${e.label.padEnd(44)} ${e.range[0].toFixed(2)}–${e.range[1].toFixed(2)} s  peak ${e.peak.toFixed(2)}  w${e.w}`);
 }
}
console.log(`\n${bad} entries outside their class or inaudible, ${report.unresolved.length} unresolved.`);
if(args.json)fs.writeFileSync(path.resolve(args.json),JSON.stringify(report,null,1));
