/* this script loads up all the json files
 templates/[synth]/templatesname.bcol
 and generates a javscript dictionary of the form
 templates = {
    "synthname": {
        "templatesname": data
    }
}

*/

const fs = require('fs');
const path = require('path');

const templates_dir = './templates';
const templates = {};

console.log("Inserting templates...");

// Read all synth directories
const synthDirs = fs.readdirSync(templates_dir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

// Process each synth directory
synthDirs.forEach(synthDir => {
    const synthPath = path.join(templates_dir, synthDir);
    templates[synthDir] = {};
    
    // Read all templates files in the synth directory
    const templatesFiles = fs.readdirSync(synthPath, { withFileTypes: true })
        .filter(dirent => dirent.isFile())
        .filter(dirent => path.extname(dirent.name) === '.bcop')
        .map(dirent => dirent.name);
    
    // Process each templates file
    templatesFiles.forEach(templatesFile => {
        const filePath = path.join(synthPath, templatesFile);
        const fileContent = fs.readFileSync(filePath, 'utf8');
        try {
            const jsonContent = JSON.parse(fileContent);
            // Extract templates name without extension
            const templatesName = path.parse(templatesFile).name;
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
                    var list = this_variety[key]
                    var new_value = variety_data[key];
                    if (list.indexOf(new_value) === -1) {
                        this_variety[key].push(new_value);
                    }
                }
            }
            templates[synthDir][templatesName] = varieties;

        } catch (error) {
            console.error(`Error parsing ${filePath}: ${error.message}`);
        }
    });
});

// Write the templates to a file
fs.writeFileSync('./js/synths/templates.js', `const TEMPLATES_JSON = ${JSON.stringify(templates, null, 2)};`);

console.log("Templates inserted.");