check_url_for_sfxr_params = function(){
    var url = window.location.href;
    var querystring = window.location.search;
    var params = new URLSearchParams(querystring);
    if (!params.has("sfx")){
        return;
    }
    var synth_dat_str = params.get("sfx");
    var [synth_name,filename,params] = shallow_dict_deserialize(synth_dat_str);
    var tab = tabs.find(tab => tab.synth.name == synth_name);
    if (!tab){
        console.error("No tab found for synth_name: " + synth_name);
        return;
    }
    tab.create_new_sound_from_params(filename,params);
    tab.set_active_tab();
    //having loaded it, we can update the url to remove the sfx parameter
    var new_url = window.location.href.split("?")[0];
    window.history.replaceState({}, '', new_url);
}

shallow_dict_serialize = function(synth_name,filename,dict){
    //instead of returning a csv string, returns a csv string (with commas delimited by \)
    var result = synth_name + "_" + filename + "_";
    var keys = Object.keys(dict);
    keys.sort();
    for (var i = 0; i < keys.length; i++){
        result += dict[keys[i]] + "_";
    }
    //trim final ","
    result = result.slice(0, -1);
    return result;
}

shallow_dict_deserialize = function(str){
    var entries = str.split("_");
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
    var dict = {};
    for (var i = 0; i < keys.length; i++){
        dict[keys[i]] = parseFloat(entries[i+2]);
    }
    return [synth_name,filename,dict];
}
