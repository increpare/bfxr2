#!/usr/bin/env node
'use strict';
const readline=require('node:readline');
const {createCompositionContext}=require('./composition_context');
const api=createCompositionContext();
readline.createInterface({input:process.stdin,crlfDelay:Infinity}).on('line',line=>{
 if(!line.trim())return;
 let result;
 try{
  const r=JSON.parse(line);let data;
  if(r.op==='inventory')data=api.inventory();
  else if(r.op==='source')data=api.source(r.source);
  else if(r.op==='render')data=api.render(r.params,{uncached:!!r.uncached});
  else throw Error('Unknown operation');
  if(data.pcm){const bytes=Buffer.alloc(data.pcm.length*4);data.pcm.forEach((v,i)=>bytes.writeFloatLE(v,i*4));
   const {pcm,...rest}=data;data={...rest,sampleRate:44100,audio:bytes.toString('base64')};}
  result={ok:true,...data};
 }catch(e){result={ok:false,error:e.message};}
 process.stdout.write(JSON.stringify(result)+'\n');
});
