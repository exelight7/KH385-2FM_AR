const {app, BrowserWindow, ipcMain, dialog, shell} = require('electron');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {execFile} = require('node:child_process');
const {promisify} = require('node:util');
const {operate, loadPatch, isGameRunning} = require('./core.cjs');
const run = promisify(execFile);
const patchDir = app.isPackaged ? path.join(process.resourcesPath, 'patch') : path.join(__dirname, 'patch');
const releases = 'https://github.com/exelight7/KH385-2FM_AR/releases';
let win, busy = false;

async function running() {
  const windows = process.platform === 'win32';
  const {stdout} = await run(windows ? 'tasklist' : 'ps', windows ? ['/FO', 'CSV', '/NH'] : ['-eo', 'args='], {windowsHide: true, maxBuffer: 4 * 1024 * 1024});
  return isGameRunning(stdout);
}
async function detect() {
  const game = 'KINGDOM HEARTS -HD 1.5+2.5 ReMIX-';
  let roots = process.platform === 'win32'
    ? ['C:\\Program Files (x86)\\Steam', 'C:\\Program Files\\Steam', ...['C', 'D', 'E', 'F', 'G'].map(d => d + ':\\SteamLibrary')]
    : [path.join(os.homedir(), '.steam/steam'), path.join(os.homedir(), '.local/share/Steam'), path.join(os.homedir(), '.var/app/com.valvesoftware.Steam/data/Steam')];
  for (const root of [...roots]) {
    try {
      const text = await fs.readFile(path.join(root, 'steamapps/libraryfolders.vdf'), 'utf8');
      for (const match of text.matchAll(/"path"\s+"([^"]+)"/g)) roots.push(match[1].replaceAll('\\\\', '\\'));
    } catch (e) { if (!['ENOENT', 'ENOTDIR'].includes(e.code)) console.warn('Steam library unavailable:', e.code); }
  }
  for (const root of new Set(roots)) {
    const p = path.join(root, 'steamapps/common', game);
    if (await fs.access(path.join(p, 'Image/Mare.hed')).then(() => true, () => false)) return p;
  }
  return '';
}
app.requestSingleInstanceLock() || app.quit();
app.on('second-instance', () => { if (win) { win.show(); win.focus(); } });
app.on('window-all-closed', () => app.quit());
app.whenReady().then(() => {
  win = new BrowserWindow({width: 1060, height: 790, minWidth: 900, minHeight: 740, backgroundColor: '#080f20', autoHideMenuBar: true, icon: path.join(__dirname, 'assets/icon.png'), webPreferences: {preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true}});
  win.webContents.setWindowOpenHandler(() => ({action: 'deny'}));
  win.webContents.on('will-navigate', e => e.preventDefault());
  win.on('close', e => { if (busy) { e.preventDefault(); win.webContents.send('progress', {percent: 85, text: 'انتظر اكتمال العملية قبل إغلاق النافذة.'}); } });
  win.loadFile(path.join(__dirname, 'ui/index.html'));
});
ipcMain.handle('initial', async () => {
  const m = await loadPatch(patchDir);
  const executable = process.env.PORTABLE_EXECUTABLE_FILE || process.env.APPIMAGE || process.execPath;
  return {folder: await detect(), version: m.version, count: m.translatedEntries, total: m.totalVisibleEntries, uninstall: /uninstall/i.test(path.basename(executable)) || process.argv.includes('--uninstall')};
});
ipcMain.handle('choose', async () => {
  if (busy) return null;
  const r = await dialog.showOpenDialog(win, {title: 'اختر مجلد KINGDOM HEARTS أو مجلد Image', properties: ['openDirectory']});
  return r.canceled ? null : r.filePaths[0];
});
ipcMain.handle('releases', () => shell.openExternal(releases));
ipcMain.handle('operate', async (_event, {folder, action} = {}) => {
  if (busy) return {ok: false, error: 'انتظر اكتمال العملية الحالية.'};
  busy = true;
  try {
    const result = await operate({folder, action, patchDir, checkRunning: running, progress: (percent, text) => win.webContents.send('progress', {percent, text})});
    return {ok: true, ...result};
  } catch (e) {
    return {ok: false, error: e.code === 'EACCES' || e.code === 'EPERM' ? 'لا توجد صلاحية للكتابة. أغلق اللعبة، ثم شغّل المثبت كمسؤول على Windows أو اختر مكتبة Steam التي تملكها على Linux.' : e.message};
  } finally { busy = false; }
});
