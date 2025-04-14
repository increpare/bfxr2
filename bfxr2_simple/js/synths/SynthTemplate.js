class SynthTemplate {
    Params () {
        var result = {};
        for (var i = 0; i < param_info.length; i++) {
            var param = param_info[i];
            //if object, then it's a buttonselect
           if (param.constructor === Array) {
                var param_name = param[2];
                var param_default_value = param[3];
                result[param_name] = param_default_value;
            } else {
                switch (param.type) {
                    case "BUTTONSELECT":
                        break;
                    case "KNOB_TRANSITION":
                        break;
                    default:
                        console.error("Unknown param type: " + param.type);
                }
            } 
        }
        return result;
    };
}
