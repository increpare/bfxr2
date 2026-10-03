"use strict";

var tabs = [];

class Tab {


    /* all the variables that determine the tab's state */
    active = false;
    create_new_sound = true;
    play_on_change = true;
    selected_file_index = -1;
    current_params = {};
    files = [
        //[name, current_state, last_saved_state]
    ];

    /* keeping track of frequently used dom elements */
    sliders = {};
    lock_buttons = {};
    transition_controls = {};
    text_controls = {};

    synth = null;

    constructor(synth_specification) {

        //add a passive onkeydown listener
        document.addEventListener("keydown", this.on_key_down.bind(this), false);

        this.synth = synth_specification;

        var tab_name = synth_specification.name;
        // Store tab name
        this.name = tab_name;

        // restore saved state
        var saved_info = SaveLoad.loaded_data[synth_specification.name];
        if (saved_info){
            this.files = saved_info.files;
            this.selected_file_index = saved_info.selected_file_index;
            if (this.selected_file_index >= 0){
                this.synth.apply_params(JSON.parse(this.files[this.selected_file_index][1]));
            }
            if (saved_info.create_new_sound !== undefined){
                this.create_new_sound = saved_info.create_new_sound;
            }
            if (saved_info.play_on_change !== undefined){
                this.play_on_change = saved_info.play_on_change;
            }
            if (saved_info.locked_params !== undefined){
                this.synth.locked_params = {...this.synth.locked_params,...saved_info.locked_params};
            }
        }        

        // Create DOM elements
        var tab_bar = document.getElementById("tab_bar");
        var tab_page_container = document.getElementById("tab_page_manager");

        var first_tab = tab_bar.children.length == 0;

        var tab_button = document.createElement("div");
        tab_button.innerText = synth_specification.display_name || tab_name;
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
            this.active = true;
        }

        var left_panel = document.createElement("div");
        left_panel.classList.add("left_panel");
        tab_page.appendChild(left_panel);

        {
            var template_list = document.createElement("div");
            template_list.classList.add("template_list");
            left_panel.appendChild(template_list);

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
            create_new_sound_checkbox.checked = this.create_new_sound;            
            create_new_sound_checkbox.addEventListener("click", this.create_new_sound_clicked.bind(this));

            var create_new_sound_label = document.createElement("label");
            create_new_sound_label.innerText = "Create new sound";
            create_new_sound_label.setAttribute("for", tab_name + "_checkbox_create_new_sound");
            create_new_sound_container_div.appendChild(create_new_sound_label);

            var save_commands_div = document.createElement("div");
            save_commands_div.classList.add("save_commands");
            left_panel.appendChild(save_commands_div);

            var apply_sfx_button = this.add_button(this.name+"_apply_sfx", "Apply Sfx", this.apply_sfx.bind(this), "Apply the current sound to the current sound to the clipboard.");
            save_commands_div.appendChild(apply_sfx_button);

            var revert_sfx_button = this.add_button(this.name+"_revert_sfx", "Revert Sfx", this.revert_sfx.bind(this), "Revert the current sound to the original sound to the clipboard.");
            save_commands_div.appendChild(revert_sfx_button);

            var duplicate_sfx_button = this.add_button(this.name+"_duplicate_sfx", "Duplicate Sfx", this.duplicate_sfx.bind(this), "Duplicate the currently-selected sound in the file list.");
            save_commands_div.appendChild(duplicate_sfx_button);

            var file_list = document.createElement("div");
            file_list.classList.add("scroll_container");
            file_list.classList.add("filelist");
            file_list.id = this.name + "_file_list";
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
            display_canvas_container.dataset.synth = this.synth.display_name || this.name;
            if (this.synth.canvas_bg_logo) {
                display_canvas_container.classList.add("has_logo");
                display_canvas_container.style.backgroundImage = `url(${this.synth.canvas_bg_logo})`;
            }
            right_panel.appendChild(display_canvas_container);

            var display_canvas = document.createElement("canvas");
            display_canvas.classList.add("display_canvas");
            display_canvas.width = "113";
            display_canvas.height = "200";
            display_canvas_container.appendChild(display_canvas);
            display_canvas.id = this.name + "_waveform_canvas";

            var play_on_change_container_div = document.createElement("div");
            right_panel.appendChild(play_on_change_container_div);

            var play_on_change_checkbox = document.createElement("input");
            play_on_change_checkbox.type = "checkbox";
            play_on_change_checkbox.id = tab_name + "_checkbox_loop";
            play_on_change_checkbox.classList.add("normie_checkbox");
            play_on_change_checkbox.checked = this.play_on_change;
            play_on_change_checkbox.addEventListener("click", this.play_on_change_clicked.bind(this));
            play_on_change_checkbox.title = "Whether the sound should play whenever a parameter is changed.";
            play_on_change_container_div.appendChild(play_on_change_checkbox);

            var play_on_change_label = document.createElement("label");
            play_on_change_label.innerText = "Play on change";
            play_on_change_label.setAttribute("for", tab_name + "_checkbox_loop");
            play_on_change_label.title = play_on_change_checkbox.title;
            play_on_change_container_div.appendChild(play_on_change_label);

            var right_panel_button_list = document.createElement("div");
            right_panel_button_list.classList.add("right_panel_button_list");
            right_panel.appendChild(right_panel_button_list);

            var play_button = this.add_button("play", "Play", this.play_button_clicked.bind(this), "Play the current sound");
            right_panel_button_list.appendChild(play_button);
            if (this.synth.loop_preview) {
                play_button.textContent = "Play loop";
                const stop_button = this.add_button(this.name + "_stop", "Stop", () => {
                    if (this.synth.sound) this.synth.sound.stop();
                }, "Stop the looping preview. Export WAV saves one seamless cycle.");
                right_panel_button_list.appendChild(stop_button);
            }

            var master_volume_container_div = document.createElement("div");
            right_panel_button_list.appendChild(master_volume_container_div);


            var master_vol_min = this.synth.param_min("masterVolume");
            var master_vol_max = this.synth.param_max("masterVolume");
            var master_vol_default = this.synth.param_default("masterVolume");
            var volume_tooltip = "Adjust the volume of the currently selected sound.";
            this.setup_slider(master_volume_container_div, "masterVolume", master_vol_min, master_vol_max, master_vol_default, this.volume_slider_changed.bind(this), volume_tooltip,true);

            var master_volume_label = document.createElement("span");
            master_volume_label.innerText = "Sound Volume";
            master_volume_label.title = volume_tooltip;
            master_volume_container_div.appendChild(master_volume_label);


            var export_wav_button = this.add_button("export_wav", "<u>E</u>xport WAV", this.export_wav_button_clicked.bind(this), "Export the current sound as a WAV file. [CTRL+E]");
            right_panel_button_list.appendChild(export_wav_button);

            var export_all_button = this.add_button("export_all", "Export All", this.export_all_button_clicked.bind(this), "Generate all sounds as WAV files and download them as a single zip file.");
            right_panel_button_list.appendChild(export_all_button);

            var save_bfxr_button = this.add_button("save_bfxr", "<u>S</u>ave .bfxr", this.save_bfxr_button_clicked.bind(this), "Save the current sound as a .bfxr file. [CTRL+S]");
            right_panel_button_list.appendChild(save_bfxr_button);

            var save_bfxrcol_button = this.add_button("save_bfxrcol", "Save .bcol", this.save_bfxrcol_button_clicked.bind(this), "Save the collection of all sounds in all tabs as a .bcol file.");
            right_panel_button_list.appendChild(save_bfxrcol_button);

            var open_data_button = this.add_button("open_data", "<u>O</u>pen Data", this.open_data_button_clicked.bind(this), "Load the current sound from a .bfxr/.bcol file on your computer. [CTRL+O]");
            right_panel_button_list.appendChild(open_data_button);

            var copy_button = this.add_button("copy", "<u>C</u>opy", this.copy_button_clicked.bind(this), "Copy the current sound [CTRL+C]");
            right_panel_button_list.appendChild(copy_button);

            var paste_button = this.add_button("paste", "Paste", this.paste_button_clicked.bind(this), "Paste the current sound [CTRL+V]");
            right_panel_button_list.appendChild(paste_button);

            if (this.name !== 'Mixr' && this.name !== 'Stackr' && typeof Mixr !== 'undefined') {
                this.stack_button = this.add_button(this.name+'_mix_sound','Mix this sound',
                    this.mix_sound.bind(this),'Copy this sound into Mixr.');
                right_panel_button_list.appendChild(this.stack_button);
            }

            var copy_link_button = this.add_button("copy_link", "Copy Link", this.copy_link_button_clicked.bind(this), "Copy the current sound link");
            right_panel_button_list.appendChild(copy_link_button);

            var clear_all_button = this.add_button("clear_all", "Clear All", this.clear_all_button_clicked.bind(this), "Reset everything! Clean slate!");
            right_panel_button_list.appendChild(clear_all_button);

            var about_button = this.add_button("about", "About", this.about_button_clicked.bind(this), "About the current sound");
            right_panel_button_list.appendChild(about_button);

        }


        this.template_list = template_list;

        tabs.push(this);

        this.load_params(synth_specification);
        this.load_templates(synth_specification);

        if (this.synth.create_editor) {
            const editor_container = document.createElement("div");
            editor_container.className = "special_editor_container";
            this.centre_header.appendChild(editor_container);
            this.centre_header.style.display = "block";
            this.custom_editor = this.synth.create_editor(this, editor_container);
        }

        // Prepare every tab without starting several sounds (or a weather loop) on load.
        const initial_play_on_change = this.play_on_change;
        this.play_on_change = false;
        if (this.files.length == 0){
            this.create_random_template();
        } else {
            this.update_ui();
            if (this.selected_file_index >= 0) {
                this.synth.generate_sound();
                this.redraw_waveform();
            }
        }
        this.play_on_change = initial_play_on_change;
        this.update_ui();
    }

    /*********************/
    /*      UI           */
    /*********************/

    toggle_all_locks() {
        //sets *all* parameters to locked or unlocked. use the first lock button to determine the state
        var lock_names = Object.keys(this.lock_buttons);
        var first_locked = this.synth.locked_param(lock_names[0]);
        var target_locked_state = !first_locked;
        for (let param_name in this.synth.locked_params){
            this.synth.set_locked_param(param_name,target_locked_state);
        }
        //set all permalocked params to the target locked state
        for (let param_name in this.synth.permalocked){
            this.synth.set_locked_param(param_name,true);
        }
        this.update_locks();
        if (this.custom_editor) this.custom_editor.update();
        SaveLoad.save_all_collections();
    }

    update_ui(){
        document.getElementById(this.name + "_checkbox_create_new_sound").checked = this.create_new_sound;
        document.getElementById(this.name + "_checkbox_loop").checked = this.play_on_change;
        this.update_ui_file_list();
        this.update_ui_params();
        this.update_ablements();
        this.update_locks();
    }

    update_stack_button(){
        if (this.stack_button) {
            const mix=tabs.find(tab=>tab.name==='Mixr');
            if(mix){this.stack_button.disabled=false;this.stack_button.title='Copy this sound into Mixr.';return;}
            const stack=tabs.find(tab=>tab.name==='Stackr');
            this.stack_button.disabled=!!stack && stack.synth.get_layers().length>=6;
            this.stack_button.title=this.stack_button.disabled ? 'Stack full. Open Stackr and start a new stack or remove a layer.'
                : 'Copy this sound into the current stack and open it.';
        }
    }

    update_ablements(){
        this.update_stack_button();
        if (this.selected_file_index===-1){
            return;
        }
        var is_current_file_modified = this.files[this.selected_file_index][1] != this.files[this.selected_file_index][2];

        var apply_sfx_button = document.getElementById(this.name+"_apply_sfx");
        apply_sfx_button.disabled = !is_current_file_modified;
        var revert_sfx_button = document.getElementById(this.name+"_revert_sfx");
        revert_sfx_button.disabled = !is_current_file_modified;

        //go through file list and set modified_filename
        for (var i = 0; i < this.files.length; i++) {
            var file = this.files[i];
            var file_name = file[0];
            var file_current_state = file[1];
            var file_last_saved_state = file[2];
            var file_item = document.getElementById(this.name + "_file_list").children[i];
            var file_name_span = file_item.children[0];
            var modified = file_current_state != file_last_saved_state;
            if (modified){
                file_name_span.classList.add("modified_filename");
            } else {
                file_name_span.classList.remove("modified_filename");
            }
        }
        
        //for every parameter, check if it is disabled
        for (var i = 0; i < this.synth.param_info.length; i++) {
            var param = this.synth.param_info[i];
            if (param.constructor === Array){
                var param_name = param[2];
                var param_disabled = this.synth.param_is_disabled(param_name);
                var slider = this.sliders[param_name];
                if (!slider) continue;
                if (param_disabled){
                    slider.disable();
                } else {
                    slider.enable();
                }
            } else {
                //not supported yet - this code is just for the square duty stuff right now.
            }   
        }
    }

    update_ui_file_list(){
        var file_list = document.getElementById(this.name + "_file_list");
        //get scroll
        var scroll_y = file_list.scrollTop;
        //clear
        file_list.innerHTML = "";
        //add new
        var selected_item=null;
        for (var i = 0; i < this.files.length; i++) {
            var file = this.files[i];
            var selected = i == this.selected_file_index;
            var file_item = this.create_file_entry(file,selected);
            file_list.appendChild(file_item);
            if (selected){
                selected_item = file_item;
            }
        }
        file_list.scrollTop = scroll_y;
        
        if (selected_item){
            setVisible(selected_item, file_list);
        }
    }

    update_ui_params(){
        //for each parameter
        for (var i = 0; i < this.synth.param_info.length; i++) {
            var param = this.synth.param_info[i];
            if (param.constructor === Array){
                var value = this.synth.params[param[2]];
                var param_name = param[2];
                //it's a slider
                var slider = this.sliders[param_name];
                if (slider) {
                    slider.setValue(value);
                }
            } else {
                switch (param.type) {
                    case "TEXT":
                        if (this.text_controls[param.name]) this.text_controls[param.name].update();
                        break;
                    case "BUTTONSELECT":
                        var value = this.synth.params[param.name];
                        var index=-1;
                        //need to find the index of the selected button with this value 
                        for (var j = 0; j < param.values.length; j++) {
                            if (param.values[j][2] === value) {
                                index = j;
                                break;
                            }
                        }
                        var button_grid = document.getElementById(this.name + "_button_grid_" + param.name);
                        if (!button_grid) break;
                        for (var j = 0; j < button_grid.children.length; j++) {
                            var child = button_grid.children[j];
                            child.disabled = false;
                            if (child.classList.contains("selected")){
                                child.classList.remove("selected");
                            }
                        }
                        if(index>=0){
                            button_grid.children[index].classList.add("selected");
                            button_grid.children[index].disabled = true;
                        }
                        break;
                    case "KNOB_TRANSITION":
                        this.update_transition_control(param.name);
                        break;  
                    default:
                        console.error("Unknown param type: " + param.type); 
                }
            }
        }
        this.update_param_visibility();
        if (this.custom_editor) this.custom_editor.update();
    }
    
    update_locks(){
        //for each lock-button
        var keys = Object.keys(this.lock_buttons);
        for (var i = 0; i < keys.length; i++){
            var key = keys[i];  
            var lock_button = this.lock_buttons[key];
            var locked = this.synth.locked_params[key];
            if (locked){
                lock_button.classList.remove("unlocked");
            } else {
                lock_button.classList.add("unlocked");
            }
        }
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

        for (var i = 0; i < tabs.length; i++){
            var tab = tabs[i];
            if (tab.active && tab !== this && tab.synth.loop_preview && tab.synth.sound) tab.synth.sound.stop();
            tab.active = tab.name == this.name;
        }
        this.update_stack_button();
        if (this.custom_editor) this.custom_editor.update();
    }
    
    load_params(synth_specification) {
        for (var i = 0; i < synth_specification.param_info.length; i++) {
            var param = synth_specification.param_info[i];

            //regularize info
            var param_normalized = synth_specification.get_param_normalized(param);
            
            if (!(param_normalized.name in synth_specification.locked_params)){
                var do_lock = synth_specification.permalocked.includes(param_normalized.name);
                this.synth.set_locked_param(param_normalized.name,do_lock);
            }

            if (synth_specification.hide_params.includes(param_normalized.name)){
                continue;
            }
            
            this.load_param(param);
        }
        this.update_ui();
    }

    load_param(param) {
        var param_name;
        //if object
        if (param.constructor === Array) {
            var display_name = param[0];
            var tooltip = param[1];
            param_name = param[2];
            var default_value = param[3];
            var min_value = param[4];
            var max_value = param[5];
            var header = param.length > 6 && param[6] === true;
            this.add_slider(param_name, display_name, tooltip, min_value, max_value, default_value, header);
        } else {            
            switch (param.type) {
                case "TEXT":
                    this.text_controls[param.name] = new SpeechEditor(this, param, this.centre_header);
                    this.centre_header.style.display = "block";
                    break;
                case "BUTTONSELECT":
                    this.add_button_grid(param.name, param.display_name, param.tooltip, param.columns, param.default_value, param.values, param.header === true ? true : false);
                    param_name = param.name;
                    break;
                case "KNOB_TRANSITION":
                    this.add_knob_transition(param.name, param.display_name, param.tooltip, param.default_value_l, param.default_value_r, param.min, param.max, param.default_tween, param.header === true ? true : false);
                    param_name = param.name;
                    break;
                default:
                    console.error("Unknown param type: " + param.type);
            }
        }        
    }


    setup_slider(parent_node, slider_id, min, max, defaultval, handler_fn, tooltip, mini = false) {
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
            step: 0.01,
            value: defaultval,
            ticks: ticks,
            formatter: (val)=>{
                return val.toFixed(2);
            },
            ticks_snap_bounds: 0.005,
            natural_arrow_keys:true
        });
        slider.sliderElem.title = tooltip;
        slider.sliderElem.className += " singleselect";
        slider.sliderElem.getElementsByClassName("slider-tick-container")[0].children[closest_to_default_i].classList.add('defaulttick');
        
        if (mini === true) {
            slider.sliderElem.classList.add('slidernarrow');
        }

        slider.on("slideStop", handler_fn);
        // A visual preview while dragging; audio and saved parameters commit on release.
        slider.on("slide", value => {
            for (const editor of Object.values(this.text_controls || {})) {
                if (editor.preview_params) editor.preview_params({...this.synth.params, [slider_id]:value});
            }
        });

        this.sliders[slider_id] = slider;        
    }

    add_button(button_uid, button_text, button_handler, button_tooltip) {
        var button = document.createElement("button");
        button.classList.add("normie_button");
        button.id = button_uid;
        if (button_tooltip != undefined && button_tooltip != "") {
            button.title = button_tooltip;
        }
        button.innerHTML = button_text;
        button.addEventListener("click", button_handler);
        return button;
    }

    create_param_label(label, tooltip) {
        var parameter_name_span = document.createElement("span");
        parameter_name_span.classList.add("parameter_name");
        if (tooltip != undefined && tooltip != "") {
            parameter_name_span.title = tooltip;
        }
        parameter_name_span.innerText = label;
        return parameter_name_span;
    }

    add_knob_transition(parameter_name, display_name, tooltip, start, end, min, max, curve, header = false) {
        const parent = header ? this.centre_header : this.centre_params;
        parent.style.display = "block";
        const table = parent.children[0];
        if (!Object.keys(this.transition_controls).length) {
            const hint = document.createElement("p");
            hint.className = "transition_hint";
            hint.textContent = "Drag A / B to set the endpoints. Drag the middle to move both. Triangle and Pulse return to A.";
            parent.appendChild(hint);
        }
        const row = table.insertRow();
        row.className = "transition_row";
        const lock = row.insertCell();
        lock.className = "lockcolumn";
        lock.appendChild(this.generate_lock_button(parameter_name));
        const cell = row.insertCell();
        cell.colSpan = 2;
        cell.className = "transition_container";
        this.transition_controls[parameter_name] = new TransitionEditor(this, this.synth.get_param_info(parameter_name), cell);
    }

    update_transition_control(name) {
        this.transition_controls[name].update();
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
        var uid = this.name + "_button_grid_" + parameter_name;
        button_grid.id = uid;
        parameter_cell.appendChild(button_grid);

        for (let i = 0; i < button_list.length; i++) {
            var button = document.createElement("button");
            button.classList.add("button_grid_button");
            button.id = uid+"_"+button_list[i][0];
            button.innerText = button_list[i][0];
            var thumbnail = button_list[i][1];
            button.title = thumbnail;
            var click_value = button_list[i][2];
            button.addEventListener("click", this.button_grid_button_clicked.bind(this, button, parameter_name, i,click_value));
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

        this.setup_slider(parameter_cell, parameter_name, min, max, default_value, this.slider_changed.bind(this, parameter_name),tooltip);

    }

    generate_lock_button(parameter_name) {
        var lock_button = document.createElement("div");
        lock_button.classList.add("lockimage");
        lock_button.title = "Lock/unlock parameter.  This prevents it from being changed when you hit Randomize/Mutate.  Press L to toggle lock on *all* parameters.";
        if (!this.synth.locked_params[parameter_name]){
            lock_button.classList.add("unlocked");
        }
        lock_button.addEventListener("click", () => {
            //unlocked if class unlocked is present
            var val = lock_button.classList.contains("unlocked") ? true : false;
            this.lock_param_clicked(lock_button, parameter_name, val)
        });
        //add param-name as data attribute
        this.lock_buttons[parameter_name] = lock_button;
        return lock_button;
    }
    

    /*********************/
    /*      WIDGETS      */
    /*********************/


    

    /*********************/
    /*      FILES        */
    /*********************/

    find_unique_filename(desired_name,ignore_index=-1){
        var new_name = desired_name.replace(/[^a-zA-Z0-9_-]/g, "");

        if (new_name.length == 0){
            new_name = "Sfx";
        }

        var file_name_already_exists = false;
        for (var i = 0; i < this.files.length; i++) {
            if (i===ignore_index){
                continue;
            }
            if (this.files[i][0] == new_name) {
                file_name_already_exists = true;
                break;
            }
        }

        if (file_name_already_exists){
            //strip all digits from end of name FROM THE RIGHT
            while (new_name.length>0 && !isNaN(new_name[new_name.length-1])){
                new_name = new_name.slice(0, -1);
            }
                
            if (new_name.length == 0){
                new_name = "Sfx";
            }
            
            var suffix = -1;
            var found=true
            var test_name;
            while(found){
                found=false;
                suffix++;
                test_name = new_name;
                if (suffix !== 0) {
                    test_name = new_name+suffix;
                }
                for (var i = 0; i < this.files.length; i++) {
                    if (i == ignore_index) {
                        continue;
                    }
                    if (this.files[i][0].toLowerCase() == test_name.toLowerCase()) {
                        found = true;
                        break;
                    }
                }
            }
            new_name = test_name;
        } 
        return new_name;
    }

    delete_file(file_name){
        var deleted_file_index = -1;
        for (var i = 0; i < this.files.length; i++) {
            if (this.files[i][0] == file_name) {
                deleted_file_index = i;
                this.files.splice(i, 1);
                break;
            }
        }
        if (this.selected_file_index >= deleted_file_index){
            this.selected_file_index--;
            if (this.selected_file_index < 0 && this.files.length > 0){
                this.selected_file_index = 0;
                this.set_selected_file(this.files[0][0]);
            }
            if (this.selected_file_index>=0){
                var file_dat = this.files[this.selected_file_index];
                this.synth.apply_params(JSON.parse(file_dat[1]));
                this.synth.generate_sound();
                this.redraw_waveform();
                if (this.play_on_change){
                    this.play_sound();
                }
            }
        }
        this.update_ui();
        SaveLoad.save_all_collections();
    }

    get_current_file_name(){
        if (this.selected_file_index===-1){
            return null;
        }
        return this.files[this.selected_file_index][0];
    }

    //returns true if the selected file was changed, false if it was already selected
    set_selected_file(file_name) {
        for (var i = 0; i < this.files.length; i++) {
            if (this.files[i][0] == file_name) {
                if (this.selected_file_index===i){
                    return false;
                }
                this.selected_file_index = i;
                break;
            }
        }
        
        var file_list = document.getElementById(this.name + "_file_list");
        for (var i = 0; i < file_list.children.length; i++) {
            var file_item = file_list.children[i];
            file_item.classList.remove("file_selected");
            let file_name_span = file_item.children[0]; 
            file_name_span.contentEditable = false;
        }
        var file_item = file_list.children[this.selected_file_index];
        file_item.classList.add("file_selected");
        let file_name_span = file_item.children[0];
        file_name_span.contentEditable = true;
        file_name_span.focus();

        //update the current params
        var params = JSON.parse(this.files[this.selected_file_index][1]);
        this.synth.apply_params(params);

        this.update_ui_params();
        this.update_ablements();
        return true;
    }

    
    create_file_entry(file_dat,selected){
        var modified = file_dat[1] !== file_dat[2];
        var file_name = file_dat[0];
        var display_name = file_name;
        var file_item = document.createElement("div");
        file_item.classList.add("file_item");
        if (selected){
            file_item.classList.add("file_selected");
        }
        var file_name_span = document.createElement("span");
        file_name_span.classList.add("file_item_name");
        file_name_span.innerText = display_name;
        if (modified){
            file_name_span.classList.add("modified_filename");
        }
        if (selected){
            file_name_span.contentEditable = true;
        }        
        file_name_span.addEventListener("blur", (event) => {
            if (file_name_span.innerText !== file_name){
                file_name = this.file_item_renamed(file_name,file_name_span.innerText);
                file_name_span.innerText = file_name;
            }
        });
        file_item.appendChild(file_name_span);
        file_name_span.addEventListener("click", (event) => {
            this.file_item_click(file_name,event.target);
        });
        
        var delete_button = document.createElement("button");
        delete_button.classList.add("delete_button");
        delete_button.innerHTML = "<img src='./img/delete.png' alt='Delete'>";
        delete_button.addEventListener("click", (event) => {
            this.delete_file(file_name);
        });
        file_item.appendChild(delete_button);
        return file_item;
    }

    /*********************/
    /*      TEMPLATES      */
    /*********************/

    load_templates(synth_specification) {
        for (var i = 0; i < synth_specification.templates.length; i++) {
            let generator = synth_specification.templates[i];
            this.add_generator(generator);
        }
    }

    create_random_template() {
        var [template_name, params] = this.synth.create_random_template();
        this.create_new_sound_from_params(template_name, params);
    }

    create_new_sound_from_params(template_name, params,forcecreate=false) {
        this.synth.apply_params(params);
        if (this.create_new_sound||this.files.length == 0||this.selected_file_index===-1||forcecreate) {
            this.current_params = params;
            var filename = this.find_unique_filename(template_name);        
            this.files.push([filename,JSON.stringify(params), JSON.stringify(params)]);
            this.selected_file_index = this.files.length - 1;
        } else {
            this.current_params = params;
            this.files[this.selected_file_index][1] = JSON.stringify(params);
        }
        if (this.play_on_change){
            this.play_sound();
        } else {
            this.synth.generate_sound();
            this.redraw_waveform();
        }
        this.update_ui();
        SaveLoad.save_all_collections();
    }

    add_generator(generator) {
        /*button_id,button_text,button_handler,button_tooltip
        */
        var button_text = generator[0];
        var button_tooltip = generator[1];
        var generator_name = generator[2];
        var button_uid = this.name + "_generator_" + generator_name;
        var button = this.add_button(button_uid, button_text, this.template_clicked.bind(this, generator_name), button_tooltip);
        this.template_list.appendChild(button);
    }

    /*********************/
    /* STATE MANAGEMENT  */
    /*********************/


    add_template(template_name, button_tooltip, param_fn) {
        var uid = this.name + "_template_" + template_name;
        var button = this.add_button(uid, template_name, param_fn, button_tooltip);
        this.template_list.appendChild(button);
    }

    serialize_params(){
        var file_dat = this.files[this.selected_file_index];
        var file_name = file_dat[0];
        var file_jstor = file_dat[1];
        var file_jstor_json_dat = JSON.parse(file_jstor);
        var file_jstor_json = {};

        file_jstor_json.synth_type = this.name;
        file_jstor_json.version = this.synth.version;
        file_jstor_json.file_name = file_name;
        file_jstor_json.params = file_jstor_json_dat;

        var file_jstor_json_string = JSON.stringify(file_jstor_json,null,2);
        return file_jstor_json_string;
    }
    /*********************/
    /* Event Handlers    */
    /*********************/

    template_clicked(template_name) {
        console.log("Template clicked: " + template_name);
        var template_data = null;
        for (var i = 0; i < this.synth.templates.length; i++) {
            if (this.synth.templates[i][2] == template_name) {
                template_data = this.synth.templates[i];
                break;
            }
        }
        // special behaviour - if you hit 'mutate', then have the new file-name be
        // based on the existing one.
        var file_name = template_name==="mutate_params"?this.get_current_file_name():template_data[3];
        this.synth[template_data[2]].bind(this.synth)();
        this.create_new_sound_from_params(file_name, this.synth.params);
    }

    create_new_sound_clicked(event) {
        this.create_new_sound = event.target.checked;
        SaveLoad.save_all_collections();
        console.log("Create new sound: " + this.create_new_sound);
    }

    play_on_change_clicked(event) {
        console.log("Play on change clicked");
        this.play_on_change = event.target.checked;
        SaveLoad.save_all_collections();
    }

    play_button_clicked() {
        console.log("Play button clicked");
        this.play_sound();
    }

    slider_changed(param_name, value) {
        console.log("Slider changed " + param_name + " to " + value);
        this.synth.set_param(param_name, value);
        this.parameter_changed();
    }

    update_param_visibility() {
        if(!this.synth.param_is_hidden)return;
        for(const [name,slider] of Object.entries(this.sliders)){
            const row=slider.sliderElem.closest('tr');
            if(row)row.hidden=this.synth.param_is_hidden(name);
        }
    }

    parameter_changed() {
        this.update_param_visibility();
        for (const editor of Object.values(this.text_controls || {})) editor.update();
        if (this.selected_file_index < 0) {
            this.create_new_sound_from_params("Sfx", this.synth.params, true);
            return;
        } else {
            this.files[this.selected_file_index][1] = JSON.stringify(this.synth.params);
            this.update_ablements();
        }
        if (this.play_on_change) this.play_sound();
        else {
            this.synth.generate_sound();
            this.redraw_waveform();
        }
        if (this.custom_editor) this.custom_editor.update();
        SaveLoad.save_all_collections();
    }

    volume_slider_changed(value) {
        this.slider_changed("masterVolume", value);
    }

    export_wav_button_clicked() {            
        var wav_uri = this.synth.generate_sound_uri();

        const a = document.createElement('a');
        a.href = wav_uri;
        a.download = this.files[this.selected_file_index][0]+".wav";
        a.click();
        a.remove();
    }

    

    async export_all_button_clicked() {
        console.log("Export all button clicked");

        var zip = new JSZip();

        //show export dialog
        var export_dialog = document.getElementById("export-dialog");
        export_dialog.showModal();
        var progress_bar = document.getElementById("export-progress");
        var download_link = document.getElementById("export-download-link");
        var export_progress_text = document.getElementById("export-progress-text");
        //hide download link
        download_link.style.display = "none";
        //set progress to 0
        progress_bar.value = 0;
        var file_count = 0;
        for (var i = 0; i < tabs.length; i++) {
            file_count += tabs[i].files.length;
        }
        progress_bar.max = file_count+1;
        
        var progress_bar_val=0;

        //each entry is [filename, blob]
        var generated_files =[];

        //for all tabs
        for (var i = 0; i < tabs.length; i++) {
            var tab = tabs[i];
            var selected_file_index = tab.selected_file_index;
            var folder = zip.folder(tab.name);
            //for all files in the tab
            for (var j = 0; j < tab.files.length; j++) {
                let file = tab.files[j];
                //get blob
                let sound_name = file[0];
                export_progress_text.innerText = progress_bar_val + "/" + file_count + "(generating " + sound_name + ")";
                let params = JSON.parse(file[1]);

                tab.synth.apply_params(params);
                tab.synth.generate_sound();
                //pause a bit
                await new Promise(resolve => setTimeout(resolve, 10));

                let datauri = tab.synth.generate_sound_uri();
                var cropped_datauri = datauri.split(",")[1];
                folder.file(sound_name+".wav", cropped_datauri, {base64: true});
                progress_bar_val++;
                progress_bar.value = progress_bar_val;
            }
            //reload selected_file_index in that tab when we're done
            {
                let file = tab.files[selected_file_index];
                let sound_name = file[0];
                let params = JSON.parse(file[1]);
                tab.synth.apply_params(params);
                tab.synth.generate_sound();
            }            
        }

        console.log("Generated files: " + generated_files.length);
        export_progress_text.innerText = "generating zip file...";
        //create a zip file
        zip.generateAsync({type:"blob"}).then(function(content) {
            download_link.href = URL.createObjectURL(content);
            download_link.style.display = "block";
            progress_bar.value = progress_bar.max;
            export_progress_text.innerText = "zip file generated!";
        });
    }

    save_bfxr_button_clicked() {
        console.log("Save bfxr button clicked");
        //save current params as bfxr        
        var file_jstor_json_string = this.serialize_params();
        var file_name = this.files[this.selected_file_index][0]+".bfxr";
        //save file to local computer
        var a = document.createElement('a');
        a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(file_jstor_json_string);
        a.download = file_name;
        a.click();
    }

    save_bfxrcol_button_clicked() {
        console.log("Save bfxrcol button clicked");
        var save_str = SaveLoad.serialize_collection();
        var a = document.createElement('a');
        a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(save_str);
        a.download = 'collection.bcol';
        a.click();
    }

    open_data_button_clicked() {
        console.log("Load data button clicked");

        //open file dialog, with .bfxr .bcol accepted   
        var file_input = document.createElement("input");
        file_input.type = "file";
        file_input.accept = ".bfxr,.bcol";
        file_input.multiple = false;
        file_input.addEventListener("change", (event) => {
            console.log("File selected: " + event.target.files[0].name);
            var file = event.target.files[0];
            var reader = new FileReader();
            reader.onload = (event) => {
                //if extension is .bfxr
                if (file.name.endsWith(".bfxr")){
                    SaveLoad.load_serialized_synth(event.target.result);
                } else if (file.name.endsWith(".bcol")){
                    SaveLoad.load_serialized_collection(event.target.result);
                }
            };
            reader.readAsText(file);
        });
        file_input.click();
    }

    mix_sound() {
        const mix=tabs.find(tab=>tab.name==='Mixr');
        if(!mix)return;
        const sources=mix.synth.get_sources();
        const slot=!sources[0]?0:!sources[1]?1:-1;
        mix.set_active_tab();
        if(slot<0){
            const params={...mix.synth.default_params(),masterVolume:mix.synth.params.masterVolume};
            mix.create_new_sound_from_params('Mix',params,true);
        }
        mix.synth.set_source(slot<0?0:slot,this.synth,this.get_current_file_name());
        mix.parameter_changed();
    }

    layer_in_stackr() {
        const stack=tabs.find(tab=>tab.name==='Stackr');
        if(!stack || !stack.synth.add_source(this.synth,this.get_current_file_name()))return;
        stack.set_active_tab();
        stack.parameter_changed();
    }

    copy_button_clicked() {
        console.log("Copy button clicked");
        var file_jstor_json_string = this.serialize_params();
        navigator.clipboard.writeText(file_jstor_json_string);
    }

    paste_button_clicked() {
        //load from clipboard
        navigator.clipboard.readText().then(text => {
            SaveLoad.load_serialized_synth(text);
        });
    }

    copy_link_button_clicked() {
        console.log("Copy link button clicked");
        var file_dat = this.files[this.selected_file_index];
        var file_name = file_dat[0];
        var file_jstor = file_dat[1];
        var params_parsed = this.synth.params;
        var file_jstor_json_string = SaveLoad.shallow_dict_serialize(this.name, file_name, params_parsed);
        //need to escape it so it can be used as a url parameter
        var file_jstor_json_string_escaped = encodeURIComponent(file_jstor_json_string);
        var current_url = window.location.href;
        //strip the query string
        var current_url_without_query = current_url.split("?")[0];
        //add the file_jstor_json_string_escaped to the url
        var new_url = current_url_without_query + "?sfx=" + file_jstor_json_string_escaped;
        //copy to clipboard
        navigator.clipboard.writeText(new_url);        
    }


    clear_all_button_clicked() {
        //need to confirm with user
        if (confirm("Are you sure you want to clear all data in this synth (THIS DELETES ALL SOUNDS FROM THIS TAB)?")) {
            console.log("Clear all button clicked");
            this.files = [];
            this.selected_file_index = -1;
            this.update_ui();
            SaveLoad.save_all_collections();
        }
    }

    about_button_clicked() {
        console.log("About button clicked");
        var about_dialog = document.getElementById("about-dialog");
        about_dialog.showModal();
    }
    
    apply_sfx() {
        if (this.files[this.selected_file_index][2] === this.files[this.selected_file_index][1]){
            return;
        }
        console.log("Apply sfx");
        this.files[this.selected_file_index][2] = this.files[this.selected_file_index][1];
        //remove modified_filename
        var file_item = document.getElementById(this.name + "_file_list").children[this.selected_file_index];
        var file_name_span = file_item.children[0];
        file_name_span.classList.remove("modified_filename");
        this.update_ablements();
        SaveLoad.save_all_collections();
    }

    revert_sfx() {
        if (this.files[this.selected_file_index][2] === this.files[this.selected_file_index][1]){
            return;
        }
        console.log("Revert sfx");
        var synth_params_json = this.files[this.selected_file_index][2];
        var synth_params = JSON.parse(synth_params_json);
        this.synth.apply_params(synth_params);
        this.files[this.selected_file_index][1] = synth_params_json;
        //add modified_filename
        var file_item = document.getElementById(this.name + "_file_list").children[this.selected_file_index];
        var file_name_span = file_item.children[0];
        file_name_span.classList.add("modified_filename");
        this.update_ui_params();
        this.update_ablements();
        if (this.play_on_change){
            this.play_sound();
        }
        SaveLoad.save_all_collections();
    }

    duplicate_sfx() {
        console.log("Duplicate sfx");
        if (this.selected_file_index===-1){
            //load from current params
            var file_name = "Sfx";
            var file_jstor = JSON.stringify(this.synth.params);
            var new_file_name = this.find_unique_filename(file_name);
            var new_file_dat = [new_file_name, file_jstor, file_jstor];
            //insert after current file
            this.files.splice(this.selected_file_index + 1, 0, new_file_dat);
            this.selected_file_index++;
            this.update_ui();
        } else {
            var cur_file_dat = this.files[this.selected_file_index];
            var file_name = cur_file_dat[0];
            var file_jstor = cur_file_dat[1];
            var new_file_name = this.find_unique_filename(file_name);
            var new_file_dat = [new_file_name, file_jstor, file_jstor];
            //insert after current file
            this.files.splice(this.selected_file_index + 1, 0, new_file_dat);
            this.selected_file_index++;
            this.update_ui();
        }
        SaveLoad.save_all_collections();
    }

    lock_param_clicked(node, param_name, value) {
        console.log("Lock param " + param_name + " clickedwith value " + value);
        value = !value;
        if (value) {
            node.classList.add("unlocked");
        } else {
            node.classList.remove("unlocked");
        }
        this.synth.locked_params[param_name]=!value;
        if (this.custom_editor) this.custom_editor.update();
        SaveLoad.save_all_collections();
    }

    button_grid_button_clicked(node, param_name, button_index,value) {
        console.log("Button grid button clicked for " + param_name + " with value " + value);
        var conatiner_uid = this.name + "_button_grid_" + param_name;
        for (var i = 0; i < node.parentElement.children.length; i++) {
            var selected = button_index === i;
            var child = node.parentElement.children[i];
            if (selected){
                child.classList.add("selected");
                child.disabled = true;
            } else {
                child.classList.remove("selected");
                child.disabled = false;
            }
        }
        this.synth.set_param(param_name, value);
        this.parameter_changed();
    }

    file_item_click(file_name,target) {
        console.log("File item clicked: " + file_name);
        var file_changed = this.set_selected_file(file_name);
        if (file_changed) {
            if (this.play_on_change) this.play_sound();
            else {
                this.synth.generate_sound();
                this.redraw_waveform();
            }
            SaveLoad.save_all_collections();
        }
    }

    file_item_renamed(file_name,new_name) {
        var file_name_index = -1;
        for (var i = 0; i < this.files.length; i++) {
            if (this.files[i][0] == file_name) {
                file_name_index = i;
                break;
            }
        }
        new_name = this.find_unique_filename(new_name,file_name_index);
        this.files[file_name_index][0] = new_name;
        console.log("File item renamed: " + file_name + " to " + new_name);
        SaveLoad.save_all_collections();
        return new_name;
    }

    play_sound(){
        this.synth.play();
        this.redraw_waveform();
        for (const editor of Object.values(this.text_controls || {})) editor.play();
    }

    redraw_waveform(){
        var canvas = document.getElementById(this.name + "_waveform_canvas");
        var context2d = canvas.getContext("2d");
        //clear
        context2d.clearRect(0, 0, canvas.width, canvas.height);
        this.synth.drawWaveform(context2d);
    }

    on_key_down(event){
        var gobbled=false;
        console.log(this.name + " sKey down: " + event.key);

        //check if the tab is focused
        if (this.active){
            //ignore if currently typing in the filename (into a file_item_name contenteditable has focus)
            if (document.activeElement.isContentEditable || document.activeElement.classList.contains("file_item_name") ||
                ["SELECT", "TEXTAREA", "INPUT"].includes(document.activeElement.tagName)){
                return;
            }
            var key_upper_case = event.key.toUpperCase();
            console.log(this.name + " Key down: " + event.key);
            var mod_key = event.ctrlKey || event.metaKey;
            switch (key_upper_case){
                //ctrl+c
                case "C":
                    if (mod_key){
                        this.copy_button_clicked();
                        gobbled=true;
                    }
                    break;  
                case "V":
                    if (mod_key){
                        this.paste_button_clicked();
                        gobbled=true;
                    }
                    break;
                case "S":
                    if (mod_key){
                        this.save_bfxr_button_clicked();
                        gobbled=true;
                    }
                    break;
                case "E":
                    if (mod_key){
                        this.export_wav_button_clicked();
                        gobbled=true;
                    }
                    break;
                case "O":
                    if (mod_key){
                        this.load_data_button_clicked();
                        gobbled=true;
                    } 
                    break;
                case "L":
                    if (!mod_key){
                        this.toggle_all_locks();
                        gobbled=true;
                    }
                    break;
                case "ENTER":
                case "NUMPADENTER":
                case " ":
                    //if button/link not focussed
                    if (!mod_key){
                        var node_name_lowercase = document.activeElement.nodeName.toLowerCase();
                        if (node_name_lowercase!=="button" && node_name_lowercase!=="a"){
                            this.play_sound();
                            gobbled=true;
                        }
                    }
                    break;
            }
        }
        if (gobbled){
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
        return true;
    }
}
