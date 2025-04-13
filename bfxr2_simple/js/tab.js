"use strict";

var tabs=[];
function Tab(tab_name) {    
    // Store tab name
    this.name = tab_name;

    // Create DOM elements
    var tab_bar = document.getElementById("tab_bar");
    var tab_page_container = document.getElementById("tab_page_manager");

    var first_tab = tab_bar.children.length==0;

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

    if (first_tab){
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

        
        var global_vol_id = tab_name + "_slider_global_vol";
        this.setup_slider(global_vol_container_div, global_vol_id,this.volume_slider_changed,true);

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
}

Tab.prototype.set_active_tab = function(){
    var tab_page = document.getElementById("tab_page_"+this.name);
    tab_page.classList.add("active_tab");
    var tab_buttons = document.getElementsByClassName("tab_button");
    for (var i = 0; i < tab_buttons.length; i++) {
      var tab_button = tab_buttons[i];  
      if (tab_button.id != "tab_button_"+this.name) {
        tab_button.classList.remove("active_tab");
      } else if (!tab_button.classList.contains("active_tab")) {
        tab_button.classList.add("active_tab");
      }
    }
    var tab_pages = document.getElementsByClassName("tab_page");
    for (var i = 0; i < tab_pages.length; i++) {
      var tab_page = tab_pages[i];
      if (tab_page.id != "tab_page_"+this.name) {
        tab_page.classList.remove("active_tab_page");
      } else if (!tab_page.classList.contains("active_tab_page")) {
        tab_page.classList.add("active_tab_page");
      }
    }
}

Tab.prototype.setup_slider = function(parent_node,slider_id,handler_fn,mini){
    var global_vol_input = document.createElement("input");
    global_vol_input.type = "text";
    global_vol_input.id = slider_id;
    parent_node.appendChild(global_vol_input);


    var slider = new Slider("#"+slider_id, {
        id: "instanced_"+slider_id,
        min: 0,
        max: 0.33,
        range: false,
        step: 0.0033,
        value: 0.231,
        ticks: [0, 0.033, 0.066, 0.099, 0.132, 0.165, 0.198, 0.231, 0.264, 0.29700000000000004, 0.33]
      });
      slider.sliderElem.className += " singleselect";
      slider.sliderElem.getElementsByClassName("slider-tick-container")[0].children[7].classList.add('defaulttick');

      if (mini===true){
        slider.sliderElem.classList.add('slidernarrow');
      }

      slider.on("slideStop", handler_fn);
}

Tab.prototype.add_button = function(button_id,button_text,button_handler,button_tooltip){
    var button = document.createElement("button");
    button.classList.add("normie_button");
    button.id = button_id;
    if (button_tooltip != undefined && button_tooltip != ""){
        var tooltip_tag = `<span class="data-tooltip">${button_tooltip}</span>`;
        button_text = tooltip_tag + button_text;
    }
    button.innerHTML = button_text;
    button.addEventListener("click", button_handler);
    return button;
}

Tab.prototype.add_preset = function (preset_name, button_tooltip, param_fn){
    var button = this.add_button(preset_name,preset_name,param_fn,button_tooltip);
    this.preset_list.appendChild(button);
}

Tab.prototype.finalize_elements = function(){    
    this.add_preset("Randomize", "Talking your life into your hands... (only modifies unlocked parameters)",this.randomize_params, );
    this.add_preset("Mutation", "Modify each unlocked parameter by a small wee amount... (only modifies unlocked parameters)",this.mutate_params, );
}

//called after adding all presets/parameters
Tab.prototype.finalize_layout = function(){
    this.finalize_elements();
}


Tab.prototype.preset_clicked = function(preset_name){
    console.log("Preset clicked: " + preset_name);
}

Tab.prototype.create_new_sound_clicked = function(){
    console.log("Create new sound clicked");
}

Tab.prototype.play_on_change_clicked = function(){
    console.log("Play on change clicked");
}

Tab.prototype.play_button_clicked = function(){
    console.log("Play button clicked");
}

Tab.prototype.volume_slider_changed = function(value){
    console.log("Volume slider changed to " + value);
}

Tab.prototype.export_wav_button_clicked = function(){
    console.log("Export wav button clicked");
}

Tab.prototype.export_all_button_clicked = function(){
    console.log("Export all button clicked");
}

Tab.prototype.save_bfxr_button_clicked = function(){
    console.log("Save bfxr button clicked");
}

Tab.prototype.save_bfxrcol_button_clicked = function(){
    console.log("Save bfxrcol button clicked");
}

Tab.prototype.copy_button_clicked = function(){
    console.log("Copy button clicked");
}

Tab.prototype.paste_button_clicked = function(){
    console.log("Paste button clicked");
}

Tab.prototype.copy_link_button_clicked = function(){
    console.log("Copy link button clicked");
}

Tab.prototype.about_button_clicked = function(){
    console.log("About button clicked");
}

Tab.prototype.randomize_params = function(){
    console.log("Randomize params");
}

Tab.prototype.mutate_params = function(){
    console.log("Mutate params");
}

Tab.prototype.apply_sfx = function(){
    console.log("Apply sfx");
}

Tab.prototype.revert_sfx = function(){
    console.log("Revert sfx");
}

Tab.prototype.duplicate_sfx = function(preset_name){
    console.log("Duplicate sfx");
}