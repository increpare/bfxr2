"use strict";

var bfxr_tab;
var footsteppr_tab;
var transfxr_tab;

function register_tabs(){
    bfxr_tab = new Tab(new Bfxr());   
    footsteppr_tab = new Tab(new Footsteppr());
    transfxr_tab = new Tab(new Transfxr());
}

function bfxr_draw_visualisation(params){

}

function bfxr_generate_sound(params){

}

function bfxr_param_changed(params){
    var square_wave_set = params["wave_type"] == 2;
    bfxr_tab.set_parameter_enabled("square_duty", !square_wave_set);
}

window.onload = function(){
    register_tabs();
    check_url_for_sfxr_params();
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
