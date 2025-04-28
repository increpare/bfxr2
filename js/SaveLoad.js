class SaveLoad {
    static collection_save_enabled=true;

    static loaded_data = {};

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
        var [synth_name,filename,params] = SaveLoad.shallow_dict_deserialize(synth_dat_str);
        var tab = tabs.find(tab => tab.synth.name == synth_name);
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
        //instead of returning a csv string, returns a csv string (with commas delimited by \)
        var result = synth_name + "~" + filename + "~";
        var keys = Object.keys(dict);
        console.log("exporting keys: " + keys);
        keys.sort();
        for (var i = 0; i < keys.length; i++){
            result += dict[keys[i]] + "~";
        }
        //trim final ","
        result = result.slice(0, -1);
        return result;
    }

    static shallow_dict_deserialize(str){
        var entries = str.split("~");
        var synth_name = entries[0];
        var filename = entries[1];
        //need to find the tab that matches the synth_name
        var tab = tabs.find(tab => tab.synth.name == synth_name);
        if (!tab){
            console.error("No tab found for synth_name: " + synth_name);
            return;
        }
        var default_params = tab.synth.default_params();
        var keys = Object.keys(default_params);
        keys.sort();
        console.log("importing keys: " + keys);
        var dict = {};
        for (var i = 0; i < keys.length; i++){
            dict[keys[i]] = parseFloat(entries[i+2]);
        }
        return [synth_name,filename,dict];
    }


    static load_serialized_synth(str){
        var data = JSON.parse(str);

        var synth_name = data.synth_type;
        var synth_version = data.version;
        var file_name = data.file_name;
        var params = data.params;

        var tab = tabs.find(tab => tab.synth.name == synth_name);
        if (!tab){
            console.error("No tab found for synth_name: " + synth_name);
            return;
        }
        tab.set_active_tab();
        tab.create_new_sound_from_params(file_name,params,true);
    }

    static load_serialized_collection(str){
        var data = JSON.parse(str);
        var active_tab_index = data.active_tab_index;
        for (var i = 0; i < tabs.length; i++){
            var tab = tabs[i];
            var files = data[tab.synth.name].files;
            var selected_file_index = data[tab.synth.name].selected_file_index;
            var create_new_sound = data[tab.synth.name].create_new_sound;
            var play_on_change = data[tab.synth.name].play_on_change;
            var locked_params = data[tab.synth.name].locked_params;
            tab.files = files;
            tab.selected_file_index = -1;
            tab.create_new_sound = create_new_sound;
            tab.play_on_change = play_on_change;
            tab.synth.locked_params = locked_params;
            tab.update_ui();
            if (files[selected_file_index]!=null && files[selected_file_index].length>0){
                tab.set_selected_file(files[selected_file_index][0]);
                tab.synth.generate_sound();
                tab.redraw_waveform();            
            }
            tab.update_ui();
        }
        tabs[active_tab_index].set_active_tab();
    }

    static serialize_collection(){
        var save_data = {};
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
            }
        }
        save_data.active_tab_index = active_tab_index;
        var serialized_str = JSON.stringify(save_data);
        return serialized_str;
    }

}