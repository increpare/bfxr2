"use strict";

var tabs = [];

class Tab {
    constructor(synth_specification) {
        var tab_name = synth_specification.name;
        // Store tab name
        this.name = tab_name;

        // Create DOM elements
        var tab_bar = document.getElementById("tab_bar");
        var tab_page_container = document.getElementById("tab_page_manager");

        var first_tab = tab_bar.children.length == 0;

        var tab_button = document.createElement("div");
        tab_button.innerText = tab_name;
        tab_button.id = "tab_button_" + tab_name;
        tab_button.classList.add("tab_button");
        tab_bar.appendChild(tab_button);
        tab_button.addEventListener("click", this.set_active_tab.bind(this));

        var tab_page = document.createElement("div");
        tab_page.classList.add("tab_page");
        tab_page.id = "tab_page_" + tab_name;
        tab_page_container.appendChild(tab_page);

        if (first_tab) {
            tab_button.classList.add("active_tab");
            tab_page.classList.add("active_tab_page");
        }

        var left_panel = document.createElement("div");
        left_panel.classList.add("left_panel");
        tab_page.appendChild(left_panel);

        {
            var preset_list = document.createElement("div");
            preset_list.classList.add("preset_list");
            left_panel.appendChild(preset_list);

            var create_new_sound_div = document.createElement("div");
            create_new_sound_div.classList.add("create_new_sound_div");
            left_panel.appendChild(create_new_sound_div);

            var create_new_sound_container_div = document.createElement("div");
            create_new_sound_container_div.classList.add("padded_item");
            create_new_sound_div.appendChild(create_new_sound_container_div);

            var create_new_sound_checkbox = document.createElement("input");
            create_new_sound_checkbox.type = "checkbox";
            create_new_sound_checkbox.id = tab_name + "_checkbox_create_new_sound";
            create_new_sound_checkbox.classList.add("normie_checkbox");
            create_new_sound_container_div.appendChild(create_new_sound_checkbox);
            create_new_sound_checkbox.addEventListener("click", this.create_new_sound_clicked);

            var create_new_sound_label = document.createElement("label");
            create_new_sound_label.innerText = "Create new sound";
            create_new_sound_label.setAttribute("for", tab_name + "_checkbox_create_new_sound");
            create_new_sound_container_div.appendChild(create_new_sound_label);

            var save_commands_div = document.createElement("div");
            save_commands_div.classList.add("save_commands");
            left_panel.appendChild(save_commands_div);

            var apply_sfx_button = this.add_button("apply_sfx", "Apply Sfx", this.apply_sfx, "Apply the current sound to the current sound");
            save_commands_div.appendChild(apply_sfx_button);

            var revert_sfx_button = this.add_button("revert_sfx", "Revert Sfx", this.revert_sfx, "Revert the current sound to the original sound");
            save_commands_div.appendChild(revert_sfx_button);

            var duplicate_sfx_button = this.add_button("duplicate_sfx", "Duplicate Sfx", this.duplicate_sfx, "Duplicate the current sound");
            save_commands_div.appendChild(duplicate_sfx_button);

            var file_list = document.createElement("div");
            file_list.classList.add("scroll_container");
            file_list.classList.add("filelist");
            left_panel.appendChild(file_list);
        }


        var centre_panel = document.createElement("div");
        centre_panel.classList.add("centre_panel");
        tab_page.appendChild(centre_panel);

        {
            var centre_header = document.createElement("div");
            centre_header.classList.add("centre_header");
            centre_header.style.display = "none";
            centre_panel.appendChild(centre_header);

            this.centre_header = centre_header;

            var header_paramtable = document.createElement("table");
            header_paramtable.classList.add("paramtable");
            centre_header.appendChild(header_paramtable);

            var centre_params = document.createElement("div");
            centre_params.classList.add("centre_params");
            centre_params.classList.add("scroll_container");
            centre_params.style.display = "none";
            centre_panel.appendChild(centre_params);

            this.centre_params = centre_params;

            var main_paramtable = document.createElement("table");
            main_paramtable.classList.add("paramtable");
            centre_params.appendChild(main_paramtable);

        }

        var right_panel = document.createElement("div");
        right_panel.classList.add("right_panel");
        tab_page.appendChild(right_panel);

        {
            var display_canvas_container = document.createElement("div");
            display_canvas_container.classList.add("display_canvas_container");
            right_panel.appendChild(display_canvas_container);

            var display_canvas = document.createElement("canvas");
            display_canvas.classList.add("display_canvas");
            display_canvas.width = "113";
            display_canvas.height = "200";
            display_canvas_container.appendChild(display_canvas);

            var play_on_change_container_div = document.createElement("div");
            right_panel.appendChild(play_on_change_container_div);

            var play_on_change_checkbox = document.createElement("input");
            play_on_change_checkbox.type = "checkbox";
            play_on_change_checkbox.id = tab_name + "_checkbox_loop";
            play_on_change_checkbox.classList.add("normie_checkbox");
            play_on_change_checkbox.addEventListener("click", this.play_on_change_clicked);
            play_on_change_container_div.appendChild(play_on_change_checkbox);

            var play_on_change_label = document.createElement("label");
            play_on_change_label.innerText = "Play on change";
            play_on_change_label.setAttribute("for", tab_name + "_checkbox_loop");
            play_on_change_container_div.appendChild(play_on_change_label);

            var right_panel_button_list = document.createElement("div");
            right_panel_button_list.classList.add("right_panel_button_list");
            right_panel.appendChild(right_panel_button_list);

            var play_button = this.add_button("play", "Play", this.play_button_clicked, "Play the current sound");
            right_panel_button_list.appendChild(play_button);

            var global_vol_container_div = document.createElement("div");
            right_panel_button_list.appendChild(global_vol_container_div);


            this.setup_slider(global_vol_container_div, "slider_global_vol", 0, 1, 1, this.volume_slider_changed, true);

            var global_vol_label = document.createElement("span");
            global_vol_label.innerText = "Sound Volume";
            global_vol_container_div.appendChild(global_vol_label);


            var export_wav_button = this.add_button("export_wav", "Export WAV", this.export_wav_button_clicked, "Export the current sound as a WAV file");
            right_panel_button_list.appendChild(export_wav_button);

            var export_all_button = this.add_button("export_all", "Export All", this.export_all_button_clicked, "Export all sounds as a WAV file");
            right_panel_button_list.appendChild(export_all_button);

            var save_bfxr_button = this.add_button("save_bfxr", "Save .bfxr", this.save_bfxr_button_clicked, "Save the current sound as a .bfxr file");
            right_panel_button_list.appendChild(save_bfxr_button);

            var save_bfxrcol_button = this.add_button("save_bfxrcol", "Save .bcol", this.save_bfxrcol_button_clicked, "Save the current sound as a .bcol file");
            right_panel_button_list.appendChild(save_bfxrcol_button);

            var copy_button = this.add_button("copy", "Copy", this.copy_button_clicked, "Copy the current sound");
            right_panel_button_list.appendChild(copy_button);

            var paste_button = this.add_button("paste", "Paste", this.paste_button_clicked, "Paste the current sound");
            right_panel_button_list.appendChild(paste_button);

            var copy_link_button = this.add_button("copy_link", "Copy Link", this.copy_link_button_clicked, "Copy the current sound link");
            right_panel_button_list.appendChild(copy_link_button);

            var about_button = this.add_button("about", "About", this.about_button_clicked, "About the current sound");
            right_panel_button_list.appendChild(about_button);

        }

        // Storage for parameters
        this.params = {};
        this.presets = [];

        this.preset_list = preset_list;

        tabs.push(this);

        this.load_params(synth_specification);
        this.load_presets(synth_specification);

        this.finalize_elements();
    }

    load_params(synth_specification) {
        for (var i = 0; i < synth_specification.param_info.length; i++) {
            var param = synth_specification.param_info[i];
            this.load_param(param);
        }
    }

    load_param(param) {
        //if object
        if (param.constructor === Array) {
            var display_name = param[0];
            var tooltip = param[1];
            var param_name = param[2];
            var default_value = param[3];
            var min_value = param[4];
            var max_value = param[5];
            var header = param.length > 6 && param[6] === true;
            this.add_slider(param_name, display_name, tooltip, min_value, max_value, default_value, header);
        } else {
            switch (param.type) {
                case "BUTTONSELECT":

                    this.add_button_grid(param.name, param.display_name, param.tooltip, param.columns, param.default_value, param.values, param.header === true ? true : false);
                    break;
                case "KNOB_TRANSITION":
                    this.add_knob_transition(param.name, param.display_name, param.tooltip, param.default_value_l, param.default_value_r, param.min, param.max, param.default_tween, param.header === true ? true : false);
                    break;
                default:
                    console.error("Unknown param type: " + param.type);
            }
        }
    }

    load_presets(synth_specification) {
        for (var i = 0; i < synth_specification.presets.length; i++) {
            let generator = synth_specification.presets[i];
            this.add_generator(generator);
        }
    }

    add_generator(generator) {
        /*button_id,button_text,button_handler,button_tooltip
        */
        var button_text = generator[0];
        var button_tooltip = generator[1];
        var generator_name = generator[2];
        var button_id = this.name + "_generator_" + generator_name;
        var button = this.add_button(button_id, button_text, this.preset_clicked.bind(this, generator_name), button_tooltip);
        this.preset_list.appendChild(button);
    }

    set_active_tab() {
        var tab_page = document.getElementById("tab_page_" + this.name);
        tab_page.classList.add("active_tab");
        var tab_buttons = document.getElementsByClassName("tab_button");
        for (var i = 0; i < tab_buttons.length; i++) {
            var tab_button = tab_buttons[i];
            if (tab_button.id != "tab_button_" + this.name) {
                tab_button.classList.remove("active_tab");
            } else if (!tab_button.classList.contains("active_tab")) {
                tab_button.classList.add("active_tab");
            }
        }
        var tab_pages = document.getElementsByClassName("tab_page");
        for (var i = 0; i < tab_pages.length; i++) {
            var tab_page = tab_pages[i];
            if (tab_page.id != "tab_page_" + this.name) {
                tab_page.classList.remove("active_tab_page");
            } else if (!tab_page.classList.contains("active_tab_page")) {
                tab_page.classList.add("active_tab_page");
            }
        }
    }

    setup_slider(parent_node, slider_id, min, max, defaultval, handler_fn, mini = false) {
        var uid = this.name + "_slider_" + slider_id;
        var global_vol_input = document.createElement("input");
        global_vol_input.type = "text";
        global_vol_input.id = uid;
        parent_node.appendChild(global_vol_input);

        //ticks
        var ticks = [];
        var closest_to_default_i = 0;
        var closest_diff = 100000;
        for (var i = 0; i <= 10; i++) {
            var v = min + (max - min) * i / 10;
            ticks.push(v);
            var diff = Math.abs(v - defaultval);
            if (diff < closest_diff) {
                closest_diff = diff;
                closest_to_default_i = i;
            }
        }

        var slider = new Slider("#" + uid, {
            id: slider_id,
            min: min,
            max: max,
            range: false,
            step: 0.00001,
            value: defaultval,
            ticks: ticks
        });
        slider.sliderElem.className += " singleselect";
        slider.sliderElem.getElementsByClassName("slider-tick-container")[0].children[closest_to_default_i].classList.add('defaulttick');

        if (mini === true) {
            slider.sliderElem.classList.add('slidernarrow');
        }

        slider.on("slideStop", handler_fn);
    }

    add_button(button_id, button_text, button_handler, button_tooltip) {
        var button = document.createElement("button");
        button.classList.add("normie_button");
        button.id = button_id;
        if (button_tooltip != undefined && button_tooltip != "") {
            var tooltip_tag = `<span class="data-tooltip">${button_tooltip}</span>`;
            button_text = tooltip_tag + button_text;
        }
        button.innerHTML = button_text;
        button.addEventListener("click", button_handler);
        return button;
    }

    create_param_label(label, tooltip) {
        var parameter_name_span = document.createElement("span");
        parameter_name_span.classList.add("parameter_name");
        parameter_name_span.innerHTML = `<span class="data-tooltip">${tooltip}</span>${label}`;
        return parameter_name_span;
    }

    add_knob_transition(
        parameter_name,
        display_name,
        tooltip,
        default_value_l,
        default_value_r,
        min,
        max,
        default_tween,
        header = false
    ) {
        /* should look something like this:
            <td class="slider_container">
                <input type="range" class="input-knob" data-width="32" data-height="32" data-bgcolor="#b7a480" data-fgcolor="#3c3831"/>	
                <input type="range" class="input-knob" data-width="32" data-height="32" data-bgcolor="#c7b490" data-fgcolor="#3c3831" />	
            </td>
        */
        var parent_container = header ? this.centre_header : this.centre_params;
        parent_container.style.display = "block";

        var table = parent_container.children[0];

        var new_row = table.insertRow();

        var lock_cell = new_row.insertCell();
        lock_cell.classList.add("lockcolumn");
        var lock_button = this.generate_lock_button(parameter_name);
        lock_cell.appendChild(lock_button);

        var rowspan = 1;
        if (display_name !== "") {
            var label_cell = new_row.insertCell();
            label_cell.classList.add("labelcolumn");
            var label = this.create_param_label(display_name, tooltip);
            label_cell.appendChild(label);
        } else {
            rowspan = 2;
        }

        var parameter_cell = new_row.insertCell();
        parameter_cell.classList.add("transition_container");

        var knob_l = this.new_knob(parameter_name + "_l", default_value_l, min, max, 0.01);
        parameter_cell.appendChild(knob_l);

        var dropdown_uid = this.name + "_dropdown_content_" + parameter_name;


        var default_tween_img = Transfxr.tweenfunctions[0][2];
        var tween_container = document.createElement("img");
        tween_container.src = default_tween_img.src;
        tween_container.classList.add("tween_select_canvas");
        tween_container.classList.add("dropdown");
        tween_container.id = parameter_name + "_tween_select_canvas";
        parameter_cell.appendChild(tween_container);
        tween_container.addEventListener("click", () => {
            document.getElementById(dropdown_uid).classList.toggle("show");
        });

        /*add dropdown for tween selection
     looks like:
  
     <div class="dropdown">
      <button onclick="myFunction()" class="dropbtn">Dropdown</button>
          <div id="myDropdown" class="dropdown-content">
              <a href="#">Link 1</a>
              <a href="#">Link 2</a>
              <a href="#">Link 3</a>
          </div>
      </div>
      */

        var dropdown_content_div = document.createElement("div");
        dropdown_content_div.classList.add("dropdown-content");
        dropdown_content_div.id = dropdown_uid;
        parameter_cell.appendChild(dropdown_content_div);

        for (var i = 0; i < Transfxr.tweenfunctions.length; i++) {
            var tween_img = Transfxr.tweenfunctions[i][2];
            var tween_button = document.createElement("img");
            tween_button.src = tween_img.src;
            tween_button.classList.add("tween_select_canvas");
            dropdown_content_div.appendChild(tween_button);
        }

        var knob_r = this.new_knob(parameter_name + "_r", default_value_r, min, max, 0.01);
        parameter_cell.appendChild(knob_r);
    }

    new_knob(id, default_value, min, max, step) {
        var knob = document.createElement("input");
        var uid = this.name + "_knob_" + id;
        knob.id = uid;
        knob.type = "range";
        knob.classList.add("input-knob");
        knob.dataset.width = "32";
        knob.dataset.height = "32";
        knob.dataset.bgcolor = "#b7a480";
        knob.dataset.fgcolor = "#3c3831";
        knob.value = default_value;
        knob.min = min;
        knob.max = max;
        knob.step = step;
        knob.addEventListener("input", () => {
            this.knob_transition_changed(parameter_name, knob_l.value, knob_r.value);
        });
        return knob;
    }

    add_button_grid(
        parameter_name,
        display_name,
        tooltip,
        column_count,
        default_value,
        button_list,
        header = false) {
        var parent_container = header ? this.centre_header : this.centre_params;
        parent_container.style.display = "block";

        var table = parent_container.children[0];

        var new_row = table.insertRow();

        var lock_cell = new_row.insertCell();
        lock_cell.classList.add("lockcolumn");
        var lock_button = this.generate_lock_button(parameter_name);
        lock_cell.appendChild(lock_button);

        var rowspan = 1;
        if (display_name !== "") {
            var label_cell = new_row.insertCell();
            label_cell.classList.add("labelcolumn");
            var label = this.create_param_label(display_name, tooltip);
            label_cell.appendChild(label);
        } else {
            rowspan = 2;
        }

        var parameter_cell = new_row.insertCell();
        parameter_cell.rowSpan = rowspan;
        var button_grid = document.createElement("div");
        button_grid.classList.add("button_grid_" + column_count + "c");
        parameter_cell.appendChild(button_grid);

        for (let i = 0; i < button_list.length; i++) {
            var button = document.createElement("button");
            button.classList.add("button_grid_button");
            button.id = button_list[i][0];
            button.innerText = button_list[i][0];
            button.addEventListener("click", () => {
                this.button_grid_button_clicked(button, parameter_name, i);
            });
            button_grid.appendChild(button);
        }
    }

    //add_slider("attack_time",0,1,0,"Attack Time","Length of the volume envelope attack.");
    add_slider(
        parameter_name,
        display_name,
        tooltip,
        min,
        max,
        default_value,
        header = false
    ) {
        var uid = this.name + "_slider_" + parameter_name;

        var parent_container = header ? this.centre_header : this.centre_params;
        parent_container.style.display = "block";

        var table = parent_container.children[0];

        var new_row = table.insertRow();

        var lock_cell = new_row.insertCell();
        lock_cell.classList.add("lockcolumn");
        var lock_button = this.generate_lock_button(parameter_name);
        lock_cell.appendChild(lock_button);

        var rowspan = 1;
        if (display_name !== "") {
            var label_cell = new_row.insertCell();
            label_cell.classList.add("labelcolumn");
            var label = this.create_param_label(display_name, tooltip);
            label_cell.appendChild(label);
        } else {
            rowspan = 2;
        }

        var parameter_cell = new_row.insertCell();
        parameter_cell.classList.add("slider_container");
        parameter_cell.rowSpan = rowspan;

        this.setup_slider(parameter_cell, uid, min, max, default_value, this.slider_changed.bind(this, parameter_name));

    }

    generate_lock_button(parameter_name) {
        var lock_button = document.createElement("div");
        lock_button.classList.add("lockimage");
        lock_button.addEventListener("click", () => {
            //unlocked if class unlocked is present
            var val = lock_button.classList.contains("unlocked") ? true : false;
            this.lock_param_clicked(lock_button, parameter_name, val)
        });
        return lock_button;
    }

    add_preset(preset_name, button_tooltip, param_fn) {
        var button = this.add_button(preset_name, preset_name, param_fn, button_tooltip);
        this.preset_list.appendChild(button);
    }

    finalize_elements() {
        this.add_preset("Randomize", "Talking your life into your hands... (only modifies unlocked parameters)", this.randomize_params,);
        this.add_preset("Mutation", "Modify each unlocked parameter by a small wee amount... (only modifies unlocked parameters)", this.mutate_params,);
    }




    preset_clicked(preset_name) {
        console.log("Preset clicked: " + preset_name);
    }

    create_new_sound_clicked() {
        console.log("Create new sound clicked");
    }

    play_on_change_clicked() {
        console.log("Play on change clicked");
    }

    play_button_clicked() {
        console.log("Play button clicked");
    }

    slider_changed(param_name, value) {
        console.log("Slider changed " + param_name + " to " + value);
    }

    volume_slider_changed(value) {
        console.log("Volume slider changed to " + value);
    }

    export_wav_button_clicked() {
        console.log("Export wav button clicked");
    }

    export_all_button_clicked() {
        console.log("Export all button clicked");
    }

    save_bfxr_button_clicked() {
        console.log("Save bfxr button clicked");
    }

    save_bfxrcol_button_clicked() {
        console.log("Save bfxrcol button clicked");
    }

    copy_button_clicked() {
        console.log("Copy button clicked");
    }

    paste_button_clicked() {
        console.log("Paste button clicked");
    }

    copy_link_button_clicked() {
        console.log("Copy link button clicked");
    }

    about_button_clicked() {
        console.log("About button clicked");
    }

    preset_clicked(generator_name) {
        console.log("Preset clicked: " + generator_name);
    }

    randomize_params() {
        console.log("Randomize params");
    }

    mutate_params() {
        console.log("Mutate params");
    }

    apply_sfx() {
        console.log("Apply sfx");
    }

    revert_sfx() {
        console.log("Revert sfx");
    }

    duplicate_sfx() {
        console.log("Duplicate sfx");
    }

    lock_param_clicked(node, param_name, value) {
        console.log("Lock param " + param_name + " clickedwith value " + value);
        value = !value;
        if (value) {
            node.classList.add("unlocked");
        } else {
            node.classList.remove("unlocked");
        }
    }

    button_grid_button_clicked(node, param_name, value) {
        console.log("Button grid button clicked for " + param_name + " with value " + value);
    }
}