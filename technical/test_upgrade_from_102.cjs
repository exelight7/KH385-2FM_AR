// Upgrade a disposable full-size copy from published 1.0.2, never the live game.
// Run after decode_release.py and before export; expects out/v1.0.2/patch-backup.
const fs = require('node:fs/promises');
const path = require('node:path');
const {operate, hash, loadPatch} = require('../installer/core.cjs');
const root = path.resolve(__dirname, '..');
const original = process.env.DAYS_GAME_IMAGE || 'C:/Program Files (x86)/Steam/steamapps/common/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Image';
const untouched = async () => {
  const backup = path.join(original, '.days-arabic-backup');
  return await fs.stat(backup).then(() => backup, () => original);
};
const verify = async (image, files, label) => {
  for (const n of Object.keys(files)) if (await hash(path.join(image, n)) !== files[n].sha256) throw Error(label + ' mismatch: ' + n);
};
(async () => {
  const oldPatch = path.join(root, 'out/v1.0.2/patch-backup'), newPatch = path.join(root, 'installer/patch');
  const old = await loadPatch(oldPatch), next = await loadPatch(newPatch);
  const scratch = await fs.mkdtemp(path.join(__dirname, 'installer-e2e-'));
  const image = path.join(scratch, 'Image');
  await fs.mkdir(image);
  try {
    const base = await untouched();
    for (const n of Object.keys(next.source)) await fs.copyFile(path.join(base, n), path.join(image, n));
    await verify(image, next.source, 'original');
    await operate({folder: scratch, patchDir: oldPatch, action: 'install'});
    await verify(image, old.target, '1.0.2');
    await operate({folder: scratch, patchDir: newPatch, action: 'install'});
    await verify(image, next.target, next.version);
    await operate({folder: scratch, patchDir: newPatch, action: 'uninstall'});
    await verify(image, next.source, 'restored original');
    await verify(base, next.source, 'original copy');
    console.log(JSON.stringify({upgradeFrom: old.version, to: next.version, target: next.target, restoredByteIdentical: true, liveGameUnchanged: true}, null, 2));
  } finally {
    await fs.rm(scratch, {recursive: true, force: true});
  }
})().catch(e => { console.error(e); process.exit(1); });
