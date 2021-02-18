/*
            name: STRING,
            tooltip: STRING,

            type:  FLOAT|BUTTONSELECT,
            unit:   STRING,

            min:    FLOAT/INT,
            max:   FLOAT/INT,

            default:    TICK-NUMBER, (0-10...I'm so sorry)

            can_vary_over_time: BOOL,
            can_randomize: BOOL,
*/

var SYNTH_PARAMETERS = [{
        name: "waveform",
        tooltip: "tooltip",

        type: "BUTTONSELECT",
        unit: "",

        min: 0,
        max: 15,

        icons: [
            ["images/icon_waveform_triangle.png", "tooltip"],
            ["images/icon_waveform_sine.png", "tooltip"],
            ["images/icon_waveform_saw.png", "tooltip"],
            ["images/icon_waveform_square.png", "tooltip"],
            ["images/icon_waveform_breaker.png", "tooltip"],
            ["images/icon_waveform_whistle.png", "tooltip"],
            ["images/icon_waveform_tan.png", "tooltip"],
            ["images/icon_waveform_holo.png", "tooltip"],
            ["images/icon_waveform_whitenoise.png", "tooltip"],
            ["images/icon_waveform_pinknoise.png", "tooltip"],
            ["images/icon_waveform_brownnoise.png", "tooltip"],
            ["images/icon_waveform_bitnoise.png", "tooltip"],
            ["images/icon_waveform_buzz.png", "tooltip"],
            ["images/icon_waveform_gravel.png", "tooltip"],
            ["images/icon_waveform_sand.png", "tooltip"],
            ["images/icon_waveform_snow.png", "tooltip"]
        ],

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "max_sound_duration",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "sec",

        min: 0.3,
        max: 5.0,

        default: 5,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "sustain_volume",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0,
        max: 100,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,
    },

    {
        name: "attack_time",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0,
        max: 33,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,
    },

    {
        name: "decay_time",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0,
        max: 33,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,
    },




    {
        name: "compression",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 3,

        can_vary_over_time: true,
        can_randomize: true,
    },




    {
        name: "harmonics",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 3,

        can_vary_over_time: true,
        can_randomize: true,
    },




    {
        name: "harmonics_falloff",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 3,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "vibrato_speed",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "vibrato_depth",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "frequency",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 3,

        can_vary_over_time: true,
        can_randomize: true,
    },


    {
        name: "pitch-jump_repeat_speed",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 3,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "pitch-jump-amount-1",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: -1,
        max: 1,

        default: 5,

        can_vary_over_time: false,
        can_randomize: true,
    },

    {
        name: "pitch-jump-onset-1",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: false,
        can_randomize: true,
    },



    {
        name: "pitch-jump-amount-2",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: -1,
        max: 1,

        default: 5,

        can_vary_over_time: false,
        can_randomize: true,
    },

    {
        name: "pitch-jump-onset-2",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: false,
        can_randomize: true,
    },

    {
        name: "duty",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "flanger",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },



    {
        name: "low-pass_filter_cutoff",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 10,

        can_vary_over_time: true,
        can_randomize: true,
    },

    {
        name: "low-pass_filter_resonance",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },



    {
        name: "high-pass_filter_cutoff",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },


    {
        name: "Bit-Crush",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,
    },

]