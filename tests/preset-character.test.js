const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext}=require('./helpers/synth-context');
const {rng}=require('../tools/preset_survey/render_corpus');
function samples(id,count=48){
 const {run}=createContext(['Transfxr']);
 const family=run(`Transfxr.preset_families.find(f=>f.id==='${id}')`);
 assert.ok(family,'missing family '+id);
 const sample=run('(f,r)=>PresetFamily.sample(f,r)'),random=rng(912);
 return Array.from({length:count},()=>sample(family,random));
}
test('taps and fuzzy chirps stay short and have no echo tail',()=>{
 for(const [id,max]of [['grainy_taps',.18],['fuzzy_chirps',.28]])for(const p of samples(id)){
  assert.ok(p.duration<=max,id+' long duration '+p.duration);
  assert.equal(p.echo,0,id+' echo tail');
 }
});
test('wavering calls sustain several cycles of actual pitch wobble',()=>{
 for(const p of samples('wavering_calls')){
  assert.ok(p.duration>=.65);
  assert.ok(p.vibrato.start>=.65&&p.vibrato.end>=.65,'wobble must be present throughout');
  assert.ok(p.waveTo===-1 || (p.waveTo===7&&p.morph.start<.12&&p.morph.end<.12),'clear voiced call');
 }
});
test('soft pips use a gentle clean voice distinct from fuzzy chirps',()=>{
 for(const p of samples('soft_pips')){
  assert.equal(p.waveType,0);assert.equal(p.echo,0);
  assert.equal(p.waveTo,-1);
  assert.ok(p.attack>=.012&&p.duration<=.22);
  assert.ok(p.level.start<=.6&&p.level.end<=.6);
 }
 for(const p of samples('fuzzy_chirps'))assert.ok(p.waveTo===7&&p.morph.start>=.18&&p.morph.end>=.18);
});
test('sand is a bright dry spray and air is a longer dark breath',()=>{
 for(const p of samples('sand_sprays')){
  assert.ok(p.waveTo===7&&p.morph.start>=.9&&p.morph.end>=.9);
  assert.ok(p.duration<=.45&&p.attack<=.012&&p.echo===0);
  assert.ok(p.tone.start>=.6&&p.tone.end>=.6);
 }
 for(const p of samples('air_currents')){
  assert.ok(p.duration>=.85&&p.attack>=.18);
  assert.ok(p.waveTo===7&&p.morph.start>=.9&&p.morph.end>=.9);
  assert.ok(p.tone.start<=.5&&p.tone.end<=.5);
 }
});
test('direction-only banks are replaced by specific voices',()=>{
 const {run}=createContext(['Transfxr']);const names=run('Transfxr.preset_families.map(f=>f.name)');
 for(const name of ['Arcade Zaps','Bubble Pops','Mournful Calls','Radio Spits','Bubble Swells'])assert.ok(names.includes(name),name);
 for(const name of ['Descending Sweeps','Rising Bloops','Falling Thumps','Submarine Calls','Static Flecks','Reverse Bloops'])assert.ok(!names.includes(name),name);
});
