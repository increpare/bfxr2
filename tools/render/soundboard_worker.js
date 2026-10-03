#!/usr/bin/env node
'use strict';
// The caller supplies an immutable git-archive snapshot, never the live checkout.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const root=path.resolve(process.argv[2]||'');
const {createBoardContext}=require(path.join(root,'tests/helpers/board-context.js'));
const api=createBoardContext();
const run=code=>vm.runInContext(code,api.context,{timeout:10000});
const plain=value=>JSON.parse(JSON.stringify(value));
const hash=crypto.createHash('sha256').update(fs.readFileSync(__filename));
function fingerprint(dir){
 for(const entry of fs.readdirSync(path.join(root,dir),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
  const relative=dir+'/'+entry.name;
  if(entry.isDirectory())fingerprint(relative);
  else if(entry.name.endsWith('.js'))hash.update(relative+'\0').update(fs.readFileSync(path.join(root,relative))).update('\0');
 }
}
fingerprint('js');fingerprint('tests/helpers');
const sourceHash=hash.digest('hex');
const entries=plain(run(`Object.entries(Soundboard.catalogue).flatMap(([verb,entries])=>entries.map((entry,index)=>({
 verb,index,weight:entry.w||1,composite:!!entry.mix,references:Soundboard.entry_references(entry),
 signature:Soundboard.entry_references(entry).join('+'),entry})))`));
function request(r){
 if(r.op==='inventory')return {sourceHash,sampleRate:44100,entries};
 if(!Number.isInteger(r.seed)||r.seed<0||r.seed>0xffffffff)throw new Error('Seed must be uint32');
 if(r.op==='sample'&&!entries.some(e=>e.verb===r.verb&&e.index===r.index))throw new Error('Unknown catalogue entry');
 if(r.op==='render'&&(!r.params||typeof r.params!=='object'||Array.isArray(r.params)))throw new Error('Invalid params');
 if(!['sample','render'].includes(r.op))throw new Error('Unknown operation');
 api.context.__input=JSON.stringify(r);
 try {
  const params=plain(run(`(()=>{const r=JSON.parse(__input);Math.random=SoundDSP.rng(r.seed/4294967296);
   globalThis.__board=new Soundboard();
   if(r.op==='sample')__board.apply_entry(Soundboard.entries(r.verb)[r.index]);
   else __board.apply_params(r.params);
   return __board.params;})()`));
  const ingredients=run('__board.describe()');
  if(r.op==='sample')return {params,ingredients};
  const pcm=run('__board.generate_sound();__board.sound.getBuffer().slice()');
  if(!pcm.length||!pcm.every(Number.isFinite))throw new Error('Invalid rendered audio');
  return {params,ingredients,audio:Buffer.from(pcm.buffer,pcm.byteOffset,pcm.byteLength).toString('base64')};
 } finally {delete api.context.__input;}
}
require('node:readline').createInterface({input:process.stdin}).on('line',line=>{
 try{process.stdout.write(JSON.stringify({ok:true,...request(JSON.parse(line))})+'\n');}
 catch(error){process.stdout.write(JSON.stringify({ok:false,error:error.message})+'\n');}
});
