class Transfxr extends SynthTemplate {

    name = "Transfxr";
    tooltip = "An idea for making simple sounds.";
    header_properties = [ "waveform" ];

    param_info = [
        {
            type: "KNOB_TRANSITION",

            name: "filterSweep",
            display_name: "Filter Sweep",

            default_value_l:0,
            default_value_r:1,
            min:0,
            max:1,

            default_tween: "Linear",
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
    ];

    pickupCoin() {
        var result = this.Params();
        return result;
    }

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
    
    constructor() {
        super();
        this.generateTweenImages();
        this.createTweenVisualizationContainer(document.body);
    }
    
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

    // Create a container and display tween function visualizations
    createTweenVisualizationContainer(parentElement) {
        if (!parentElement) {
            console.error("No parent element provided for tween container");
            return;
        }
        
        // Create a container for the tween visualizations
        const tweenContainer = document.createElement("div");
        tweenContainer.id = "tween_container_" + this.name;
        tweenContainer.classList.add("tween_container");
        tweenContainer.style.marginTop = "20px";
        tweenContainer.style.padding = "10px";
        tweenContainer.style.border = "1px solid #ccc";
        tweenContainer.style.borderRadius = "5px";
        tweenContainer.style.backgroundColor = "#fff";
        
        // Add the container to the parent
        parentElement.appendChild(tweenContainer);
        
        // Fill the container with visualizations
        this.displayTweenVisualizations(tweenContainer);
        
        return tweenContainer;
    }
    
    // Display tween functions using the pre-generated images
    displayTweenVisualizations(container) {
        if (!container) {
            console.error("No container provided for tween visualizations");
            return;
        }
        
        // Clear the container
        container.innerHTML = '';
        
        // Add a title
        const title = document.createElement("h3");
        title.textContent = "Tween Functions";
        title.style.margin = "10px 0";
        title.style.fontSize = "14px";
        title.style.fontWeight = "bold";
        title.style.color = "#333";
        container.appendChild(title);
        
        // Create a flex container for the images
        const flexContainer = document.createElement("div");
        flexContainer.style.display = "flex";
        flexContainer.style.flexWrap = "wrap";
        flexContainer.style.justifyContent = "center";
        flexContainer.style.gap = "10px";
        flexContainer.style.padding = "5px";
        container.appendChild(flexContainer);
        
        // Add each tween function image to the container
        for (let i = 0; i < Transfxr.tweenfunctions.length; i++) {
            const [name, func, img] = Transfxr.tweenfunctions[i];
            
            if (!img) {
                console.error(`No image generated for tween function: ${name}`);
                continue;
            }
            
            // Create a wrapper for the image
            const wrapper = document.createElement("div");
            wrapper.style.display = "flex";
            wrapper.style.flexDirection = "column";
            wrapper.style.alignItems = "center";
            wrapper.style.margin = "5px";
            wrapper.style.padding = "5px";
            wrapper.style.border = "1px solid #ccc";
            wrapper.style.borderRadius = "3px";
            wrapper.style.backgroundColor = "#f5f5f5";
            wrapper.style.boxShadow = "0 2px 4px rgba(0,0,0,0.1)";
            wrapper.style.cursor = "pointer";
            
            // Create label
            const label = document.createElement("div");
            label.textContent = name;
            label.style.fontSize = "12px";
            label.style.fontWeight = "bold";
            label.style.textAlign = "center";
            label.style.marginBottom = "5px";
            wrapper.appendChild(label);
            
            // Clone the image to prevent any parent-child issues
            const imgClone = img.cloneNode(true);
            wrapper.appendChild(imgClone);
            
            // Add click handler to select this function
            wrapper.addEventListener('click', () => {
                console.log(`Selected tween function: ${name}`);
                
                // Remove highlight from all wrappers
                const allWrappers = flexContainer.querySelectorAll('div[style*="border"]');
                allWrappers.forEach(w => {
                    w.style.border = "1px solid #ccc";
                });
                
                // Highlight selected wrapper
                wrapper.style.border = "2px solid #007bff";
                
                // Store the selected tween function
                this.selectedTweenFunction = func;
            });
            
            flexContainer.appendChild(wrapper);
        }
    }
}