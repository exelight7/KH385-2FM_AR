const $ = id => document.getElementById(id);
const controls = ['folder', 'choose', 'install', 'uninstall'];
function status(text, kind = '') { $('status').textContent = text; $('status').className = 'status ' + kind; }
function busy(value) { for (const id of controls) $(id).disabled = value; }
window.days.onProgress(({percent, text}) => { $('operation-track').hidden = false; $('bar').style.width = percent + '%'; status(text); });
$('choose').onclick = async () => { const p = await window.days.choose(); if (p) { $('folder').value = p; $('found').textContent = 'المجلد المختار'; } };
$('releases').onclick = () => window.days.releases();
async function operate(action) {
  if (!$('folder').value.trim()) return status('اختر مجلد اللعبة أولا.', 'error');
  busy(true); status('جارٍ فحص الملفات…');
  try {
    const r = await window.days.operate($('folder').value.trim(), action);
    if (!r.ok) return status(r.error, 'error');
    const message = action === 'install' ? 'تم تثبيت النصوص العربية والقوائم المصورة. أعد تشغيل اللعبة واختر English للنص.' : 'تم إلغاء التعريب واسترجاع ملفات اللعبة الأصلية.';
    status(r.status === 'unchanged' ? (action === 'install' ? 'هذه الدفعة مثبتة بالفعل.' : 'ملفات اللعبة أصلية بالفعل.') : message, 'success');
  } catch (e) { status('تعذر إكمال العملية: ' + e.message, 'error'); }
  finally { busy(false); }
}
$('install').onclick = () => operate('install');
$('uninstall').onclick = () => operate('uninstall');
window.days.initial().then(info => {
  $('folder').value = info.folder; $('version').textContent = info.version;
  $('count').textContent = info.count; $('total').textContent = info.total;
  document.querySelector('.translation-track i').style.width = (100 * info.count / info.total) + '%';
  $('found').textContent = info.folder ? 'تم العثور على نسخة Steam' : 'اختر مجلد Steam يدويًا';
  if (info.uninstall) { $('install').className = 'secondary'; $('uninstall').className = 'primary'; status('اضغط «إلغاء التعريب» لاسترجاع النسخة الأصلية.'); }
}).catch(e => { status('تعذر قراءة الحزمة: ' + e.message, 'error'); busy(true); });
