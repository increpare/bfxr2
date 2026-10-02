#!/usr/bin/env node
// Editorially constrain complete survey states, then render exactly what ships.
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {root,createContext,wav,runtimeFingerprint}=require('./render_corpus');
const plain=value=>JSON.parse(JSON.stringify(value));
function get(p,key){return key.split('.').reduce((p,k)=>p[k],p);}
function set(p,key,value){const keys=key.split('.');let target=p;for(const k of keys.slice(0,-1))target=target[k]||={};target[keys.at(-1)]=value;}
function quantile(values,t){const sorted=values.slice().sort((a,b)=>a-b),at=(sorted.length-1)*t;return sorted[Math.floor(at)]+(sorted[Math.ceil(at)]-sorted[Math.floor(at)])*(at%1);}
function project(source,profile,pool){
 const p=plain(source.params);
 if(profile.preserve){
  if(profile.limits.duration){const duration=Math.max(profile.limits.duration[0],Math.min(profile.limits.duration[1],p.duration));
   const scale=duration/p.duration;p.duration=duration;p.attack*=scale;p.release*=scale;}
 }else{
  // Monotonic remapping preserves the survey's joint ordering and correlations.
  // Values are never sampled independently from unrelated minimum/maximum ranges.
  for(const [key,range]of Object.entries(profile.limits))if(Array.isArray(range)){
   const values=pool.map(s=>get(s.params,key)),lo=quantile(values,.1),hi=quantile(values,.9);
   const position=hi-lo>1e-8?Math.max(0,Math.min(1,(get(p,key)-lo)/(hi-lo))):.5;
   set(p,key,range[0]+(range[1]-range[0])*position);
  }
 }
 return p;
}
function curate(directory){
 const output=path.resolve(directory),report=JSON.parse(fs.readFileSync(path.join(output,'analysis.json'),'utf8'));
 const profiles=JSON.parse(fs.readFileSync(path.join(__dirname,'family_profiles.json'),'utf8'));
 const byId=new Map(report.sounds.map(s=>[s.id,s])),context=createContext(['js/synths/PresetFamily.js']);
 const normalize=vm.runInContext('(p,f)=>{const s=new Transfxr();s.apply_params(PresetFamily.constrain(p,f));return s.params;}',context);
 const render=vm.runInContext('(p)=>Transfxr_DSP.render(p)',context),sounds=[],groups=[],bank=[];
 fs.mkdirSync(path.join(output,'curated','audio'),{recursive:true});
 for(const [index,profile]of profiles.families.entries()){
  const original=report.groups.find(g=>g.name===profile.source_group);
  if(!original)throw Error('Missing survey group '+profile.source_group);
  const pool=(profile.preserve?original.exemplars:original.members.slice().sort((a,b)=>byId.get(a).distance-byId.get(b).distance))
   .map(id=>byId.get(id)).filter(s=>s.rms>=.009).slice(0,profile.preserve?24:12);
  const exemplars=[],ids=[];
  for(const source of pool){
   const params=plain(normalize(project(source,profile,pool),profile)),pcm=render(params);
   let energy=0,peak=0;for(const value of pcm){energy+=value*value;peak=Math.max(peak,Math.abs(value));}
   const rms=Math.sqrt(energy/pcm.length),id='C'+String(sounds.length+1).padStart(3,'0');
   if(!Number.isFinite(energy)||peak>=1||rms<.004)throw Error('Invalid curated sound '+profile.name+' '+source.id+' RMS '+rms);
   const audio='curated/audio/'+id+'.wav';fs.writeFileSync(path.join(output,audio),wav(pcm));
   sounds.push({id,survey_source:source.id,params,audio,duration:pcm.length/44100,rms,peak,cluster:index});
   exemplars.push(params);ids.push(id);
  }
  groups.push({...profile,index,count:ids.length,members:ids,exemplars:ids,discovery_count:original.count});
  bank.push({id:profile.id,name:profile.name,tip:profile.tip,limits:profile.limits,intervals:profile.intervals,
   variation:profile.variation,source_ids:ids,survey_source_ids:pool.map(s=>s.id),exemplars});
  console.log(profile.name+': '+ids.length+' curated exemplars');
 }
 const result={revision:profiles.revision,basis:profiles.basis,synth:'Transfxr',count:sounds.length,discovery_count:report.count,
  seed:report.seed,chosen_k:groups.length,groups,sounds};
 fs.writeFileSync(path.join(root,'js/synths/TransfxrPresets.js'),'// Curated from the survey and user listening feedback. See tools/preset_survey/family_profiles.json.\nconst TRANSFXR_PRESET_FAMILIES = '+JSON.stringify(bank)+';\n');
 result.runtime_sha256=runtimeFingerprint();
 fs.writeFileSync(path.join(output,'curated.json'),JSON.stringify(result,null,2)+'\n');
 return result;
}
if(require.main===module)curate(process.argv[2]||path.join(root,'examples/Transfxr/survey'));
module.exports={curate,project};
