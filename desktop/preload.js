const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('bfxrDesktop', {
  windowCommand: command => { if (['minimize', 'maximize', 'close'].includes(command)) ipcRenderer.send('window-command', command); },
  onWindowState: callback => ipcRenderer.on('window-state', (_event, state) => callback(state)),
  onDownload: callback => ipcRenderer.on('download-result', (_event, message) => callback(message))
});
