# تعريب KINGDOM HEARTS 358/2 Days

نسخة Steam ضمن HD 1.5+2.5 ReMIX. آخر إصدار: **2.0.0**. التعريب: **EXELIGHT7**.

[تحميل آخر إصدار](https://github.com/exelight7/KH385-2FM_AR/releases/tag/v2.0.0) · [المشاكل والتحسينات](release-notes.md)

## التحميل

| النظام | الملف |
|---|---|
| Windows | [مثبت التعريب](https://github.com/exelight7/KH385-2FM_AR/releases/download/v2.0.0/Days-Arabic-Setup-2.0.0.exe) · [إلغاء التعريب](https://github.com/exelight7/KH385-2FM_AR/releases/download/v2.0.0/Days-Arabic-Uninstall-2.0.0.exe) |
| Linux / Steam Deck | [AppImage](https://github.com/exelight7/KH385-2FM_AR/releases/download/v2.0.0/Days-Arabic-2.0.0.AppImage) |

أغلق اللعبة ومشغل المجموعة، ثم شغل المثبت واختر مجلد اللعبة. اختر English للنص داخل اللعبة وأعد تشغيلها. على Linux امنح AppImage صلاحية التنفيذ؛ قد تحتاج FUSE 2.

لإلغاء التعريب استخدم برنامج الإلغاء أو الزر داخل المثبت. احتفظ بمجلد `.days-arabic-backup`؛ فهو نسخة ملفات Days الأصلية. التحديث يدعم النسخ المنشورة من 0.1.0 حتى 1.0.2.

## ما الجديد وما بقي

تعريب 2461 نصا، وخط Noto Sans Arabic SemiBold أوضح بحافة أخف، ومعد لمنع الفواصل بين الحروف المتصلة، مع ضبط المسافات وترجمة «إعدادات اللعبة». لا إعادة ترميز للفيديو.

لم يُختبر الإصدار على كل المشاهد داخل اللعبة؛ مشهد يوم 96 دون لقطة جديدة. بعض الكتابات داخل الصور إنجليزية، وLinux لم يختبر داخل اللعبة. لا يوجد ضمان لحل كل التعليقات والكراشات السابقة. أرسل صورة واسم المشهد عند الإبلاغ عن مشكلة.

هذا المشروع خاص بـ358/2 Days؛ لا يتضمن تعريب KH2 أو KH3 أو تثبيت محمل لهما.

## البناء والترخيص

داخل `installer`: نفذ `npm ci` ثم `npm test` ثم `npm run build:win` أو `npm run build:linux`. ينشر GitHub Actions البرامج عند تحديث رقم الإصدار. الحزمة تحتوي فروق XOR فقط وتتطلب النسخة الأصلية المطابقة من اللعبة. [تفاصيل الأدوات](technical/README.md).

الكود GPL-3.0. خطا Noto وIBM Plex برخصة OFL المرفقة. حقوق اللعبة والشخصيات والعلامات لأصحابها؛ المشروع مستقل عن Disney وSQUARE ENIX. أدوات الأصول: [OpenKH](https://github.com/OpenKH/OpenKh) و[LittleBitUA](https://github.com/LittleBitUA/KINGDOM-HEARTS-LOCALIZATION-TOOL).
