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
        
            group_with_next: BOOL, (if things are visually grouped or not in synth editor)
*/

var SYNTH_PARAMETERS = [


    {
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

        group_with_next: true,
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

        group_with_next: false,
    },

    {
        name: "volume",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 7,

        can_vary_over_time: false,
        can_randomize: false,

        group_with_next: true,
    },

    {
        name: "max_sound_duration",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "sec",

        min: 0.3,
        max: 10.0,

        default: 2,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },


    {
        name: "note_held_time",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "sec",

        min: 0.0,
        max: 0.66,

        default: 5,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },

    {
        name: "attack_time",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0.0,
        max: 0.33,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },

    {
        name: "decay_time",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0.00,
        max: 0.33,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },



    {
        name: "sustain_level",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "%",

        min: 0,
        max: 1,

        default: 7,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: false,
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

        group_with_next: false,
    },




    {
        name: "harmonics",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,

        group_with_next: true,
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

        group_with_next: false,
    },


    {
        name: "vibrato_depth",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 4,

        can_vary_over_time: true,
        can_randomize: true,

        group_with_next: true,
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

        group_with_next: false,
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

        group_with_next: false,
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

        group_with_next: false,
    },

    {
        name: "pitch-jump_amount_1",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: -1,
        max: 1,

        default: 5,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },

    {
        name: "pitch-jump_onset_1",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: false,
    },



    {
        name: "pitch-jump_amount_2",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: -1,
        max: 1,

        default: 5,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: true,
    },

    {
        name: "pitch-jump_onset_2",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: 0,
        max: 1,

        default: 0,

        can_vary_over_time: false,
        can_randomize: true,

        group_with_next: false,
    },


    {
        name: "phaser",
        tooltip: "tooltip",

        type: "FLOAT",
        unit: "",

        min: -1,
        max: 1,

        default: 0,

        can_vary_over_time: true,
        can_randomize: true,

        group_with_next: false,
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

        group_with_next: true,
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

        group_with_next: false,
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

        group_with_next: false,
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

        group_with_next: false,
    },

]

var SYNTH_PARAMS_DICT = {};

for (var i = 0; i < SYNTH_PARAMETERS.length; i++) {
    var parameter = SYNTH_PARAMETERS[i];

    SYNTH_PARAMS_DICT[parameter.name] = parameter;
}

var INTERPOLATION_ICONS = [
    ["images/icon_trajectory_linear.png", "tooltip"],
    ["images/icon_trajectory_easein.png", "tooltip"],
    ["images/icon_trajectory_easeout.png", "tooltip"],
    ["images/icon_trajectory_bounce_linear.png", "tooltip"],
    ["images/icon_trajectory_bounce_smooth.png", "tooltip"],
    ["images/icon_trajectory_transition_sudden.png", "tooltip"],
]

var BUTTONLIST_ICONCOUNT = {};

var SLIDER_OBJECT_INDEX = {};