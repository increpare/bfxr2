class Footsteppr extends SynthTemplate {

    name = "Footsteppr";
    tooltip = "Bfxr is a wonderful physical simulation of footstep sounds, originally by Obiwannabe.";
    header_properties = [ "waveform" ];

    param_info = [
        {
            type: "BUTTONSELECT",

            name: "waveform",
            display_name: "Terrain",
            tooltip: "",

            default_value: 0,
            columns: 5,
            header: true,

            values: [ 
                [
                    "Snow",
                    "Traipsing around in the snow-blanketed forest."
                ],
                [
                    "Grass",
                    "Dancing around the summer meadows."
                ],
                [
                    "Dirt",
                    "The grass is all trampled away."
                ],
                [
                    "Gravel",
                    "I hope you're not disrespecting anyone's grave!"
                ],
                [
                    "Wood",
                    "Fancy wooden floor - don't scratch it with your caperings."
                ],
            ]
        },
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume",1,0,1
        ], 	
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
            "randomize_params"
        ],
    ];

    pickupCoin() {
        var result = this.default_params();
        return result;
    }
}