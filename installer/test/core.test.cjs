const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const {operate} = require('../core.cjs');
const info = b => ({bytes: b.length, sha256: crypto.createHash('sha256').update(b).digest('hex')});
async function fixture(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'days-installer-test-'));
  t.after(() => fs.rm(root, {recursive: true, force: true}));
  const game = path.join(root, 'game'), image = path.join(game, 'Image'), patch = path.join(root, 'patch');
  await fs.mkdir(image, {recursive: true}); await fs.mkdir(patch);
  const hed = Buffer.alloc(96, 33), pkg = Buffer.from('original encrypted package fixture');
  const changedHed = Buffer.from(hed); changedHed.fill(44, 32, 64);
  const tail = Buffer.from('arabic replacement blocks fixture');
  const delta = Buffer.from(tail);
  for (let i = 0; i < 12; i++) delta[3 + i] ^= pkg[2 + i];
  const m = {format: 2, source: {'Mare.hed': info(hed), 'Mare.pkg': info(pkg)}, target: {'Mare.hed': info(changedHed), 'Mare.pkg': info(Buffer.concat([pkg, tail]))}, tail: info(tail), delta: {file: 'tail.gz', ...info(delta), baseSegments: [{sourceOffset: 2, tailOffset: 3, bytes: 12}]}, hedChanges: [{offset: 32, before: hed.subarray(32, 64).toString('hex'), after: changedHed.subarray(32, 64).toString('hex')}]};
  await fs.writeFile(path.join(image, 'Mare.hed'), hed); await fs.writeFile(path.join(image, 'Mare.pkg'), pkg);
  await fs.writeFile(path.join(patch, 'tail.gz'), zlib.gzipSync(delta)); await fs.writeFile(path.join(patch, 'manifest.json'), JSON.stringify(m));
  return {root, game, image, patch, m, hed, pkg, changedHed, args: {folder: game, patchDir: patch}};
}
test('install, repeat, uninstall and repeat preserve exact originals and backup', async t => {
  const f = await fixture(t);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'unchanged');
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.deepEqual(await fs.readFile(path.join(f.image, '.days-arabic-backup/Mare.pkg')), f.pkg);
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'unchanged');
});
test('unknown mod and running game are refused without creating backups', async t => {
  const f = await fixture(t);
  await assert.rejects(operate({...f.args, action: 'install', checkRunning: async () => true}), /أغلق/);
  await fs.appendFile(path.join(f.image, 'Mare.pkg'), 'other mod');
  await assert.rejects(operate({...f.args, action: 'install'}), /مختلفة/);
  await assert.rejects(fs.access(path.join(f.image, '.days-arabic-backup')));
});
test('corrupt payload is rejected before game files change', async t => {
  const f = await fixture(t);
  await fs.writeFile(path.join(f.patch, 'tail.gz'), zlib.gzipSync(Buffer.from('corrupt')));
  await assert.rejects(operate({...f.args, action: 'install'}), /تالف/);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
test('failure after first archive swap rolls the whole pair back', async t => {
  const f = await fixture(t);
  await assert.rejects(operate({...f.args, action: 'install', fault: async () => {throw Error('injected failure');}}), /injected/);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
});
test('damaged backup blocks uninstall and is never overwritten', async t => {
  const f = await fixture(t);
  await operate({...f.args, action: 'install'});
  const backup = path.join(f.image, '.days-arabic-backup/Mare.pkg');
  await fs.writeFile(backup, 'damaged backup');
  await assert.rejects(operate({...f.args, action: 'uninstall'}), /الاحتياطية مختلفة/);
  assert.equal(await fs.readFile(backup, 'utf8'), 'damaged backup');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
});
test('journal recovers crash with temporarily missing HED before retry', async t => {
  const f = await fixture(t), tx = path.join(f.image, '.days-arabic-backup/transaction');
  await fs.mkdir(tx, {recursive: true});
  await fs.rename(path.join(f.image, 'Mare.hed'), path.join(tx, 'Mare.hed.previous'));
  await fs.writeFile(path.join(tx, 'journal.json'), JSON.stringify({before: 'source', after: 'target', committed: false}));
  assert.equal((await operate({...f.args, folder: f.image, action: 'uninstall'})).status, 'unchanged');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
});
test('external update during staging is preserved and blocks archive replacement', async t => {
  const f = await fixture(t); let count = 0;
  const checkRunning = async () => {
    if (++count === 3) await fs.writeFile(path.join(f.image, 'Mare.hed'), 'external Steam update');
    return false;
  };
  await assert.rejects(operate({...f.args, action: 'install', checkRunning}), /مختلفة/);
  assert.equal(await fs.readFile(path.join(f.image, 'Mare.hed'), 'utf8'), 'external Steam update');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.deepEqual(await fs.readFile(path.join(f.image, '.days-arabic-backup/Mare.hed')), f.hed);
});

async function previousFixture(t) {
  const f = await fixture(t);
  const oldHed = Buffer.from(f.hed); oldHed.fill(77, 0, 32);
  const oldPkg = Buffer.concat([f.pkg, Buffer.from('version 0.1 fixture')]);
  f.m.previous = {'Mare.hed': info(oldHed), 'Mare.pkg': info(oldPkg)};
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  await fs.mkdir(path.join(f.image, '.days-arabic-backup'));
  for (const [n, b] of [['Mare.hed', f.hed], ['Mare.pkg', f.pkg]]) await fs.writeFile(path.join(f.image, '.days-arabic-backup', n), b);
  await fs.writeFile(path.join(f.image, 'Mare.hed'), oldHed);
  await fs.writeFile(path.join(f.image, 'Mare.pkg'), oldPkg);
  return {...f, oldHed, oldPkg};
}
test('upgrade from previous release and uninstall preserve original backups', async t => {
  const f = await previousFixture(t);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
test('failed upgrade restores previous release and retries successfully', async t => {
  const f = await previousFixture(t);
  await assert.rejects(operate({...f.args, action: 'install', fault: async () => {throw Error('upgrade failure');}}), /upgrade failure/);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.oldHed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.oldPkg);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
});
test('previous release journal recovers a missing HED before uninstall', async t => {
  const f = await previousFixture(t), tx = path.join(f.image, '.days-arabic-backup/transaction');
  await fs.mkdir(tx);
  await fs.rename(path.join(f.image, 'Mare.hed'), path.join(tx, 'Mare.hed.previous'));
  await fs.writeFile(path.join(tx, 'journal.json'), JSON.stringify({before: 'previous', after: 'target', committed: false}));
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
