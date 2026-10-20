const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const output = path.join(__dirname, 'build');
fs.mkdirSync(output, { recursive: true });
for (const name of ['js', 'css', 'img', 'favicon.ico', 'favicon.svg', 'LICENSE']) {
  fs.cpSync(path.join(root, name), path.join(output, name), { recursive: true });
}
for (const name of ['renderer.js', 'win95.css', 'caption-controls.css', 'assets', 'NOTICES.txt']) {
  fs.cpSync(path.join(__dirname, name), path.join(output, name), { recursive: true });
}
// Compile bundled PureData terrain patches at build time, so the renderer
// needs no runtime eval permission (the shared library uses the same approach).
const context = vm.createContext({ console });
vm.runInContext(fs.readFileSync(path.join(root,'js/audio/puredata_modules.js'),'utf8') + '\n' + fs.readFileSync(path.join(root,'js/audio/puredata_parser.js'),'utf8'),context);
fs.writeFileSync(path.join(output,'js/audio/puredata_parser.js'), 'const puredata_functions = {\n' + Object.entries(context.puredata_functions).map(([name, fn]) => JSON.stringify(name) + ': ' + fn.toString()).join(',\n') + '\n};');
let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
html = html.replace('<head>', `<head>
        <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">`)
  .replace('</head>', '<link rel="stylesheet" href="win95.css"><link rel="stylesheet" href="caption-controls.css"><script src="renderer.js" defer></script></head>')
  .replace('<body>', '<body class="desktop95">')
  .replace('<title>Bfxr.  Make sound effects for your games.</title>', '<title>Bfxr — Sound Effects</title>');
fs.writeFileSync(path.join(output, 'index.html'), html);
console.log('Desktop assets ready.');
