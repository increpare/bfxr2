fs = require('fs')

eval(fs.readFileSync('js/synth_params.js', 'utf8'));

console.log(SYNTH_SPECS);