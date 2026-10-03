const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){
 const api=createContext(['Jinglr']);
 api.run(`class TestElement {
   constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.listeners={};this.attributes={};this.value='';}
   append(...children){this.children.push(...children);} appendChild(child){this.children.push(child);return child;}
   setAttribute(name,value){this.attributes[name]=value;} addEventListener(type,fn){this.listeners[type]=fn;}
 }
 var document={createElement:tag=>new TestElement(tag)}, SaveLoad={save_all_collections(){}};
 var s=new Jinglr(), updates=0, tab={synth:s,parameter_changed(){updates++;},update_locks(){},play_sound(){}};`);
 api.load('js/PhraseEditor.js');api.run(`var editor=new PhraseEditor(tab,new TestElement('div'));`);return api;
}
test('combined seed keeps both five-digit values and leading zeroes',()=>{
 const {run}=setup();const result=plain(run(`s.set_param('seed',123/99999);s.set_param('instrumentSeed',42);
 editor.update();[editor.seedInput.value,updates,editor.instrumentButtons.length];`));
 assert.deepEqual(result,['0012300042',0,8]);
});
test('editing either half preserves the other half and instrument family',()=>{
 const {run}=setup();assert.equal(run(`s.set_param('seed',12345/99999);s.set_param('instrument',6);s.set_param('instrumentSeed',123);
 editor.update();var phrase=s.params.phrase;editor.seedInput.value='1234504567';editor.seedInput.listeners.change();
 var voiceOnly=s.params.phrase===phrase && s.params.instrument===6 && s.params.instrumentSeed===4567;
 editor.seedInput.value='5432104567';editor.seedInput.listeners.change();
 voiceOnly && s.params.seed===54321/99999 && s.params.instrumentSeed===4567 && s.params.instrument===6;`),true);
});
test('combined seed reconstructs generated melody and voice with the same musical controls',()=>{
 const {run}=setup();assert.equal(run(`s.generate_recipe('discovery');editor.update();var code=editor.seedInput.value;
 var phrase=s.params.phrase,voice=s.params.instrumentSeed;
 editor.seedInput.value='0000000000';editor.seedInput.listeners.change();
 editor.seedInput.value=code;editor.seedInput.listeners.change();
 s.params.phrase===phrase && s.params.instrumentSeed===voice;`),true);
});
test('reseed actions always change their own half, preserving the other and existing locks',()=>{
 const {run}=setup();assert.equal(run(`s.generate_recipe('discovery');editor.update();
 for(const name of ['phrase','seed','instrument','instrumentSeed'])s.set_locked_param(name,true);
 var melody=s.params.seed,phrase=s.params.phrase,voice=s.params.instrumentSeed;
 editor.instrumentButtons[6].button.listeners.click();
 var voiceOnly=s.params.seed===melody && s.params.phrase===phrase && s.params.instrument===6 && s.params.instrumentSeed!==voice;
 voice=s.params.instrumentSeed;editor.generateButton.listeners.click();
 voiceOnly && s.params.seed!==melody && s.params.instrumentSeed===voice && s.params.instrument===6 &&
 ['phrase','seed','instrument','instrumentSeed'].every(name=>s.locked_param(name));`),true);
});
test('invalid combined seeds restore the existing code without changing the sound',()=>{
 const {run}=setup();assert.equal(run(`editor.update();var code=editor.seedInput.value,before=JSON.stringify(s.params);
 ['','123','12345hello','12345678901'].every(value=>{
 editor.seedInput.value=value;editor.seedInput.listeners.change();
 return editor.seedInput.value===code && JSON.stringify(s.params)===before && updates===0;});`),true);
});
test('older melody links acquire a voice seed without shifting musical controls',()=>{
 const api=createContext(['Jinglr']);api.load('js/Tab.js');api.load('js/SaveLoad.js');
 assert.equal(api.run(`var s=new Jinglr();s.set_param('tempo',117);s.set_param('instrument',2);
 var legacy={...s.params};delete legacy.instrumentSeed;tabs=[{synth:s}];
 var link=SaveLoad.shallow_dict_serialize('Jinglr','Old cue',legacy);
 var p=SaveLoad.shallow_dict_deserialize(link)[2];
 p.tempo===117 && p.instrument===2 && p.phrase===s.params.phrase && p.instrumentSeed===42731;`),true);
});
