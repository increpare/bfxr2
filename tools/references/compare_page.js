#!/usr/bin/env node
// Build a listening page that pairs tagged reference sounds with the Soundboard's takes and
// with matcher fits, lets the listener rate each approximation, and emits JSON to paste back.
//   node tools/references/compare_page.js <tagged_wav_root> <match_out_root> <output_dir> [--takes 3] [--round 2] [--max-score 1.5] [--no-matches]
// Only the items to be rated are listed: our takes per verb and matcher fits paired with their source.
// The output is private: it contains the listener's own reference audio. Nothing here is committed.
'use strict';
const fs=require('node:fs'),path=require('node:path');
const {createBoardContext,activeDuration,plain}=require('../../tests/helpers/board-context');
const {encodeWav16}=require('../render/wav');
const [root,matchRoot,outDir]=process.argv.slice(2,5);
const flag=(name,fallback)=>{const i=process.argv.indexOf(name);return i>0?process.argv[i+1]:fallback;};
const takesPerVerb=parseInt(flag('--takes','3'),10),round=parseInt(flag('--round','1'),10),maxScore=parseFloat(flag('--max-score','1.5')),noMatches=process.argv.includes('--no-matches');
// Keep in step with tools/references/measure_tagged.py.
const TAG_TO_VERB={jump:'jump',double_jump:'jump',fall:'land',footstep:'step',step:'step',clothes:'step',attack:'swing',sword:'swing',draw_weapon:'swing',hit:'hit',shoot:'shoot',laser:'shoot',explode:'explode',collect:'coin',chips:'coin',power_up:'powerup',unlock:'unlock',motiv:'confirm',bell:'confirm',select:'confirm',click:'blip',card:'blip',forbidden:'alert',carbeep:'alert',magic:'cast',monster:'roar',animal:'roar',voice:'hurt',door:'door',dice:'break',slime:'splash',die:'lose'};
// Matcher runs are named <slug>; this maps them back to their source file.
const MATCH_SOURCES={coin_nes:'collect/coin (nes).wav',mario1_jump:'jump/Mario 1 - Jump.wav',mario3_jump_nes:'jump/Mario 3 - jump (nes).wav',fox_laser:'laser/Fox - Laser Gun.wav',select2:'select/Select 2.wav',error1:'forbidden/error_001.wav',hit_block_nes:'hit/hit block (nes).wav',power_up:'power_up/Power Up.wav',samus_jump:'jump/Samus - Super High Jump.wav',laser_retro:'laser/laserRetro_002.wav'};
fs.mkdirSync(path.join(outDir,'ref'),{recursive:true});fs.mkdirSync(path.join(outDir,'ours'),{recursive:true});
const api=createBoardContext();
const verbs=plain(api.run('GAME_VERBS'));
const slug=s=>s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
function seedFor(text){let h=2166136261;for(const c of text)h=Math.imul(h^c.charCodeAt(0),16777619);return (h>>>0)/4294967296;}
const sections=[];
const byVerb={};
for(const tag of fs.readdirSync(root)){
 const verb=TAG_TO_VERB[tag];if(!verb)continue;
 const dir=path.join(root,tag);if(!fs.statSync(dir).isDirectory())continue;
 for(const file of fs.readdirSync(dir).filter(f=>f.endsWith('.wav'))){
  const id=slug(tag+'-'+file.replace(/\.wav$/,''));
  (byVerb[verb]??=[]).push({id,tag,file,src:path.join(dir,file)});
 }
}
const matches=[];
if(!noMatches&&matchRoot&&fs.existsSync(matchRoot))for(const name of fs.readdirSync(matchRoot)){
 const report=path.join(matchRoot,name,'report.json');if(!fs.existsSync(report)||!MATCH_SOURCES[name])continue;
 const r=JSON.parse(fs.readFileSync(report,'utf8'));const best=r.results.slice().sort((a,b)=>a.score-b.score)[0];
 const wav=path.join(matchRoot,name,best.file.replace('.bfxr','.wav'));if(!fs.existsSync(wav)||best.score>maxScore)continue;
 const dest='ours/match-'+slug(name)+'.wav';fs.copyFileSync(wav,path.join(outDir,dest));
 const source=MATCH_SOURCES[name];const tag=source.split('/')[0];const refDest='ref/'+slug(tag+'-'+source.split('/')[1].replace(/\.wav$/,''))+'.wav';
 fs.copyFileSync(path.join(root,source),path.join(outDir,refDest));
 matches.push({id:'r'+round+'-match-'+slug(name),verb:TAG_TO_VERB[tag],source:refDest,sourceName:source,ours:dest,score:+best.score.toFixed(2),wave:best.wave_type_name});
}
for(const verb of verbs){
 const refs=byVerb[verb.id]||[];if(!refs.length)continue;
 const takes=[];const seen=new Set();
 for(let take=0;take<takesPerVerb;take++){
  api.run(`Math.random=SoundDSP.rng(${seedFor('page'+round+verb.id+take)});var s=new Soundboard();s.generate_recipe(${JSON.stringify(verb.id)});`);
  let label=plain(api.run('s.describe()'));
  for(let tries=0;seen.has(label)&&tries<6;tries++){api.run(`Math.random=SoundDSP.rng(${seedFor('page'+round+verb.id+take+'-'+tries)});s.generate_recipe(${JSON.stringify(verb.id)});`);label=plain(api.run('s.describe()'));}
  seen.add(label);
  const pcm=api.run('s.generate_sound();s.sound.getBuffer().slice()');
  const id='r'+round+'-'+verb.id+'-take-'+(take+1);const dest='ours/'+id+'.wav';
  fs.writeFileSync(path.join(outDir,dest),encodeWav16(pcm,44100));
  takes.push({id,label,file:dest,seconds:+activeDuration(pcm).toFixed(2)});
 }
 sections.push({verb,refs,takes,matches:matches.filter(m=>m.verb===verb.id)});
}
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
const audio=(file)=>`<audio controls preload="none" src="${esc(file)}"></audio>`;
const rating=(id,kind)=>`<span class="stars" data-id="${esc(id)}" data-kind="${kind}">${[1,2,3,4,5].map(n=>`<button type="button" data-n="${n}" title="${n} of 5">${n}</button>`).join('')}</span><input class="note" data-id="${esc(id)}" placeholder="note (optional)">`;
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Soundboard rating, round ${round}</title>
<style>body{margin:24px auto;max-width:1000px;padding:0 18px;font:14px/1.4 system-ui;background:#d6c9af;color:#423225}h1{font-size:24px}h2{font-size:18px;margin:34px 0 4px;border-bottom:1px solid #b9a78a;padding-bottom:4px}h3{font-size:13px;text-transform:uppercase;letter-spacing:.08em;opacity:.7;margin:16px 0 6px}
.row{display:grid;grid-template-columns:1fr 240px auto;gap:10px;align-items:center;padding:6px 8px;border-radius:5px;background:#ede4d2;margin-bottom:5px}.row.ref{background:#e4dac4}.row .name{font-size:13px;overflow-wrap:anywhere}.row small{display:block;opacity:.7}
audio{width:240px;height:30px}.stars button{width:26px;height:26px;margin-right:2px;border:1px solid #b9a78a;border-radius:4px;background:#f6efe0;cursor:pointer}.stars button.on{background:#593b2a;color:#fff}.note{margin-left:8px;width:170px;padding:4px;border:1px solid #b9a78a;border-radius:4px;background:#fff8ea}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;background:#ede4d2;padding:8px;border-radius:5px;margin-bottom:6px}.pair .half{font-size:13px}.pair .half b{display:block;font-weight:normal;opacity:.75;font-size:12px}
textarea{width:100%;height:220px;font:12px monospace;margin-top:8px}.bar{display:flex;gap:8px;align-items:center;margin:8px 0}.bar button{padding:6px 12px}p.help{font-size:13px;opacity:.85}</style>
<h1>Soundboard rating, round ${round}</h1>
<p class="help">Our takes for each verb, and any matcher fits paired with their source. Rate from 1 (nothing like it) to 5 (would use it); add a note where a number is not enough. Ratings save in this browser; the JSON at the bottom updates as you go. Copy it and paste it back.</p>
<div class="bar"><button type="button" id="stop">Stop all</button><span id="progress"></span></div>
${sections.map(s=>`<h2>${esc(s.verb.name)} <small style="font-weight:normal;font-size:12px;opacity:.7">${esc(s.verb.tip)}</small></h2>
<h3>Our takes for ${esc(s.verb.name)} (${s.refs.length} of your references are tagged for it)</h3>
${s.takes.map(t=>`<div class="row"><div class="name">${esc(t.label)}<small>${t.seconds}s</small></div>${audio(t.file)}<span>${rating(t.id,'take')}</span></div>`).join('')}
${s.matches.length?`<h3>Matcher fits</h3>${s.matches.map(m=>`<div class="pair"><div class="half"><b>source: ${esc(m.sourceName)}</b>${audio(m.source)}</div><div class="half"><b>fit: Bfxr ${esc(m.wave)}, score ${m.score}</b>${audio(m.ours)}<div>${rating(m.id,'match')}</div></div></div>`).join('')}`:''}`).join('')}
<h2>Your ratings</h2>
<div class="bar"><button type="button" id="copy">Copy JSON</button><button type="button" id="clear">Clear ratings</button><span id="count"></span></div>
<textarea id="json" readonly></textarea>
<script>
const KEY='bfxr-reference-ratings-round-${round}';let data={};try{data=JSON.parse(localStorage.getItem(KEY)||'{}')}catch{data={}}
const labels=${JSON.stringify(Object.fromEntries([...sections.flatMap(s=>s.takes.map(t=>[t.id,{verb:s.verb.id,kind:'take',label:t.label}])),...matches.map(m=>[m.id,{verb:m.verb,kind:'match',label:m.sourceName+' -> Bfxr '+m.wave}])]))};
function render(){for(const span of document.querySelectorAll('.stars')){const r=data[span.dataset.id]?.rating;for(const b of span.children)b.classList.toggle('on',+b.dataset.n===r);}
 for(const input of document.querySelectorAll('.note'))input.value=data[input.dataset.id]?.note||'';
 const out={};for(const [id,v] of Object.entries(data))out[id]={...labels[id],...v};
 document.getElementById('json').value=JSON.stringify(out,null,1);
 const total=Object.keys(labels).length,done=Object.values(data).filter(v=>v.rating).length;
 document.getElementById('count').textContent=done+' of '+total+' rated';document.getElementById('progress').textContent=done+' / '+total;}
function save(){try{localStorage.setItem(KEY,JSON.stringify(data))}catch{}render();}
document.addEventListener('click',e=>{const b=e.target.closest('.stars button');if(!b)return;const id=b.parentElement.dataset.id;data[id]={...(data[id]||{}),rating:+b.dataset.n};save();});
document.addEventListener('input',e=>{if(!e.target.classList.contains('note'))return;const id=e.target.dataset.id;data[id]={...(data[id]||{}),note:e.target.value};save();});
document.getElementById('copy').addEventListener('click',()=>{const t=document.getElementById('json');t.select();navigator.clipboard?.writeText(t.value);});
document.getElementById('clear').addEventListener('click',()=>{if(confirm('Clear all ratings?')){data={};save();}});
document.getElementById('stop').addEventListener('click',()=>{for(const a of document.querySelectorAll('audio'))a.pause();});
document.addEventListener('play',e=>{for(const a of document.querySelectorAll('audio'))if(a!==e.target)a.pause()},true);
render();
</script></html>`;
fs.writeFileSync(path.join(outDir,'index.html'),html);
console.log(JSON.stringify({sections:sections.length,references:Object.values(byVerb).reduce((n,a)=>n+a.length,0),takes:sections.reduce((n,s)=>n+s.takes.length,0),matches:matches.length}));
