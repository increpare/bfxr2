const canvasEle = document.getElementById('logo-canvas');
const context2d = canvasEle.getContext('2d');

//returns values before final volume transformation is applied, and time is scaled between 0 and 1.
function calcEnvelope(state) {

    var attacktime = state.attack_time;
    var holdtime = state.note_held_time;
    var sustain = state.sustain_level;
    var decaytime = state.decay_time;
    var decaytime_from_peak = decaytime;

    //work in 1x1 grid then transform later (origin still top-left tho) ), also ignore volume param

    var peakval = 1;

    if (holdtime < attacktime) {
        peakval *= holdtime / attacktime;
        decaytime *= peakval;
        attacktime = holdtime
    }

    if (sustain > peakval) {
        sustain *= peakval;
    }

    var peakoffset = attacktime;


    var sustain_start_offset = peakoffset + decaytime * (peakval - sustain) / (peakval);

    var sustain_val = sustain;

    var sustain_end_offset = holdtime;

    var decay_end_offset = holdtime + sustain * decaytime;

    if (sustain_end_offset < sustain_start_offset) {
        var delta = sustain_start_offset - sustain_end_offset;
        sustain_end_offset += delta;
        decay_end_offset += delta;
    }

    decay_end_offset = sustain_end_offset + sustain_val * decaytime_from_peak;

    return [peakoffset, peakval, sustain_start_offset, sustain_val, sustain_end_offset, decay_end_offset];
}

var visualisefunctions = [
    [
        ["Bit_Crush"],
        function(state) {
            context2d.beginPath();
            context2d.lineWidth = '5'; // width of the line
            context2d.strokeStyle = '#c89057'; // color of the line
            context2d.moveTo(50, 50); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(50, 100); // used to create a pointer based on x and y  
            context2d.stroke(); // this is where the actual drawing happens.

        },
    ],
    [
        [
            "attack_time",
            "decay_time",
            "max_sound_duration",
            "sustain_level",
            "note_held_time",
            "volume",
        ],
        function(state) {
            var w = canvasEle.width;
            var h = canvasEle.height;
            var margin = 4;
            var bmargin = 40;

            h = h - margin - bmargin;
            w = w - 2 * margin;

            var volume = state.volume;

            var t = margin;
            var b = t + h;
            var l = margin;
            var r = l + w;

            var [
                peakoffset,
                peakval,
                sustain_start_offset,
                sustain_val,
                sustain_end_offset,
                decay_end_offset
            ] = calcEnvelope(state);

            var start_x = 0;
            var start_y = 1;

            var peakpoint_x = peakoffset;
            var peakpoint_y = 1 - peakval;

            var sustain_l_x = sustain_start_offset;
            var sustain_l_y = 1 - sustain_val;

            var sustain_r_x = sustain_end_offset;
            var sustain_r_y = 1 - sustain_val;

            var decay_end_x = decay_end_offset;
            var decay_end_y = 1;

            var end_x = 1;
            var end_y = 1;

            start_x = margin + w * start_x;
            start_y = margin + h * (1 - (1 - start_y) * volume);
            peakpoint_x = margin + w * peakpoint_x;
            peakpoint_y = margin + h * (1 - (1 - peakpoint_y) * volume);
            sustain_l_x = margin + w * sustain_l_x;
            sustain_l_y = margin + h * (1 - (1 - sustain_l_y) * volume);
            sustain_r_x = margin + w * sustain_r_x;
            sustain_r_y = margin + h * (1 - (1 - sustain_r_y) * volume);
            decay_end_x = margin + w * decay_end_x;
            decay_end_y = margin + h * (1 - (1 - decay_end_y) * volume);
            end_x = margin + w * end_x;
            end_y = margin + h * end_y;

            context2d.beginPath();
            context2d.lineWidth = '5'; // width of the line
            context2d.lineCap = "round";
            context2d.lineJoin = "round";
            context2d.strokeStyle = '#c89057'; //'#c89057'; // color of the line
            context2d.moveTo(start_x, start_y); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(peakpoint_x, peakpoint_y); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(sustain_l_x, sustain_l_y); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(sustain_r_x, sustain_r_y); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(decay_end_x, decay_end_y); // begins a new sub-path based on the given x and y values.
            context2d.lineTo(end_x, end_y); // begins a new sub-path based on the given x and y values.
            context2d.stroke(); // this is where the actual drawing happens.

            context2d.font = "20px Arial";
            context2d.fontWeight = 500;
            context2d.fillStyle = '#c89057'; //'#c89057'; // color of the line
            context2d.lineStyle = 'transparent';
            context2d.textAlign = "center";
            context2d.textBaseline = "top";
            context2d.fillText(state.max_sound_duration + "s", l + w / 2, b + 10);

        },
    ],
    [
        [
            "duty",
        ],
        function(state) {

        },
    ],
    [
        [
            "frequency",
        ],
        function(state) {

        },
    ],
    [
        [
            "harmonics",
            "harmonics_falloff"
        ],
        function(state) {

        },
    ],
    [
        [
            "high_pass_filter_cutoff",
        ],
        function(state) {

        },
    ],
    [
        [
            "low_pass_filter_cutoff",
            "low_pass_filter_resonance"
        ],
        function(state) {

        },
    ],
    [
        [
            "phaser",
        ],
        function(state) {

        },
    ],
    [
        [
            "pitch_jump_amount_1",
            "pitch_jump_onset_1",
        ],
        function(state) {

        },
    ],
    [
        [
            "pitch_jump_amount_2",
            "pitch_jump_onset_2",
        ],
        function(state) {

        },
    ],
    [
        [
            "pitch_jump_repeate_speed",
        ],
        function(state) {

        },
    ],
    [
        [
            "vibrato_depth",
            "vibrato_speed"
        ],
        function(state) {

        },
    ],
    [
        [
            "waveform",
        ],
        function(state) {

        },
    ],
];

var functionDict = {}

for (let i = 0; i < visualisefunctions.length; i++) {
    var keys = visualisefunctions[i][0];
    for (let j = 0; j < keys.length; j++) {
        functionDict[keys[j]] = visualisefunctions[i][1];
    }
}
console.log(functionDict);

function visualiseFunctionParam(state, paramname) {
    context2d.clearRect(0, 0, canvasEle.width, canvasEle.height);
    var tag_index = paramname.indexOf('__');
    if (tag_index >= 0) {
        paramname = paramname.substr(0, tag_index);
    }
    console.log(paramname);
    functionDict[paramname](state);
}