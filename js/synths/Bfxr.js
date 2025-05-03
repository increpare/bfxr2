class Bfxr extends SynthBase {
    /*********************/
    /*      METADATA     */
    /*********************/

    name = "Bfxr";
    version = Bfxr_DSP.version;
    tooltip = "Bfxr is a simple sound effect generator, based on DrPetter's Sfxr.";

    canvas_bg_logo = "img/logo_bfxr.png";

    header_properties = ["waveType"];

    permalocked = ["masterVolume"];
    hide_params = ["masterVolume"];

    param_info = [
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume", 0.5, 0, 1
        ],
        {
            type: "BUTTONSELECT",

            name: "waveType",
            display_name: "",
            tooltip: "",

            default_value: 0,
            columns: 4,
            header: true,

            values: [
                [
                    "Triangle",
                    "Triangle waves are robust at all frequencies, stand out quite well in most situations, and have a clear, resonant quality.",
                    4
                ],
                [
                    "Sin",
                    "Sin waves are the most elementary of all wave-types.  However, they can be sensitive to context (background noise or accoustics can drown them out sometimes), so be careful.",
                    2
                ],
                [
                    "Square",
                    "quare waves can be quite powerful.  They have two extra properties, Square Duty and Duty Sweep, that can further control the timbre of the wave.",
                    0
                ],
                [
                    "Saw",
                    "Saw waves are pretty raspy",
                    1
                ],
                [
                    "Breaker",
                    "These are defined by a quadratic equation (a=t*t%1, giving a toothed-shaped), making them a little more hi-fi than other wave-types on this list.  For the most part, like a smoother, slicker triangle wave.",
                    8
                ],
                [
                    "Tan",
                    "A potentially crazy wave.  Does strange things.  Tends to produce plenty of distortion	 (because the basic shape goes outside of the standard waveform range).",
                    6
                ],
                [
                    "Whistle",
                    "A sin wave with an additional sine wave overlayed at a lower amplitude and 20x the frequency.  It can end up sounding buzzy, hollow, resonant, or breathy.",
                    7
                ],
                [
                    "White",
                    "White noise is your bog standard random number stream.  Quite hard-sounding, compared to pink noise.",
                    3
                ],
                [
                    "Voice",
                    "A digital voice sample.",
                    11
                ],
                [
                    "Bitnoise",
                    "Periodic 1-bit \"white\" noise. Useful for glitchy and punky sound effects.",
                    9
                ],
                [
                    "Rasp",
                    "Periodic 1-bit noise with a shortened period. It makes a nice digital buzz or clang sound.",
                    5
                ],
                [
                    "FMSyn",
                    "A pretty dense mix of lots of waveforms.  Breathier/distorteder than the classic ones.",
                    10
                ],
            ]
        },
        [
            "Attack Time",
            "Length of the volume envelope attack.",
            "attackTime", 0, 0, 1
        ],
        [
            "Sustain Time",
            "Length of the volume envelope sustain.",
            "sustainTime", 0.3, 0, 1
        ],
        [
            "Punch",
            "Tilts the sustain envelope for more 'pop'.",
            "sustainPunch", 0, 0, 1
        ],
        [
            "Decay Time",
            "Length of the volume envelope decay (yes, I know it's called release).",
            "decayTime", 0.4, 0.03, 1
        ],
        [
            "Compression",
            "Pushes amplitudes together into a narrower range to make them stand out more.  Very good for sound effects, where you want them to stick out against background music. If unlocked, this is set to zero during randomization.",
            "compressionAmount", 0, 0, 1
        ],
        [
            "Frequency",
            "Base note of the sound.",
            "frequency_start", 0.3, 0, 1
        ],
        [
            "Frequency Slide",
            "Slides the frequency up or down.",
            "frequency_slide", 0.0, -0.5, 0.5
        ],
        [
            "Delta Slide",
            "Accelerates the frequency.  Can be used to get the frequency to change direction.",
            "frequency_acceleration", 0.0, -1, 1
        ],
        [
            "Frequency Cutoff",
            "If sliding, the sound will stop at this frequency, to prevent really low notes.  0 means no cuttoff, 1 refers to the starting frequency of the sound. Ignores vibrato.  If the sound trajectory only goes up, this is disabled.",
            "min_frequency_relative_to_starting_frequency", 0.0, 0, 0.99
        ],
        [
            "Vibrato Depth",
            "Strength of the vibrato effect.",
            "vibratoDepth", 0, 0, 1
        ],
        [
            "Vibrato Speed",
            "Speed of the vibrato effect (i.e. frequency).",
            "vibratoSpeed", 0, 0, 1
        ],
        [
            "Pitch Jump Repeat Speed",
            "Larger Values means more pitch jumps, which can be useful for arpeggiation. 0 means a single jump in the whole sound, 1 means 50 jumps a second.",
            "pitch_jump_repeat_speed", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 1",
            "Jump in pitch, either up or down.",
            "pitch_jump_amount", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 1",
            "When the first pitch-jump happens.",
            "pitch_jump_onset_percent", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 2",
            "Second jump in pitch, either up or down.",
            "pitch_jump_2_amount", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 2",
            "When the second pitch-jump happens.",
            "pitch_jump_onset2_percent", 0, 0, 1
        ],
        [
            "Harmonics",
            "Overlays copies of the waveform with copies and multiples of its frequency.  Good for bulking out or otherwise enriching the texture of the sounds (warning: this is the number 1 cause of bfxr slowdown!).",
            "overtones", 0, 0, 1
        ],
        [
            "Harmonics Falloff",
            "The rate at which higher overtones should decay.",
            "overtoneFalloff", 0, 0, 1
        ],
        [
            "Square Duty",
            "Square waveform only : Controls the ratio between the up and down states of the square wave, changing the timbre.",
            "squareDuty", 0, 0, 0.99
        ],
        [
            "Duty Sweep",
            "Square waveform only : Sweeps the duty up or down.",
            "dutySweep", 0, -1, 1
        ],
        [
            "Repeat Speed",
            "Speed of the note repeating - certain variables are reset each time (sweeps, pitch slide, delta slide, etc. - doesn't apply to pitch jumps which have their own repeat parameter). 0 means no repeat, 1 means 10 repeats a second.",
            "repeatSpeed", 0, 0, 1
        ],
        [
            "Flanger Offset",
            "Offsets a second copy of the wave by a small phase, changing the timbre.",
            "flangerOffset", 0, -1, 1
        ],
        [
            "Flanger Sweep",
            "Sweeps the phase up or down.",
            "flangerSweep", 0, -1, 1
        ],
        [
            "Low-pass Filter Cutoff",
            "Frequency at which the low-pass filter starts attenuating higher frequencies.  Named most likely to result in 'Huh why can't I hear anything?' at her high-school grad. ",
            "lpFilterCutoff", 1, 0.01, 1
        ],
        [
            "Low-pass Filter Cutoff Sweep",
            "Sweeps the low-pass cutoff up or down.",
            "lpFilterCutoffSweep", 0, -1, 1
        ],
        [
            "Low-pass Filter Resonance",
            "Changes the attenuation rate for the low-pass filter, changing the timbre.",
            "lpFilterResonance", 0, 0, 1
        ],
        [
            "High-pass Filter Cutoff",
            "Frequency at which the high-pass filter starts attenuating lower frequencies.",
            "hpFilterCutoff", 0, 0, 1
        ],
        [
            "High-pass Filter Cutoff Sweep",
            "Sweeps the high-pass cutoff up or down.",
            "hpFilterCutoffSweep", 0, -1, 1
        ],
        [
            "Bit Crush",
            "Resamples the audio at a lower frequency.",
            "bitCrush", 0, 0, 1
        ],
        [
            "Bit Crush Sweep",
            "Sweeps the Bit Crush filter up or down.",
            "bitCrushSweep", 0, -1, 1
        ]
    ];

    templates = [
        [
            "Pickup/Coin",
            "Blips and baleeps.  Try messing with the wave-forms to get your own sound.",
            "generate_pickup_coin",
            "Pickup",
        ],
        [
            "Laser/Shoot",
            "Pew pew.  Try playing about with the Frequency properties (slide + delta slide especially).  If you want to add some texture, try adding some light, high-frequency vibrato.",
            "generate_laser_shoot",
            "Shoot"
        ],
        [
            "Explosion",
            "Boom.  To make this louder, try increasing compression, or fiddling with the frequency parameters.  To make this softer, try switching to pink noise or decreasing the frequency.  If you're hearing nothing after messing with parameters, try fiddling with 'frequency cutoff'.",
            "generate_explosion",
            "Boom"

        ],
        [
            "Powerup",
            "Whoo.  Try messing with the slide + delta slide parameters to make these less unreservedly exhuberant.  Or how about increasing the decay and playing with the Pitch Jump/Onset parameters?",
            "generate_powerup",
            "PowerUp"
        ],
        [
            "Hit/Hurt",
            "If you want something more crackly, try out a tan wave here.",
            "generate_hit_hurt",
            "Hit"
        ],
        [
            "Jump",
            "Try turn your jump into a soggy kiss with some bitcrush.",
            "generate_jump",
            "Jump"
        ],
        [
            "Blip/Select",
            "You might want to make a variation of this with longer decay for blips that accompany fadeouts or animations.",
            "generate_blip_select",
            "Blip"
        ],
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
    /*TEMPLATE FUNCTIONS */
    /*********************/

    generate_sin() {
        this.reset_params(true);
        this.set_param("waveType", 1, true);
    }

    generate_pickup_coin() {
        this.reset_params(true);

        this.set_param("frequency_start", 0.4 + Math.random() * 0.5, true);

        this.set_param("sustainTime", Math.random() * 0.1, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.4, true);
        this.set_param("sustainPunch", 0.3 + Math.random() * 0.3, true);

        if (Math.random() < 0.5) {
            this.set_param("pitch_jump_Speed", 0.5 + Math.random() * 0.2, true);
            var cnum = Math.floor(Math.random() * 7) + 1;
            var cden = Math.floor(Math.random() * 7) + cnum + 2;

            this.set_param("pitch_jump_amount", cnum / cden, true);
        }
    }

    generate_laser_shoot() {
        this.reset_params(true);
        this.set_param("waveType", (Math.random() * 3)|0, true);
        if (this.get_param("waveType") == 2 && Math.random() < 0.5) {
            this.set_param("waveType",
                (Math.random() * 2)|0, true);
        }

        if (Math.random() < 0.33) {
            this.set_param("frequency_start", 0.1+Math.random() * 0.5, true);
            this.set_param("min_frequency_relative_to_starting_frequency", Math.random() * 0.1, true);
            this.set_param("frequency_slide", -0.35 - Math.random() * 0.3, true);
        } else {
            this.set_param("frequency_start",
                0.5 + Math.random() * 0.5, true);
            this.set_param("min_frequency_relative_to_starting_frequency",
                this.get_param("frequency_start") - 0.2 - Math.random() * 0.6, true);
    
            if (this.get_param("min_frequency_relative_to_starting_frequency") < 0.2)
                this.set_param("min_frequency_relative_to_starting_frequency", 0.2, true);
    
            this.set_param("frequency_slide", -0.15 - Math.random() * 0.2, true);
        }

        //if frequency_start is less than 0.15, cutoff should be zero
        if (this.get_param("frequency_start") < 0.15) {
            this.set_param("min_frequency_relative_to_starting_frequency", 0, true);
            //frequency_slide should be between -.2 and -0.05
            this.set_param("frequency_slide", -0.1 - Math.random() * 0.1, true);
            console.log("adjusting for low frequency");
        }

        if (Math.random() < 0.5) {
            this.set_param("squareDuty", Math.random() * 0.5, true);
            this.set_param("dutySweep", Math.random() * 0.2, true);
        }
        else {
            this.set_param("squareDuty", 0.4 + Math.random() * 0.5, true);
            this.set_param("dutySweep", - Math.random() * 0.7, true);
        }

        this.set_param("sustainTime", 0.1 + Math.random() * 0.2, true);
        this.set_param("decayTime", Math.random() * 0.4, true);
        if (Math.random() < 0.5) this.set_param("sustainPunch", Math.random() * 0.3, true);

        if (Math.random() < 0.33) {
            this.set_param("flangerOffset", Math.random() * 0.2, true);
            this.set_param("flangerSweep", -Math.random() * 0.2, true);
        }

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
    }

    generate_explosion() {
        this.reset_params(true);
        if (Math.random() < 0.5) {
            this.set_param("waveType", 3, true);
        } else {
            this.set_param("waveType", 9, true);
        }

        if (Math.random() < 0.5) {
            this.set_param("frequency_start", 0.1 + Math.random() * 0.4, true);
            this.set_param("frequency_slide", -0.1 + Math.random() * 0.4, true);
        }
        else {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.7, true);
            this.set_param("frequency_slide", -0.2 - Math.random() * 0.2, true);
        }

        this.set_param("frequency_start", this.get_param("frequency_start") * this.get_param("frequency_start"), true);

        if (Math.random() < 0.2) this.set_param("frequency_slide", 0.0, true);
        if (Math.random() < 0.33) this.set_param("repeatSpeed", 0.3 + Math.random() * 0.5, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.3, true);
        this.set_param("decayTime", Math.random() * 0.5, true);
        this.set_param("sustainPunch", 0.2 + Math.random() * 0.6, true);

        if (Math.random() < 0.5) {
            this.set_param("flangerOffset", -0.3 + Math.random() * 0.9, true);
            this.set_param("flangerSweep", -Math.random() * 0.3, true);
        }

        if (Math.random() < 0.33) {
            this.set_param("pitch_jump_Speed", 0.6 + Math.random() * 0.3, true);
            this.set_param("pitch_jump_amount", 0.8 - Math.random() * 1.6, true);
        }
    }

    generate_powerup() {
        this.reset_params(true);

        if (Math.random() < 0.5) this.set_param("waveType", 1, true);
        else this.set_param("squareDuty", Math.random() * 0.6, true);

        if (Math.random() < 0.5) {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.3, true);
            this.set_param("frequency_slide", 0.1 + Math.random() * 0.4, true);
            this.set_param("repeatSpeed", 0.4 + Math.random() * 0.4, true);
        }
        else {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.3, true);
            this.set_param("frequency_slide", 0.05 + Math.random() * 0.2, true);

            if (Math.random() < 0.5) {
                this.set_param("vibratoDepth", Math.random() * 0.7, true);
                this.set_param("vibratoSpeed", Math.random() * 0.6, true);
            }
        }

        this.set_param("sustainTime", Math.random() * 0.4, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.4, true);
    }

    generate_hit_hurt() {
        this.reset_params(true);
        this.set_param("waveType", this.select_random_wave_type("White","Bitnoise","Saw","Square","Voice"), true);
        if (this.get_param("waveType") == 0)
            this.set_param("squareDuty", Math.random() * 0.6);

        this.set_param("frequency_start", 0.2 + Math.random() * 0.6, true);
        this.set_param("frequency_slide", -0.3 - Math.random() * 0.4, true);

        this.set_param("sustainTime", Math.random() * 0.1, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.2, true);

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
    }
    
    generate_jump() {
        this.reset_params(true);

        this.set_param("waveType", this.select_random_wave_type("Square","Saw","FMSyn"), true);
        this.set_param("squareDuty", Math.random() * 0.6, true);
        this.set_param("frequency_start", 0.3 + Math.random() * 0.3, true);
        this.set_param("frequency_slide", 0.1 + Math.random() * 0.2, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.3, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.2, true);

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
        if (Math.random() < 0.5) this.set_param("lpFilterCutoff", 1.0 - Math.random() * 0.6, true);
    }

    generate_blip_select() {
        this.reset_params(true);
        this.set_param("waveType", this.select_random_wave_type("Square","Saw","FMSyn","Whistle"), true);
        if (this.get_param("waveType") == 0)
            this.set_param("squareDuty", Math.random() * 0.6, true);

        this.set_param("frequency_start", 0.2 + Math.random() * 0.4, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.1, true);
        this.set_param("decayTime", Math.random() * 0.2, true);
        this.set_param("hpFilterCutoff", 0.1, true);
    }

    static #RandomizationPower =
        {
            attackTime: 4,
            sustainTime: 2,
            sustainPunch: 2,
            overtones: 3,
            overtoneFalloff: 2,
            vibratoDepth: 3,
            dutySweep: 3,
            flangerOffset: 3,
            flangerSweep: 3,
            lpFilterCutoff: 3,
            lpFilterSweep: 3,
            hpFilterCutoff: 5,
            hpFilterSweep: 5,
            bitCrush: 4,
            bitCrushSweep: 5,
            slide:4,
            frequency_acceleration:7,
            frequency_start:4
        }

    static #WaveTypeWeights =
        [
            1,//0:square
            1,//1:saw
            1,//2:sin
            1,//3:noise
            1,//4:triangle
            1,//5:buzz
            1,//6:tan
            1,//7:whistle
            1,//8:breaker
            1,//9:bitnoise
            1,//10:new 1
        ];

    static #WaveTypeIndices = {
        "Triangle":4,
        "Sin":2,
        "Square":0,
        "Saw":1,
        "Breaker":8,
        "Tan":6,
        "Whistle":7,
        "White":3,
        "Voice":11,
        "Bitnoise":9,
        "Rasp":5,
        "FMSyn":10
    }
    
    select_random_wave_type(...possible_wave_types){
        var wave_type_name = possible_wave_types[Math.floor(Math.random() * possible_wave_types.length)];
        var wave_type_index = Bfxr.#WaveTypeIndices[wave_type_name];
        return wave_type_index;
    }
    generate_random_centered_around_x(min,max,centre){
        //first decided if above or below centre
        if (Math.random() < 0.5){
            //above centre
            var r = Math.random();
            r = Math.pow(r, 2);
            return centre + r*(max-centre);
        }
        else{
            //below centre
            var r = Math.random();
            r = Math.pow(r, 2);
            return centre - r*(centre-min);
        }
    }

    randomize_params() {
        for (var param in this.params) {
            if (!this.locked_params[param]) {
                var min = this.param_min(param);
                var max = this.param_max(param);
                var default_val = this.param_default(param);
                var r = Math.random();
                if (param in Bfxr.#RandomizationPower)
                    r = Math.pow(r, Bfxr.#RandomizationPower[param]);
                var above = Math.random() < 0.5;
                if (min===default_val){
                    above=true;
                }
                if (max===default_val){
                    above=false;
                }
                if (above){
                    this.params[param] = default_val + (max - default_val) * r;
                } else {
                    this.params[param] = default_val - (default_val - min) * r;
                }
            }
        }

        if (!this.locked_params["waveType"]) {
            var count = 0;
            for (var i = 0; i < Bfxr.#WaveTypeWeights.length; i++) {
                count += Bfxr.#WaveTypeWeights[i];
            }
            r = Math.random() * count;
            for (i = 0; i < Bfxr.#WaveTypeWeights.length; i++) {
                r -= Bfxr.#WaveTypeWeights[i];
                if (r <= 0) {
                    this.set_param("waveType", i);
                    break;
                }
            }

        }

        if (Math.random() < 0.5)
            this.set_param("repeatSpeed", 0,true);
    

        this.set_param("min_frequency_relative_to_starting_frequency", 0,true);
    
        this.set_param("compressionAmount", 0,true);

        this.rectify_params();
    
    }

    mutate_params(){
        //with a small probability, mutate the waveType
        if (Math.random() < 0.1){
            var wave_count = Object.keys(Bfxr.#WaveTypeIndices).length;
            var random_wave_index_offset = Math.floor(Math.random() * (wave_count-1));
            var random_wave_index = (this.get_param("waveType") + random_wave_index_offset) % wave_count;
            this.set_param("waveType", random_wave_index, true);
            return;
        }
        super.mutate_params();
        this.rectify_params();
    }

    //tidies up bad parameters that might cause the sound to be inaudible/bad
    rectify_params(){
        //want startfrequency centered around 0.3, falling off quadratically
        var frequency_default = this.param_default("frequency_start");
        //set to 0.2 if waveType is voice (11)
        if (this.get_param("waveType") == 11){
            frequency_default = 0.22;
        }
        this.set_param("frequency_start", this.generate_random_centered_around_x(0,0.6,frequency_default),true);

        if ((!this.locked_params["sustainTime"]) && (!this.locked_params["decayTime"])) {
            if (this.get_param("attackTime") + this.get_param("sustainTime") + this.get_param("decayTime") < 0.2) {
                this.set_param("sustainTime", 0.2 + Math.random() * 0.3);
                this.set_param("decayTime", 0.2 + Math.random() * 0.3);
            }
        }
        //punch between 0 and 1, but square the random value so that smaller values are more likely
        var r = Math.random()*Math.random();
        this.set_param("sustainPunch", r*r, true);

        if ((this.get_param("frequency_start") > 0.7 && this.get_param("frequency_slide") > 0.2) || (this.get_param("frequency_start") < 0.2 && this.get_param("frequency_slide") < -0.05)) {
            this.set_param("frequency_slide", -this.get_param("frequency_slide"),true);
        }

        if (this.get_param("lpFilterCutoff") < 0.1 && this.get_param("lpFilterCutoffSweep") < 0) {
            this.set_param("lpFilterCutoffSweep", -this.get_param("lpFilterCutoffSweep")+0.2,true);
        }

        //if wavetype is not square, set duty values to default
        if (this.get_param("waveType") !== 0){
            this.set_param("squareDuty", this.param_default("squareDuty"),true);
            this.set_param("dutySweep", this.param_default("dutySweep"),true);
        } else {
            //when duty is 0, dutysweep can be anything between min and max
            //when duty is near 1, dutysweep should be <=0 80% of the time, and >=0 20% of the time
            var duty = this.get_param("squareDuty");
            var random_param = Math.random();
            if (duty>0.7 && random_param<0.5){
                this.set_param("dutySweep", -Math.random()*0.5,true);
                //this is just to stop the dutySweep from wiping out the sound when it gets too high (too regularly)
            }
        }
    }

    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/

    generate_sound() {
        var dsp = new Bfxr_DSP(this.params, this);
        dsp.generate_sound();
        this.sound = RealizedSound.from_buffer(dsp.buffer);
    }

    /*********************/
    /* MISCELLANEOUS     */
    /*********************/
    param_is_disabled(param_name){
        if (this.get_param("waveType") !== 0){//if not a square wave, disable squareDuty and dutySweep
            if (param_name == "squareDuty" || param_name == "dutySweep"){
                return true;
            }
        }
        if (param_name == "min_frequency_relative_to_starting_frequency"){
            //disable if frequency slide and frequency delta are both non-negative
            if (this.get_param("frequency_slide") >= 0 && this.get_param("frequency_acceleration") >= 0){
                return true;
            }
        }
        return false;
    }

}