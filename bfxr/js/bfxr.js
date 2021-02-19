console.log("hello world");

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
            result[param_name + "__timevaryswitch"] = false;
            result[param_name + "__timevaryswitch_to"] = param_default_value;
            result[param_name + "__timevaryswitch_curve"] = 0;
            result[param_name + "__timevaryswitch_bias"] = 0;

            if (parameter.can_randomize) {
                result[param_name + "__timevaryswitch__locked"] = false;
                result[param_name + "__timevaryswitch_to__locked"] = false;
                result[param_name + "__timevaryswitch_curve__locked"] = false;
                result[param_name + "__timevaryswitch_bias__locked"] = false;
            }
        }
    };

    return result;
}

var synth_state = gen_new_bfxr_synthstate();

console.log(synth_state);

function onStateModify() {
    console.log(synth_state);
}

function onButtonSelectChange(varname, index, checked) {
    var buttoncount = SYNTH_PARAMS_DICT[varname].icons.length;

    if (checked) {
        synth_state[varname] = index;
        for (var i = 0; i < buttoncount; i++) {
            if (i === index) {
                continue;
            }
            var checkbox = document.getElementById("buttonselect_" + varname + "_" + i);
            checkbox.checked = false;
        }
    } else {
        var default_index = SYNTH_PARAMS_DICT[varname].default;
        var checkbox = document.getElementById("buttonselect_" + varname + "_" + default_index);
        synth_state[varname] = default_index;
        checkbox.checkbox = true;
    }
    onStateModify();
}

function onLockboxSelectChange(varname, checked) {
    synth_state[varname + "__locked"] = checked;
    onStateModify();
}

function onTimevaryswitchSelectChange(varname, checked) {
    synth_state[varname + "__timevaryswitch"] = checked;
    var tablerow = document.getElementById("tablerow_" + varname);
    if (checked) {
        tablerow.classList.add("timevarying_expanded");
    } else {
        tablerow.classList.remove("timevarying_expanded");
    }
    onStateModify();
}

function hook_up_checkbox(varname, index) {
    var buttonselect = document.getElementById(`buttonselect_${varname}_${index}`);
    buttonselect.addEventListener('change', (event) => {
        onButtonSelectChange(varname, index, event.currentTarget.checked);
    });
}

function hook_up_lockbox(varname) {
    var buttonselect = document.getElementById(`lock_checkbox_${varname}`);
    buttonselect.addEventListener('change', (event) => {
        onLockboxSelectChange(varname, event.currentTarget.checked);
    });
}

function hook_up_timevaryswitch(varname) {
    var buttonselect = document.getElementById(`timevarying_checkbox_${varname}`);
    buttonselect.addEventListener('change', (event) => {
        onTimevaryswitchSelectChange(varname, event.currentTarget.checked);
    });
}

function onSliderValueChange(varname, value, eventover) {
    if (eventover === false) {
        return;
    }
    synth_state[varname] = value;
    onStateModify();
}