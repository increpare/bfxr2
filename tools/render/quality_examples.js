#!/usr/bin/env node
// Compact, editable listening set for the sound-quality pass.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {createContext,root,plain}=require('../../tests/helpers/synth-context');
const {encodeWav16}=require('./wav');
const families=['Transfxr','Fractr','Boomr','Rollr','Rustlr','Breathr','Pluckr','Tappr','Notifr','Pulser','Whooshr','Stackr'];
const api=createContext(families),rate=44100;
for(const file of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP'])api.load(`js/audio/${file}.js`);
api.load('js/synths/Chattr.js');
const output=path.resolve(process.argv[2]||path.join(root,'examples/Quality'));
fs.mkdirSync(output,{recursive:true});
const demos=[
 ['Fractr','glass_cascade','Glass crack',{duration:.9,spread:.18,decay:.22,fragments:40}],
 ['Fractr','stone_collapse','Stone fracture',{duration:1.1,spread:.35,fragments:45}],
 ['Boomr','grenade','Grenade',{duration:1.1}],
 ['Boomr','depth_charge','Deep blast',{duration:1.4}],
 ['Rollr','wooden_wheels','Wood over boards',{duration:1.25,surface:1}],
 ['Rollr','skateboard','Skateboard over grit',{duration:1.25,surface:2}],
 ['Rustlr','page_turn','Paper turn',{duration:.65}],
 ['Rustlr','cloth_fold','Cloth fold',{duration:.6}],
 ['Tappr','focus','Focus',{}],['Tappr','select','Select',{}],['Tappr','back','Back',{}],['Tappr','panel_open','Panel open',{}],
 ['Breathr','deep_breath','Airflow breath',{duration:2.8,source:0}],
 ['Breathr','tired_runner','Retro breath',{duration:1.8,source:1,cycles:2}],
 ['Breathr','sleeping_beast','Snore',{duration:2.8,source:2,cycles:1}],
 ...['Nylon','Steel','Gut','Rubber','Glass','Gravity'].map((name,material)=>['Pluckr','metal_string',name+' string',
  {duration:1.4,material,pitch:.43,strings:2,damping:.12,brightness:.65,pluck:.28,coupling:.2,strum:.12,inharmonic:.05,seed:.312}]),
 ...[.1,.5,.9].map((instrumentSeed,i)=>['Notifr','message','Bell '+(i+1),
  {tone:1,instrumentSeed,seed:.312,duration:.45,pitch:.55,interval:5,pulses:2,softness:.18,ring:.7,echo:0}]),
 ['Pulser','panic','Panic pulse',{duration:1.1,beats:3}],
 ...[['Whistle',6],['Voice',8],['FMSyn',11]].map(([name,waveType])=>['Transfxr','laser_zip',name+' transition',{waveType,duration:.35,echo:0}]),
 ...[['Vocal',-1],['Square',0],['Voice',11]].map(([name,waveType])=>['Chattr','clear_speaker',name+' hello',{waveType,text:'Hello!',seed:.3}])
];
const collection={},sounds=[];
function seedFor(name){let hash=2166136261;for(const c of name)hash=Math.imul(hash^c.charCodeAt(0),16777619);return(hash>>>0)/4294967296;}
function measure(pcm,name){let peak=0,energy=0;for(const v of pcm){assert.ok(Number.isFinite(v),name);peak=Math.max(peak,Math.abs(v));energy+=v*v;}
 const rms=Math.sqrt(energy/pcm.length);assert.ok(peak<1&&peak>.015&&rms>.0008,`${name}: RMS ${rms}, peak ${peak}`);
 assert.ok(Math.abs(pcm[0])<.00001&&Math.abs(pcm.at(-1))<.00001,name+' edges');
 return{duration:pcm.length/rate,rms,peak,sha256:crypto.createHash('sha256').update(Buffer.from(pcm.buffer)).digest('hex')};}
function save(synth,name,params){
 const serialized=JSON.stringify(params),pcm=api.run('s.generate_sound();s.sound.getBuffer().slice()');
 const metrics=measure(pcm,name);
 const replay=api.run(`var replay=new ${synth}();replay.apply_params(${serialized});replay.generate_sound();replay.sound.getBuffer()`);
 assert.equal(measure(replay,name+' replay').sha256,metrics.sha256);
 const file=(synth+'-'+name).toLowerCase().replace(/[^a-z0-9]+/g,'-')+'.wav';
 fs.writeFileSync(path.join(output,file),encodeWav16(pcm,rate));
 collection[synth]??={files:[],selected_file_index:0,create_new_sound:true,play_on_change:true,locked_params:plain(api.run('s.locked_params'))};
 collection[synth].files.push([name,serialized,serialized]);sounds.push({synth,name,file,params,...metrics,pcm});
}
for(const [synth,recipe,name,overrides] of demos){
 api.run(`Math.random=SoundDSP.rng(${seedFor(synth+name)});var s=new ${synth}();`);
 if(synth==='Transfxr')api.run(`s.generate_example(${JSON.stringify(recipe)},false)`);
 else if(synth==='Chattr')api.run(`s.generate_character(${JSON.stringify(recipe)},false)`);
 else api.run(`s.generate_recipe(${JSON.stringify(recipe)})`);
 const params=plain(api.run(`s.apply_params(${JSON.stringify(overrides)});s.params`));save(synth,name,params);
}
api.run(`var s=new Stackr(),air=new Whooshr(),impact=new Boomr();Math.random=SoundDSP.rng(.618);
 air.generate_recipe('heavy_swing');air.set_param('duration',.6);impact.generate_recipe('grenade');impact.set_param('duration',1.1);
 s.add_source(air,'Incoming air');s.add_source(impact,'Impact');var layers=s.get_layers();layers[1].start=.38;s.set_param('layers',layers);`);
save('Stackr','Whoosh into impact',plain(api.run('s.params')));
collection.active_tab_index=12;
fs.writeFileSync(path.join(output,'Quality.bcol'),JSON.stringify(collection,null,2)+'\n');
const selected=['Glass crack','Grenade','Wood over boards','Paper turn','Focus','Select','Back','Panel open',
 'Airflow breath','Retro breath','Snore','Nylon string','Steel string','Rubber string','Glass string','Gravity string','Bell 1','Bell 2','Bell 3','Whoosh into impact'];
const clips=[];let frames=0;const gap=Math.round(.25*rate);
for(const name of selected){const sound=sounds.find(s=>s.name===name),gain=Math.min(3,.085/sound.rms,.65/sound.peak);
 const pcm=sound.pcm.map(v=>v*gain);clips.push({synth:sound.synth,name,start:frames/rate,end:(frames+pcm.length)/rate,gain,pcm});frames+=pcm.length+gap;}
const reel=new Float32Array(frames-gap);for(const clip of clips)reel.set(clip.pcm,Math.round(clip.start*rate));
fs.writeFileSync(path.join(output,'quality_showcase.wav'),encodeWav16(reel,rate));
const clean=({pcm,...v})=>v;
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({sounds:sounds.map(clean),reel:{duration:reel.length/rate,clips:clips.map(clean)}},null,2)+'\n');
fs.writeFileSync(path.join(output,'README.md'),[
 '# Sound quality examples','',`${sounds.length} editable examples from the sound-quality pass. Open Quality.bcol using Open Data. It replaces the example lists in its included tabs; save your current collection first if needed.`,'',
 `The [${(reel.length/rate).toFixed(1)}-second reel](quality_showcase.wav) plays complete sounds with short gaps. Levels are balanced in the reel; individual WAVs match their saved settings.`,
 '', '| Start | Tab | Sound |','| --- | --- | --- |',...clips.map(c=>`| ${c.start.toFixed(2)} s | ${c.synth} | ${c.name} |`),
 '', 'The three bells use the same alert pattern and different instrument seeds. The strings share tuning, excitation seed and editable controls; only their material changes.',
 '', 'Stackr: click New empty stack, make a sound in another tab, then Layer in Stackr. Add another sound the same way. Leave Start at zero to overlay, or increase it to make a sequence. The included Whoosh into impact is an editable example.',
 '', 'Rebuild: `node tools/render/quality_examples.js`. WAVs are generated locally and ignored by Git. All examples are checked for finite bounded audio, faded edges and identical replay after parameter serialization.',''
].join('\n'));
console.log(`Wrote ${sounds.length} examples and ${(reel.length/rate).toFixed(2)} s reel to ${output}`);
