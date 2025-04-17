"use strict";

function register_tabs(){
    SaveLoad.load_all_collections();
    SaveLoad.collection_save_enabled=false;
    var bfxr_tab = new Tab(new Bfxr());   
    var footsteppr_tab = new Tab(new Footsteppr());
    // var transfxr_tab = new Tab(new Transfxr());
    SaveLoad.collection_save_enabled=true;
    set_tab_from_loaded_data();
    SaveLoad.save_all_collections();
}

function set_tab_from_loaded_data(){
    if (!SaveLoad.loaded_data){
        return;
    }
    var active_tab_index = SaveLoad.loaded_data.active_tab_index;
    if (active_tab_index>=0){
        tabs[active_tab_index].set_active_tab();
    }
}

function bfxr_draw_visualisation(params){

}

function bfxr_generate_sound(params){

}

window.onload = function(){
    register_tabs();
    SaveLoad.check_url_for_sfxr_params();
    register_drop_handlers();
}

function register_drop_handlers(){
    
    const dropZone = document.querySelector('body');
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();        
        //either file is a single .bcol file, or a list of .bfxr files
        if (e.dataTransfer.files.length===1 && e.dataTransfer.files[0].name.endsWith('.bcol')){
            var file = e.dataTransfer.files[0];
            var reader = new FileReader();
            reader.onload = (event) => {
                SaveLoad.load_serialized_collection(event.target.result);
                SaveLoad.save_all_collections();
            };
            reader.readAsText(file);
        } else {
            for (var i=0;i<e.dataTransfer.files.length;i++){
                if (e.dataTransfer.files[i].name.endsWith('.bfxr')){
                    var file = e.dataTransfer.files[i];
                    var reader = new FileReader();
                    reader.onload = (event) => {
                        SaveLoad.load_serialized_synth(event.target.result);
                        SaveLoad.save_all_collections();
                    };
                    reader.readAsText(file);
                } else {
                    console.error("Only .bfxr and .bcol files are supported, but you dropped a file with the following name: " + e.dataTransfer.files[i].name);
                }
            }
        }
    });

    // Add dragover event listener to prevent default browser behavior
    document.addEventListener('dragover', (e) => {
        e.preventDefault();
    });
}

function bfxr_preset_pickupcoin(){
    console.log("Pickup/Coin");
}

function bfxr_preset_lasershoot(){
    console.log("Laser/Shoot");
}

function bfxr_preset_explosion(){
    console.log("Explosion");
}

function bfxr_preset_powerup(){
    console.log("Powerup");
}

function bfxr_preset_hithurt(){
    console.log("Hit/Hurt");
}

function bfxr_preset_jump(){
    console.log("Jump");
}

function bfxr_preset_blipselect(){
    console.log("Blip/Select");
}

// Initialize dialog tab functionality
document.addEventListener('DOMContentLoaded', function() {
    // Tab handling for the about dialog
    const dialogTabs = document.querySelectorAll('.dialog-tab');
    
    dialogTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and content
            document.querySelectorAll('.dialog-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            // Add active class to current tab
            tab.classList.add('active');
            
            // Show corresponding content
            const tabContent = document.getElementById(tab.dataset.tab + '-tab');
            if (tabContent) {
                tabContent.classList.add('active');
            }
        });
    });
});
