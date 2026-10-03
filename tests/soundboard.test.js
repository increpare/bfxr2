const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createBoardContext,activeDuration,root,plain}=require('./helpers/board-context');

test('the game-verb vocabulary is a 5×5 board of unique verbs with duration classes',()=>{
 const {run}=createBoardContext();
 const verbs=plain(run('GAME_VERBS'));
 assert.equal(verbs.length,25);
 assert.equal(new Set(verbs.map(v=>v.id)).size,25);
 const rows=[...new Set(verbs.map(v=>v.row))];
 assert.deepEqual(rows,['Move','Fight','Reward','World','Fantasy']);
 for(const row of rows)assert.equal(verbs.filter(v=>v.row===row).length,5);
 for(const verb of verbs){assert.ok(verb.duration[0]>0&&verb.duration[1]>verb.duration[0],verb.id);assert.ok(verb.name&&verb.tip);}
 assert.equal(run("game_verb('jump').name"),'Jump');assert.equal(run("game_verb('nope')"),null);
});

test('every catalogue ingredient resolves and every verb has at least three solo bases',()=>{
 const {run}=createBoardContext();
 const verbs=plain(run('GAME_VERBS'));
 for(const reference of plain(run('Soundboard.references()')))assert.ok(run(`Mixr.resolve_reference(${JSON.stringify(reference)})`),reference);
 for(const verb of verbs){
  const entries=plain(run(`Soundboard.entries(${JSON.stringify(verb.id)})`));
  assert.ok(entries.filter(e=>e.src).length>=3,verb.id+' bases');
  for(const entry of entries)if(entry.mix)assert.equal(entry.mix.length,2,verb.id+' mixes are base plus sweetener');
 }
 assert.equal(run("Mixr.resolve_reference('Clonkr:hit').generator"),'generate_hit');
 assert.equal(run("Mixr.resolve_reference('Bfxr:coin').generator"),'generate_pickup_coin');
 assert.equal(run("Mixr.resolve_reference('Footsteppr:step').generator"),'randomize_params');
 assert.equal(run("Mixr.resolve_reference('Clonkr:generate_glass_ping').generator"),'generate_glass_ping');
 assert.equal(run("Mixr.resolve_reference('Clonkr:fly')"),null);
 assert.equal(run("Mixr.resolve_reference('Clonkr:set_param')"),null);
 assert.equal(run("Mixr.resolve_reference('Nobody:hit')"),null);
});

test('each catalogue entry renders audible, finite audio inside its verb duration class',()=>{
 const {run}=createBoardContext();
 const verbs=plain(run('GAME_VERBS'));
 const failures=[];
 verbs.forEach((verb,v)=>{
  const entries=plain(run(`Soundboard.entries(${JSON.stringify(verb.id)})`));
  entries.forEach((entry,index)=>{
   run(`Math.random=SoundDSP.rng(${0.17+v*0.031+index*0.007});var s=new Soundboard();s.apply_entry(Soundboard.entries(${JSON.stringify(verb.id)})[${index}]);s.generate_sound();`);
   const pcm=run('s.sound.getBuffer()');
   const label=verb.id+': '+(entry.mix?entry.mix.join(' × '):entry.src);
   if(!pcm.every(x=>Number.isFinite(x)&&Math.abs(x)<=1))failures.push(label+' not finite');
   let peak=0;for(const x of pcm)peak=Math.max(peak,Math.abs(x));
   if(peak<0.02)failures.push(label+' inaudible');
   const duration=activeDuration(pcm);
   if(duration<verb.duration[0]*0.8||duration>verb.duration[1]*1.25)failures.push(label+' '+duration.toFixed(2)+'s outside '+verb.duration.join('–'));
   const sources=plain(run('s.get_sources()'));
   assert.equal(sources.length,entry.mix?2:1,label);
   for(const source of sources)assert.ok(source.generator&&source.generator!=='*',label+' keeps a named generator');
  });
 });
 assert.deepEqual(failures,[]);
});

test('a verb press stores a Mixr record that replays identically, including retired ingredients and alignment',()=>{
 const {run,load}=createBoardContext();load('js/SaveLoad.js');
 const result=plain(run(`(()=>{
  Math.random=SoundDSP.rng(0.41);
  const board=new Soundboard();
  board.apply_entry({mix:['Machinr:door','Clonkr:hit'],balance:0.45,align:2});
  board.generate_sound();const pcm=board.sound.getBuffer().slice();
  tabs=[{synth:board}];
  const saved=SaveLoad.shallow_dict_deserialize(SaveLoad.shallow_dict_serialize('Soundboard','Door',board.params));
  const copy=new Soundboard();copy.apply_params(saved[2]);copy.generate_sound();
  const asMix=new Mixr();asMix.apply_params(JSON.parse(JSON.stringify(board.params)));asMix.generate_sound();
  const retired=new Soundboard();retired.apply_entry({src:'Tappr:generate_select'});retired.generate_sound();
  const retiredCopy=new Soundboard();retiredCopy.apply_params(JSON.parse(JSON.stringify(retired.params)));retiredCopy.generate_sound();
  return {same:pcm.every((v,i)=>v===copy.sound.getBuffer()[i]),mixSame:pcm.every((v,i)=>v===asMix.sound.getBuffer()[i]),
   align:copy.params.align,generator:copy.get_sources()[1].generator,retiredKept:retiredCopy.get_sources()[0].generator,
   retiredSame:retired.sound.getBuffer().every((v,i)=>v===retiredCopy.sound.getBuffer()[i]),
   rejected:asMix.set_source(0,board,'Board')===false};
 })()`));
 assert.equal(result.same,true);assert.equal(result.mixSame,true);assert.equal(result.align,2);
 assert.equal(result.generator,'generate_hit');assert.equal(result.retiredKept,'generate_select');assert.equal(result.retiredSame,true);
 assert.equal(result.rejected,true);
 assert.ok(!plain(run('Stackr.sources().map(c=>c.name)')).includes('Soundboard'));
 assert.ok(!plain(run('Mixr.generators().map(g=>g.synth)')).includes('Soundboard'));
});

test('verb presses draw varied ingredients, avoid immediate repeats and respect a sources lock',()=>{
 const {run}=createBoardContext();
 const result=plain(run(`(()=>{
  Math.random=SoundDSP.rng(0.77);
  const board=new Soundboard();const labels=[];
  for(let i=0;i<12;i++){board.generate_jump();labels.push(board.get_sources().map(s=>s.synth+':'+s.generator).join('+'));}
  const repeats=labels.filter((label,i)=>i&&label===labels[i-1]).length;
  const verb=board.verb();
  board.set_locked_param('sources',true);const before=board.params.sources;board.generate_coin();
  const templates=board.templates.map(t=>t[0]);
  return {distinct:new Set(labels).size,repeats,verb,locked:before===board.params.sources,templates,describe:board.describe()};
 })()`));
 assert.ok(result.distinct>=4,'varied takes: '+result.distinct);
 assert.equal(result.repeats,0);
 assert.equal(result.verb,'jump');
 assert.equal(result.locked,true);
 assert.deepEqual(result.templates.slice(0,5),['Jump','Land','Step','Dash','Splash']);
 assert.deepEqual(result.templates.slice(-2),['Randomize','Mutate']);
 assert.ok(result.describe.length>3);
});

test('engine verb presets come first, read as their verb, and use ids from the vocabulary',()=>{
 const {run}=createBoardContext();
 const verbs=plain(run('GAME_VERBS.map(v=>v.id)'));
 const names=plain(run('GAME_VERBS.map(v=>v.name)'));
 const engines=['Clonkr','Machinr','Jinglr','Squishr','Crittr','Birdr','Signlr','Fractr','Riftr','Swarmr','Rustlr','Boomr','Zappr','Whooshr','Bouncr','Breathr','Choirr','Pluckr','Glitchr'];
 for(const engine of engines){
  const recipes=plain(run(`new ${engine}().recipes`)),templates=plain(run(`new ${engine}().templates`));
  const verbCount=recipes.filter(r=>r.verb).length;
  assert.ok(verbCount>=2,engine+' has verb presets');
  recipes.forEach((recipe,i)=>{
   if(i<verbCount){assert.ok(recipe.verb,engine+' verb presets lead');assert.ok(verbs.includes(recipe.verb),engine+' '+recipe.verb);assert.equal(templates[i][0],names[verbs.indexOf(recipe.verb)]);}
   else assert.ok(!recipe.verb,engine+' character presets follow');
  });
  const seen=new Set();for(const recipe of recipes)if(recipe.verb){assert.ok(!seen.has(recipe.verb),engine+' one preset per verb: '+recipe.verb);seen.add(recipe.verb);}
  assert.equal(templates.at(-2)[2],'randomize_params');
 }
 assert.deepEqual(plain(run("new Bfxr().verbs()")).sort(),['blip','coin','explode','hit','hurt','jump','powerup','shoot']);
 assert.deepEqual(plain(run("new Jinglr().verbs()")),['coin','powerup','unlock','win','lose','confirm','alert','cast','heal']);
});

test('Mixr alignment places B at the start, peak or tail of A and legacy records are unchanged',()=>{
 const {run}=createBoardContext();
 const result=plain(run(`(()=>{
  const a=new Float32Array(44100),b=new Float32Array(22050);
  for(let i=0;i<a.length;i++)a[i]=Math.sin(i*0.05)*(i<2205?i/2205:Math.exp(-(i-2205)/8000));
  for(let i=0;i<b.length;i++)b[i]=Math.sin(i*0.09)*Math.exp(-i/3000);
  const render=(align,offset)=>Mixr_DSP.render({sources:JSON.stringify([{synth:'x'},{synth:'y'}]),balance:0.5,masterVolume:0.5,align,offset},s=>s.synth==='x'?a:b);
  const legacy=(()=>{const out=new Float32Array(a.length);for(let i=0;i<a.length;i++)out[i]=Math.max(-1,Math.min(1,a[i]*0.5+(i<b.length?b[i]*0.5:0)));for(let i=0;i<out.length;i++)if(i>out.length-128)out[i]*=(out.length-1-i)/127;return out;})();
  const start=render(0,0),peak=render(1,0),tail=render(2,0),offset=render(0,0.25);
  const bOnly=(mix,shift)=>{let e=0;for(let i=0;i<4000;i++){const j=shift+i;e+=Math.abs(mix[j]-a[j]*0.5-b[i]*0.5);}return e;};
  return {legacySame:start.every((v,i)=>Math.abs(v-legacy[i])<1e-6),
   peakShift:Mixr_DSP.shift(a,b,1,0),tailShift:Mixr_DSP.shift(a,b,2,0),offsetShift:Mixr_DSP.shift(a,b,0,0.25),
   peakPlaced:bOnly(peak,Mixr_DSP.shift(a,b,1,0))<1e-3,tailPlaced:bOnly(tail,Mixr_DSP.shift(a,b,2,0))<1e-3,offsetPlaced:bOnly(offset,11025)<1e-3,
   lengths:[start.length,peak.length,tail.length,offset.length],aPeak:Mixr_DSP.peak_index(a),tailIndex:Mixr_DSP.tail_index(a)};
 })()`));
 assert.equal(result.legacySame,true);
 assert.ok(result.peakShift>1500&&result.peakShift<3000,'peak shift '+result.peakShift);
 assert.ok(result.tailShift>result.peakShift,'tail after peak');
 assert.equal(result.offsetShift,11025);
 assert.equal(result.peakPlaced,true);assert.equal(result.tailPlaced,true);assert.equal(result.offsetPlaced,true);
 assert.equal(result.lengths[0],44100);assert.ok(result.lengths[2]>=result.tailIndex+22050-1);
 assert.ok(result.lengths.every(n=>n<=44100*12));
});

test('the board editor builds a 5×5 grid, regenerates the same verb, and pins ingredients',()=>{
 const {run,load}=createBoardContext();load('js/BoardEditor.js');
 const result=plain(run(`(()=>{
  function element(tag){return {tag,children:[],classList:{set:new Set(),add(c){this.set.add(c);},toggle(c,on){on?this.set.add(c):this.set.delete(c);},contains(c){return this.set.has(c);}},dataset:{},
   appendChild(child){this.children.push(child);},replaceChildren(){this.children=[];},addEventListener(name,fn){this[name]=fn;},setAttribute(){}};}
  globalThis.document={createElement:element,getElementById(){return null;},addEventListener(){},activeElement:null};
  Math.random=SoundDSP.rng(0.5);
  const board=new Soundboard();const created=[];
  const tab={name:'Soundboard',synth:board,active:true,template_clicked(method){board[method]();created.push(method);editor.update();},
   create_new_sound_from_params(name,params){created.push('new:'+name);editor.update();},get_current_file_name(){return 'Sfx';}};
  const editor=new BoardEditor(tab,element('div'));
  const verbButtons=editor.grid.children.filter(c=>c.tag==='button');
  const labels=editor.grid.children.filter(c=>c.tag==='div').map(c=>c.textContent);
  verbButtons[0].click();const firstVerb=board.verb(),firstSources=board.get_sources().map(s=>s.generator).join('+');
  editor.again.click();const againVerb=board.verb();
  editor.pin.click();const pinnedGenerators=board.get_sources().map(s=>s.generator).join('+');const pinnedSeeds=board.get_sources().map(s=>s.renderSeed).join('+');
  editor.again.click();
  const afterPin={generators:board.get_sources().map(s=>s.generator).join('+'),seeds:board.get_sources().map(s=>s.renderSeed).join('+'),verb:board.verb()};
  editor.on_key_down({key:'q',preventDefault(){}});const keyVerb=board.verb();
  return {buttons:verbButtons.length,labels,firstVerb,againVerb,pinnedGenerators,afterPin,pinnedSeeds,keyVerb,opens:editor.opens.children.map(b=>b.textContent),
   description:editor.description.textContent,active:verbButtons.filter(b=>b.classList.contains('board-active')).map(b=>b.dataset.verb),created:created.length};
 })()`));
 assert.equal(result.buttons,25);
 assert.deepEqual(result.labels,['Move','Fight','Reward','World','Fantasy']);
 assert.equal(result.firstVerb,'jump');assert.equal(result.againVerb,'jump');
 assert.equal(result.afterPin.verb,'jump');
 assert.equal(result.afterPin.generators,result.pinnedGenerators,'pinned ingredients keep their generators');
 assert.notEqual(result.afterPin.seeds,result.pinnedSeeds,'pinned Again still re-rolls the take');
 assert.equal(result.keyVerb,'shoot');
 assert.ok(result.opens.length>=2&&result.opens.at(-1)==='Open in Mixfxr',JSON.stringify(result.opens));
 assert.deepEqual(result.active,['shoot']);
 assert.ok(result.description.includes('·'));
 assert.ok(result.created>=4);
});

test('the Soundboard is wired in as the first tab and the bundle includes its scripts and styles',()=>{
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
 assert.ok(html.includes('src="js/synths/Soundboard.js"'));
 assert.ok(html.includes('src="js/BoardEditor.js"'));
 assert.ok(html.indexOf('js/synths/Mixr.js')<html.indexOf('js/synths/Soundboard.js'));
 const index=fs.readFileSync(path.join(root,'js/index.js'),'utf8');
 assert.ok(index.indexOf('new Soundboard()')<index.indexOf('new Bfxr()'));
 const css=fs.readFileSync(path.join(root,'css/index.css'),'utf8');
 assert.ok(css.includes('.board-grid'));
 const tab=fs.readFileSync(path.join(root,'js/Tab.js'),'utf8');
 assert.ok(tab.includes("['Mixr','Stackr','Soundboard'].includes(this.name)"));
});
