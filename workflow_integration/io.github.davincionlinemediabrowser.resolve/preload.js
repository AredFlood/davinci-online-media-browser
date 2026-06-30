const { contextBridge, ipcRenderer } = require('electron/renderer');

contextBridge.exposeInMainWorld('resolveWfi', {
  isAvailable: true,
  getRuntimeInfo: () => ipcRenderer.invoke('runtime:getInfo'),
  getProjectInfo: () => ipcRenderer.invoke('resolve:getProjectInfo'),
  importMedia: (payload) => ipcRenderer.invoke('resolve:importMedia', payload),
});
