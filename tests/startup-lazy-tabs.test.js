const test=require('node:test');
const assert=require('node:assert/strict');
const {createContext,plain}=require('./helpers/synth-context');

function setup(){
 const api=createContext(['Clonkr','Choirr']);
 api.load('js/Tab.js');api.load('js/SaveLoad.js');
 api.run(`
 const nodes={};
 function element(){return {children:[],style:{},dataset:{},classList:{add(){},remove(){},contains(){return false;}},
  appendChild(child){this.children.push(child);if(child.id)nodes[child.id]=child;},addEventListener(name,callback){this[name]=callback;},setAttribute(){}};}
 nodes.tab_bar=element();nodes.tab_page_manager=element();
 globalThis.document={createElement:element,getElementById(id){return nodes[id];},addEventListener(){},
  getElementsByClassName(name){return name==='tab_button'?nodes.tab_bar.children:nodes.tab_page_manager.children;}};
 let controls=0,editors=0,renders=0;
 Tab.prototype.setup_slider=()=>{controls++;};
 Tab.prototype.load_params=()=>{controls++;};
 Tab.prototype.update_ui=function(){const list=nodes[this.name+'_file_list'];if(list)list.children=this.files.map(()=>{const item=element(),span=element();span.focus=()=>{};item.children=[span];return item;});};
 Tab.prototype.redraw_waveform=()=>{};
 function makeSynth(){const synth=new Clonkr();const render=synth.generate_sound.bind(synth);
  synth.generate_sound=()=>{renders++;render();};synth.create_editor=()=>{editors++;return {update(){}};};return synth;}
 `);
 return api;
}

test('unopened tabs retain exportable initial sounds without panels, editors or audio rendering',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const tab=new Tab(makeSynth());const saved=JSON.parse(SaveLoad.serialize_collection()).Clonkr;
 return {controls,editors,renders,panelChildren:nodes.tab_page_Clonkr.children.length,files:saved.files.length,
  selected:saved.selected_file_index,params:JSON.parse(saved.files[0][1]),current:tab.synth.params};})()`));
 assert.equal(result.controls,0);assert.equal(result.editors,0);assert.equal(result.renders,0);
 assert.equal(result.panelChildren,0);assert.equal(result.files,1);assert.equal(result.selected,0);
 assert.deepEqual(result.params,result.current);
});

test('first activation builds the panel and preview once, later activation reuses unchanged audio',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const tab=new Tab(makeSynth());tab.set_active_tab();const first={controls,editors,renders};
 tab.set_active_tab();const second={controls,editors,renders};tab.synth.set_param('seed',.314);tab.set_active_tab();
 return [first,second,{controls,editors,renders},tab.synth.sound_params===JSON.stringify(tab.synth.params)];})()`));
 assert.equal(result[0].editors,1);assert.equal(result[0].renders,1);assert.ok(result[0].controls>0);
 assert.deepEqual(result[1],result[0]);assert.equal(result[2].renders,2);assert.equal(result[2].editors,1);
 assert.equal(result[3],true);
});

test('saved inactive tabs restore parameters and locks without rendering',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const synth=makeSynth();synth.set_param('seed',.42);const params=JSON.stringify(synth.params);
 SaveLoad.loaded_data={Clonkr:{files:[['Saved',params,params]],selected_file_index:0,create_new_sound:false,
  play_on_change:false,locked_params:{seed:true}}};const tab=new Tab(makeSynth());
 return {renders,editors,seed:tab.synth.params.seed,locked:tab.synth.locked_param('seed'),create:tab.create_new_sound,play:tab.play_on_change};})()`));
 assert.deepEqual(result,{renders:0,editors:0,seed:.42,locked:true,create:false,play:false});
});

test('collection import updates an unopened tab without building its panel or rendering it',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const tab=new Tab(makeSynth());const synth=new Clonkr();synth.set_param('seed',.271);
 const params=JSON.stringify(synth.params);SaveLoad.load_serialized_collection(JSON.stringify({Clonkr:{
 files:[['Imported',params,params]],selected_file_index:0,create_new_sound:false,play_on_change:false,locked_params:{seed:true}}}));
 return {renders,editors,seed:tab.synth.params.seed,selected:tab.selected_file_index,file:tab.files[0][0]};})()`));
 assert.deepEqual(result,{renders:0,editors:0,seed:.271,selected:0,file:'Imported'});
});

test('restoring the saved active tab initializes only that panel and preserves the other collection',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const first=new Tab(makeSynth());const initial=JSON.stringify(first.files);
 const synth=new Choirr(),render=synth.generate_sound.bind(synth);synth.generate_sound=()=>{renders++;render();};
 const second=new Tab(synth);SaveLoad.restore_active_tab({active_tab_name:'Choirr'});
 const saved=JSON.parse(SaveLoad.serialize_collection());
 return {firstReady:first.ui_initialized,secondReady:second.ui_initialized,renders,
  active:saved.active_tab_name,preserved:JSON.stringify(first.files)===initial};})()`));
 assert.deepEqual(result,{firstReady:false,secondReady:true,renders:1,active:'Choirr',preserved:true});
});

test('unopened sounds can be rendered for export without creating a panel',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const tab=new Tab(makeSynth()),state=JSON.stringify(tab.files);
 const wav=tab.synth.generate_sound_uri();return wav.startsWith('data:audio/wav;base64,')&&renders===1&&editors===0&&
  controls===0&&!tab.ui_initialized&&JSON.stringify(tab.files)===state;})()`),true);
});

test('clicking a different tab plays its selected preview even with play-on-change off',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const first=new Tab(makeSynth());first.set_active_tab();let stops=0;
 first.synth.sound.stop=()=>{stops++;};const second=new Tab(new Choirr());second.play_on_change=false;
 nodes.tab_button_Choirr.click();const sound=second.synth.sound,source=sound.source;
 return {played:!!source,loop:source?.loop,stops,active:second.active,create:second.files.length};})()`));
 assert.deepEqual(result,{played:true,loop:false,stops:1,active:true,create:1});
});

test('clicking the active tab does not replay, while returning to it reuses the same rendered sound',()=>{
 const {run}=setup();
 const result=plain(run(`(()=>{const first=new Tab(makeSynth()),second=new Tab(new Choirr());second.set_active_tab();
 nodes.tab_button_Clonkr.click();const sound=first.synth.sound,source=sound.source;let animationPlays=0;
 first.text_controls={test:{play(){animationPlays++;}}};nodes.tab_button_Clonkr.click();
 const unchanged=source===sound.source;second.set_active_tab();nodes.tab_button_Clonkr.click();
 return {played:!!source,unchanged,sameSound: sound===first.synth.sound,renders,animationPlays};})()`));
 assert.deepEqual(result,{played:true,unchanged:true,sameSound:true,renders:1,animationPlays:1});
});

test('startup restoration and programmatic selection remain silent',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const first=new Tab(makeSynth()),second=new Tab(new Choirr());
 SaveLoad.restore_active_tab({active_tab_name:'Choirr'});if(second.synth.sound.source)return false;
 first.set_active_tab();return !first.synth.sound.source;})()`),true);
});

test('switching to an empty tab does not play a stale sound',()=>{
 const {run}=setup();
 assert.equal(run(`(()=>{const first=new Tab(makeSynth());first.set_active_tab();const second=new Tab(new Choirr());
 second.files=[];second.selected_file_index=-1;second.synth.generate_sound();nodes.tab_button_Choirr.click();
 return second.active&&!second.synth.sound.source;})()`),true);
});
