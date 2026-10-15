const { app, BrowserWindow, ipcMain, shell, Menu } = require('electron');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const fs = require('node:fs');

app.setName('Bfxr95');
app.setPath('userData', process.env.BFXR_TEST_PROFILE || path.join(app.getPath('appData'), 'Bfxr95'));
app.commandLine.appendSwitch('disable-lcd-text');
const entry = path.join(__dirname, 'build', 'index.html');
const entryURL = pathToFileURL(entry).href;
let win;

function external(url) {
  try { if (['https:', 'http:'].includes(new URL(url).protocol)) shell.openExternal(url); } catch {}
}
function createWindow() {
  win = new BrowserWindow({
    width: 1040, height: 800, minWidth: 760, minHeight: 560,
    frame: false, show: false, backgroundColor: '#c0c0c0',
    title: 'Bfxr — Sound Effects', icon: path.join(__dirname, 'build', 'favicon.ico'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, sandbox: true, nodeIntegration: false }
  });
  win.removeMenu();
  win.once('ready-to-show', () => win.show());
  for (const event of ['maximize', 'unmaximize', 'focus', 'blur']) {
    win.on(event, () => win.webContents.send('window-state', { maximized: win.isMaximized(), focused: win.isFocused() }));
  }
  win.webContents.setWindowOpenHandler(({ url }) => { external(url); return { action: 'deny' }; });
  win.webContents.on('will-navigate', (event, url) => { if (url !== entryURL) { event.preventDefault(); external(url); } });
  win.webContents.session.setPermissionRequestHandler((contents, permission, callback) => callback(contents === win.webContents && ['clipboard-read', 'clipboard-sanitized-write'].includes(permission)));
  win.webContents.session.on('will-download', (_event, item) => {
    item.setSaveDialogOptions({ title: 'Save ' + item.getFilename(), defaultPath: path.join(app.getPath('documents'), item.getFilename()) });
    item.once('done', (_event, state) => {
      if (!win.isDestroyed()) win.webContents.send('download-result', state === 'completed' ? 'Saved ' + item.getFilename() : state === 'cancelled' ? 'Save cancelled.' : 'Could not save the file.');
    });
  });
  win.loadFile(entry);
}

ipcMain.on('window-command', (event, command) => {
  if (!win || event.sender !== win.webContents || event.senderFrame !== win.webContents.mainFrame) return;
  if (command === 'minimize') win.minimize();
  if (command === 'maximize') win.isMaximized() ? win.unmaximize() : win.maximize();
  if (command === 'close') win.close();
});
app.whenReady().then(() => {
  if (!fs.existsSync(entry)) throw new Error('Run npm run build:desktop before starting Bfxr.');
  Menu.setApplicationMenu(null);
  createWindow();
});
app.on('window-all-closed', () => app.quit());
