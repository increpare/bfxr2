class SaveLoad {
    static collection_save_enabled=true;

    static loaded_data = {};

    static save_all_collections(){
        if (!SaveLoad.collection_save_enabled){
            return;
        }
        //collect all file info together
        var save_str = StateSerialization.serialize_collection();
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

}