const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){const c=createContext(['Transfxr','Stackr']);return c;}
test('layers preserve embedded source settings independently of the original',()=>{
 const {run}=setup();assert.equal(run(`var s=new Stackr(),source=new Transfxr(); source.generate_example('laser_zip',false);
 s.add_source(source,'Laser');var layers=s.get_layers();source.set_param('duration',4);
 layers.length===1 && layers[0].params.duration===0.22;`),true);
});
test('timeline offsets and pitch alter sample placement and duration',()=>{
 const {run}=setup();const r=run(`var fake=()=>new Float32Array(4410).fill(0.2);
 var p={masterVolume:0.5,seed:0.5,layers:JSON.stringify([{synth:'Transfxr',params:{},start:0.2,gain:1,pitch:0}])};
 var a=Stackr_DSP.render(p,fake);p.layers=JSON.stringify([{synth:'Transfxr',params:{},start:0.2,gain:1,pitch:12}]);
 var b=Stackr_DSP.render(p,fake);[a.length,b.length,a.slice(0,8800).every(v=>v===0),a.some(v=>v>0.01)];`);
 assert.deepEqual(plain(r),[13230,11025,true,true]);
});
test('stack sources are deterministic, finite and bounded',()=>{
 const {run}=setup();assert.equal(run(`var s=new Stackr(),source=new Transfxr();source.generate_example('portal_bloom',false);
 s.add_source(source,'Portal');s.add_source(source,'Another portal');s.generate_sound();var a=s.sound.getBuffer().slice();
 s.generate_sound();a.every((v,i)=>Number.isFinite(v)&&Math.abs(v)<1&&v===s.sound.getBuffer()[i]);`),true);
});
test('bad imports and recursive stacks are bounded or excluded',()=>{
 const {run}=setup();assert.equal(run(`var s=new Stackr();s.set_param('layers',JSON.stringify([
 {synth:'Stackr',params:{},start:0},{synth:'missing',params:{}},
 {synth:'Transfxr',params:{duration:999},start:999,gain:999,pitch:-999}]));
 var a=s.get_layers();a.length===1&&a[0].start===4&&a[0].gain===1&&a[0].pitch===-12&&a[0].params.duration===4;`),true);
});
test('locked stacks survive randomized recipes and mutations',()=>{
 const {run}=setup();assert.equal(run(`var s=new Stackr();s.generate_recipe(s.recipes[0].id);s.set_locked_param('layers',true);
 var before=s.params.layers;s.randomize_params();s.mutate_params();s.params.layers===before;`),true);
});
test('embedded edited musical phrases survive sanitizing and replay',()=>{
 const {run}=createContext(['Jinglr','Stackr']);assert.equal(run(`var s=new Stackr(),source=new Jinglr();
 source.set_param('phrase',JSON.stringify([{degree:null,beats:2},{degree:13,beats:0.25}]));
 var phrase=source.params.phrase;s.add_source(source,'Hand edited');
 var layer=s.get_layers()[0];var restored=new Jinglr();Stackr.sanitize_source(restored,layer.params);
 layer.params.phrase===phrase && restored.params.phrase===phrase;`),true);
});
