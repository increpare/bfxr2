'use strict';
// Independent bridge: frozen single-source and Mixr datasets keep their identities.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {createMultisynthContext}=require('./multisynth_context');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
function createTimelineContext(){
 const base=createMultisynthContext().inventory();
 const names=base.synths.map(s=>s.name).filter(n=>n!=='Footsteppr');
 const allowed=new Set(names);
 const {context,run}=createContext([...names,'Stackr']);
 const dependencies={};
 for(const file of ['tools/render/timeline_context.js','tools/render/timeline_worker.js',
  'tools/multisynth/timeline.py','tests/helpers/synth-context.js',
  'js/audio/Stackr_DSP.js','js/synths/Stackr.js']){
  dependencies[file]=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex');
 }
 const sourceHash=crypto.createHash('sha256').update(JSON.stringify([base.sourceHash,dependencies])).digest('hex');
 run(`
  const __timelineCache=new Map();
  function __timelineSource(layer,seed){
   const key=JSON.stringify([layer.synth,layer.params,seed]);
   if(!__timelineCache.has(key)){
    if(__timelineCache.size>=2048)__timelineCache.clear();
    __timelineCache.set(key,Stackr.render_source(layer,seed));
   }
   return __timelineCache.get(key);
  }
  function __timeline(request){
   Math.random=SoundDSP.rng(.5);
   const stack=new Stackr();stack.apply_params(request.params);
   const params=JSON.parse(JSON.stringify(stack.params));
   if(request.sourceOnly){
    const source=stack.get_layers()[0];
    return {source,pcm:__timelineSource(source,params.seed)};
   }
   let pcm;
   if(request.uncached){stack.generate_sound();pcm=stack.sound.getBuffer();}
   else pcm=Stackr_DSP.render(params,layer=>__timelineSource(layer,params.seed));
   return {params,pcm};
  }
 `);
 function validate(params){
  if(!params||typeof params!=='object'||Array.isArray(params))throw Error('Stackr params required');
  for(const [k,v] of Object.entries(params)){
   if(!['layers','spacing','masterVolume','seed'].includes(k))throw Error('Unknown Stackr control: '+k);
   if(k!=='layers'&&!Number.isFinite(v))throw Error('Nonfinite Stackr control: '+k);
  }
  if(typeof params.layers!=='string'||params.layers.length>60000)throw Error('Bounded layers JSON required');
  const layers=JSON.parse(params.layers);
  if(!Array.isArray(layers)||layers.length<1||layers.length>6)throw Error('One to six layers required');
  for(const layer of layers){
   if(!layer||!allowed.has(layer.synth))throw Error('Unsupported source');
   if(!layer.params||typeof layer.params!=='object'||Array.isArray(layer.params))throw Error('Source controls required');
   for(const k of ['start','gain','pitch'])if(k in layer&&!Number.isFinite(layer[k]))throw Error('Nonfinite '+k);
  }
 }
 function invoke(params,extra={}){
  validate(params);context.__timelineRequest=JSON.stringify({params,...extra});
  let result;
  try{result=run('__timeline(JSON.parse(__timelineRequest))');}finally{delete context.__timelineRequest;}
  const pcm=new Float32Array(result.pcm);
  if(!pcm.length||pcm.some(v=>!Number.isFinite(v)))throw Error('Invalid timeline PCM');
  return {...plain({...result,pcm:undefined}),pcm};
 }
 return {
  inventory:()=>({sourceHash,baseSourceHash:base.sourceHash,dependencies,sampleRate:44100,sources:names,
   seedPolicy:'Actual Stackr seed; canonical layers have no individual renderSeed.'}),
  source(source,seed=.5){return invoke({layers:JSON.stringify([source]),seed,masterVolume:.5,spacing:1},{sourceOnly:true});},
  render(params,{uncached=false}={}){return invoke(params,{uncached});}
 };
}
module.exports={createTimelineContext};
