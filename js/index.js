"use strict";

function register_tabs(){
    SaveLoad.load_all_collections();
    SaveLoad.collection_save_enabled=false;
    var bfxr_tab = new Tab(new Bfxr());   
    var footsteppr_tab = new Tab(new Footsteppr());
    // var transfxr_tab = new Tab(new Transfxr());
    SaveLoad.collection_save_enabled=true;
    set_tab_from_loaded_data();
    SaveLoad.save_all_collections();
}

function set_tab_from_loaded_data(){
    if (!SaveLoad.loaded_data){
        return;
    }
    var active_tab_index = SaveLoad.loaded_data.active_tab_index;
    if (active_tab_index>=0){
        tabs[active_tab_index].set_active_tab();
    }
}

function bfxr_draw_visualisation(params){

}

function bfxr_generate_sound(params){

}

window.onload = function(){
    register_tabs();
    StateSerialization.check_url_for_sfxr_params();
}

function bfxr_preset_pickupcoin(){
    console.log("Pickup/Coin");
}

function bfxr_preset_lasershoot(){
    console.log("Laser/Shoot");
}

function bfxr_preset_explosion(){
    console.log("Explosion");
}

function bfxr_preset_powerup(){
    console.log("Powerup");
}

function bfxr_preset_hithurt(){
    console.log("Hit/Hurt");
}

function bfxr_preset_jump(){
    console.log("Jump");
}

function bfxr_preset_blipselect(){
    console.log("Blip/Select");
}
