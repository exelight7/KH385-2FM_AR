const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const {operate, isGameRunning} = require('../core.cjs');
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
for (const group of ['upgrade101', 'upgrade100']) test(`upgrade via ${group} preserves original backups and uninstalls exactly`, async t => {
  const f = await previousFixture(t);
  f.m[group] = f.m.previous;
  delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});

test('upgrade from previous release and uninstall preserve original backups', async t => {
  const f = await previousFixture(t);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});

test('upgrade from legacy release also preserves and restores exact original backups', async t => {
  const f = await previousFixture(t);
  f.m.legacy = f.m.previous;
  delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});

test('upgrade from older release retains the same verified original backup', async t => {
  const f = await previousFixture(t);
  f.m.older = f.m.previous;
  delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.deepEqual(await fs.readFile(path.join(f.image, '.days-arabic-backup/Mare.pkg')), f.pkg);
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

test('upgrade from the fourth historical release preserves the original backup', async t => {
  const f = await previousFixture(t);
  f.m.earlier = f.m.previous;
  delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  await operate({...f.args, action: 'install'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.deepEqual(await fs.readFile(path.join(f.image, '.days-arabic-backup/Mare.pkg')), f.pkg);
});

async function shiftedJournal(t, committed, descriptors = false) {
  const f = await previousFixture(t), tx = path.join(f.image, '.days-arabic-backup/transaction');
  const olderHed = Buffer.from(f.hed); olderHed.fill(88, 0, 32);
  const olderPkg = Buffer.concat([f.pkg, Buffer.from('older release fixture')]);
  f.m.older = {'Mare.hed': info(olderHed), 'Mare.pkg': info(olderPkg)};
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  await fs.mkdir(tx);
  await fs.writeFile(path.join(tx, 'Mare.hed.previous'), olderHed);
  await fs.writeFile(path.join(f.image, 'Mare.pkg'), committed ? f.oldPkg : olderPkg);
  if (committed) await fs.writeFile(path.join(tx, 'Mare.pkg.previous'), olderPkg);
  const journal = {before: 'previous', after: 'target', committed};
  if (descriptors) Object.assign(journal, {beforeFiles: f.m.older, afterFiles: f.m.previous});
  await fs.writeFile(path.join(tx, 'journal.json'), JSON.stringify(journal));
  return {...f, tx};
}
for (const committed of [false, true]) test(`legacy journal survives changed release slots (committed=${committed})`, async t => {
  const f = await shiftedJournal(t, committed);
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  await assert.rejects(fs.access(f.tx));
});
test('new journal binds file hashes across release slot changes', async t => {
  const f = await shiftedJournal(t, false, true);
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
test('recovery rejects an unknown external update before restoring either file', async t => {
  const f = await shiftedJournal(t, false, true);
  await fs.writeFile(path.join(f.image, 'Mare.hed'), 'external update');
  const beforePkg = await fs.readFile(path.join(f.image, 'Mare.pkg'));
  await assert.rejects(operate({...f.args, action: 'uninstall'}), /خارجي/);
  assert.equal(await fs.readFile(path.join(f.image, 'Mare.hed'), 'utf8'), 'external update');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), beforePkg);
  assert.ok(await fs.readFile(path.join(f.tx, 'Mare.hed.previous')));
});
test('backup junction cannot write outside the selected game', async t => {
  const f = await fixture(t), outside = path.join(f.root, 'outside');
  await fs.mkdir(outside);
  await fs.writeFile(path.join(outside, 'Mare.pkg'), 'unrelated file');
  await fs.symlink(outside, path.join(f.image, '.days-arabic-backup'), 'junction');
  await assert.rejects(operate({...f.args, action: 'install'}), /روابط/);
  await assert.rejects(fs.access(path.join(outside, 'Mare.hed')));
  assert.equal(await fs.readFile(path.join(outside, 'Mare.pkg'), 'utf8'), 'unrelated file');
});
test('transaction junction cannot overwrite unrelated files', async t => {
  const f = await previousFixture(t), outside = path.join(f.root, 'outside');
  await fs.mkdir(outside);
  await fs.writeFile(path.join(outside, 'Mare.hed'), 'unrelated file');
  await fs.symlink(outside, path.join(f.image, '.days-arabic-backup/transaction'), 'junction');
  await assert.rejects(operate({...f.args, action: 'install'}), /روابط/);
  assert.equal(await fs.readFile(path.join(outside, 'Mare.hed'), 'utf8'), 'unrelated file');
});
test('lock metadata failure releases the lock and permits retry', async t => {
  const f = await fixture(t), open = fs.open;
  const mock = t.mock.method(fs, 'open', async (...args) => {
    const handle = await open(...args);
    if (String(args[0]).endsWith('.days-arabic.lock')) {
      t.after(async () => { if (handle.fd !== -1) await handle.close(); });
      handle.writeFile = async () => { throw Object.assign(Error('injected disk full'), {code: 'ENOSPC'}); };
    }
    return handle;
  });
  await assert.rejects(operate({...f.args, action: 'install'}), /injected disk full/);
  mock.mock.restore();
  await assert.rejects(fs.access(path.join(f.image, '.days-arabic.lock')));
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
});
test('fifth historical release upgrades and restores the exact original', async t => {
  const f = await previousFixture(t);
  f.m.oldest = f.m.previous; delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  await operate({...f.args, action: 'install'});
  await operate({...f.args, action: 'uninstall'});
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
test('process detection covers the collection launcher without matching installer directory names', () => {
  for (const line of ['"KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe","123","Console"', 'wine /games/KINGDOM HEARTS/WaitTitleProject.exe', '"WaitTitleProject.exe","42"', '/games/KINGDOM HEARTS HD 1.5+2.5 ReMIX.exe']) assert.equal(isGameRunning(line), true, line);
  for (const line of ['wine /games/KINGDOM HEARTS -HD 1.5+2.5 ReMIX-/Days-Arabic-Setup-1.0.0.exe', '"explorer.exe","42"', '']) assert.equal(isGameRunning(line), false, line);
});

// The sixth historical release remains recognizable after adding 1.0.0.
test('sixth historical release upgrades and restores the exact original pair', async t => {
  const f = await previousFixture(t);
  f.m.ancient = f.m.previous;
  delete f.m.previous;
  await fs.writeFile(path.join(f.patch, 'manifest.json'), JSON.stringify(f.m));
  assert.equal((await operate({...f.args, action: 'install'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.changedHed);
  assert.equal((await operate({...f.args, action: 'uninstall'})).status, 'complete');
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.hed')), f.hed);
  assert.deepEqual(await fs.readFile(path.join(f.image, 'Mare.pkg')), f.pkg);
});
