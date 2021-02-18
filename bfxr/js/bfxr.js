console.log("hello world");

function gen_new_bfxr_synthstate() {
    var result = {};

    for (var i = 0; i < SYNTH_PARAMETERS.length; i++) {
        var parameter = SYNTH_PARAMETERS[i];
        var param_name = variablize_param_name(parameter.name);
        var param_default_value = parameter.type === "BUTTONSELECT" ? parameter.default : (parameter.min + (parameter.max - parameter.min) * parameter.default / 10.0);

        result[param_name] = param_default_value;
    };

    return result;
}

var synth_state = gen_new_bfxr_synthstate();

console.log(synth_state);

function onButtonSelectChange(varname, index, checked) {
    var buttoncount = SYNTH_PARAMS_DICT[varname].icons.length;

    if (checked) {
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
        checkbox.checkbox = true;
    }
}

function hook_up_checkbox(varname, index) {
    var buttonselect = document.getElementById(`buttonselect_${varname}_${index}`);
    buttonselect.addEventListener('change', (event) => {
        onButtonSelectChange(varname, index, event.currentTarget.checked);
    });
}

function onSliderValueChange(varname, value, eventover) {
    if (eventover === false) {
        return;
    }
    synth_state[varname] = value;
    console.log(synth_state);
}