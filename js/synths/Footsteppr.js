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

    templates = [        
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
    /* TEMPLATE FUNCTIONS  */
    /*********************/

    generate_pickup_coin() {
        return this.params;
    }
    
    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/
    
    render() {
        return Footsteppr_DSP.render(this.params);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }
}
