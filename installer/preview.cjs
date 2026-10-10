// Render the real desktop UI for visual review. Does not call install/uninstall.
const {app, BrowserWindow, ipcMain} = require('electron');
const fs = require('node:fs/promises');
const path = require('node:path');
ipcMain.handle('initial', () => ({folder: 'C:\\Program Files (x86)\\Steam\\steamapps\\common\\KINGDOM HEARTS -HD 1.5+2.5 ReMIX-', version: require('./package.json').version, count: 1616, total: 2556, uninstall: false}));
app.whenReady().then(async () => {
  const win = new BrowserWindow({width: 1060, height: 790, show: false, useContentSize: true, webPreferences: {preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, sandbox: true}});
  await win.loadFile(path.join(__dirname, 'ui/index.html'));
  await new Promise(r => setTimeout(r, 500));
  const image = await win.webContents.capturePage();
  await fs.mkdir(path.join(__dirname, '../out/apps'), {recursive: true});
  await fs.writeFile(path.join(__dirname, '../out/apps/installer-preview.png'), image.toPNG());
  const iconWin = new BrowserWindow({width: 512, height: 512, show: false, useContentSize: true, transparent: true, webPreferences: {sandbox: true}});
  const svg = await fs.readFile(path.join(__dirname, 'assets/emblem.svg'), 'utf8');
  await iconWin.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent('<html style="background:transparent"><body style="margin:0">' + svg.replace('viewBox=', 'width="512" height="512" viewBox=') + '</body></html>'));
  await fs.writeFile(path.join(__dirname, 'assets/icon.png'), (await iconWin.webContents.capturePage()).toPNG());
  app.quit();
});
