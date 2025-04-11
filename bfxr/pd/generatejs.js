//load all the .pd files in this directory, and output them as a dictionary to ../js/puredata_modules.js

const fs = require('fs');
const path = require('path');

const pdFiles = fs.readdirSync(path.join(__dirname, './'));

const pdModules = {};

pdFiles.forEach(file => {
    //extension has to be .pd
    if (!file.endsWith('.pd')){
        return;
    }
    const pdModule = fs.readFileSync(path.join(__dirname, file), 'utf8');

    const moduleName = path.basename(file, '.pd');
    pdModules[moduleName] = pdModule;
});

fs.writeFileSync(path.join(__dirname, '../js/puredata_modules.js'), `
const puredata_modules = ${JSON.stringify(pdModules)};
`);


