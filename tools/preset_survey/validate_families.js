#!/usr/bin/env node
// Render fresh seeded samples through the same parameter validation as the UI.
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createContext,rng,wav}=require('./render_corpus');
function validate(directory,count=16,seed=20261003){
 const output=path.resolve(directory),context=createContext(['js/synths/PresetFamily.js','js/synths/TransfxrPresets.js']);
 const families=JSON.parse(vm.runInContext('JSON.stringify(Transfxr.preset_families)',context));
 const sample=vm.runInContext('(family,random)=>{const s=new Transfxr(); s.apply_params(PresetFamily.sample(family,random),true); return s.params;}',context);
 const render=vm.runInContext('(p)=>Transfxr_DSP.render(p)',context),random=rng(seed),sounds=[];
 fs.mkdirSync(path.join(output,'audio'),{recursive:true});
 for(const [cluster,family]of families.entries())for(let i=0;i<count;i++){
  const params=sample(family,random),pcm=render(params);let sum=0,peak=0;
  for(const value of pcm){sum+=value*value;peak=Math.max(peak,Math.abs(value));}
  const rms=Math.sqrt(sum/pcm.length),id=family.id+'_'+String(i+1).padStart(2,'0');
  if(!Number.isFinite(sum)||peak>=1||rms<.004)throw Error('Invalid or quiet family sample '+id+' RMS '+rms);
  fs.writeFileSync(path.join(output,'audio',id+'.wav'),wav(pcm));
  sounds.push({id,cluster,params,rms,peak,audio:'audio/'+id+'.wav'});
 }
 fs.writeFileSync(path.join(output,'samples.json'),JSON.stringify({seed,count:sounds.length,sounds},null,2)+'\n');
 console.log('Rendered '+sounds.length+' audible fresh family samples');
}
if(require.main===module)validate(process.argv[2]||'/private/tmp/transfxr-family-validation',+(process.argv[3]||16));
module.exports={validate};
