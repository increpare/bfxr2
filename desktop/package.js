// An unpacked runtime avoids extracting a portable archive at every launch.
const fs = require('node:fs');
const path = require('node:path');
require('./build');
if (process.platform !== 'win32') throw new Error('The Windows desktop package must be built on Windows.');
const root = path.resolve(__dirname, '..');
const target = path.join(root, 'dist', 'Bfxr95');
const runtime = path.dirname(require('electron'));
fs.mkdirSync(target, { recursive: true });
fs.cpSync(runtime, target, { recursive: true, filter: source => path.basename(source) !== 'electron.exe' });
fs.copyFileSync(path.join(runtime, 'electron.exe'), path.join(target, 'Bfxr.exe'));
const app = path.join(target, 'resources', 'app');
fs.mkdirSync(path.join(app, 'desktop'), { recursive: true });
for (const name of ['main.js', 'preload.js', 'build']) fs.cpSync(path.join(__dirname, name), path.join(app, 'desktop', name), { recursive: true });
const pkg = require('../package.json');
fs.writeFileSync(path.join(app, 'package.json'), JSON.stringify({ name: 'bfxr95', productName: 'Bfxr', version: pkg.version, main: 'desktop/main.js', license: pkg.license }));
fs.copyFileSync(path.join(root, 'LICENSE'), path.join(app, 'LICENSE'));
console.log('Ready: ' + path.join(target, 'Bfxr.exe'));
