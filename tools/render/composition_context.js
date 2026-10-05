'use strict';
// Separate bridge: do not alter the source identity of existing inverse datasets.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {createMultisynthContext}=require('./multisynth_context');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
function createCompositionContext(){
 const base=createMultisynthContext().inventory();
 const names=base.synths.map(s=>s.name).filter(n=>n!=='Footsteppr');
 const allowed=new Set(names);
 const {context,run}=createContext([...names,'Stackr','Mixr']);
 const dependencies={};
 const files=['tools/render/composition_context.js','tools/render/composition_worker.js',
  'tools/multisynth/composition.py','tests/helpers/synth-context.js',
  'js/audio/Stackr_DSP.js','js/synths/Stackr.js','js/audio/Mixr_DSP.js','js/synths/Mixr.js'];
 for(const file of files) dependencies[file]=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
 const hash=crypto.createHash('sha256').update(base.sourceHash);
 for(const [key,value] of Object.entries(dependencies).sort())hash.update(key).update('\0').update(value).update('\0');
 const sourceHash=hash.digest('hex');
 run(`
  const __compositionCache=new Map();
  function __sourcePcm(source,seed){
   const key=JSON.stringify([source,seed]);
   if(!__compositionCache.has(key)){
    if(__compositionCache.size>=1024)__compositionCache.clear();
    __compositionCache.set(key,Stackr.render_source(source,seed));
   }
   return __compositionCache.get(key);
  }
  function __composition(request){
   Math.random=SoundDSP.rng(.5);
   const mix=new Mixr();mix.apply_params(request.params);
   const params=JSON.parse(JSON.stringify(mix.params));
   if(request.sourceOnly){
    const source=mix.get_sources()[0];
    return {source,pcm:Stackr.render_source(source,Number.isFinite(source.renderSeed)?source.renderSeed:params.seed)};
   }
   let pcm;
   if(request.uncached){mix.generate_sound();pcm=mix.sound.getBuffer();}
   else pcm=Mixr_DSP.render(params,source=>__sourcePcm(source,Number.isFinite(source.renderSeed)?source.renderSeed:params.seed));
   return {params,pcm};
  }
 `);
 function validate(params){
  if(!params||typeof params!=='object'||Array.isArray(params))throw Error('Mix params required');
  for(const [key,value] of Object.entries(params)){
   if(!['sources','balance','masterVolume','seed'].includes(key))throw Error('Unknown Mixr control: '+key);
   if(key!=='sources'&&!Number.isFinite(value))throw Error('Mix control must be finite: '+key);
  }
  if(typeof params.sources!=='string'||params.sources.length>60000)throw Error('Sources must be bounded JSON text');
  const sources=JSON.parse(params.sources);
  if(!Array.isArray(sources)||sources.length<1||sources.length>2||!sources.some(Boolean))throw Error('One or two sources required');
  for(const s of sources){
   if(s===null)continue;
   if(!s||!allowed.has(s.synth))throw Error('Unsupported source synth');
   if(!s.params||typeof s.params!=='object'||Array.isArray(s.params))throw Error('Source params required');
   if(s.renderSeed!==undefined&&(!Number.isFinite(s.renderSeed)||s.renderSeed<0||s.renderSeed>1))throw Error('Source seed must be finite in [0,1]');
  }
 }
 function invoke(params,extra={}){
  validate(params);context.__compositionRequest=JSON.stringify({params,...extra});
  let result;
  try{result=run('__composition(JSON.parse(__compositionRequest))');}
  finally{delete context.__compositionRequest;}
  const pcm=new Float32Array(result.pcm);
  if(!pcm.length||pcm.some(v=>!Number.isFinite(v)))throw Error('Invalid composition PCM');
  return {...plain({...result,pcm:undefined}),pcm};
 }
 return {
  inventory:()=>({sourceHash,baseSourceHash:base.sourceHash,sampleRate:44100,sources:names,
   dependencies,excluded:[{name:'Footsteppr',reason:'Separate PureData host is not loaded in this first composition bridge.'}],
   seedPolicy:'Actual Stackr.render_source and SoundDSP.rng; source renderSeed in [0,1].'}),
  source(source){return invoke({sources:JSON.stringify([source]),seed:.5,masterVolume:.5,balance:.5},{sourceOnly:true});},
  render(params,{uncached=false}={}){return invoke(params,{uncached});}
 };
}
module.exports={createCompositionContext};
