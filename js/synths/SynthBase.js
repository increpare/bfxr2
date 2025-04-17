class SynthBase {

    sound = null;
    params = {};
    locked_params = null;

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

    create_random_template() {
        this.reset_params();
        var random_template_idx = Math.floor(Math.random() * this.templates.length);
        var template = this.templates[random_template_idx];
        var template_name = template[0];
        var template_generator_name = template[2];
        var template_file_name = template[3];
        this[template_generator_name]();
        return [template_file_name, this.params];
    }


    apply_params(other_params,check_locked = false) {
        for (var key in other_params) {
            if ( !check_locked || !this.locked_params[key] ) {
                this.params[key] = other_params[key];
            }
        }
    }

    reset_params(check_locked = false) {
        var default_params = this.default_params();
        this.apply_params(default_params,check_locked);
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
            this.locked_params[param[2]] = false;
        }
        for (var i = 0; i < this.permalocked.length; i++) {
            this.locked_params[this.permalocked[i]] = true;
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
    
    param_default(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_uniformized = this.get_param_uniformized(param_o);
            if (param_o_uniformized.name === param_name) {
                return param_o_uniformized.default_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 0;
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

    get_param(param_name) {
        if (!(param_name in this.params)) {
            console.error(`Could not get parameter (not found): ${param_name}`);
            return 0;
        }
        return this.params[param_name];
    }

    /*********************/
    /* TEMPLATE FUNCTIONS  */
    /*********************/

    randomize_params() {
        this.reset_params(true);
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            var param_uniformized = this.get_param_uniformized(param);
            
            if (this.locked_params[param_uniformized.name]) {
                continue;
            }
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
        for (var i = 0; i < this.param_info.length; i++) {
            if (Math.random()<0.5){
                continue;
            }
            //if locked, skip
            if (this.locked_params[this.param_info[i][2]]) {
                continue;
            }
            var param = this.param_info[i];
            var param_uniformized = this.get_param_uniformized(param);
            if (param_uniformized.type !== "RANGE") {
                continue;
            }
            var min_val = param_uniformized.min_value;
            var max_val = param_uniformized.max_value;
            var range = max_val - min_val;
            var mutated_diff = (Math.random()-0.5)*0.1*range;
            var mutated_val = this.params[param_uniformized.name] + mutated_diff;
            this.set_param(param_uniformized.name, mutated_val);
        }

    }

    play(){
        if (this.sound){
            this.sound.stop();        
        }
        this.generate_sound();
        //if sound already playing, stop it
        this.sound.play();
    }

    generate_sound_uri(){
        if (!this.sound){
            this.generate_sound();
        }
        return this.sound.getDataUri();
    }

    generate_sound_blob(){
        
        if (!this.sound){
            this.generate_sound();
        }
        var audioBuffer = this.sound;

        var channelData = [],
            totalLength = 0,
            channelLength = 0;
    
        for (var i = 0; i < audioBuffer.numberOfChannels; i++) {
            channelData.push(audioBuffer.getChannelData(i));
            totalLength += channelData[i].length;
            if (i == 0) channelLength = channelData[i].length;
        }
    
        // interleaved
        const interleaved = new Float32Array(totalLength);
    
        for (
            let src = 0, dst = 0;
            src < channelLength;
            src++, dst += audioBuffer.numberOfChannels
        ) {
            for (var j = 0; j < audioBuffer.numberOfChannels; j++) {
            interleaved[dst + j] = channelData[j][src];
            }
            //interleaved[dst] = left[src];
            //interleaved[dst + 1] = right[src];
        }
    
        // get WAV file bytes and audio params of your audio source
        const wavBytes = this.getWavBytes(interleaved.buffer, {
            isFloat: true, // floating point or 16-bit integer
            numChannels: audioBuffer.numberOfChannels,
            sampleRate: 48000,
        });
        const wav = new Blob([wavBytes], { type: "audio/wav" });
        return wav;        
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
                    
                if (Math.abs(curmax-curmin)<0.01){
                    curmax+=0.005;
                    curmin-=0.005;
                }
            
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
       if (this.sound){
        this.sound.stop();
       }
       this.sound = RealizedSound.from_buffer(tempbuffer);
    }

    set_sound(sound){
        if (sound){
           //pause and dispose of the old sound
        }
        this.sound = sound;
    }
}
