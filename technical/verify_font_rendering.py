"""Regression for COD-width sampling: inspect shipped pixels, not full cells.

These are offline zero-extra-spacing quads. The Days engine has not been
instrumented; user screenshots remain necessary for runtime approval.
"""
import hashlib
import json
from pathlib import Path
import struct
import unicodedata

import numpy as np
from PIL import Image, ImageDraw
from build_v030 import visual, TAG
from font_atlas import cod_entries

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ('1.0.0', '1.0.1')


def atlas(version, name):
    out = ROOT / f'out/v{version}'
    data = (out / f'payload/original/uk/font/{name}.tm2').read_bytes()
    manifest = json.loads((ROOT / f'technical/verification/v{version}-build.json').read_text(encoding='utf-8')) if version == '1.0.0' else json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    for ext in ('cod', 'tm2'):
        relative = f'original/uk/font/{name}.{ext}'
        expected = next(item['sha256'] for item in manifest['files'] if item['path'] == relative)
        assert hashlib.sha256((out / 'payload' / relative).read_bytes()).hexdigest() == expected
    _, palette_size, image_size, header = struct.unpack_from('<IIIH', data, 16)
    offset = 16 + header
    if palette_size:
        pixels = np.frombuffer(data[offset:offset+image_size], np.uint8).reshape(2048, 2048)
        palette = np.frombuffer(data[offset+image_size:offset+image_size+palette_size], np.uint8).reshape(256, 4)
        order = [(i & ~31) | ((i & 8) << 1) | ((i & 16) >> 1) | (i & 7) for i in range(256)]
        rgba = palette[order].copy()
        rgba[:, :3] = np.minimum(rgba[:, :3].astype(np.int32)*2, 255)
        pixels = rgba[pixels]
    else:
        pixels = np.frombuffer(data[offset:offset+image_size], np.uint8).reshape(2048, 2048, 4).copy()
        pixels[:, :, :3] = np.minimum(pixels[:, :, :3].astype(np.int32)*2, 255)
        pixels[:, :, 3] = np.minimum(pixels[:, :, 3].astype(np.int32)*2, 255)
    count = struct.unpack_from('<H', (ROOT / f'technical/extracted_mare/original/uk/font/{name}.inf').read_bytes())[0]
    entries = {e['id']: e for e in cod_entries((out / f'payload/original/uk/font/{name}.cod').read_bytes(), count)}
    donors = {chr(int(e['form'][2:], 16)): e['id'] for e in json.loads((out / 'allocation.json').read_text())}
    return {char: pixels[e['y']:e['y']+32, e['x']:e['x']+e['width']] for char, donor in donors.items() for e in [entries[donor]]}


def form(char):
    return unicodedata.decomposition(char).split(' ')[0]


def main():
    out = ROOT / 'out/v1.0.1'
    rows = []
    unchanged = {}
    for p in sorted((ROOT / 'translation/v1.0.1').glob('ct*.json')):
        before = ROOT / 'translation/v1.0.0' / p.name
        assert before.read_bytes() == p.read_bytes(), p.name
        unchanged[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        rows.extend(json.loads(p.read_text(encoding='utf-8')))
    pairs = set()
    for row in rows:
        for part in TAG.split(visual(row['arabic'])):
            if TAG.fullmatch(part):
                continue
            for a, b in zip(part, part[1:]):
                if form(a) in ('<final>', '<medial>') and form(b) in ('<initial>', '<medial>'):
                    pairs.add((a, b))
    report = {'version': '1.0.1', 'sampling': 'COD.width cropped quads; zero extra spacing',
              'runtimeVerified': False, 'textFilesByteIdenticalTo100': unchanged,
              'distinctAdjacentJoinPairs': len(pairs), 'fonts': {}}
    samples = ['هل حفظت ذلك يا روكساس؟', 'لا تقلق. سأحرص على أن يكون على قدر المهمة.',
               'تستخدم هذه اللعبة ميزة الحفظ التلقائي.', 'روكساس وشيون وديميكس وسايكس',
               'قال فيل إن التدريب يزداد مشقة كلما علت توقعاته.']
    sheet = Image.new('RGBA', (2240, 90+len(samples)*180), (70, 73, 82, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((16, 12), 'COD-WIDTH CROPPED QUADS / OFFLINE / 1.0.0 -> 1.0.1', fill='white')
    for font_index, name in enumerate(('eventfont', 'menufont')):
        report['fonts'][name] = {}
        for version_index, version in enumerate(VERSIONS):
            glyphs = atlas(version, name)
            failures = []
            minimum = 255
            for a, b in sorted(pairs):
                left, right = glyphs[a], glyphs[b]
                # White stroke (not just a black outline) must reach both
                # sides of the seam on the same baseline rows20 and21.
                def stroke(cell, column):
                    return cell[20:22, column, :3].max(axis=1).astype(np.int32)*cell[20:22, column, 3]//255
                ink = int(np.minimum(stroke(left, -1), stroke(right, 0)).min())
                minimum = min(minimum, ink)
                if ink < 200:
                    failures.append([f'U+{ord(a):04X}', f'U+{ord(b):04X}', ink])
            report['fonts'][name][version] = {'pairsChecked': len(pairs), 'brokenPairs': len(failures), 'minimumSeamInk': minimum, 'failureExamples': failures[:20]}
            if version == '1.0.1':
                assert not failures, (name, failures[:10])
            else:
                assert len(failures) == len(pairs), 'Frozen1.0.0 regression baseline changed'
            for index, sample in enumerate(samples):
                line = visual(sample)
                cells = [glyphs[c] for c in line]
                width = sum(c.shape[1] for c in cells)
                image = Image.new('RGBA', (width, 32))
                x = 0
                for cell in cells:
                    image.alpha_composite(Image.fromarray(cell), (x, 0))
                    x += cell.shape[1]
                y = 55+index*180+font_index*80
                draw.text((16+version_index*1120, y), name+' / '+version, fill='white')
                sheet.alpha_composite(image.resize((width*2, 64), Image.Resampling.NEAREST), (16+version_index*1120, y+15))
    sheet.convert('RGB').save(out / 'cod-cropped-comparison.png')
    (out / 'font-rendering-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({name: {v: {k:d[k] for k in ('pairsChecked','brokenPairs','minimumSeamInk')} for v,d in versions.items()} for name,versions in report['fonts'].items()}))


if __name__ == '__main__':
    main()
