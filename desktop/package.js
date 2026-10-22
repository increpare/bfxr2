// An unpacked runtime avoids extracting a portable archive at every launch.
const fs = require('node:fs');
const path = require('node:path');
require('./build');

const root = path.resolve(__dirname, '..');
const target = path.join(root, 'dist', 'Bfxr95');
const electronExecutable = require('electron');
const runtime = process.platform === 'darwin' ? path.resolve(path.dirname(electronExecutable), '../../..') : path.dirname(electronExecutable);
fs.mkdirSync(target, { recursive: true });
let resources, executable;
if (process.platform === 'darwin') {
  const bundle = path.join(target, 'Bfxr.app');
  fs.rmSync(bundle, { recursive: true, force: true });
  // Framework symlinks must stay relative, or codesign rejects them as unsealed contents.
  fs.cpSync(path.join(runtime, 'Electron.app'), bundle, { recursive: true, verbatimSymlinks: true });
  const plist = path.join(bundle, 'Contents', 'Info.plist');
  fs.writeFileSync(plist, fs.readFileSync(plist, 'utf8').replaceAll('com.github.Electron', 'net.bfxr.desktop').replace(/(<key>CFBundle(?:DisplayName|Name)<\/key>\s*<string>)Electron(<\/string>)/g, '$1Bfxr$2'));
  resources = path.join(bundle, 'Contents', 'Resources');
  executable = bundle;
} else {
  const binary = process.platform === 'win32' ? 'electron.exe' : 'electron';
  const name = process.platform === 'win32' ? 'Bfxr.exe' : 'bfxr';
  fs.cpSync(runtime, target, { recursive: true, filter: source => path.basename(source) !== binary });
  executable = path.join(target, name);
  fs.copyFileSync(path.join(runtime, binary), executable);
  if (process.platform !== 'win32') fs.chmodSync(executable, 0o755);
  resources = path.join(target, 'resources');
}
const app = path.join(resources, 'app');
fs.mkdirSync(path.join(app, 'desktop'), { recursive: true });
for (const name of ['main.js', 'preload.js', 'build']) fs.cpSync(path.join(__dirname, name), path.join(app, 'desktop', name), { recursive: true });
const pkg = require('../package.json');
fs.writeFileSync(path.join(app, 'package.json'), JSON.stringify({ name: 'bfxr95', productName: 'Bfxr', version: pkg.version, main: 'desktop/main.js', license: pkg.license }));
fs.copyFileSync(path.join(root, 'LICENSE'), path.join(app, 'LICENSE'));
if (process.platform === 'darwin') require('node:child_process').execFileSync('codesign', ['--force', '--deep', '--sign', '-', executable]);
console.log('Ready: ' + executable);
