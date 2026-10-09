class SaveLoad {
    static collection_save_enabled=true;

    static loaded_data = {};
    static legacy_tabs = ['Bfxr','Footsteppr','Transfxr','Chattr','Clonkr','Machinr','Weathr','Jinglr','Squishr','Stackr','Crittr','Signlr','Fractr','Riftr','Swarmr','Tappr','Rustlr','Notifr','Tickr','Holor','Boomr','Pewpr','Zappr','Whooshr','Bouncr','Rollr','Breathr','Choirr','Pluckr','Glitchr','Pulser','Rumblr'];

    static tab_for_import(name) {
        return tabs.find(tab=>tab.synth.name===name) || null;
    }

    static restore_active_tab(data) {
        const previous=data.active_tab_name || SaveLoad.legacy_tabs[data.active_tab_index];
        const aliases={Stackr:'Mixr',Notifr:'Jinglr',Tappr:'Jinglr',Holor:'Bfxr'};
        const tab=tabs.find(tab=>tab.synth.name===(aliases[previous]||previous));
        if(tab)tab.set_active_tab();
    }

    static save_all_collections(){
        if (!SaveLoad.collection_save_enabled){
            return;
        }
        //collect all file info together
        var save_str = SaveLoad.serialize_collection();
        //save to local storage
        localStorage.setItem("save_data", save_str);
        console.log("saved all collections (length " + save_str.length + ")");
    }


    static load_all_collections(){
        //check if there is any save data
        if (!localStorage.getItem("save_data")){
            return;
        }
        SaveLoad.loaded_data = JSON.parse(localStorage.getItem("save_data"));    
    }

    static check_url_for_sfxr_params(){
        var url = window.location.href;
        var querystring = window.location.search;
        var params = new URLSearchParams(querystring);
        if (!params.has("sfx")){
            return;
        }
        var synth_dat_str = params.get("sfx");
        const decoded = SaveLoad.shallow_dict_deserialize(synth_dat_str);
        if(!decoded)return;
        var [synth_name,filename,params] = decoded;
        var tab = SaveLoad.tab_for_import(synth_name);
        if (!tab){
            console.error("No tab found for synth_name: " + synth_name);
            return;
        }
        tab.set_active_tab();
        tab.create_new_sound_from_params(filename,params,true);
        //having loaded it, we can update the url to remove the sfx parameter
        var new_url = window.location.href.split("?")[0];
        window.history.replaceState({}, '', new_url);
    }

    static shallow_dict_serialize(synth_name,filename,dict){
        // New specialist links carry names so later controls cannot shift saved values.
        if(synth_name!=='Bfxr' && synth_name!=='Footsteppr') {
            return synth_name+'~@2~'+JSON.stringify({filename,params:dict}).replace(/~/g,'\\u007e');
        }
        // Preserve the original Bfxr/Footsteppr numeric format.
        var result = synth_name + "~" + filename + "~";
        var keys = Object.keys(dict);
        console.log("exporting keys: " + keys);
        keys.sort();
        for (var i = 0; i < keys.length; i++){
            // Escape the field separator inside JSON strings; numeric/transition links stay compatible.
            result += JSON.stringify(dict[keys[i]]).replace(/~/g, '\\u007e') + "~";
        }
        //trim final ","
        result = result.slice(0, -1);
        return result;
    }

    static shallow_dict_deserialize(str){
        var entries = str.split("~");
        var synth_name = entries[0];
        var filename = entries[1];
        if(filename==='@2') {
            try {
                const saved=JSON.parse(entries.slice(2).join('~'));
                if(!saved.params || typeof saved.params!=='object')return;
                const tab=tabs.find(tab=>tab.synth.name===synth_name);
                const synth=tab ? new tab.synth.constructor() : null;
                if(synth){synth.apply_params(saved.params);return [synth_name,saved.filename,{...synth.params}];}
                return;
            } catch { return; }
        }
        //need to find the tab that matches the synth_name
        var tab = SaveLoad.tab_for_import(synth_name);
        if (!tab){
            console.error("No tab found for synth_name: " + synth_name);
            return;
        }
        var default_params = tab.synth.default_params();
        var keys = Object.keys(default_params);
        if(synth_name==='Transfxr' && [keys.length+1,keys.length-1].includes(entries.length-2)) {
            // The former schema had a Noise curve alongside Morph.
            const oldKeys=(entries.length-2===keys.length+1 ? [...keys,'noise'] :
                [...keys.filter(key=>key!=='waveTo'&&key!=='morph'),'noise']).sort(),old={};
            for(let i=0;i<oldKeys.length;i++)old[oldKeys[i]]=JSON.parse(entries[i+2]);
            const synth=new tab.synth.constructor();synth.apply_params(old);
            return [synth_name,filename,{...synth.params}];
        }
        // Links from earlier palettes omitted these controls. Their sorted,
        // positional fields must be read against the schema that wrote them.
        const additions = {
            Transfxr:[['waveTo','morph']],
            Jinglr:[['instrumentSeed']],
            Breathr:[['mode','direction'],['mode','direction','source']], Pluckr:[['vibrato'],['vibrato','tremolo','tremoloRate'],['vibrato','tremolo','tremoloRate','material']],
            Fractr:[['shards'],['shards','stress','fracture']], Boomr:[['gas','aftershock','rubbleSize'],['gas','aftershock','rubbleSize','mechanism','space']],
            Bouncr:[['surface','force','tail']],
            Glitchr:[['mode']]
        };
        const missing = (additions[synth_name] || []).find(fields =>
            entries.length - 2 === keys.length - fields.length) || [];
        keys = keys.filter(key => !missing.includes(key)).sort();
        var dict = {};
        for (const key of missing) dict[key] = default_params[key];
        if(synth_name==='Breathr' && missing.includes('mode'))dict.mode=1;
        for (var i = 0; i < keys.length; i++){
            const entry = entries[i+2];
            dict[keys[i]] = typeof default_params[keys[i]] !== "number"
                ? JSON.parse(entry) : parseFloat(entry);
        }
        if(synth_name==='Pluckr' && dict.material===5 && missing.includes('tremolo')) {dict.tremolo=.35;dict.tremoloRate=1.7;}
        return [synth_name,filename,dict];
    }


    static load_serialized_synth(str){
        var data = JSON.parse(str);

        var synth_name = data.synth_type;
        var synth_version = data.version;
        var file_name = data.file_name;
        var params = data.params;

        var tab = SaveLoad.tab_for_import(synth_name);
        if (!tab){
            console.error("No tab found for synth_name: " + synth_name);
            return;
        }
        tab.set_active_tab();
        tab.create_new_sound_from_params(file_name,params,true);
    }

    static load_serialized_collection(str){
        var data = JSON.parse(str);
        // Keep records for retired tabs when importing/exporting a collection.
        SaveLoad.loaded_data={...SaveLoad.loaded_data,...data};
        for (var i = 0; i < tabs.length; i++){
            var tab = tabs[i];
            // Older collections predate Transfxr; partial collections are also useful.
            if (!data[tab.synth.name]) continue;
            var files = data[tab.synth.name].files;
            var selected_file_index = data[tab.synth.name].selected_file_index;
            var create_new_sound = data[tab.synth.name].create_new_sound;
            var play_on_change = data[tab.synth.name].play_on_change;
            var locked_params = data[tab.synth.name].locked_params;
            tab.files = files;
            tab.selected_file_index = -1;
            tab.create_new_sound = create_new_sound;
            tab.play_on_change = play_on_change;
            // Older collections omit newly added controls; keep those in the lock map.
            tab.synth.locked_params = {...tab.synth.locked_params, ...locked_params};
            tab.update_ui();
            if (files[selected_file_index]!=null && files[selected_file_index].length>0){
                tab.set_selected_file(files[selected_file_index][0]);
                if (tab.ui_initialized !== false) {
                    tab.synth.generate_sound();
                    tab.redraw_waveform();
                }
            }
            tab.update_ui();
        }
        SaveLoad.restore_active_tab(data);
        SaveLoad.save_all_collections();
    }

    static serialize_collection(){
        var save_data = {...SaveLoad.loaded_data};
        var active_tab_index=-1;
        for (var i = 0; i < tabs.length; i++){
            var tab = tabs[i];
            var files = tab.files;
            var selected_file_index = tab.selected_file_index;
            var compiled_data = {
                files: files,
                selected_file_index: selected_file_index,
                create_new_sound: tab.create_new_sound,
                play_on_change: tab.play_on_change,
                locked_params: tab.synth.locked_params
            }
            save_data[tab.synth.name] = compiled_data;
            if (tab.active){
                active_tab_index = i;
                save_data.active_tab_name = tab.synth.name;
            }
        }
        save_data.active_tab_index = active_tab_index;
        var serialized_str = JSON.stringify(save_data);
        return serialized_str;
    }

}
