"use strict";

function register_tabs(){
    SaveLoad.load_all_collections();
    SaveLoad.collection_save_enabled=false;
    // Display names are separate from the engine names used by saved sounds and links.
    const add_tab = synth => {
        const label = synth_display_name(synth.name);
        if (label !== synth.name) synth.display_name = label;
        return new Tab(synth);
    };
    var bfxr_tab = add_tab(new Bfxr());
    add_tab(new Footsteppr());
    add_tab(new Mixr());
    add_tab(new Transfxr());

    // Music and voices.
    add_tab(new Jinglr());
    add_tab(new Pluckr());
    add_tab(new Choirr());

    // Creatures and flocks.
    add_tab(new Crittr());
    add_tab(new Birdr());
    add_tab(new Swarmr());

    // Physical materials and impacts.
    add_tab(new Clonkr());
    add_tab(new Bouncr());
    add_tab(new Fractr());
    add_tab(new Boomr());
    add_tab(new Rustlr());
    add_tab(new Squishr());

    // Motion, machines and electronic effects.
    add_tab(new Machinr());
    add_tab(new Breathr());
    add_tab(new Whooshr());
    add_tab(new Signlr());
    add_tab(new Riftr());
    add_tab(new Zappr());
    add_tab(new Glitchr());
    SaveLoad.collection_save_enabled=true;
    set_tab_from_loaded_data();
    // New collections have no saved selection. Build only the visible panel.
    (tabs.find(tab => tab.active) || bfxr_tab).set_active_tab();
    SaveLoad.save_all_collections();
}

function set_tab_from_loaded_data(){
    if (!SaveLoad.loaded_data){
        return;
    }
    SaveLoad.restore_active_tab(SaveLoad.loaded_data);
}

function bfxr_draw_visualisation(params){

}

function bfxr_generate_sound(params){

}

document.addEventListener('DOMContentLoaded', function(){
    register_tabs();
    SaveLoad.check_url_for_sfxr_params();
    register_drop_handlers();
    register_background_fade();
});

function register_background_fade(){
    const panel = document.getElementById('main_container');
    const fadeStartDistance = 50;
    const update = () => {
        const bounds = panel.getBoundingClientRect();
        const width = document.documentElement.clientWidth;
        const height = document.documentElement.clientHeight;
        const stops = {
            '--fade-left-end': Math.max(1, bounds.left - fadeStartDistance),
            '--fade-right-start': Math.min(width - 1, bounds.right + fadeStartDistance),
            '--fade-top-end': Math.max(1, bounds.top - fadeStartDistance),
            '--fade-bottom-start': Math.min(height - 1, bounds.bottom + fadeStartDistance)
        };
        for (const [name, position] of Object.entries(stops)) {
            document.documentElement.style.setProperty(name, `${position}px`);
        }
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, {passive: true});
    new ResizeObserver(update).observe(panel);
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
