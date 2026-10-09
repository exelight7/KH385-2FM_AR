const fs = require('node:fs/promises');
const {createReadStream} = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const zlib = require('node:zlib');

const names = ['Mare.hed', 'Mare.pkg'];
const exists = async p => fs.access(p).then(() => true, () => false);
async function hash(p) {
  const h = crypto.createHash('sha256');
  for await (const chunk of createReadStream(p)) h.update(chunk);
  return h.digest('hex');
}
async function matches(p, expected) {
  return (await fs.stat(p).catch(() => null))?.size === expected.bytes && await hash(p) === expected.sha256;
}
async function loadPatch(dir) {
  const m = JSON.parse(await fs.readFile(path.join(dir, 'manifest.json'), 'utf8'));
  if (m.format !== 2 || m.delta?.file !== 'tail.gz' || !Array.isArray(m.delta.baseSegments) || !Array.isArray(m.hedChanges)) throw Error('حزمة تعريب غير صالحة.');
  for (const n of names) for (const group of ['source', 'target', ...(m.previous ? ['previous'] : [])]) {
    const v = m[group]?.[n];
    if (!Number.isSafeInteger(v?.bytes) || v.bytes < 0 || !/^[a-f0-9]{64}$/.test(v.sha256)) throw Error('بيانات التحقق غير صالحة.');
  }
  if (m.source['Mare.hed'].bytes !== m.target['Mare.hed'].bytes || m.target['Mare.pkg'].bytes - m.source['Mare.pkg'].bytes !== m.tail.bytes) throw Error('أحجام الحزمة غير متطابقة.');
  if (!Number.isSafeInteger(m.delta.bytes) || m.delta.bytes <= 0 || m.delta.bytes > 64 * 1024 * 1024 || m.delta.bytes !== m.tail.bytes || !/^[a-f0-9]{64}$/.test(m.delta.sha256) || !/^[a-f0-9]{64}$/.test(m.tail.sha256)) throw Error('بيانات الفروق غير صالحة.');
  let end = 0;
  for (const s of m.delta.baseSegments) {
    if (![s.sourceOffset, s.tailOffset, s.bytes].every(Number.isSafeInteger) || s.sourceOffset < 0 || s.tailOffset < end || s.bytes <= 0 || s.sourceOffset + s.bytes > m.source['Mare.pkg'].bytes || s.tailOffset + s.bytes > m.delta.bytes) throw Error('نطاق فروق غير صالح.');
    end = s.tailOffset + s.bytes;
  }
  for (const c of m.hedChanges) if (!Number.isSafeInteger(c.offset) || c.offset < 0 || c.offset + 32 > m.source['Mare.hed'].bytes || !/^[a-f0-9]{64}$/.test(c.before) || !/^[a-f0-9]{64}$/.test(c.after)) throw Error('تعديل فهرس غير صالح.');
  return m;
}
async function resolveImage(folder) {
  if (!folder || typeof folder !== 'string') throw Error('اختر مجلد اللعبة أولا.');
  const candidate = await exists(path.join(folder, 'Mare.hed')) || await exists(path.join(folder, 'Mare.pkg')) || await exists(path.join(folder, '.days-arabic-backup/transaction/journal.json')) ? folder : path.join(folder, 'Image');
  const real = await fs.realpath(candidate).catch(() => { throw Error('مجلد Image غير موجود في المسار المحدد.'); });
  for (const n of names) {
    const st = await fs.lstat(path.join(real, n)).catch(async e => {
      if (e.code === 'ENOENT' && await exists(path.join(real, '.days-arabic-backup/transaction/journal.json'))) return null;
      throw e;
    });
    if (!st) continue; // A journal can recover a crash between the two rename calls.
    if (!st.isFile() || st.isSymbolicLink()) throw Error('اختر ملفات اللعبة الأصلية مباشرة.');
  }
  return real;
}
async function writeJournal(file, value) {
  const temp = file + '.next';
  const handle = await fs.open(temp, 'w');
  try { await handle.writeFile(JSON.stringify(value)); await handle.sync(); } finally { await handle.close(); }
  await fs.rename(temp, file);
}
async function recover(image, backup, m) {
  const tx = path.join(backup, 'transaction'), journalPath = path.join(tx, 'journal.json');
  if (!await exists(journalPath)) return;
  const j = JSON.parse(await fs.readFile(journalPath, 'utf8'));
  const groups = ['source', 'target', ...(m.previous ? ['previous'] : [])];
  if (!groups.includes(j.before) || !groups.includes(j.after)) throw Error('سجل الاسترجاع غير صالح.');
  if (j.committed) {
    for (const n of names) if (!await matches(path.join(image, n), m[j.after][n])) throw Error('تغيرت ملفات اللعبة بعد العملية؛ يلزم فحص يدوي.');
  } else {
    // Validate the whole pair before touching either file during crash recovery.
    for (const n of names) {
      const prev = path.join(tx, n + '.previous'), current = path.join(image, n);
      if (await exists(prev)) {
        if (!await matches(prev, m[j.before][n])) throw Error('نسخة الاسترجاع غير سليمة.');
        if (await exists(current) && !await matches(current, m[j.before][n]) && !await matches(current, m[j.after][n])) throw Error('تعديل خارجي أثناء العملية؛ تم إيقاف الاسترجاع.');
      } else if (!await matches(current, m[j.before][n])) throw Error('تعذر استرجاع العملية السابقة بأمان.');
    }
    for (const n of names) {
      const prev = path.join(tx, n + '.previous');
      if (await exists(prev)) { await fs.rm(path.join(image, n), {force: true}); await fs.rename(prev, path.join(image, n)); }
    }
  }
  await fs.rm(tx, {recursive: true, force: true});
}
async function classify(image, m) {
  if ((await Promise.all(names.map(n => matches(path.join(image, n), m.source[n])))).every(Boolean)) return 'source';
  if ((await Promise.all(names.map(n => matches(path.join(image, n), m.target[n])))).every(Boolean)) return 'target';
  if (m.previous && (await Promise.all(names.map(n => matches(path.join(image, n), m.previous[n])))).every(Boolean)) return 'previous';
  throw Error('نسخة اللعبة مختلفة أو عليها تعديل آخر. لن يتم استبدال ملفاتها. هذه الحزمة لنسخة Steam الإنجليزية المحددة.');
}
async function operate({folder, patchDir, action, progress = () => {}, checkRunning = async () => false, fault}) {
  if (!['install', 'uninstall'].includes(action)) throw Error('عملية غير صالحة.');
  const m = await loadPatch(patchDir), image = await resolveImage(folder);
  if (await checkRunning()) throw Error('أغلق KINGDOM HEARTS قبل بدء العملية.');
  const lockPath = path.join(image, '.days-arabic.lock');
  let lock;
  try { lock = await fs.open(lockPath, 'wx'); }
  catch (e) {
    if (e.code !== 'EEXIST') throw e;
    const previous = JSON.parse(await fs.readFile(lockPath, 'utf8').catch(() => '{}'));
    let alive = true;
    if (Number.isInteger(previous.pid) && previous.pid > 0) {
      try { process.kill(previous.pid, 0); } catch (check) { if (check.code === 'ESRCH') alive = false; }
    }
    if (alive) throw Error('هناك مثبت آخر يعمل. أغلقه ثم أعد المحاولة. إذا انقطع أثناء إنشاء القفل، احذف ملف .days-arabic.lock من مجلد Image بعد إغلاق المثبتات.');
    await fs.rm(lockPath);
    lock = await fs.open(lockPath, 'wx');
  }
  await lock.writeFile(JSON.stringify({pid: process.pid}));
  const backup = path.join(image, '.days-arabic-backup'), tx = path.join(backup, 'transaction');
  try {
    progress(5, 'فحص الملفات واسترجاع أي عملية منقطعة…');
    await recover(image, backup, m);
    const before = await classify(image, m), after = action === 'install' ? 'target' : 'source';
    if (before === after) return {status: 'unchanged', action, folder: path.dirname(image)};
    if (await checkRunning()) throw Error('أغلق اللعبة أولا.');
    const space = await fs.statfs(image);
    const needed = m.source['Mare.pkg'].bytes * (await exists(path.join(backup, 'Mare.pkg')) ? 1.1 : 2.1);
    if (Number(space.bavail) * Number(space.bsize) < needed) throw Error('المساحة الحرة غير كافية. وفر نحو 6 غيغابايت.');
    await fs.mkdir(backup, {recursive: true});
    progress(15, 'حفظ النسخة الأصلية والتحقق منها…');
    for (const n of names) {
      const dest = path.join(backup, n);
      if (!await exists(dest)) {
        if (before !== 'source') throw Error('النسخة الأصلية الاحتياطية مفقودة؛ أوقفنا الإلغاء لحماية اللعبة.');
        // A failed copy is not promoted to the permanent backup name.
        const tmp = dest + '.copying';
        await fs.copyFile(path.join(image, n), tmp);
        if (!await matches(tmp, m.source[n])) throw Error('فشل التحقق من النسخة الأصلية.');
        await fs.rename(tmp, dest);
      }
      if (!await matches(dest, m.source[n])) throw Error('النسخة الاحتياطية مختلفة؛ لن تتم الكتابة فوقها.');
    }
    await fs.mkdir(tx, {recursive: true});
    progress(35, action === 'install' ? 'تجهيز الحوار والخط العربي…' : 'تجهيز استرجاع النسخة الأصلية…');
    for (const n of names) await fs.copyFile(path.join(backup, n), path.join(tx, n));
    if (action === 'install') {
      const tail = zlib.gunzipSync(await fs.readFile(path.join(patchDir, m.delta.file)), {maxOutputLength: m.delta.bytes});
      if (tail.length !== m.delta.bytes || crypto.createHash('sha256').update(tail).digest('hex') !== m.delta.sha256) throw Error('ملف التعريب تالف؛ لم تتغير اللعبة.');
      const original = await fs.open(path.join(backup, 'Mare.pkg'), 'r');
      try {
        for (const s of m.delta.baseSegments) {
          const base = Buffer.alloc(s.bytes);
          let filled = 0;
          while (filled < base.length) {
            const {bytesRead} = await original.read(base, filled, base.length - filled, s.sourceOffset + filled);
            if (!bytesRead) throw Error('ملف اللعبة الأصلي غير مكتمل.');
            filled += bytesRead;
          }
          for (let i = 0; i < base.length; i++) tail[s.tailOffset + i] ^= base[i];
        }
      } finally { await original.close(); }
      if (crypto.createHash('sha256').update(tail).digest('hex') !== m.tail.sha256) throw Error('فشل بناء التعريب من ملفات اللعبة الأصلية.');
      await fs.appendFile(path.join(tx, 'Mare.pkg'), tail);
      const hed = await fs.readFile(path.join(tx, 'Mare.hed'));
      for (const c of m.hedChanges) {
        if (hed.subarray(c.offset, c.offset + 32).toString('hex') !== c.before) throw Error('الفهرس لا يطابق النسخة المدعومة.');
        Buffer.from(c.after, 'hex').copy(hed, c.offset);
      }
      await fs.writeFile(path.join(tx, 'Mare.hed'), hed);
    }
    progress(65, 'التحقق من الحزمة قبل تطبيقها…');
    for (const n of names) if (!await matches(path.join(tx, n), m[after][n])) throw Error('فشل التحقق النهائي؛ لم تتغير اللعبة.');
    if (await checkRunning()) throw Error('بدأت اللعبة أثناء التجهيز. أغلقها وأعد المحاولة.');
    if (await classify(image, m) !== before) throw Error('تغيرت ملفات اللعبة أثناء التجهيز. أوقف تحديث Steam وأعد المحاولة.');
    const journal = {before, after, committed: false};
    await writeJournal(path.join(tx, 'journal.json'), journal);
    try {
      progress(85, 'تطبيق الملفات…');
      for (const n of names) {
        await fs.rename(path.join(image, n), path.join(tx, n + '.previous'));
        await fs.rename(path.join(tx, n), path.join(image, n));
        if (fault) await fault(n);
      }
      for (const n of names) if (!await matches(path.join(image, n), m[after][n])) throw Error('فشل التحقق بعد التطبيق.');
      journal.committed = true;
      await writeJournal(path.join(tx, 'journal.json'), journal);
    } catch (e) { await recover(image, backup, m); throw e; }
    await fs.rm(tx, {recursive: true, force: true});
    progress(100, action === 'install' ? 'تم تثبيت الدفعة التجريبية.' : 'تم استرجاع الملفات الأصلية.');
    return {status: 'complete', action, folder: path.dirname(image)};
  } finally {
    await lock.close(); await fs.rm(lockPath, {force: true});
  }
}
module.exports = {hash, matches, loadPatch, resolveImage, operate};
