const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {createContext, root, plain} = require('./helpers/synth-context');
const families = ['Crittr', 'Signlr', 'Fractr', 'Riftr', 'Swarmr', 'Tappr', 'Rustlr', 'Notifr', 'Tickr', 'Holor', 'Boomr', 'Pewpr', 'Zappr', 'Whooshr', 'Bouncr', 'Rollr', 'Breathr', 'Choirr', 'Pluckr', 'Glitchr', 'Pulser', 'Rumblr'];

for (const family of families) {
    test(`${family} survives sound files, share links, collections and Stackr copies`, () => {
        const api = createContext([...families, 'Stackr']);
        api.load('js/SaveLoad.js');
        api.load('js/Tab.js');
        const result = api.run(`
            var source = new ${family}(); source.generate_recipe(source.recipes[0].id);
            source.set_param('duration', 0.3); source.generate_sound();
            var expected = source.sound.getBuffer().slice();
            var original = JSON.stringify(source.params);
            var tab = Object.create(Tab.prototype); tab.name=source.name; tab.synth=source;
            tab.files=[['Example', original, original]]; tab.selected_file_index=0;
            tab.active=true; tab.create_new_sound=true; tab.play_on_change=false;
            tab.set_active_tab=()=>{}; tab.update_ui=()=>{}; tab.redraw_waveform=()=>{};
            tab.create_new_sound_from_params=(name,params)=>source.apply_params(params);
            tab.set_selected_file=name=>{tab.selected_file_index=tab.files.findIndex(file=>file[0]===name);
                source.apply_params(JSON.parse(tab.files[tab.selected_file_index][1]));};
            tabs=[tab];
            var link=SaveLoad.shallow_dict_serialize(source.name,'Example',source.params);
            var linked=SaveLoad.shallow_dict_deserialize(link)[2];
            var file=tab.serialize_params(), collection=SaveLoad.serialize_collection();
            source.set_param('seed',0.97); SaveLoad.load_serialized_synth(file);
            var fileOK=JSON.stringify(source.params)===original;
            source.set_param('seed',0.23); tab.files=[];
            SaveLoad.load_serialized_collection(collection);
            var collectionOK=JSON.stringify(source.params)===original && tab.files.length===1;
            var stack=new Stackr(); stack.add_source(source,'Copied example');
            var copied=stack.get_layers()[0]; source.set_param('seed',0.79);
            var rendered=Stackr.render_source(copied);
            [JSON.parse(original),linked,fileOK,collectionOK,
                rendered.length===expected.length && rendered.every((v,i)=>v===expected[i])];
        `);
        assert.deepEqual(plain(result[0]), plain(result[1]));
        assert.deepEqual(plain(result.slice(2)), [true, true, true]);
    });
}

test('new tabs are appended so saved active-tab indexes keep their meaning', () => {
    const api = createContext(families);
    api.load('js/SaveLoad.js');
    api.run(`var window={}; var document={addEventListener(){}}; var tabs=[];
        class Tab {constructor(synth){this.synth=synth; tabs.push(this);} set_active_tab(){}}
        var previous=['Bfxr','Footsteppr','Transfxr','Chattr','Clonkr','Machinr','Weathr','Jinglr','Squishr','Stackr'];
        previous.forEach(name=>globalThis[name]=class {constructor(){this.name=name;}});`);
    api.load('js/index.js');
    const names = plain(api.run('register_tabs(); tabs.map(tab=>tab.synth.name)'));
    assert.deepEqual(names, ['Bfxr','Footsteppr','Transfxr','Chattr','Clonkr','Machinr','Weathr','Jinglr','Squishr','Stackr', ...families]);
    const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
    for (const family of families) {
        assert.ok(html.includes(`src="js/audio/${family}_DSP.js"`));
        assert.ok(html.includes(`src="js/synths/${family}.js"`));
    }
});

test('old collections leave new sound lists untouched', () => {
    const api = createContext(families);
    api.load('js/SaveLoad.js');
    assert.equal(api.run(`tabs=[{synth:{name:'Bfxr',locked_params:{}},update_ui(){},set_active_tab(){}},
        ...[Crittr,Signlr,Fractr,Riftr,Swarmr,Tappr,Rustlr,Notifr,Tickr,Holor,Boomr,Pewpr,Zappr,Whooshr,Bouncr,Rollr,Breathr,Choirr,Pluckr,Glitchr,Pulser,Rumblr].map(C=>({synth:new C(),files:[['Keep me']]}))];
        SaveLoad.load_serialized_collection(JSON.stringify({Bfxr:{files:[],selected_file_index:-1,
            locked_params:{},create_new_sound:true,play_on_change:false},active_tab_index:0}));
        tabs.slice(1).every(tab=>tab.files[0][0]==='Keep me');`), true);
});
