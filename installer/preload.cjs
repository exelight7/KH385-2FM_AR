const {contextBridge, ipcRenderer} = require('electron');
contextBridge.exposeInMainWorld('days', {
  initial: () => ipcRenderer.invoke('initial'),
  choose: () => ipcRenderer.invoke('choose'),
  operate: (folder, action) => ipcRenderer.invoke('operate', {folder, action}),
  releases: () => ipcRenderer.invoke('releases'),
  onProgress: fn => ipcRenderer.on('progress', (_event, value) => fn(value))
});
