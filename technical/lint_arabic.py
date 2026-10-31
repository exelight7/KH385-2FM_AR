"""Mechanical Arabic spelling checks for a translation version; prints every hit."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['ct00100', 'ctmn000', 'ctmn200', 'ctmn300', 'cthd000', 'cthd050', 'cthd100', 'cthd300', 'cthd800']
TAG = re.compile(r'\{[^}]+\}|\[(?:BGTRANS|WAIT)[^]]*\]')
L = '[ء-ي]'


def word(pattern):
    return rf'(?<!{L})(?:{pattern})(?!{L})'


# Each hit is wrong however the sentence continues.
ERRORS = {
    'double space': r' {2,}',
    'space before punctuation': r' [،؛؟.!,:]',
    'no space after Arabic punctuation': rf'[،؛؟]{L}',
    'Latin comma or question mark': r'[,?;]',
    'repeated punctuation': r'،،|\.{4,}|\?\?|؟؟؟|!!!',
    'trailing space': r' +(?:\n|$)',
    'tatweel, vowel mark or zero-width character': '[ـً-ٟ‌-‏]',
    'presentation form': '[ﭐ-﷿ﹰ-ﻼ]',
    'Persian or Urdu letter': '[کیھہ]',
    'taa marbuta inside a word': f'ة{L}',
    'alif maqsura inside a word': f'ى{L}',
    'missing hamza': word('الى|اذا|انا|انت|انتم|انها|انني|اننا|اين|ايضا|احد|اخر|اخرى|اكثر|اول|اولا|لان|لانه|لانني|لاننا|الان|اعرف|اريد|اظن|امر|امام|اكبر|اقل|اصبح|اخي|اخت|اسف|اسفة'),
    'wrong letter in a common word': word('هاذا|هاذه|ذالك|لاكن|هاكذا|اللذي|اللتي|الذى|التى|فى|مسئول|شئ|ماالذي|مالذي'),
    'hamza spelling': rf'شيئ(?!ا|{L})|مسؤل|{L}+اءا(?!{L})',
    'إن needed after قال': word('قال|قالت|قالوا|يقول|تقول|أقول|يقولون|القول|قلت|قلنا|يقال') + r'\s+' + word('أن|أنه|أنها|أنني|أننا|أنك|أنهم|أنهما'),
    'أن needed after a verb of knowing': word('أظن|أعتقد|أعرف|أعلم|ظننت|أدرك|تظن|يظن|نعرف|يعرف|عرفت|علمت') + r'\s+' + word('إن|إنه|إنها|إنني|إننا|إنك|إنهم'),
    'indicative after لم': word('لم') + r'\s+' + word('يبقى|تبقى|يأتي|تأتي|يرى|ترى|أرى|يكون|تكون|أكون|ينسى|تنسى|أنسى|يدري|أدري|يجري|يبدو|تبدو|يقول|تقول|يعود|تعود|أعود|يستطيع|تستطيع|أستطيع'),
    'jussive after لن': word('لن') + r'\s+' + word('أكن|تكن|يكن|أقل|تقل|يقل|أعد|تعد|يعد|أنس|تنس|يبق|تبق|أبق'),
    'Kingdom Hearts is masculine': r'هارتس\s+العظيمة|وها\s+هي\s+كينغدوم',
    'name spelled off-glossary': word('اكسل|روكسس|روكسا|زيون|سيون|كيبليد|الكيبليد|زمناس|سيكس|لارسين|كايرى|ريكوو'),
}
# Possibly fine: علي and إلي are valid words, so these only list rows to reread.
NOTES = {
    'علي before a definite noun': word('علي') + r'\s+ال',
    'إلي before a definite noun': word('إلي') + r'\s+ال',
}


def main(version):
    errors = notes = rows = 0
    words = set()
    for name in NAMES:
        for row in json.loads((ROOT / f'translation/v{version}/{name}.json').read_text(encoding='utf-8')):
            if row['arabic'] == row['english']:
                continue
            rows += 1
            quotes = row['arabic'].count('«'), row['arabic'].count('»')
            # A placeholder keeps the spaces around tags from reading as errors.
            text = TAG.sub('', row['arabic'])
            words.update(re.findall(rf'{L}+', text))
            if quotes[0] != quotes[1]:
                errors += 1
                print(f'ERROR unbalanced quotes [{name} {row["id"]}]')
            for label, pattern in ERRORS.items():
                for hit in re.finditer(pattern, text):
                    errors += 1
                    print(f'ERROR {label} [{name} {row["id"]}] {hit.group()!r}')
            for label, pattern in NOTES.items():
                if re.search(pattern, text):
                    notes += 1
                    print(f'NOTE {label} [{name} {row["id"]}]')
    print(json.dumps({'version': version, 'rows': rows, 'uniqueWords': len(words), 'errors': errors, 'notes': notes}))
    return errors


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(1 if main(sys.argv[1] if len(sys.argv) > 1 else '2.0.0') else 0)
