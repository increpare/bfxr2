const fs = require('fs')
const pretty = require('pretty');

eval(fs.readFileSync('bfxr/js/utils.js', 'utf8'));
eval(fs.readFileSync('bfxr/js/synth_parameters.js', 'utf8'));



var SYNTHPARAMS_HTML = "";

var ACTIVATIONSCRIPTS_JS = "";


function createSynthTableRow(varname, display, slidercell_html_content, canlock, cantimechange) {

}

function spawn_bar(parameter) {
    var varname = variablize_param_name(parameter.name);
    SYNTHPARAMS_HTML += `
        <tr class="tableborder ${parameter.group_with_next?"mergewithnext":""}" id="tablerow_${varname}">
            <td class="tableborder iconcell">${
                parameter.can_randomize?`
                <input type="checkbox" class="btn-check" id="lock_checkbox_${varname}" autocomplete="off">
                <label class="btn btn-outline-primary lock-checkbox" id="lock_checkbox_${varname}_LABEL" for="lock_checkbox_${varname}"></label><br>
                ` : ``}
            </td>
            <td class="tableborder fieldtext">${prettify_param_name(parameter.name)}</td>
            <td class="tableborder slidercell">
                <input id="${varname}" type="text" />
            </td>
            <td class="tableborder expandcell">
                ${
                    parameter.can_vary_over_time ? `
                <input type="checkbox" class="btn-check" id="timevarying_checkbox_${varname}" autocomplete="off">
                <label class="btn btn-outline-primary timevarying-checkbox"  id="timevarying_checkbox_${varname}_LABEL" for="timevarying_checkbox_${varname}"></label><br>`:''
                }
            </td>

        </tr>`;

        if (parameter.can_randomize){
            ACTIVATIONSCRIPTS_JS += `
            hook_up_lockbox("${varname}");
            `;
        }

        if (parameter.can_vary_over_time){
            ACTIVATIONSCRIPTS_JS += `
            hook_up_timevaryswitch("${varname}");
            `;
        }

    var rangeticks = [];
    for (var i = 0; i <= 10; i++) {
        var val = parameter.min + (parameter.max - parameter.min) * i / 10.0;
        rangeticks.push(val);
    }

    var defaultval = rangeticks[parameter.default];

    ACTIVATIONSCRIPTS_JS += `
        var slider_${varname} = new Slider("#${varname}", {
            id: "instanced_${varname}",
            min: ${parameter.min},
            max: ${parameter.max},
            range: false,
            step: ${(parameter.max-parameter.min)/100},
            value: ${defaultval},
            ticks: ${JSON.stringify(rangeticks)}
        });
        slider_${varname}.sliderElem.className += " singleselect";
        slider_${varname}.sliderElem.getElementsByClassName("slider-tick-container")[0].children[${parameter.default}].classList.add('defaulttick');

        slider_${varname}.on("slide", function(sliderValue) {
            onSliderValueChange("${varname}",sliderValue,false);
        });
        slider_${varname}.on("slideStop", function(sliderValue) {
            onSliderValueChange("${varname}",sliderValue,true);
        });
        `;

}

function spawn_buttonselect(parameter) {
    var varname = variablize_param_name(parameter.name);

    SYNTHPARAMS_HTML += `
    <tr class="tableborder ${parameter.group_with_next?"mergewithnext":""}" id="tablerow_${varname}">
        <td class="tableborder iconcell">    
            <input type="checkbox" class="btn-check" id="lock_checkbox_${parameter.name}" autocomplete="off">
            <label class="btn btn-outline-primary lock-checkbox" id="lock_checkbox_${varname}_LABEL" for="lock_checkbox_${parameter.name}"></label><br>
            <!--<img class="iconimg" src="images/symbol_mutation_unlocked.png ">-->
        </td>
        <td class="tableborder fieldtext">${parameter.name}</td>
        <td class="tableborder slidercell">`;

    var col_index = 0;
    var cols_per_row = 6;
    for (var i = 0; i < parameter.icons.length; i++) {

        if (i % cols_per_row === 0) {
            if (i > 0) {
                SYNTHPARAMS_HTML += `</div>`;
            }

            SYNTHPARAMS_HTML += `<div class="btn-group" role="group" aria-label="Basic checkbox toggle button group">`;

        }

        var icon_file_name = parameter.icons[i][0];
        var icon_tooltip = parameter.icons[i][1];
        SYNTHPARAMS_HTML += `
            <input type="checkbox" class="btn-check " id="buttonselect_${varname}_${i}" autocomplete="off" ${i===parameter.default?"checked":""}>
            <label class="btn btn-outline-primary buttongroupcheck" id="buttonselect_${varname}_LABEL" for="buttonselect_${varname}_${i}">
                <img class="icon" src="${icon_file_name}">
            </label>`;

        ACTIVATIONSCRIPTS_JS += `
        hook_up_checkbox("${varname}",${i});
        `;
        
    }

    SYNTHPARAMS_HTML += `</div>
    
    <td class="tableborder expandcell">
        ${
            parameter.can_vary_over_time ? `
        <input type="checkbox" class="btn-check" id="timevarying_checkbox_${varname}" autocomplete="off">
        <label class="btn btn-outline-primary timevarying-checkbox" id="timevarying_checkbox_${varname}_LABEL" for="timevarying_checkbox_${varname}"></label><br>`:''
        }
    </td>
    </td>`;

    
    if (parameter.can_randomize){
        ACTIVATIONSCRIPTS_JS += `
        hook_up_lockbox("${varname}");
        `;
    }

    if (parameter.can_vary_over_time){
        ACTIVATIONSCRIPTS_JS += `
        hook_up_timevaryswitch("${varname}");
        `;
    }
}

for (var i = 0; i < SYNTH_PARAMETERS.length; i++) {
    var parameter = SYNTH_PARAMETERS[i];
    if (parameter.type === "FLOAT") {
        spawn_bar(parameter);
    } else if (parameter.type === "BUTTONSELECT") {
        spawn_buttonselect(parameter);
    }
}

var template_index = fs.readFileSync('bfxr/template.html', 'utf8');

template_index = template_index.replace('<!--__SYNTHPARAMS_HTML__-->', SYNTHPARAMS_HTML);
template_index = template_index.replace('/*__ACTIVATIONSCRIPTS_JS__*/', ACTIVATIONSCRIPTS_JS);


template_index = pretty(template_index);

fs.writeFileSync('bfxr/index.html', template_index, 'utf8');