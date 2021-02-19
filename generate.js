const fs = require('fs')
const pretty = require('pretty');

eval(fs.readFileSync('bfxr/js/utils.js', 'utf8'));
eval(fs.readFileSync('bfxr/js/synth_parameters.js', 'utf8'));



var SYNTHPARAMS_HTML = "";

var ACTIVATIONSCRIPTS_JS = "";


function createSynthTableRow(varname, display_name, group_with_next, slidercell_html_content, can_randomize, can_vary_over_time, extraClass) {
    SYNTHPARAMS_HTML += `
        <tr class="tableborder ${group_with_next?"mergewithnext":""} ${extraClass}" id="tablerow_${varname}">
            <td class="tableborder iconcell">${
                can_randomize?`
                <input type="checkbox" class="btn-check" id="${varname}__locked" autocomplete="off">
                <label class="btn btn-outline-primary lock-checkbox" id="${varname}__locked__LABEL" for="${varname}__locked"></label><br>
                ` : ``}
            </td>
            <td class="tableborder fieldtext">${display_name}</td>
            <td class="tableborder slidercell">
                ${slidercell_html_content}
            </td>
            <td class="tableborder expandcell">
                ${
                    can_vary_over_time ? `
                <input type="checkbox" class="btn-check" id="${varname}__timevarying" autocomplete="off">
                <label class="btn btn-outline-primary timevarying-checkbox"  id="${varname}__timevarying__LABEL" for="${varname}__timevarying"></label><br>`:''
                }
            </td>

        </tr>`;

        if (can_randomize){
            ACTIVATIONSCRIPTS_JS += `
            hook_up_lockbox("${varname}");
            `;
        }

        if (can_vary_over_time){
            ACTIVATIONSCRIPTS_JS += `
            hook_up_timevaryswitch("${varname}");
            `;
        }
}

function new_html_buttonlist(varname,icons,default_val){
    var SLIDERCELL_HTML_CONTENT = '';
    
    var col_index = 0;
    var cols_per_row = 6;
    for (var i = 0; i < icons.length; i++) {

        if (i % cols_per_row === 0) {
            if (i > 0) {
                SLIDERCELL_HTML_CONTENT += `</div>`;
            }

            SLIDERCELL_HTML_CONTENT += `<div class="btn-group" role="group" aria-label="Basic checkbox toggle button group">`;

        }

        var icon_file_name = icons[i][0];
        var icon_tooltip = icons[i][1];
        SLIDERCELL_HTML_CONTENT += `
            <input type="checkbox" class="btn-check " id="buttonselect_${varname}_${i}" autocomplete="off" ${i===default_val?"checked":""}>
            <label class="btn btn-outline-primary buttongroupcheck" id="buttonselect_${varname}_${i}_LABEL" for="buttonselect_${varname}_${i}">
                <img class="icon" src="${icon_file_name}">
            </label>`;

        ACTIVATIONSCRIPTS_JS += `
        hook_up_checkbox("${varname}",${i},${icons.length});
        `;

    }

    SLIDERCELL_HTML_CONTENT += `</div>`

    return SLIDERCELL_HTML_CONTENT;
}

function new_html_slider(varname,max,min,default_val){
    var SLIDERCELL_HTML_CONTENT =`<input id="${varname}" type="text" />`

    var rangeticks = [];
    for (var i = 0; i <= 10; i++) {
        var val = min + (max - min) * i / 10.0;
        rangeticks.push(val);
    }

    var defaultval = rangeticks[default_val];

    ACTIVATIONSCRIPTS_JS += `
        var slider_${varname} = new Slider("#${varname}", {
            id: "instanced_${varname}",
            min: ${min},
            max: ${max},
            range: false,
            step: ${(max-min)/100},
            value: ${defaultval},
            ticks: ${JSON.stringify(rangeticks)}
        });
        slider_${varname}.sliderElem.className += " singleselect";
        slider_${varname}.sliderElem.getElementsByClassName("slider-tick-container")[0].children[${default_val}].classList.add('defaulttick');

        slider_${varname}.on("slide", function(sliderValue) {
            onSliderValueChange("${varname}",sliderValue,false);
        });
        slider_${varname}.on("slideStop", function(sliderValue) {
            onSliderValueChange("${varname}",sliderValue,true);
        });
        SLIDER_OBJECT_INDEX["${varname}"]=slider_${varname};
        `;

    return SLIDERCELL_HTML_CONTENT;
}


function spawn_bar(parameter) {
    var varname = variablize_param_name(parameter.name);
    var display_name = prettify_param_name(parameter.name);

    var SLIDERCELL_HTML_CONTENT = new_html_slider(varname,parameter.max,parameter.min,parameter.default);

    createSynthTableRow(
        varname,
        display_name,
        parameter.group_with_next,
        SLIDERCELL_HTML_CONTENT,
        parameter.can_randomize,
        parameter.can_vary_over_time,
        "synthtablerow_slider"
        );

    if (parameter.can_vary_over_time){

        var varname_FROM = varname+"__timevarying_from";
        var SLIDERCELL_HTML_FROM = new_html_slider(varname_FROM,parameter.max,parameter.min,parameter.default);
        createSynthTableRow(
            varname_FROM,
            "from",
            true,
            SLIDERCELL_HTML_FROM,
            parameter.can_randomize,
            false,
            "synthtablerow_slider timevaryrow"
            );

        var varname_TO = varname+"__timevarying_to";
        var SLIDERCELL_HTML_TO = new_html_slider(varname_TO,parameter.max,parameter.min,parameter.default);
        createSynthTableRow(
            varname_TO,
            "to",
            true,
            SLIDERCELL_HTML_TO,
            parameter.max,
            parameter.min,
            "synthtablerow_slider timevaryrow"
            );

        var varname_CURVE = varname+"__timevarying_curve";
        var SLIDERCELL_HTML_CURVE = new_html_buttonlist(varname_CURVE,INTERPOLATION_ICONS,0);
        //INTERPOLATION_ICONS
        createSynthTableRow(
            varname_CURVE,
            "curve",
            true,
            SLIDERCELL_HTML_CURVE,
            parameter.max,
            parameter.min,
            "synthtablerow_buttonlist timevaryrow"
            );

        var varname_BIAS = varname+"__timevarying_bias";
        var SLIDERCELL_HTML_BIAS = new_html_slider(varname_BIAS,1,0,parameter.default);
        createSynthTableRow(
            varname_BIAS,
            "bias",
            parameter.group_with_next,
            SLIDERCELL_HTML_BIAS,
            parameter.max,
            parameter.min,
            "synthtablerow_slider timevaryrow"
            );

    }

}

function spawn_buttonselect(parameter) {
    var varname = variablize_param_name(parameter.name);
    var display_name = prettify_param_name(parameter.name);

    var SLIDERCELL_HTML_CONTENT = new_html_buttonlist(varname,parameter.icons,parameter.default);
    
    createSynthTableRow(
        varname,
        display_name,
        parameter.group_with_next,
        SLIDERCELL_HTML_CONTENT,
        parameter.can_randomize,
        parameter.can_vary_over_time,
        "synthtablerow_buttonlist"
        );

        if (parameter.can_vary_over_time){

            var varname_FROM = varname+"__timevarying_from";
            var SLIDERCELL_HTML_FROM = new_html_buttonlist(varname_FROM,parameter.icons,parameter.default);
            createSynthTableRow(
                varname_FROM,
                "from",
                true,
                SLIDERCELL_HTML_FROM,
                parameter.can_randomize,
                false,
                "synthtablerow_buttonlist timevaryrow"
                );
    
            var varname_TO = varname+"__timevarying_to";
            var SLIDERCELL_HTML_TO = new_html_buttonlist(varname_TO,parameter.icons,parameter.default);
            createSynthTableRow(
                varname_TO,
                "to",
                true,
                SLIDERCELL_HTML_TO,
                parameter.max,
                parameter.min,
                "synthtablerow_buttonlist timevaryrow"
                );
    
            var varname_CURVE = varname+"__timevarying_curve";
            var SLIDERCELL_HTML_CURVE = new_html_buttonlist(varname_CURVE,INTERPOLATION_ICONS,0);
            //INTERPOLATION_ICONS
            createSynthTableRow(
                varname_CURVE,
                "curve",
                true,
                SLIDERCELL_HTML_CURVE,
                parameter.max,
                parameter.min,
                "synthtablerow_buttonlist timevaryrow"
                );
    
            var varname_BIAS = varname+"__timevarying_bias";
            var SLIDERCELL_HTML_BIAS = new_html_slider(varname_BIAS,1,0,parameter.default);
            createSynthTableRow(
                varname_BIAS,
                "bias",
                parameter.group_with_next,
                SLIDERCELL_HTML_BIAS,
                parameter.max,
                parameter.min,
                "synthtablerow_slider timevaryrow"
                );
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