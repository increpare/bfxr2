var bfxr_tab;

function register_bfxr_tab(){
    bfxr = guifxr_create_tab("bfxr");
    bfxr_tab.add_button_grid(
        "wave_type",
        4, // columns
        0, //default value
        [
            ["Triangle","I love triangle waves"],
            ["Sin","I love sin waves"],
            ["Square","I love square waves"],
            ["Saw","I love saw waves"],
            ["Breaker","I love breaker waves"],            
            ["Tan","I love tan waves"],
            ["Whistle","I love whistle waves"],
            ["White","I love white waves"],
            ["Pink","I love pink waves"],
            ["Bitnoise","I love bitnoise waves"],
            ["Buzz","I love buzz waves"],
            ["Holo","I love holo waves"],
        ]
    );
    bfxr_tab.add_slider("attack_time",0,1,0,"Attack Time","Length of the volume envelope attack.");
    bfxr_tab.add_slider("decay_time",0,1,0,"Decay Time","Length of the volume envelope decay.");
    bfxr_tab.add_slider("punch",0,1,0,"Punch","Volume level of the volume envelope punch.");
    bfxr_tab.add_slider("sustain_time",0,1,0,"Sustain Time","Length of the volume envelope sustain.");
    bfxr_tab.add_slider("release_time",0,1,0,"Release Time","Length of the volume envelope release.");
    bfxr_tab.add_slider("square_duty",0,1,0,"Square Duty","Ratio between length of up and down part of a square wave.");

    bfxr_tab.draw_visualisation = bfxr_draw_visualisation;
    bfxr_tab.generate_sound = bfxr_generate_sound;
    bfxr_tab.on_parameter_change = bfxr_param_changed;
}

function bfxr_draw_visualisation(params){

}

function bfxr_generate_sound(params){

}

function bfxr_param_changed(params){
    var square_wave_set = params["wave_type"] == 2;
    bfxr_tab.set_parameter_enabled("square_duty", !square_wave_set);
}

// register_bfxr_tab();