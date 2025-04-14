var collection_save_enabled=true;

function save_all_collections(){
    if (!collection_save_enabled){
        return;
    }
    //collect all file info together
    var save_data = {};
    var active_tab_index=-1;
    for (var i = 0; i < tabs.length; i++){
        var tab = tabs[i];
        var files = tab.files;
        var selected_file_index = tab.selected_file_index;
        var compiled_data = {
            files: files,
            selected_file_index: selected_file_index
        }
        save_data[tab.synth.name] = compiled_data;
        if (tab.active){
            active_tab_index = i;
        }
    }
    save_data.active_tab_index = active_tab_index;
    var save_str = JSON.stringify(save_data);
    //save to local storage
    localStorage.setItem("save_data", save_str);
    console.log("saved all collections (length " + save_str.length + ")");
}

var loaded_data = {};

function load_all_collections(){
    //check if there is any save data
    if (!localStorage.getItem("save_data")){
        return;
    }
    loaded_data = JSON.parse(localStorage.getItem("save_data"));    
}
