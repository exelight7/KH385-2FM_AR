// Exercise the shipped patch on a disposable copy, never on the live game.
const fs = require('node:fs/promises');
const path = require('node:path');
const {operate, hash, loadPatch} = require('../installer/core.cjs');
const root = path.resolve(__dirname, '..');
const original = 'C:/Program Files (x86)/Steam/steamapps/common/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Image';
(async () => {
  const scratch = await fs.mkdtemp(path.join(__dirname, 'installer-e2e-'));
  const image = path.join(scratch, 'Image');
  await fs.mkdir(image);
  const patchDir = path.join(root, 'installer/patch'), m = await loadPatch(patchDir);
  const checks = [];
  for (const n of Object.keys(m.source)) {
    if (await hash(path.join(original, n)) !== m.source[n].sha256) throw Error('Live source differs; aborting fixture test');
    await fs.copyFile(path.join(original, n), path.join(image, n));
  }
  const progress = (percent, text) => console.log(percent, text);
  await operate({folder: scratch, patchDir, action: 'install', progress});
  for (const n of Object.keys(m.target)) {
    if (await hash(path.join(image, n)) !== m.target[n].sha256) throw Error('Fixture install mismatch');
  }
  checks.push('full-size install hashes match verified archive');
  await operate({folder: scratch, patchDir, action: 'uninstall', progress});
  for (const n of Object.keys(m.source)) {
    if (await hash(path.join(image, n)) !== m.source[n].sha256) throw Error('Fixture restore mismatch');
    if (await hash(path.join(original, n)) !== m.source[n].sha256) throw Error('Live source changed');
  }
  checks.push('full-size uninstall restores byte-identical originals', 'live game original hashes unchanged');
  await fs.writeFile(path.join(root, 'out/apps/full-archive-verification.json'), JSON.stringify({date: new Date().toISOString(), translatedEntries: m.translatedEntries, checks, gameInstalled: false, inGameVerified: false}, null, 2));
  // mkdtemp created this exact disposable directory within technical/.
  if (path.dirname(scratch) !== __dirname || !path.basename(scratch).startsWith('installer-e2e-')) throw Error('Unexpected cleanup target');
  await fs.rm(scratch, {recursive: true, force: true});
  console.log(JSON.stringify(checks));
})().catch(e => { console.error(e); process.exitCode = 1; });
