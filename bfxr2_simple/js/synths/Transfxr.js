class Transfxr extends SynthTemplate {

    name = "Transfxr";
    tooltip = "An idea for making simple sounds.";
    header_properties = [ "waveform" ];

    param_info = [
        {
            type: "KNOB_TRANSITION",

            name: "roll",
            display_name: "Filter Sweep",

            default_value_l:0,
            default_value_r:1,
            min:0,
            max:1,

            default_tween: "Linear",

            header: true,
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

    static tweenfunctions = [
        [        
            "Linear",
            (t) => t,
        ],
        [
            "Ease In",
            (t) => t * t,
        ],
        [
            "Triangle",
            (t) => 1 - Math.abs(t - 0.5) * 2,
        ],
        [
            "Bounce",
            (t) => {
                if (t < 0.5) {
                    return 1 - (t * 2) * (t * 2);
                } else {
                    return (t * 2 - 1) * (t * 2 - 1) + 1;
                }
            },
        ],
        [
            "Cosine",
            (t) => 1-(Math.cos(t * Math.PI * 2)+1)/2,
        ],
        [
            "Accelerating Sine",
            (t) => Math.sin(t * Math.PI * 2) * t,
        ],
        [
            "Decelerating Sine",
            (t) => Math.sin(t * Math.PI * 2) * (1 - t),
        ],                
    ]
    
    // Generate images for each tween function and store them in the tweenfunctions array
    generateTweenImages() {
        var style = window.getComputedStyle(document.body)

        for (let i = 0; i < Transfxr.tweenfunctions.length; i++) {
            const [name, func] = Transfxr.tweenfunctions[i];
            // base on height/width from style variables --tween-canvas-width and --tween-canvas-height
            var img_width = style.getPropertyValue("--tween-canvas-width");
            var img_height = style.getPropertyValue("--tween-canvas-height");

            // Create a canvas to draw the function
            const canvas = document.createElement("canvas");
            canvas.width = img_width;
            canvas.height = img_height;
            
            // Draw the tween function
            const ctx = canvas.getContext("2d");
            
            // Set single pixel drawing style
            ctx.fillStyle = "black";
            
            // Draw individual pixels for each x coordinate
            const numPoints = img_width;
            
            for (let j = 0; j <= numPoints; j++) {
                const t = j / numPoints;
                const x = j;
                const y = Math.round(canvas.height * (1 - func(t)));
                
                // Ensure y is within canvas bounds
                const pixelY = Math.max(0, Math.min(canvas.height - 1, y));
                
                // Set a single pixel at (x, y)
                ctx.fillRect(x, pixelY, 1, 1);
            }
            
            // Convert canvas to image and store it in the tweenfunctions array
            const dataURL = canvas.toDataURL("image/png");
            const img = document.createElement("img");
            img.src = dataURL;
            img.width = img_width;
            img.height = img_height;
            img.style.border = "1px solid #ccc";
            img.style.borderRadius = "3px";
            img.style.margin = "5px";
            img.title = name;
            
            // Store the image in the tweenfunctions array
            Transfxr.tweenfunctions[i][2] = img;
        }
    }
    
    
    /*********************/
    /* CONSTRUCTOR       */
    /*********************/

    constructor() {
        super();
        this.post_initialize();
        this.generateTweenImages();
    }    

    /*********************/
    /* PRESET FUNCTIONS  */
    /*********************/

    generate_pickup_coin() {
        return this.params;
    }

}