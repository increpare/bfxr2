class SynthTemplate {

    sound = null;
    params = {};
    locked_params = {};

    default_params() {
        var result = {};
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            //if object, then it's a buttonselect
            if (param.constructor === Array) {
                var param_name = param[2];
                var param_default_value = param[3];
                result[param_name] = param_default_value;
            } else {
                switch (param.type) {
                    case "BUTTONSELECT":
                        result[param.name] = param.default_value;
                        break;
                    case "KNOB_TRANSITION":
                        result[param.name] = param.default_value_l;
                        break;
                    default:
                        console.error("Unknown param type: " + param.type);
                }
            }
        }
        return result;
    };

    create_random_preset() {
        this.reset_params();
        var random_preset_idx = Math.floor(Math.random() * this.presets.length);
        var preset = this.presets[random_preset_idx];
        var preset_name = preset[0];
        var preset_generator_name = preset[2];
        var preset_file_name = preset[3];
        this[preset_generator_name]();
        return [preset_file_name, this.params];
    }


    apply_params(other_params) {
        for (var key in other_params) {
            this.params[key] = other_params[key];
        }
    }

    reset_params() {
        var default_params = this.default_params();
        this.apply_params(default_params);
    }

    post_initialize(){
        this.params = this.default_params();
        this.create_locked_params_array();
    }

    create_locked_params_array() {
        if (this.locked_params) {
            return;
        }
        this.locked_params = {};
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            this.locked_params[param[0]] = false;
        }
    }
    
    /*********************/
    /* PARAM FUNCTIONS  */
    /*********************/

    /* returns a param with nice fields name/min/max */
    get_param_uniformized(param){
        var result={};
        //if array
        if (param.constructor === Array) {
            result.name = param[2];
            result.default_value = param[3];
            result.min_value = param[4];
            result.max_value = param[5];
            result.type = "RANGE";
        } else {
            switch (param.type) {
                case "BUTTONSELECT":
                    result.name = param.name;
                    result.default_value = param.default_value;
                    result.min_value = 0;
                    result.max_value = param.values.length;
                    result.type = "BUTTONSELECT";
                    break;
                case "KNOB_TRANSITION":
                    result.name = param.name;
                    result.default_value = param.default_value_l;
                    result.min_value = param.min;
                    result.max_value = param.max;
                    result.type = "KNOB_TRANSITION";
                    break;
                default:
                    console.error("Don't know how to uniformize param type: " + param.type);
            }
        }
        return result;
    }

    param_min(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_uniformized = this.get_param_uniformized(param_o);
            if (param_o_uniformized.name === param_name) {
                return param_o_uniformized.min_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 0;
    }

    param_max(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_uniformized = this.get_param_uniformized(param_o);
            if (param_o_uniformized.name === param_name) {
                return param_o_uniformized.max_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 1;
    }

    set_param(param_name, value, checkLocked = false) {
        if (!(param_name in this.params)) {
            console.error(`Could not set parameter (not found): ${param_name}`);
            return;
        }
        if (checkLocked) {
            if (this.locked_params[param_name]) {
                return;
            }
        }
        var min_val = this.param_min(param_name);
        var max_val = this.param_max(param_name);
        this.params[param_name] = Math.clamp(value, min_val, max_val);
    }

    /*********************/
    /* PRESET FUNCTIONS  */
    /*********************/

    randomize_params() {
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            var param_uniformized = this.get_param_uniformized(param);
            var min_val = param_uniformized.min_value;
            var max_val = param_uniformized.max_value;
            var random_val = Math.random() * (max_val - min_val) + min_val;
            if (param_uniformized.type === "BUTTONSELECT") {
                random_val = Math.floor(random_val);
                if (random_val >= max_val) {
                    random_val = max_val - 1;
                }
            }
            this.set_param(param_uniformized.name, random_val);
        }
    }

    mutate_params() {
        this.reset_params();
    }

    play(){
        this.generate_sound();
        this.sound.play();
    }

    generate_sound_uri(){
        return this.sound.getDataUri();
    }


    /*********************/
    /* CANVAS STUFF      */
    /*********************/

    generateSilhouette(height){
        var result=[];
        
        var buffer=this.sound.getBuffer();

        var curbar=0;
        var curmax=buffer[0];
        var curmin=buffer[0];
        var len=buffer.length;
        for (var i=0;i<len;i++){
            var val = buffer[i];
            if (i/len>curbar/height){
                result.push(curmax);
                result.push(curmin);
                curbar++;
                curmin=val;
                curmax=val;
            } else {
                if (val<curmin) {
                    curmin=val;
                }
                if (val>curmax) {
                    curmax=val;
                }
            }
        }
        result.push(curmax);
        result.push(curmin);

        return result;
    }

    drawWaveform(context2d){
        var w = context2d.canvas.width;
        var h = context2d.canvas.height;

        var silhouette = this.generateSilhouette(h);

        //go from top to bottom, drawing lines

        context2d.beginPath();
        context2d.lineWidth = '1'; // width of the line
        context2d.strokeStyle = '#663931'; // color of the line
    
        var c = w/2;
        for (var y=0;y<h;y++){
            var l = c+silhouette[2*y+0]*1*c;
            var r = c+silhouette[2*y+1]*1*c;
            context2d.moveTo(l,h-y);
            context2d.lineTo(r,h-y);
        }
      
        context2d.stroke();    
    }


    generate_sound(){
       console.error("generate_sound not implemented");
       var tempbuffer = new Float32Array(1);
       this.sound = RealizedSound.from_buffer(tempbuffer);
    }

    set_sound(sound){
        if (sound){
           //pause and dispose of the old sound
        }
        this.sound = sound;
    }
}
