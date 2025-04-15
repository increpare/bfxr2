class Bfxr extends SynthTemplate {
    /*********************/
    /*      METADATA     */
    /*********************/

    name = "Bfxr";
    version = Bfxr_DSP.version;
    tooltip = "Bfxr is a simple sound effect generator, based on DrPetter's Sfxr.";
    
    header_properties = ["waveform"];

    default_locked = ["masterVolume"];
    hide_params = ["masterVolume"];
    
    param_info = [
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume",0.5,0,1
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
                    "Pink",
                    "Pink noise is a stream of random numbers with a filtered frequency spectrum to make it softer than white noise.",
                    5
                ],
                [
                    "Bitnoise",
                    "Periodic 1-bit \"white\" noise. Useful for glitchy and punky sound effects.",
                    9
                ],
                [
                    "Buzz",
                    "Periodic 1-bit noise with a shortened period. It makes a nice digital buzz or clang sound.",
                    11
                ],
                [
                    "Holo",
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
            "decayTime", 0.4, 0, 1
        ],
        [
            "Compression",
            "Pushes amplitudes together into a narrower range to make them stand out more.  Very good for sound effects, where you want them to stick out against background music.",
            "compressionAmount", 0, 0, 1
        ],
        [
            "Frequency",
            "Base note of the sound.",
            "startFrequency", 0.3, 0, 1
        ],
        [
            "Frequency Cutoff",
            "If sliding, the sound will stop at this frequency, to prevent really low notes.  If unlocked, this is set to zero during randomization.",
            "minFrequency", 0.0, 0, 1
        ],
        [
            "Frequency Slide",
            "Slides the frequency up or down.",
            "slide", 0.0, -1, 1
        ],
        [
            "Delta Slide",
            "Accelerates the frequency slide.  Can be used to get the frequency to change direction.",
            "deltaSlide", 0.0, -1, 1
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
            "Pitch Jump Repeat Speed",
            "Larger Values means more pitch jumps, which can be useful for arpeggiation.",
            "changeRepeat", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 1",
            "Jump in pitch, either up or down.",
            "changeAmount", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 1",
            "How quickly the note shift happens.",
            "changeSpeed", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 2",
            "Jump in pitch, either up or down.",
            "changeAmount2", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 2",
            "How quickly the note shift happens.",
            "changeSpeed2", 0, 0, 1
        ],
        [
            "Square Duty",
            "Square waveform only : Controls the ratio between the up and down states of the square wave, changing the tibre.",
            "squareDuty", 0, 0, 1
        ],
        [
            "Duty Sweep",
            "Square waveform only : Sweeps the duty up or down.",
            "dutySweep", 0, -1, 1
        ],
        [
            "Repeat Speed",
            "Speed of the note repeating - certain variables are reset each time.",
            "repeatSpeed", 0, 0, 1
        ],
        [
            "Flanger Offset",
            "Offsets a second copy of the wave by a small phase, changing the tibre.",
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
            "lpFilterCutoff", 1, 0, 1
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

    presets = [
        //display name, tooltip, function name, file name
        [
            "Sin test",
            "Sin test",
            "generate_sin",
            "Sin",
        ],
        [
            "Pickup/Coin",
            "Blips and baleeps.  Try messing with the wave-forms to get your own sound.",
            "generate_pickup_coin",
            "Pickup",
        ],
        [
            "Laser/Shoot",
            "Pew pew.  Try playing about with the Frequency properties (slide + delta slide especially).  If you want to add some texture, try adding some light, high-frequency vibrato.",
            "generate_pickup_coin",
            "Shoot"
        ],
        [
            "Explosion",
            "Boom.  To make this louder, try increasing compression, or fiddling with the frequency parameters.  To make this softer, try switching to pink noise or decreasing the frequency.  If you're hearing nothing after messing with parameters, try fiddling with 'frequency cutoff'.",
            "generate_pickup_coin",
            "Boom"

        ],
        [
            "Powerup",
            "Whoo.  Try messing with the slide + delta slide parameters to make these less unreservedly exhuberant.  Or how about increasing the decay and playing with the Pitch Jump/Onset parameters?",
            "generate_pickup_coin",
            "PowerUp"
        ],
        [
            "Hit/Hurt",
            "If you want something more crackly, try out a tan wave here.",
            "generate_pickup_coin",
            "Hit"
        ],
        [
            "Jump",
            "Try turn your jump into a soggy kiss with some bitcrush.",
            "generate_pickup_coin",
            "Jump"
        ],
        [
            "Blip/Select",
            "You might want to make a variation of this with longer decay for blips that accompany fadeouts or animations.",
            "generate_pickup_coin",
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
    /* PRESET FUNCTIONS  */
    /*********************/

    generate_sin() {
        this.reset_params(true);
        this.set_param("waveType", 1, true);
    }

    generate_pickup_coin() {
        this.reset_params(true);

        this.set_param("startFrequency", 0.4 + Math.random() * 0.5, true);

        this.set_param("sustainTime", Math.random() * 0.1, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.4, true);
        this.set_param("sustainPunch", 0.3 + Math.random() * 0.3, true);

        if (Math.random() < 0.5) {
            this.set_param("changeSpeed", 0.5 + Math.random() * 0.2, true);
            var cnum = Math.floor(Math.random() * 7) + 1;
            var cden = Math.floor(Math.random() * 7) + cnum + 2;

            this.set_param("changeAmount", cnum / cden, true);
        }
    }

    generate_laser_shoot(){
        this.reset_params(true);

    }

    generate_explosion(){
        this.reset_params(true);

    }

    generate_powerup(){
        this.reset_params(true);

    }

    generate_hit_hurt(){
        this.reset_params(true);
    }

    generate_jump(){
        this.reset_params(true);
    }

    generate_blip_select(){
        this.reset_params(true);
    }

    randomize_params(){
        super.randomize_params();
        //frequency cutoff must be less than frequency
        var cutoff = Math.random() * this.params.startFrequency;
        this.set_param("minFrequency", cutoff, true);
    }

    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/

    generate_sound(){
        var dsp = new Bfxr_DSP(this.params,this);
        dsp.generate_sound();
        this.sound = RealizedSound.from_buffer(dsp.buffer);
    }
}