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

function showDropZone() {
    const dropZone = document.getElementById('dropzone');
	dropZone.style.display = "flex";
}
function hideDropZone() {
    const dropZone = document.getElementById('dropzone');
    dropZone.style.display = "none";
}

function register_drop_handlers(){
    
    const dropZone = document;
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();        
        hideDropZone();
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
        e.dataTransfer.dropEffect = "copy   ";
        e.preventDefault();
        showDropZone();
    });

    document.addEventListener('dragleave', (e) => {
        console.log("dragleave");
        console.log(e);
        if (e.fromElement==null){
            hideDropZone();
        }
    });

    
    document.addEventListener('dragend', (e) => {
        hideDropZone();
    });

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
