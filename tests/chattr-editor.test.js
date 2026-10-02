const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');
function setup(){
    const api=createContext([]);
    for(const file of ['ChattrLexicon','ChattrFormants','Chattr_Pronunciation','Chattr_DSP']) api.load(`js/audio/${file}.js`);
    api.load('js/synths/Chattr.js');
    api.run(`class TestElement {
        constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.listeners={};this.attributes={};this.value='';}
        append(...children){this.children.push(...children);} appendChild(child){this.children.push(child);return child;}
        setAttribute(name,value){this.attributes[name]=value;} addEventListener(type,fn){this.listeners[type]=fn;}
        insertRow(){return this.appendChild(new TestElement('tr'));} insertCell(){return this.appendChild(new TestElement('td'));}
    }
    var document={createElement:tag=>new TestElement(tag)}, SaveLoad={save_all_collections(){}},cancelAnimationFrame=()=>{};
    class SpeechPortrait{update(){} speak(){}}
    var s=new Chattr(),updates=0,tab={name:'Chattr',synth:s,slider_changed(name,value){s.set_param(name,value);updates++;},play_sound(){}};
    var parent=new TestElement('div');parent.appendChild(new TestElement('table'));`);
    api.load('js/SpeechEditor.js');api.run(`var editor=new SpeechEditor(tab,s.get_param_info('text'),parent);`);
    return api;
}
test('compact selectors change mode and character without changing typed words',()=>{
    const {run}=setup();
    assert.deepEqual(plain(run(`s.set_param('text','A note for you');editor.update();
        editor.voiceMode.value='0';editor.voiceMode.listeners.change();editor.update();
        var disabled=editor.character.disabled;editor.voiceMode.value='1';editor.voiceMode.listeners.change();editor.update();
        editor.character.value='6';editor.character.listeners.change();
        [s.params.text,s.params.character,s.params.voiceMode,disabled,editor.character.disabled,updates];`)),
    ['A note for you',6,1,true,false,3]);
});
test('loading a saved voice refreshes compact selectors',()=>{
    const {run}=setup();
    assert.deepEqual(plain(run(`s.apply_params({voiceMode:0,character:3});editor.update();
        [editor.voiceMode.value,editor.character.value,editor.character.attributes['aria-label']];`)),['0','3','Character texture']);
});
