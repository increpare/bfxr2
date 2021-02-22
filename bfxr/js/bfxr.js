function gen_new_bfxr_synthstate() {
    var result = {};

    for (var i = 0; i < SYNTH_PARAMETERS.length; i++) {
        var parameter = SYNTH_PARAMETERS[i];
        var param_name = variablize_param_name(parameter.name);
        var param_default_value = parameter.type === "BUTTONSELECT" ? parameter.default : (parameter.min + (parameter.max - parameter.min) * parameter.default / 10.0);

        result[param_name] = param_default_value;
        if (parameter.can_randomize) {
            result[param_name + "__locked"] = false;
        }
        if (parameter.can_vary_over_time) {
            result[param_name + "__timevarying"] = false;
            result[param_name + "__timevarying_from"] = param_default_value;
            result[param_name + "__timevarying_to"] = param_default_value;
            result[param_name + "__timevarying_curve"] = 0;
            result[param_name + "__timevarying_bias"] = 0;

            if (parameter.can_randomize) {
                result[param_name + "__timevarying_from__locked"] = false;
                result[param_name + "__timevarying_to__locked"] = false;
                result[param_name + "__timevarying_curve__locked"] = false;
                result[param_name + "__timevarying_bias__locked"] = false;
            }
        }
    };

    return result;
}

function copy_synth_state(state) {
    return JSON.parse(JSON.stringify(state));
}

var synth_state = gen_new_bfxr_synthstate();
var previous_state = copy_synth_state(synth_state);

console.log(synth_state);

function onStateModify(forceall = false, forceupdate_id = "") {
    console.log(synth_state);

    var keys = Object.keys(synth_state);

    var modified = true;

    while (modified) {
        modified = false;
        var future_previoua_state = copy_synth_state(synth_state);

        for (const key of keys) {
            if (synth_state[key] !== previous_state[key] || forceall === true || key === forceupdate_id) {
                console.log(key + " changed.");
                if (key.endsWith("__locked") || key.endsWith("__timevarying")) {
                    // is checkbox

                    var checkbox = document.getElementById(key);
                    var value = synth_state[key];
                    checkbox.checked = value;
                    if (key.endsWith("__timevarying")) {
                        var tablerow = document.getElementById("tablerow_" + key.substr(0, key.length - 13));
                        if (value) {
                            tablerow.classList.add("timevarying_expanded");
                        } else {
                            tablerow.classList.remove("timevarying_expanded");
                        }
                    }

                    if (key.endsWith("__timevarying_from__locked")) {
                        var mirror_to_key = key.substr(0, key.length - "__timevarying_from__locked".length) + "__locked";
                        if (synth_state[mirror_to_key] !== value) {
                            synth_state[mirror_to_key] = value;
                            modified = true;
                        }
                    } else {
                        var mirror_to_key = key.substring(0, key.length - "__locked".length) + "__timevarying_from__locked";
                        if (keys.indexOf(mirror_to_key) >= 0) {
                            if (synth_state[mirror_to_key] !== value) {
                                synth_state[mirror_to_key] = value;
                                modified = true;
                            }
                        }
                    }

                } else {
                    elem = document.getElementById("tablerow_" + key);
                    value = synth_state[key];


                    if (key.endsWith("__timevarying_from")) {
                        var mirror_to_key = key.substr(0, key.length - "__timevarying_from".length);
                        if (synth_state[mirror_to_key] !== value) {
                            synth_state[mirror_to_key] = value;
                            modified = true;
                        }
                    } else {
                        var mirror_to_key = key + "__timevarying_from";
                        if (keys.indexOf(mirror_to_key) >= 0) {
                            if (synth_state[mirror_to_key] !== value) {
                                synth_state[mirror_to_key] = value;
                                modified = true;
                            }
                        }
                    }


                    if (elem.classList.contains("synthtablerow_buttonlist")) {
                        //is buttonlist
                        var iconcount = BUTTONLIST_ICONCOUNT[key];

                        for (var i = 0; i < iconcount; i++) {
                            var checkbox = document.getElementById("buttonselect_" + key + "_" + i);
                            checkbox.checked = i === value;
                        }

                    } else {
                        //is slider (synthtablerow_slider)
                        var slider = document.getElementById(key);
                        slider.value = value;
                        var slider_object = SLIDER_OBJECT_INDEX[key];
                        slider_object.setValue(value);
                    }

                }
            }
        }
        previous_state = future_previoua_state;
    }

    playCurrentSound();
}

function onButtonSelectChange(varname, index, checked, iconcount) {
    if (checked === false) {
        checked = true;
    }
    if (checked) {
        synth_state[varname] = index;
    } else {
        var default_index = SYNTH_PARAMS_DICT[varname].default;
        synth_state[varname] = default_index;
    }
    visualiseFunctionParam(synth_state, varname);
    onStateModify(false, varname);
}

function onLockboxSelectChange(varname, checked) {
    synth_state[varname + "__locked"] = checked;
    visualiseFunctionParam(synth_state, varname);
    onStateModify();
}

function onTimevaryswitchSelectChange(varname, checked) {
    synth_state[varname + "__timevarying"] = checked;
    visualiseFunctionParam(synth_state, varname);
    onStateModify();
}

function hook_up_checkbox(varname, index, iconcount) {
    var buttonselect = document.getElementById(`buttonselect_${varname}_${index}`);
    buttonselect.addEventListener('change', (event) => {
        onButtonSelectChange(varname, index, event.currentTarget.checked, iconcount);
    });
    if (index === 0) {
        BUTTONLIST_ICONCOUNT[varname] = iconcount;
    }
}

function hook_up_lockbox(varname) {
    var buttonselect = document.getElementById(`${varname}__locked`);
    buttonselect.addEventListener('change', (event) => {
        onLockboxSelectChange(varname, event.currentTarget.checked);
    });
}

function hook_up_timevaryswitch(varname) {
    var buttonselect = document.getElementById(`${varname}__timevarying`);
    buttonselect.addEventListener('change', (event) => {
        onTimevaryswitchSelectChange(varname, event.currentTarget.checked);
    });
}

function onSliderValueChange(varname, value, eventover) {
    synth_state[varname] = value;
    visualiseFunctionParam(synth_state, varname);
    if (eventover === false) {
        return;
    }
    onStateModify();
}


function playCurrentSound() {
    var params = Params();

    params.wave_type = synth_state.waveform;

    // Envelope
    params.p_env_attack = 0.0; // Attack time
    params.p_env_sustain = 0.3; // Sustain time
    params.p_env_punch = 0.0; // Sustain punch
    params.p_env_decay = 0.4; // Decay time

    // Tone
    params.p_base_freq = synth_state.frequency; // Start frequency
    params.p_freq_limit = 0.0; // Min frequency cutoff
    params.p_freq_ramp = 0.0; // Slide (SIGNED)
    params.p_freq_dramp = 0.0; // Delta slide (SIGNED)
    // Vibrato
    params.p_vib_strength = synth_state.vibrato_depth; // Vibrato depth
    params.p_vib_speed = synth_state.vibrato_speed; // Vibrato speed

    // Tonal change
    params.p_arp_mod = synth_state.jump_amount1; // Change amount (SIGNED)
    params.p_arp_speed = synth_state.jump_onset1; // Change speed

    // Duty (wat's that?)
    params.p_duty = synth_state.duty; // Square duty
    params.p_duty_ramp = 0.0; // Duty sweep (SIGNED)

    // Repeat
    params.p_repeat_speed = synth_state.repeat_speed; // Repeat speed

    // Phaser
    params.p_pha_offset = synth_state.phaser; // Phaser offset (SIGNED)
    params.p_pha_ramp = 0.0; // Phaser sweep (SIGNED)

    // Low-pass filter
    params.p_lpf_freq = synth_state.low_pass_filter_cutoff; // Low-pass filter cutoff
    params.p_lpf_ramp = 0.0; // Low-pass filter cutoff sweep (SIGNED)
    params.p_lpf_resonance = synth_state.low_pass_filter_resonance; // Low-pass filter resonance

    // High-pass filter
    params.p_hpf_freq = synth_state.high_pass_filter_cutoff; // High-pass filter cutoff
    params.p_hpf_ramp = 0.0; // High-pass filter cutoff sweep (SIGNED)

    // Sample parameters
    params.sound_vol = 0.5;
    params.sample_rate = 44100;
    params.bit_depth = 8;


    playSound(params);
}

var rightcol_button_play = document.getElementById("rightcol_button_play");
rightcol_button_play.addEventListener("click", function(event) {
    console.log(synth_state);
    playCurrentSound();
});