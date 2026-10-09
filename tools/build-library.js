// Build-time tools only: the emitted scripts need no Node, packages or assets.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const UglifyJS = require('uglify-js');
const root = path.resolve(__dirname, '..');
const read = file => fs.readFileSync(path.join(root, file), 'utf8');

function compileTerrains() {
    const context = vm.createContext({console});
    vm.runInContext(read('js/audio/puredata_modules.js') + '\n' + read('js/audio/puredata_parser.js'), context);
    return 'const puredata_functions = {\n' + Object.entries(context.puredata_functions)
        .map(([name, fn]) => JSON.stringify(name) + ': ' + fn.toString()).join(',\n') + '\n};';
}

function buildLibrary() {
    const excluded = new Set(['js/audio/audio_globals.js', 'js/audio/RealizedSound.js',
        'js/audio/riffwave.js', 'js/audio/puredata_modules.js', 'js/audio/puredata_parser.js']);
    const files = [...read('index.html').matchAll(/<script src="([^"]+)"/g)]
        .map(m => m[1].split('?')[0])
        .filter(file => file === 'js/globals.js' || file.startsWith('js/audio/') || file.startsWith('js/synths/'))
        .filter(file => !excluded.has(file));
    const bases = new Set(['templates', 'SynthBase', 'PresetSynth', 'PresetFamily', 'TransfxrPresets']);
    const engines = files.filter(file => file.startsWith('js/synths/'))
        .map(file => path.basename(file, '.js')).filter(name => !bases.has(name));
    const notice = '/*! bfxrlib — standalone sound synthesis\n' + read('LICENSE') +
        '\nIncludes SfxrSynth-derived DSP, Copyright 2010 Thomas Vian, Apache License 2.0.\n' +
        'Modified for Bfxr/Bfxr2 by Stephen Lavelle.\n' + read('js/library/APACHE-2.0.txt') + '\n' +
        'Includes Adventure Kid Waveforms (CC0), converted by Brad Roy.\n' +
        'https://www.adventurekid.se/akrt/waveforms/adventure-kid-waveforms/\n*/\n';
    const prelude = '"use strict";\n' +
        '// Keep existing seeded generators private, including Math.clamp and Math.random.\n' +
        'const Math = Object.create(global.Math);\n' +
        'const SAMPLE_RATE = 44100, CONVERSION_FACTOR = 2 * Math.PI / SAMPLE_RATE;\n';
    const runtime = ['sounds', 'cache', 'playback', 'api'].map(name => read('js/library/' + name + '.js')).join('\n');
    const body = prelude + files.map(file => '// ' + file + '\n' + read(file)).join('\n') + '\n' +
        compileTerrains() + '\nconst BFXR_SYNTHS = {' + engines.join(',') + '};\n' + runtime;
    // Mixr also identifies source constructors by name; preserve those names when minifying.
    const result = UglifyJS.minify(body, {compress: {toplevel: true}, mangle: {toplevel: true}, keep_fnames: true});
    if (result.error) throw result.error;
    // Wrap after compression so optimizer assumptions cannot hoist private helpers globally.
    const wrap = code => (notice + '(function(global) {\n' + code + '\n})(globalThis);\n')
        .replace(/[\t ]+$/gm, '');
    return {readable: wrap(body), minified: wrap(result.code)};
}

if (require.main === module) {
    const result = buildLibrary();
    fs.mkdirSync(path.join(root, 'lib'), {recursive: true});
    fs.writeFileSync(path.join(root, 'lib/bfxrlib.js'), result.readable);
    fs.writeFileSync(path.join(root, 'lib/bfxrlib.min.js'), result.minified);
    console.log('bfxrlib: ' + Buffer.byteLength(result.minified) + ' bytes minified, ' +
        zlib.gzipSync(result.minified).length + ' bytes gzip');
}

module.exports = {buildLibrary};
