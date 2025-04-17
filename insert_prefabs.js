/* this script loads up all the json files
 prefabs/[synth]/prefabname.bcol
 and generates a javscript dictionary of the form
 prefabs = {
    "synthname": {
        "prefabname": data
    }
}

*/

const fs = require('fs');
const path = require('path');

const prefab_dir = './prefabs';
const prefabs = {};

// Read all synth directories
const synthDirs = fs.readdirSync(prefab_dir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

// Process each synth directory
synthDirs.forEach(synthDir => {
    const synthPath = path.join(prefab_dir, synthDir);
    prefabs[synthDir] = {};
    
    // Read all prefab files in the synth directory
    const prefabFiles = fs.readdirSync(synthPath, { withFileTypes: true })
        .filter(dirent => dirent.isFile())
        .map(dirent => dirent.name);
    
    // Process each prefab file
    prefabFiles.forEach(prefabFile => {
        const filePath = path.join(synthPath, prefabFile);
        const fileContent = fs.readFileSync(filePath, 'utf8');
        try {
            const jsonContent = JSON.parse(fileContent);
            // Extract prefab name without extension
            const prefabName = path.parse(prefabFile).name;
            var files = jsonContent[synthDir].files;
            // a file is an array of [name, data, data]
            //delete the third element

            //then convert to a dictionary
            var dict = {};
            files.forEach(file => {
                dict[file[0]] = JSON.parse(file[1]);
            });

            // dict is a dictionary of variety_suffix: dict
            // we want to collate all the data for each variety to give
            // [ variety, merged_dict (with arrays as keys)]
            // (we don't care about the suffix)
            var varieties = {};
            for (var variety_name_extended in dict) {
                var variety_name = variety_name_extended.split("_")[0];
                var variety_data = dict[variety_name_extended];
                var this_variety = {};
                if (!varieties[variety_name]) {
                    varieties[variety_name] = {};     
                    this_variety = varieties[variety_name];
                    for (var key in variety_data) {
                        this_variety[key] = [variety_data[key]];
                    }                    
                    continue;
                }
                this_variety = varieties[variety_name];
                for (var key in variety_data) {
                    this_variety[key].push(variety_data[key]);
                }
            }
            prefabs[synthDir][prefabName] = varieties;

        } catch (error) {
            console.error(`Error parsing ${filePath}: ${error.message}`);
        }
    });
});

// Write the prefabs to a file
fs.writeFileSync('./js/synths/prefabs.js', `const PREFAB_JSON = ${JSON.stringify(prefabs, null, 2)};`);


