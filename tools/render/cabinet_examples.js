#!/usr/bin/env node
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
const {encodeWav16}=require('./wav');
const names=['Bfxr','Transfxr','Clonkr','Machinr','Jinglr','Squishr','Crittr','Birdr','Signlr','Fractr','Riftr','Swarmr','Rustlr','Boomr','Zappr','Whooshr','Bouncr','Breathr','Choirr','Pluckr','Glitchr','Mixr'];
const api=createContext(names),rate=44100,output=path.resolve(process.argv[2]||path.join(root,'examples/Cabinet'));
fs.mkdirSync(output,{recursive:true});
const demos=[
 ...plain(api.run('new Mixr().recipes')).map(r=>['Mixr',r.id,r.name,{}]),
 ...plain(api.run('new Birdr().recipes')).map(r=>['Birdr',r.id,r.name,{}]),
 ['Crittr','woof','Woof',{}],['Crittr','meow','Meow',{}],
 ['Fractr','bone_scatter','Bone Snap',{}],['Fractr','biscuit_crunch','Biscuit Crunch',{}],
 ['Fractr','glass_snap','Glass Snap',{}],['Fractr','ice_crack','Ice Crack',{}],
 ['Boomr','grenade','Grenade',{}],['Boomr','gas_tank','Gas Tank',{}],
 ['Boomr','demolition','Rubble and Aftershock',{}],['Boomr','implosion','Implosion',{}],
 ['Breathr','inhale','Inhale',{}],['Breathr','exhale','Exhale',{}],['Breathr','sigh','Sigh',{}],['Breathr','snore','Snore',{}],
 ['Pluckr','metal_string','Steel Tremolo',{duration:1.5,strings:1,tremolo:.7,vibrato:0,tremoloRate:4.5}],
 ['Pluckr','harp','Nylon Vibrato',{duration:1.7,strings:1,material:0,tremolo:0,vibrato:.5,tremoloRate:5.1}],
 ['Swarmr','locusts','Locusts',{}],['Swarmr','drone_patrol','Drone Patrol',{}],['Swarmr','scarabs','Scarabs',{}]
];
const hash=pcm=>crypto.createHash('sha256').update(Buffer.from(pcm.buffer,pcm.byteOffset,pcm.byteLength)).digest('hex');
function seedFor(text){let h=2166136261;for(const c of text)h=Math.imul(h^c.charCodeAt(0),16777619);return (h>>>0)/4294967296;}
function metrics(pcm){let peak=0,energy=0;for(const v of pcm){assert.ok(Number.isFinite(v));peak=Math.max(peak,Math.abs(v));energy+=v*v;}return {peak,rms:Math.sqrt(energy/pcm.length)};}
const collection={},sounds=[];
for(const [synth,id,name,overrides] of demos){
 api.run(`Math.random=SoundDSP.rng(${seedFor(synth+name)});var s=new ${synth}();s.generate_recipe(${JSON.stringify(id)});s.apply_params(${JSON.stringify(overrides)});`);
 const params=plain(api.run('s.params')),serialized=JSON.stringify(params),pcm=api.run('s.generate_sound();s.sound.getBuffer().slice()');
 const levels=metrics(pcm);assert.ok(levels.peak>.025&&levels.peak<=1&&levels.rms>.001,name+' audible');
 const replay=api.run(`var copy=new ${synth}();copy.apply_params(${serialized});copy.generate_sound();copy.sound.getBuffer()`);
 assert.equal(hash(pcm),hash(replay),name+' replay');
 const file=(synth+'-'+name).toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.wav';
 fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));
 const sourceClips=synth==='Mixr'?plain(api.run('s.get_sources()')).map((source,index)=>{
  const a=api.run(`Mixr.render_source(${JSON.stringify(source)},${source.renderSeed})`),levels=metrics(a);
  const sourceFile=file.replace('.wav',index===0?'-a.wav':'-b.wav');fs.writeFileSync(path.join(output,sourceFile),encodeWav16(a,rate));
  return {name:source.synth+' · '+source.name,file:sourceFile,...levels};
 }):[];
 collection[synth]??={files:[],selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params:plain(api.run('s.locked_params'))};
 collection[synth].files.push([name,serialized,serialized]);
 sounds.push({synth,name,file,params,sourceClips,duration:pcm.length/rate,...levels,sha256:hash(pcm),pcm});
}
collection.active_tab_name='Mixr';fs.writeFileSync(path.join(output,'Cabinet.bcol'),JSON.stringify(collection,null,2)+'\n');
const reelIds=['haunted','crystal_prize','goo_machine','garden_lute','clockwork_familiar','spark_impact'];
const reelNames=reelIds.map(id=>plain(api.run('new Mixr().recipes')).find(recipe=>recipe.id===id).name);
const clips=reelNames.map(name=>sounds.find(s=>s.synth==='Mixr'&&s.name===name));
const gap=Math.round(rate*.25),reel=new Float32Array(clips.reduce((n,s)=>n+s.pcm.length+gap,0)-gap);let offset=0;
for(const s of clips){reel.set(s.pcm,offset);offset+=s.pcm.length+gap;}
fs.writeFileSync(path.join(output,'mixr-preview.wav'),encodeWav16(reel,rate));
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({sounds:sounds.map(({pcm,...s})=>s)},null,2)+'\n');
const editLink=s=>'../../?sfx='+encodeURIComponent(s.synth+'~@2~'+JSON.stringify({filename:s.name,params:s.params}).replace(/~/g,'\\u007e'));
const audio=file=>`<audio controls preload="none" src="${file}"></audio>`;
fs.writeFileSync(path.join(output,'index.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Mixr & friends · Bfxr</title>
<style>body{margin:30px auto;max-width:1050px;padding:0 22px;background:#d6c9af;color:#423225;font:15px system-ui}h1{font-size:28px}h2{font-size:19px;margin:30px 0 12px}a{color:#593b2a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}article{background:#ede4d2;border:1px solid #b9a78a;border-radius:6px;padding:14px}article strong{display:block;margin-bottom:8px}audio{width:100%;height:34px}small{display:block;font-size:12px;margin-top:9px}details{margin-top:12px;font-size:12px}summary{cursor:pointer}details label{display:block;margin:10px 0 5px}</style>
<h1>Mixr & friends</h1><p><a href="../../">Bfxr</a> · <a href="Cabinet.bcol" download>Editable collection</a></p>
<article><strong>Six combinations</strong>${audio('mixr-preview.wav')}</article>
${[...new Set(sounds.map(s=>s.synth))].map(synth=>`<h2>${synth}</h2><div class="grid">${sounds.filter(s=>s.synth===synth).map(s=>`<article><strong>${s.name}</strong>${audio(s.file)}<small>${s.duration.toFixed(2)}s · <a href="${editLink(s)}">Edit in Bfxr</a></small>${s.sourceClips.length?`<details><summary>Hear A / B</summary>${s.sourceClips.map((source,i)=>`<label>${i?'B':'A'} · ${source.name}</label>${audio(source.file)}`).join('')}</details>`:''}</article>`).join('')}</div>`).join('')}
<script>document.addEventListener('play',e=>{for(const a of document.querySelectorAll('audio'))if(a!==e.target)a.pause()},true)</script></html>`);
console.log(JSON.stringify({examples:sounds.length,reelSeconds:reel.length/rate,mixes:sounds.filter(s=>s.synth==='Mixr').map(s=>({name:s.name,rms:s.rms,sources:s.sourceClips.map(a=>({name:a.name,rms:a.rms}))}))},null,2));
