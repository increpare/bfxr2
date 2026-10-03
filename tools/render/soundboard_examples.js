#!/usr/bin/env node
// Render a listening gallery for the Soundboard: several takes per verb, a reel, an editable
// collection and a validation record.   node tools/render/soundboard_examples.js [outputDir]
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {createBoardContext,activeDuration,root,plain}=require('../../tests/helpers/board-context');
const {encodeWav16}=require('./wav');
const api=createBoardContext(),rate=44100,output=path.resolve(process.argv[2]||path.join(root,'examples/Soundboard'));
const TAKES=4;
fs.mkdirSync(output,{recursive:true});
const hash=pcm=>crypto.createHash('sha256').update(Buffer.from(pcm.buffer,pcm.byteOffset,pcm.byteLength)).digest('hex');
function seedFor(text){let h=2166136261;for(const c of text)h=Math.imul(h^c.charCodeAt(0),16777619);return (h>>>0)/4294967296;}
function metrics(pcm){let peak=0,energy=0;for(const v of pcm){assert.ok(Number.isFinite(v));peak=Math.max(peak,Math.abs(v));energy+=v*v;}return {peak,rms:Math.sqrt(energy/pcm.length)};}
const verbs=plain(api.run('GAME_VERBS'));
const sounds=[],collection={Soundboard:{files:[],selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params:{}}};
for(const verb of verbs){
 const seen=new Set();
 for(let take=0;take<TAKES;take++){
  // Walk the catalogue so the gallery shows different ingredients, not four rolls of the favourite.
  api.run(`Math.random=SoundDSP.rng(${seedFor(verb.id+take)});var s=new Soundboard();s.generate_recipe(${JSON.stringify(verb.id)});`);
  let label=plain(api.run('s.get_sources().map(x=>x.synth+":"+x.generator).join("+")'));
  for(let tries=0;seen.has(label)&&tries<6;tries++){api.run(`Math.random=SoundDSP.rng(${seedFor(verb.id+take+'-'+tries)});s.generate_recipe(${JSON.stringify(verb.id)});`);label=plain(api.run('s.get_sources().map(x=>x.synth+":"+x.generator).join("+")'));}
  seen.add(label);
  const params=plain(api.run('s.params')),serialized=JSON.stringify(params),pcm=api.run('s.generate_sound();s.sound.getBuffer().slice()');
  const levels=metrics(pcm);assert.ok(levels.peak>.02&&levels.peak<=1,verb.id+' audible');
  const replay=api.run(`var copy=new Soundboard();copy.apply_params(${serialized});copy.generate_sound();copy.sound.getBuffer()`);
  assert.equal(hash(pcm),hash(replay),verb.id+' replay');
  const name=verb.name+' '+(take+1),file=('soundboard-'+verb.id+'-'+(take+1))+'.wav';
  fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));
  collection.Soundboard.files.push([name,serialized,serialized]);
  sounds.push({verb:verb.id,verbName:verb.name,row:verb.row,name,file,params,ingredients:plain(api.run('s.describe()')),duration:activeDuration(pcm),...levels,sha256:hash(pcm),pcm});
 }
}
collection.active_tab_name='Soundboard';fs.writeFileSync(path.join(output,'Soundboard.bcol'),JSON.stringify(collection,null,2)+'\n');
const gap=Math.round(rate*.22),reelClips=verbs.map(verb=>sounds.find(s=>s.verb===verb.id));
const reel=new Float32Array(reelClips.reduce((n,s)=>n+s.pcm.length+gap,0)-gap);let offset=0;
for(const s of reelClips){reel.set(s.pcm,offset);offset+=s.pcm.length+gap;}
fs.writeFileSync(path.join(output,'soundboard-reel.wav'),encodeWav16(reel,rate));
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({takes:TAKES,sounds:sounds.map(({pcm,...s})=>s)},null,1)+'\n');
const editLink=s=>'../../?sfx='+encodeURIComponent('Soundboard~@2~'+JSON.stringify({filename:s.name,params:s.params}).replace(/~/g,'\\u007e'));
const audio=file=>`<audio controls preload="none" src="${file}"></audio>`;
const rows=[...new Set(verbs.map(v=>v.row))];
fs.writeFileSync(path.join(output,'index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Soundboard · Bfxr</title>
<style>body{margin:30px auto;max-width:1100px;padding:0 22px;background:#d6c9af;color:#423225;font:15px system-ui}h1{font-size:28px}h2{font-size:20px;margin:28px 0 6px}h3{font-size:15px;margin:14px 0 6px}a{color:#593b2a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}article{background:#ede4d2;border:1px solid #b9a78a;border-radius:6px;padding:10px 12px}article strong{display:block;margin-bottom:6px;font-size:13px}audio{width:100%;height:32px}small{display:block;font-size:12px;margin-top:6px}p.row{font-size:12px;opacity:.8;margin:0 0 8px}</style>
<h1>Soundboard</h1><p><a href="../../">Open Bfxr</a> · <a href="Soundboard.bcol" download>Editable collection</a> · ${sounds.length} takes, ${TAKES} per verb. Each take names its ingredients; the catalogue decides their odds.</p>
<article><strong>Reel: one take of every verb</strong>${audio('soundboard-reel.wav')}</article>
${rows.map(row=>`<h2>${row}</h2>`+verbs.filter(v=>v.row===row).map(verb=>`<h3>${verb.name} <span style="font-weight:normal;opacity:.7">· ${verb.tip}</span></h3><div class="grid">${sounds.filter(s=>s.verb===verb.id).map(s=>`<article><strong>${s.ingredients}</strong>${audio(s.file)}<small>${s.duration.toFixed(2)}s · <a href="${editLink(s)}">Edit in Bfxr</a></small></article>`).join('')}</div>`).join('')).join('')}
<script>document.addEventListener('play',e=>{for(const a of document.querySelectorAll('audio'))if(a!==e.target)a.pause()},true)</script></html>`);
console.log(JSON.stringify({examples:sounds.length,reelSeconds:+(reel.length/rate).toFixed(1),ingredients:[...new Set(sounds.map(s=>s.ingredients))].length},null,1));
