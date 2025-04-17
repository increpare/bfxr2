class Footsteppr extends SynthBase {

    name = "Footsteppr";
    version = "1.0.0"
    tooltip = "Bfxr is a wonderful physical simulation of footstep sounds, originally by Obiwannabe.";
    
    canvas_bg_logo = "img/logo_footsteppr.png";
    
    header_properties = ["waveType"];

    permalocked = ["masterVolume"];
    hide_params = ["masterVolume"];

    param_info = [
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume",0.5,0,1
        ], 	
        {
            type: "BUTTONSELECT",

            name: "terrain",
            display_name: "Terrain",
            tooltip: "",

            default_value: 0,
            columns: 5,
            header: true,

            values: [ 
                [
                    "Snow",
                    "Traipsing around in the snow-blanketed forest.",
                    0
                ],
                [
                    "Grass",
                    "Dancing around the summer meadows.",
                    1
                ],
                [
                    "Dirt",
                    "The grass is all trampled away.",
                    2
                ],
                [
                    "Gravel",
                    "I hope you're not disrespecting anyone's grave!",
                    3
                ],
                [
                    "Wood",
                    "Fancy wooden floor - don't scratch it with your caperings.",
                    4
                ],
            ]
        },
        [
            "Heel",
            "How hard you strike the ground with your heel.",
            "heel",0.5,0,1
        ],		
        [
            "Roll",
            "After making initial contact with the ground, how much you roll your foot to the side.",
            "roll",0.5,0,1
        ], 	
        [
            "Ball",
            "At the final part of your step, how much you dig the front of your foot into the ground.",
            "ball",0.5,0,1
        ], 	
        [
            "Swiftness",
            "How quick the step is.",
            "swiftness",0.5,0,1
        ], 		
    ];

    presets = [        
        [   
            "Randomize",
            "Talking your life into your hands... (only modifies unlocked parameters)",
            "randomize_params",
            "Random"
        ],
        [
            "Mutate", 
            "Modify each unlocked parameter by a small wee amount... (only modifies unlocked parameters)", 
            "mutate_params",
            "Mutant"
        ],
    ];
    
    /*********************/
    /* CONSTRUCTOR       */
    /*********************/

    constructor() {
        super();
        this.post_initialize();
    }    

    /*********************/
    /* PRESET FUNCTIONS  */
    /*********************/

    generate_pickup_coin() {
        return this.params;
    }
    
    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/
    
    generate_sound(){
        var step_heel = this.params.heel;
        var step_roll = this.params.roll;
        var step_ball = this.params.ball;
        var step_speed = this.params.swiftness;
        var step_vol = this.params.masterVolume;

        //speed is between 0 and 1, this corresponds to a step-length between 0.8 and 0.1 
        var step_length = 0.1+0.7*(1-step_speed)
        
        //constant signal 0 
        pd_set_stream_length_seconds(step_length);
    
        var heel_envelope = resize_fn(step(step_heel),0,1,0,0.3333);
        var roll_envelope = resize_fn(step(step_roll),0,1,0.125,0.875);
        var ball_envelope = resize_fn(step(step_ball),0,1,0.6667,1);
        var step_envelope_0_1 = add_fns(heel_envelope,roll_envelope,ball_envelope);
        var step_envelope_resized = resize_fn(step_envelope_0_1,0,1,0,step_length);
    
        var envelope_signal = pd_fn(step_envelope_resized);
    
        var signal = this.generate_terrain_texture(envelope_signal);
    
        signal = pd_mul(signal,pd_c(step_vol));
        signal = pd_clip(signal, pd_c(-1.0), pd_c(1.0));
        signal = pd_mul(signal, pd_c(2.0));
    
        this.sound = RealizedSound.from_buffer(signal);
    }
 
    generate_terrain_texture(envelope_signal){
        var terrain_names = ["snow","grass","dirt","gravel","wood"];
        if (this.params.terrain >= terrain_names.length){
            step_terrain = 0;
            console.log("step_terrain reset to 0");
        }
        var terrain_name = terrain_names[this.params.terrain];     
        console.log("generating terrain texture for " + terrain_name);
        return puredata_functions[terrain_name](envelope_signal);    
    }
    
}


