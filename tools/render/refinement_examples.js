#!/usr/bin/env node
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
const {encodeWav16}=require('./wav');
const families=['Transfxr','Clonkr','Machinr','Jinglr','Squishr','Crittr','Signlr','Fractr','Riftr','Swarmr','Rustlr','Boomr','Zappr','Whooshr','Bouncr','Breathr','Choirr','Pluckr','Glitchr','Mixr'];
const api=createContext(families),rate=44100;
const output=path.resolve(process.argv[2]||path.join(root,'examples/Refined'));
fs.mkdirSync(output,{recursive:true});
const demos=[

 ['Fractr','glass_cascade','Glass breaks',{duration:.85,spread:.2,stress:.55,fracture:1}],
 ['Fractr','ice_wall','Ice splits',{duration:1.1,fracture:1}],
 ['Fractr','bone_scatter','Dry snap',{duration:.6,fragments:12,spread:.1,fracture:1}],
 ['Boomr','grenade','Grenade',{duration:1.2}],
 ['Boomr','depth_charge','Depth charge',{duration:1.6}],
 ['Boomr','fireball','Gas fireball',{duration:1.3}],
 ['Boomr','demolition','Structural collapse',{duration:1.5}],

 ['Bouncr','metal_ball','Steel on concrete',{duration:.85}],
 ['Bouncr','wooden_dice','Wood on metal',{duration:1.1}],
 ['Bouncr','coin_spin','Coin on glass',{duration:1.2}],
 ['Bouncr','heavy_tumble','Stone into earth',{duration:.9}],
 ...['save_corruption','teleport_error','rewind_burst','digital_death'].map((id,i)=>
  ['Glitchr',id,['Buffer underrun','Codec warble','Tape scrub','Granular tear'][i],{duration:.8}]),
 ['Signlr','radar_blip','Radar blip',{duration:.5}],
 ['Signlr','target_lock','Target lock',{duration:.6}],
 ['Signlr','sonar_map','Sonar return',{duration:1.2,packets:1}],
 ['Breathr','snore','Snore',{duration:2.3}],
 ['Pluckr','metal_string','Steel tremolo',{duration:1.5,strings:1,tremolo:.75,tremoloRate:5.2}],

 ...['confirm','message','dismiss','denied'].map(id=>['Jinglr',id,id[0].toUpperCase()+id.slice(1),{}]),
 ['Transfxr','morph','Whistle into FM',{duration:1.1,waveType:6,waveTo:11,echo:.15}],
 ['Mixr','spell_hit','Air and ice',{}],['Mixr','spark_impact','Steel and electricity',{}]
];
const collection={},sounds=[];
function hash(pcm){return crypto.createHash('sha256').update(Buffer.from(pcm.buffer,pcm.byteOffset,pcm.byteLength)).digest('hex');}
function seedFor(name){let h=2166136261;for(const c of name)h=Math.imul(h^c.charCodeAt(0),16777619);return(h>>>0)/4294967296;}
for(const [synth,recipe,name,overrides] of demos){
 api.run(`Math.random=SoundDSP.rng(${seedFor(synth+name)});var s=new ${synth}();`);
 if(synth==='Transfxr')api.run('s.generate_morph()');
 else api.run(`s.generate_recipe(${JSON.stringify(recipe)})`);
 const params=plain(api.run(`s.apply_params(${JSON.stringify(overrides)});s.params`)),serialized=JSON.stringify(params);
 const pcm=api.run('s.generate_sound();s.sound.getBuffer().slice()');
 let peak=0,energy=0;for(const v of pcm){assert.ok(Number.isFinite(v),name);peak=Math.max(peak,Math.abs(v));energy+=v*v;}
 const rms=Math.sqrt(energy/pcm.length);assert.ok(peak<=1&&peak>.015&&rms>.001,`${name}: ${peak} / ${rms}`);
 assert.ok(Math.abs(pcm[0])<.0001&&Math.abs(pcm.at(-1))<.0001,name+' edges');
 const replay=api.run(`var copy=new ${synth}();copy.apply_params(${serialized});copy.generate_sound();copy.sound.getBuffer()`);
 assert.equal(hash(pcm),hash(replay),name+' snapshot replay');
 const file=(synth+'-'+name).toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.wav';
 fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));
 collection[synth]??={files:[],selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params:plain(api.run('s.locked_params'))};
 collection[synth].files.push([name,serialized,serialized]);
 sounds.push({synth,name,file,params,duration:pcm.length/rate,peak,rms,sha256:hash(pcm),pcm});
}
collection.active_tab_name='Fractr';
fs.writeFileSync(path.join(output,'Refined.bcol'),JSON.stringify(collection,null,2)+'\n');
const reelNames=['Glass breaks','Ice splits','Grenade','Depth charge','Gas fireball','Steel on concrete','Wood on metal','Codec warble','Tape scrub','Radar blip','Target lock','Snore','Confirm','Whistle into FM','Air and ice'];
function reel(file,selected){let length=0;const clips=[];for(const name of selected){const s=sounds.find(s=>s.name===name),gain=Math.min(2.5,.08/s.rms,.65/s.peak);clips.push({name,start:length/rate,duration:s.duration,gain,pcm:s.pcm.map(v=>v*gain)});length+=s.pcm.length+Math.round(rate*.22);}
 const pcm=new Float32Array(length-Math.round(rate*.22));for(const clip of clips)pcm.set(clip.pcm,Math.round(clip.start*rate));fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));return {file,duration:pcm.length/rate,clips:clips.map(({pcm,...clip})=>clip)};}
const reels=[reel('effects.wav',reelNames)];
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({sounds:sounds.map(({pcm,...sound})=>sound),reels},null,2)+'\n');
const editLink=s=>'../../?sfx='+encodeURIComponent(s.synth+'~@2~'+JSON.stringify({filename:s.name,params:s.params}).replace(/~/g,'\\u007e'));
const html=`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Refined sounds · Bfxr</title>
<style>body{margin:32px auto;max-width:1000px;padding:0 20px;background:#d6c9af;color:#423225;font:15px system-ui}h1{font-size:28px}h2{font-size:18px;margin-top:28px}a{color:#593b2a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:12px}article{background:#ede4d2;border:1px solid #b9a78a;border-radius:6px;padding:14px}article strong{display:block;margin-bottom:8px}audio{width:100%;height:34px}.intro{margin-bottom:22px}.tag{font-size:12px;color:#806c51;margin-top:8px}</style>
<h1>Refined sounds</h1><p class="intro"><a href="../../">Back to Bfxr</a> · <a href="Refined.bcol" download>Editable collection</a></p>
<div class="grid">${reels.map((r,i)=>`<article><strong>Effects · ${r.duration.toFixed(1)}s</strong><audio controls preload="none" src="${r.file}"></audio></article>`).join('')}</div>
${[...new Set(sounds.map(s=>s.synth))].map(synth=>`<h2>${synth==='Bouncr'?'Impactr':synth}</h2><div class="grid">${sounds.filter(s=>s.synth===synth).map(s=>`<article><strong>${s.name}</strong><audio controls preload="none" src="${s.file}"></audio><div class="tag">${s.duration.toFixed(2)}s · <a href="${editLink(s)}">Edit in Bfxr</a></div></article>`).join('')}</div>`).join('')}
<script>document.addEventListener('play',e=>{for(const a of document.querySelectorAll('audio'))if(a!==e.target)a.pause()},true)</script></html>`;
fs.writeFileSync(path.join(output,'index.html'),html);
console.log(`Rendered ${sounds.length} reproducible examples; effects reel ${reels[0].duration.toFixed(1)}s.`);
