/*
            name: STRING,
            tooltip: STRING,

            type:  FLOAT|WAVEFORM,
            unit:   STRING,

            min:    FLOAT/INT,
            max:   FLOAT/INT,

            default:    TICK-NUMBER, (0-10...I'm so sorry)

            can_vary_over_time: BOOL,
            can_randomize: BOOL,
*/

var SYNTH_SPECS = [{
        name: "waveform",
        tooltip: "tooltip",

        type: "WAVEFORM",
        unit: "",

        min: 0,
        max: 15,

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
        name: "sustain volume",
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
        name: "attack time",
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
        name: "decay time",
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
        name: "harmonics falloff",
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
        name: "vibrato speed",
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
        name: "vibrato depth",
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
        name: "pitch-jump-repeat-speed",
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